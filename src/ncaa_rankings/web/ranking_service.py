from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ncaa_rankings.models import DivisionIWeightedModel, Site, TeamGame

from .config import get_settings
from .models import (
    Game,
    RankingEntry,
    RankingGameAudit,
    RankingSnapshot,
    Team,
    TeamSeason,
)

DIVISION_I = {"FBS", "FCS"}


def latest_snapshot(session: Session, season: int) -> RankingSnapshot | None:
    settings = get_settings()
    return session.scalar(
        select(RankingSnapshot)
        .where(
            RankingSnapshot.season == season,
            RankingSnapshot.model_version == settings.model_version,
            RankingSnapshot.official.is_(True),
        )
        .order_by(RankingSnapshot.week.desc())
        .limit(1)
    )


def get_snapshot(session: Session, season: int, week: int) -> RankingSnapshot | None:
    settings = get_settings()
    return session.scalar(
        select(RankingSnapshot).where(
            RankingSnapshot.season == season,
            RankingSnapshot.week == week,
            RankingSnapshot.model_version == settings.model_version,
            RankingSnapshot.official.is_(True),
        )
    )


def snapshot_entries(session: Session, snapshot_id: int) -> list[RankingEntry]:
    return list(
        session.scalars(
            select(RankingEntry)
            .where(RankingEntry.snapshot_id == snapshot_id)
            .order_by(RankingEntry.rank)
        )
    )


def active_pool(session: Session, season: int) -> list[Team]:
    return list(
        session.scalars(
            select(Team)
            .join(TeamSeason, TeamSeason.team_id == Team.id)
            .where(
                TeamSeason.season == season,
                TeamSeason.active.is_(True),
                TeamSeason.subdivision.in_(tuple(DIVISION_I)),
            )
            .order_by(Team.name)
        )
    )


def week_games(session: Session, season: int, week: int) -> list[Game]:
    return list(
        session.scalars(
            select(Game)
            .where(
                Game.season == season,
                Game.week == week,
                Game.season_type == "regular",
                or_(
                    Game.home_subdivision.in_(tuple(DIVISION_I)),
                    Game.away_subdivision.in_(tuple(DIVISION_I)),
                ),
            )
            .order_by(Game.start_time, Game.id)
        )
    )


def week_is_complete(session: Session, season: int, week: int) -> bool:
    games = week_games(session, season, week)
    if not games:
        return False
    return all(
        game.completed
        and game.home_points is not None
        and game.away_points is not None
        for game in games
    )


def completed_weeks(session: Session, season: int) -> list[int]:
    weeks = sorted(
        set(
            session.scalars(
                select(Game.week).where(
                    Game.season == season,
                    Game.season_type == "regular",
                )
            )
        )
    )
    return [week for week in weeks if week > 0 and week_is_complete(session, season, week)]


def _subdivision_map(session: Session, season: int) -> dict[int, str]:
    rows = session.execute(
        select(TeamSeason.team_id, TeamSeason.subdivision).where(
            TeamSeason.season == season
        )
    )
    return {team_id: subdivision for team_id, subdivision in rows}


def _average_scoring_ranks(entries: list[RankingEntry]) -> dict[int, float]:
    """Give exact score ties the average rank of the positions they occupy."""
    ordered = sorted(entries, key=lambda entry: entry.rank)
    scoring_ranks: dict[int, float] = {}
    start = 0
    while start < len(ordered):
        score = ordered[start].score
        end = start + 1
        while end < len(ordered) and ordered[end].score == score:
            end += 1

        first_position = start + 1
        last_position = end
        average_rank = (first_position + last_position) / 2.0
        for index in range(start, end):
            scoring_ranks[ordered[index].team_id] = average_rank
        start = end
    return scoring_ranks


