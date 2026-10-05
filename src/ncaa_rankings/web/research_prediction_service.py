from __future__ import annotations

from dataclasses import dataclass
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Game, RankingSnapshot
from .prediction_service import (
    _entry_map,
    _monotonic_margin,
    _normal_cdf,
    fit_calibration,
)

DIVISION_I = ("FBS", "FCS")
HYBRID_VERSION = "hybrid_core_v1"
DEFAULT_TEAM_POINTS = 26.0
DEFAULT_PRIOR_GAMES = 3.0
RANK_MARGIN_WEIGHT = 0.40
OFFDEF_MARGIN_WEIGHT = 0.60


@dataclass(frozen=True, slots=True)
class ScoringProfile:
    offense: float
    defense: float
    games: int


@dataclass(frozen=True, slots=True)
class ResearchProjection:
    home_rank: int | None
    away_rank: int | None
    projected_home_points: float
    projected_away_points: float
    projected_margin: float
    projected_total: float
    display_home_points: int
    display_away_points: int
    home_win_probability: float
    sample_size: int
    detail: dict[str, float | int | str]


def normalize_nonnegative_scores(
    home_points: float,
    away_points: float,
) -> tuple[float, float, float]:
    """Translate both scores equally until neither is below zero.

    Equal translation preserves the modeled margin. It intentionally does not
    clamp only the negative side, which would silently shrink the margin.
    """
    shift = max(0.0, -min(home_points, away_points))
    return home_points + shift, away_points + shift, shift


def _round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def winner_consistent_display_scores(
    home_points: float,
    away_points: float,
    margin: float,
) -> tuple[int, int]:
    """Round scores without displaying a tie against a non-zero model margin."""
    home = max(0, _round_half_up(home_points))
    away = max(0, _round_half_up(away_points))

    if margin > 0.0 and home <= away:
        home = away + 1
    elif margin < 0.0 and away <= home:
        away = home + 1

    return home, away


def fit_scoring_profiles(
    session: Session,
    season: int,
    through_week: int,
    *,
    prior_games: float = DEFAULT_PRIOR_GAMES,
) -> tuple[dict[int, ScoringProfile], float, int]:
    """Fit leakage-safe shrunk offense/defense scoring profiles.

    Only completed Division I-vs-Division I games through the supplied week
    are used. Each team is shrunk toward the season-wide mean team score by a
    configurable number of pseudo-games.
    """
    games = list(
        session.scalars(
            select(Game)
            .where(
                Game.season == season,
                Game.week <= through_week,
                Game.completed.is_(True),
                Game.home_points.is_not(None),
                Game.away_points.is_not(None),
                Game.home_subdivision.in_(DIVISION_I),
                Game.away_subdivision.in_(DIVISION_I),
            )
            .order_by(Game.week, Game.start_time, Game.id)
        )
    )

    if games:
        total_points = sum(
            float(game.home_points + game.away_points)
            for game in games
        )
        mean_team_points = total_points / (2.0 * len(games))
    else:
        mean_team_points = DEFAULT_TEAM_POINTS

    totals: dict[int, list[float]] = {}
    for game in games:
        home = totals.setdefault(game.home_team_id, [0.0, 0.0, 0.0])
        away = totals.setdefault(game.away_team_id, [0.0, 0.0, 0.0])
        home[0] += float(game.home_points)
        home[1] += float(game.away_points)
        home[2] += 1.0
        away[0] += float(game.away_points)
        away[1] += float(game.home_points)
        away[2] += 1.0

    profiles: dict[int, ScoringProfile] = {}
    for team_id, (points_for, points_against, game_count) in totals.items():
        denominator = game_count + prior_games
        profiles[team_id] = ScoringProfile(
            offense=(points_for + prior_games * mean_team_points) / denominator,
            defense=(points_against + prior_games * mean_team_points) / denominator,
            games=int(game_count),
        )

    return profiles, mean_team_points, len(games)


def _profile_or_mean(
    profiles: dict[int, ScoringProfile],
    team_id: int,
    mean_team_points: float,
) -> ScoringProfile:
    return profiles.get(
        team_id,
        ScoringProfile(
            offense=mean_team_points,
            defense=mean_team_points,
            games=0,
        ),
    )