def _previous_state(
    session: Session,
    season: int,
    week: int,
) -> tuple[
    dict[int, int],
    dict[int, float],
    dict[int, float],
    dict[int, int],
    dict[int, int],
    dict[int, float],
]:
    if week <= 1:
        return {}, {}, {}, {}, {}, {}
    previous = get_snapshot(session, season, week - 1)
    if previous is None:
        raise RuntimeError(
            f"Cannot calculate Week {week}: official Week {week - 1} snapshot is missing."
        )

    entries = snapshot_entries(session, previous.id)
    display_ranks: dict[int, int] = {}
    scores: dict[int, float] = {}
    wins: dict[int, int] = {}
    losses: dict[int, int] = {}
    strength: dict[int, float] = {}
    for entry in entries:
        display_ranks[entry.team_id] = entry.rank
        scores[entry.team_id] = entry.score
        wins[entry.team_id] = entry.wins
        losses[entry.team_id] = entry.losses
        strength[entry.team_id] = entry.opponent_strength

    scoring_ranks = _average_scoring_ranks(entries)
    return display_ranks, scoring_ranks, scores, wins, losses, strength


def _teams_with_completed_game_before(
    session: Session,
    season: int,
    week: int,
) -> set[int]:
    """Teams with actual current-season evidence before this ranking week."""
    played: set[int] = set()
    games = session.scalars(
        select(Game).where(
            Game.season == season,
            Game.week < week,
            Game.completed.is_(True),
            Game.home_points.is_not(None),
            Game.away_points.is_not(None),
        )
    )
    for game in games:
        played.add(game.home_team_id)
        played.add(game.away_team_id)
    return played


def _head_to_head(session: Session, season: int, through_week: int) -> dict[tuple[int, int], int]:
    h2h: dict[tuple[int, int], int] = defaultdict(int)
    games = session.scalars(
        select(Game).where(
            Game.season == season,
            Game.week <= through_week,
            Game.completed.is_(True),
            Game.home_subdivision.in_(tuple(DIVISION_I)),
            Game.away_subdivision.in_(tuple(DIVISION_I)),
        )
    )
    for game in games:
        if game.home_points is None or game.away_points is None:
            continue
        if game.home_points > game.away_points:
            h2h[(game.home_team_id, game.away_team_id)] += 1
        elif game.away_points > game.home_points:
            h2h[(game.away_team_id, game.home_team_id)] += 1
    return h2h


def _order_team_ids(
    team_ids: Iterable[int],
    names: dict[int, str],
    totals: dict[int, float],
    wins: dict[int, int],
    opponent_strength: dict[int, float],
    h2h: dict[tuple[int, int], int],
) -> list[int]:
    groups: dict[float, list[int]] = defaultdict(list)
    for team_id in team_ids:
        groups[float(totals.get(team_id, 0.0))].append(team_id)

    ordered: list[int] = []
    for score in sorted(groups, reverse=True):
        tied = groups[score]
        tied_set = set(tied)
        tied.sort(
            key=lambda team_id: (
                -sum(
                    h2h.get((team_id, opponent_id), 0)
                    for opponent_id in tied_set
                    if opponent_id != team_id
                ),
                -wins.get(team_id, 0),
                -opponent_strength.get(team_id, 0.0),
                names[team_id],
            )
        )
        ordered.extend(tied)
    return ordered


def _site(neutral: bool, home_view: bool) -> Site:
    if neutral:
        return Site.NEUTRAL
    return Site.HOME if home_view else Site.AWAY


def _game_scale(team_subdivision: str, opponent_subdivision: str, points_for: int, points_against: int) -> float:
    if team_subdivision != "FCS":
        return 1.0
    if opponent_subdivision == "FCS":
        return 0.5
    if opponent_subdivision == "FBS":
        if points_for > points_against:
            return 1.0
        return 0.5
    return 1.0