def hybrid_project_game(
    session: Session,
    game: Game,
    snapshot: RankingSnapshot,
    *,
    prior_games: float = DEFAULT_PRIOR_GAMES,
    rank_weight: float = RANK_MARGIN_WEIGHT,
    offdef_weight: float = OFFDEF_MARGIN_WEIGHT,
) -> ResearchProjection | None:
    """Research-only hybrid projection that never writes official predictions."""
    entries = _entry_map(session, snapshot.id)
    team_count = max(len(entries), 1)
    home_entry = entries.get(game.home_team_id)
    away_entry = entries.get(game.away_team_id)
    if home_entry is None and away_entry is None:
        return None

    home_rank = home_entry.rank if home_entry else None
    away_rank = away_entry.rank if away_entry else None
    effective_home_rank = home_rank or (team_count + 1)
    effective_away_rank = away_rank or (team_count + 1)

    calibration = fit_calibration(session, snapshot.season, snapshot.week)
    rank_gap = float(effective_away_rank - effective_home_rank)
    rank_margin = _monotonic_margin(rank_gap, calibration.rank_slope)

    profiles, mean_team_points, scoring_games = fit_scoring_profiles(
        session,
        snapshot.season,
        snapshot.week,
        prior_games=prior_games,
    )
    home_profile = _profile_or_mean(
        profiles,
        game.home_team_id,
        mean_team_points,
    )
    away_profile = _profile_or_mean(
        profiles,
        game.away_team_id,
        mean_team_points,
    )

    home_base = (home_profile.offense + away_profile.defense) / 2.0
    away_base = (away_profile.offense + home_profile.defense) / 2.0
    offdef_margin = home_base - away_base
    projected_total = home_base + away_base

    weight_total = rank_weight + offdef_weight
    if weight_total <= 0.0:
        raise ValueError("Hybrid margin weights must sum to a positive value.")
    normalized_rank_weight = rank_weight / weight_total
    normalized_offdef_weight = offdef_weight / weight_total
    margin = (
        normalized_rank_weight * rank_margin
        + normalized_offdef_weight * offdef_margin
    )

    raw_home = (projected_total + margin) / 2.0
    raw_away = (projected_total - margin) / 2.0
    home_points, away_points, score_shift = normalize_nonnegative_scores(
        raw_home,
        raw_away,
    )
    display_home, display_away = winner_consistent_display_scores(
        home_points,
        away_points,
        margin,
    )

    if margin == 0.0:
        probability = 0.5
    else:
        probability = _normal_cdf(margin / calibration.residual_sd)
        probability = min(max(probability, 0.02), 0.98)

    return ResearchProjection(
        home_rank=home_rank,
        away_rank=away_rank,
        projected_home_points=round(home_points, 2),
        projected_away_points=round(away_points, 2),
        projected_margin=round(margin, 2),
        projected_total=round(home_points + away_points, 2),
        display_home_points=display_home,
        display_away_points=display_away,
        home_win_probability=round(probability, 4),
        sample_size=calibration.sample_size,
        detail={
            "method": HYBRID_VERSION,
            "rank_gap": round(rank_gap, 2),
            "rank_margin": round(rank_margin, 2),
            "offdef_margin": round(offdef_margin, 2),
            "rank_weight": round(normalized_rank_weight, 4),
            "offdef_weight": round(normalized_offdef_weight, 4),
            "prior_games": round(prior_games, 2),
            "mean_team_points": round(mean_team_points, 2),
            "scoring_games": scoring_games,
            "home_offense": round(home_profile.offense, 2),
            "home_defense": round(home_profile.defense, 2),
            "away_offense": round(away_profile.offense, 2),
            "away_defense": round(away_profile.defense, 2),
            "score_shift": round(score_shift, 2),
            "display_rule": "winner_consistent_half_up",
        },
    )


def hybrid_retrocast_game(
    session: Session,
    game: Game,
) -> ResearchProjection | None:
    """Leakage-safe research retrocast using only the prior weekly snapshot."""
    if game.week <= 1:
        return None

    from .ranking_service import get_snapshot

    snapshot = get_snapshot(session, game.season, game.week - 1)
    if snapshot is None:
        return None
    return hybrid_project_game(session, game, snapshot)