def calculate_week_snapshot(
    session: Session,
    season: int,
    week: int,
    *,
    force: bool = False,
) -> RankingSnapshot:
    settings = get_settings()
    existing = get_snapshot(session, season, week)
    if existing is not None and not force:
        return existing
    if not week_is_complete(session, season, week):
        raise RuntimeError(f"Week {week} is not complete and cannot be frozen.")
    if existing is not None and force:
        raise RuntimeError(
            "Official ranking snapshots are immutable. Delete/rebuild manually if a correction is required."
        )

    teams = active_pool(session, season)
    if not teams:
        raise RuntimeError(f"No Division I teams are loaded for season {season}.")
    team_ids = [team.id for team in teams]
    names = {team.id: team.name for team in teams}
    subdivisions = _subdivision_map(session, season)
    team_count = len(team_ids)

    (
        previous_display_ranks,
        previous_scoring_ranks,
        previous_scores,
        previous_wins,
        previous_losses,
        previous_strength,
    ) = _previous_state(session, season, week)
    neutral_rank = (team_count + 1) / 2.0
    previously_played = _teams_with_completed_game_before(session, season, week)
    totals = defaultdict(float, previous_scores)
    wins = defaultdict(int, previous_wins)
    losses = defaultdict(int, previous_losses)
    opponent_strength = defaultdict(float, previous_strength)

    model = DivisionIWeightedModel()
    pending_audits: list[dict] = []

    for game in week_games(session, season, week):
        if not game.completed or game.home_points is None or game.away_points is None:
            continue
        perspectives = (
            (game.home_team_id, game.away_team_id, game.home_subdivision, game.away_subdivision, int(game.home_points), int(game.away_points), True),
            (game.away_team_id, game.home_team_id, game.away_subdivision, game.home_subdivision, int(game.away_points), int(game.home_points), False),
        )
        for team_id, opponent_id, team_subdivision, opponent_subdivision, points_for, points_against, home_view in perspectives:
            if team_subdivision not in DIVISION_I:
                continue
            team_name = names.get(team_id)
            if team_name is None:
                continue
            opponent = session.get(Team, opponent_id)
            if opponent is None:
                continue
            opponent_in_pool = opponent_subdivision in DIVISION_I
            opponent_rank = None
            if opponent_in_pool:
                if week == 1 or opponent_id not in previously_played:
                    opponent_rank = neutral_rank
                else:
                    opponent_rank = previous_scoring_ranks.get(opponent_id)
            team_game = TeamGame(
                team=team_name,
                opponent=opponent.name,
                points_for=points_for,
                points_against=points_against,
                site=_site(game.neutral_site, home_view),
                played_on=game.start_time.date() if game.start_time else None,
                opponent_in_rank_pool=opponent_in_pool,
                season_type=game.season_type,
                week=week,
                team_subdivision=team_subdivision,
                opponent_subdivision=opponent_subdivision,
            )
            component = model.score_game(team_game, opponent_rank, team_count)
            totals[team_id] += component.total
            if opponent_rank is not None:
                opponent_strength[team_id] += (team_count + 1) - opponent_rank
            if points_for > points_against:
                wins[team_id] += 1
            elif points_for < points_against:
                losses[team_id] += 1

            pending_audits.append({
                "game_id": game.id,
                "team_id": team_id,
                "opponent_team_id": opponent_id,
                "opponent_rank_used": opponent_rank,
                "opponent_points": component.opponent_points,
                "win_points": component.win_points,
                "margin_points": component.margin_points,
                "multiplier": _game_scale(team_subdivision, opponent_subdivision, points_for, points_against),
                "game_total": component.total,
            })

    h2h = _head_to_head(session, season, week)
    ordered = _order_team_ids(team_ids, names, totals, wins, opponent_strength, h2h)
    current_ranks = {team_id: index + 1 for index, team_id in enumerate(ordered)}

    snapshot = RankingSnapshot(
        season=season,
        week=week,
        model_version=settings.model_version,
        official=True,
        locked_at=datetime.now(timezone.utc),
        source_note=(
            "Calculated automatically from completed CFBD game results using "
            "the neutral first-game baseline, Week 0-to-Week 1 normalization, "
            "and averaged scoring ranks for ties."
        ),
    )
    session.add(snapshot)
    session.flush()

    for team_id in ordered:
        previous_rank = previous_display_ranks.get(team_id)
        new_rank = current_ranks[team_id]
        session.add(RankingEntry(
            snapshot_id=snapshot.id,
            team_id=team_id,
            rank=new_rank,
            score=float(totals[team_id]),
            wins=wins[team_id],
            losses=losses[team_id],
            opponent_strength=float(opponent_strength[team_id]),
            movement=(previous_rank - new_rank) if previous_rank is not None else None,
        ))

    for audit in pending_audits:
        session.add(RankingGameAudit(snapshot_id=snapshot.id, **audit))

    session.commit()
    return snapshot


def calculate_all_new_complete_weeks(session: Session, season: int) -> list[int]:
    created: list[int] = []
    for week in completed_weeks(session, season):
        if get_snapshot(session, season, week) is not None:
            continue
        if week > 1 and get_snapshot(session, season, week - 1) is None:
            break
        calculate_week_snapshot(session, season, week)
        created.append(week)
    return created
