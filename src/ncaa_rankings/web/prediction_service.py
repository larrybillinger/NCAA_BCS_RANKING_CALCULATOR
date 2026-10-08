from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import statistics

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import get_settings
from .memo import session_memo
from .models import Game, PredictionSnapshot, RankingEntry, RankingSnapshot, TeamSeason
from .ranking_service import get_snapshot, latest_snapshot

DIVISION_I = {"FBS", "FCS"}
HYBRID_PREDICTOR_VERSION = "hybrid_core_v1"
LEGACY_RANK_GAP_VERSION = "rank_gap_v3"

# Rank-gap calibration remains a component of the hybrid predictor and is kept
# available for archived rank_gap_v3 rows and research comparisons.
FALLBACK_POINTS_PER_RANK = 0.20
MIN_POINTS_PER_RANK = 0.08
MAX_POINTS_PER_RANK = 0.35
MAX_PROJECTED_MARGIN = 45.0


@dataclass(frozen=True, slots=True)
class Calibration:
    rank_slope: float
    average_total: float
    residual_sd: float
    sample_size: int


@dataclass(frozen=True, slots=True)
class Projection:
    home_rank: int | None
    away_rank: int | None
    home_points: float
    away_points: float
    margin: float
    home_win_probability: float
    sample_size: int
    detail: dict[str, float | int | str]

    @property
    def projected_home_points(self) -> float:
        return self.home_points

    @property
    def projected_away_points(self) -> float:
        return self.away_points

    @property
    def projected_margin(self) -> float:
        return self.margin


def _entry_map(session: Session, snapshot_id: int) -> dict[int, RankingEntry]:
    return session_memo(
        session,
        ("entry_map", snapshot_id),
        lambda: {
            entry.team_id: entry
            for entry in session.scalars(
                select(RankingEntry).where(RankingEntry.snapshot_id == snapshot_id)
            )
        },
    )


def _clamp_slope(value: float) -> float:
    return min(max(value, MIN_POINTS_PER_RANK), MAX_POINTS_PER_RANK)


def _monotonic_margin(rank_gap: float, rank_slope: float) -> float:
    """Translate rank gap into the legacy rank-gap margin component."""
    margin = rank_gap * _clamp_slope(rank_slope)
    return min(max(margin, -MAX_PROJECTED_MARGIN), MAX_PROJECTED_MARGIN)


def fit_calibration(session: Session, season: int, through_week: int) -> Calibration:
    return session_memo(
        session,
        ("calibration", get_settings().model_version, season, through_week),
        lambda: _fit_calibration(session, season, through_week),
    )


def _fit_calibration(session: Session, season: int, through_week: int) -> Calibration:
    samples: list[tuple[float, float]] = []
    totals: list[float] = []

    for week in range(2, through_week + 1):
        prior = get_snapshot(session, season, week - 1)
        if prior is None:
            continue
        entries = _entry_map(session, prior.id)
        games = session.scalars(
            select(Game).where(
                Game.season == season,
                Game.week == week,
                Game.completed.is_(True),
                Game.home_points.is_not(None),
                Game.away_points.is_not(None),
                Game.home_subdivision.in_(tuple(DIVISION_I)),
                Game.away_subdivision.in_(tuple(DIVISION_I)),
            )
        )
        for game in games:
            home = entries.get(game.home_team_id)
            away = entries.get(game.away_team_id)
            if home is None or away is None:
                continue
            rank_gap = float(away.rank - home.rank)
            actual_margin = float(game.home_points - game.away_points)
            if rank_gap != 0:
                samples.append((rank_gap, actual_margin))
            totals.append(float(game.home_points + game.away_points))

    sample_size = len(samples)
    average_total = statistics.fmean(totals) if totals else 52.0

    if sample_size < 5:
        return Calibration(
            rank_slope=FALLBACK_POINTS_PER_RANK,
            average_total=average_total,
            residual_sd=14.0,
            sample_size=sample_size,
        )

    denominator = sum(rank_gap * rank_gap for rank_gap, _ in samples)
    fitted_slope = (
        sum(rank_gap * actual_margin for rank_gap, actual_margin in samples)
        / denominator
        if denominator > 0
        else FALLBACK_POINTS_PER_RANK
    )

    blend = min(1.0, sample_size / 100.0)
    blended_slope = FALLBACK_POINTS_PER_RANK * (1.0 - blend) + fitted_slope * blend
    rank_slope = _clamp_slope(blended_slope)

    residuals = [
        actual_margin - _monotonic_margin(rank_gap, rank_slope)
        for rank_gap, actual_margin in samples
    ]
    residual_sd = statistics.pstdev(residuals) if len(residuals) > 1 else 14.0
    residual_sd = max(residual_sd, 7.0)

    return Calibration(
        rank_slope=rank_slope,
        average_total=average_total,
        residual_sd=residual_sd,
        sample_size=sample_size,
    )


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _projection_from_ranks(
    home_rank: int,
    away_rank: int,
    calibration: Calibration,
) -> tuple[float, float, float, float]:
    rank_gap = float(away_rank - home_rank)
    margin = _monotonic_margin(rank_gap, calibration.rank_slope)
    total = min(max(calibration.average_total, 34.0), 76.0)
    home_points = max(0.0, (total + margin) / 2.0)
    away_points = max(0.0, (total - margin) / 2.0)

    if margin == 0:
        probability = 0.5
    else:
        probability = _normal_cdf(margin / calibration.residual_sd)
        probability = min(max(probability, 0.02), 0.98)

    return home_points, away_points, margin, probability


def _legacy_rank_gap_projection(
    session: Session,
    game: Game,
    snapshot: RankingSnapshot,
) -> Projection | None:
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
    home_points, away_points, margin, probability = _projection_from_ranks(
        effective_home_rank,
        effective_away_rank,
        calibration,
    )
    rank_gap = float(effective_away_rank - effective_home_rank)

    return Projection(
        home_rank=home_rank,
        away_rank=away_rank,
        home_points=round(home_points, 1),
        away_points=round(away_points, 1),
        margin=round(margin, 2),
        home_win_probability=round(probability, 4),
        sample_size=calibration.sample_size,
        detail={
            "method": LEGACY_RANK_GAP_VERSION,
            "rank_gap": round(rank_gap, 2),
            "rank_slope": round(calibration.rank_slope, 4),
            "average_total": round(calibration.average_total, 2),
            "residual_sd": round(calibration.residual_sd, 2),
            "winner_rule": "higher_rank_always_projected_winner",
        },
    )


def project_game(session: Session, game: Game, snapshot: RankingSnapshot) -> Projection | None:
    """Project a game with the configured official predictor.

    hybrid_core_v1 became the official predictor in v0.11.0. It blends the
    calibrated rank-gap component with shrunk current-season offense/defense
    scoring profiles. rank_gap_v3 remains available only for archived rows and
    explicit legacy comparisons.
    """
    settings = get_settings()
    if settings.predictor_version == HYBRID_PREDICTOR_VERSION:
        # Local import avoids an import cycle: research_prediction_service uses
        # the calibration helpers in this module.
        from .research_prediction_service import hybrid_project_game

        hybrid = hybrid_project_game(session, game, snapshot)
        if hybrid is None:
            return None
        detail = dict(hybrid.detail)
        detail["official_predictor"] = HYBRID_PREDICTOR_VERSION
        return Projection(
            home_rank=hybrid.home_rank,
            away_rank=hybrid.away_rank,
            home_points=hybrid.projected_home_points,
            away_points=hybrid.projected_away_points,
            margin=hybrid.projected_margin,
            home_win_probability=hybrid.home_win_probability,
            sample_size=hybrid.sample_size,
            detail=detail,
        )

    return _legacy_rank_gap_projection(session, game, snapshot)


def retrocast_game(session: Session, game: Game) -> Projection | None:
    """Research-only projection using only information available before a game."""
    if game.week <= 1:
        return None
    prior = get_snapshot(session, game.season, game.week - 1)
    if prior is None:
        return None
    return project_game(session, game, prior)


def generate_predictions_for_snapshot(session: Session, snapshot: RankingSnapshot) -> int:
    settings = get_settings()
    games = session.scalars(
        select(Game).where(
            Game.season == snapshot.season,
            Game.week > snapshot.week,
            or_(
                Game.home_subdivision.in_(tuple(DIVISION_I)),
                Game.away_subdivision.in_(tuple(DIVISION_I)),
            ),
        )
    )
    created = 0
    for game in games:
        exists = session.scalar(
            select(PredictionSnapshot).where(
                PredictionSnapshot.game_id == game.id,
                PredictionSnapshot.ranking_snapshot_id == snapshot.id,
                PredictionSnapshot.predictor_version == settings.predictor_version,
            )
        )
        if exists is not None:
            continue
        projection = project_game(session, game, snapshot)
        if projection is None:
            continue
        session.add(
            PredictionSnapshot(
                game_id=game.id,
                ranking_snapshot_id=snapshot.id,
                predictor_version=settings.predictor_version,
                locks_at=game.start_time,
                home_rank=projection.home_rank,
                away_rank=projection.away_rank,
                projected_home_points=projection.home_points,
                projected_away_points=projection.away_points,
                projected_margin=projection.margin,
                home_win_probability=projection.home_win_probability,
                sample_size=projection.sample_size,
                model_detail=projection.detail,
            )
        )
        created += 1
    session.commit()
    return created


def lock_started_predictions(session: Session, now: datetime | None = None) -> int:
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    games = list(
        session.scalars(
            select(Game).where(
                Game.start_time.is_not(None),
                Game.start_time <= now,
                or_(
                    Game.home_subdivision.in_(tuple(DIVISION_I)),
                    Game.away_subdivision.in_(tuple(DIVISION_I)),
                ),
            )
        )
    )
    active_model_rows = (
        select(PredictionSnapshot)
        .join(RankingSnapshot, RankingSnapshot.id == PredictionSnapshot.ranking_snapshot_id)
        .where(RankingSnapshot.model_version == settings.model_version)
    )
    locked = 0
    for game in games:
        already = session.scalar(
            active_model_rows.where(
                PredictionSnapshot.game_id == game.id,
                PredictionSnapshot.predictor_version == settings.predictor_version,
                PredictionSnapshot.official.is_(True),
            )
        )
        if already is not None:
            continue
        candidate = session.scalar(
            active_model_rows
            .where(
                PredictionSnapshot.game_id == game.id,
                PredictionSnapshot.predictor_version == settings.predictor_version,
                PredictionSnapshot.created_at <= game.start_time,
            )
            .order_by(PredictionSnapshot.created_at.desc())
            .limit(1)
        )
        if candidate is None:
            continue
        candidate.official = True
        candidate.locked_at = game.start_time
        session.add(candidate)
        locked += 1
    session.commit()
    return locked


def latest_prediction(
    session: Session,
    game_id: int,
    *,
    as_of_week: int | None = None,
    official_only: bool = False,
) -> PredictionSnapshot | None:
    settings = get_settings()
    query = (
        select(PredictionSnapshot)
        .join(RankingSnapshot, RankingSnapshot.id == PredictionSnapshot.ranking_snapshot_id)
        .where(
            PredictionSnapshot.game_id == game_id,
            PredictionSnapshot.predictor_version == settings.predictor_version,
            RankingSnapshot.model_version == settings.model_version,
        )
    )
    if official_only:
        query = query.where(PredictionSnapshot.official.is_(True))
    if as_of_week is not None:
        query = query.where(RankingSnapshot.week <= as_of_week)
    return session.scalar(
        query.order_by(
            RankingSnapshot.week.desc(), PredictionSnapshot.created_at.desc()
        ).limit(1)
    )


def team_matchup_projection(
    session: Session,
    season: int,
    home_team_id: int,
    away_team_id: int,
) -> Projection | None:
    """Project a hypothetical current matchup using the active full predictor."""
    if home_team_id == away_team_id:
        return None
    snapshot = latest_snapshot(session, season)
    if snapshot is None:
        return None
    home_season = session.scalar(
        select(TeamSeason).where(
            TeamSeason.team_id == home_team_id,
            TeamSeason.season == season,
            TeamSeason.active.is_(True),
        )
    )
    away_season = session.scalar(
        select(TeamSeason).where(
            TeamSeason.team_id == away_team_id,
            TeamSeason.season == season,
            TeamSeason.active.is_(True),
        )
    )
    if home_season is None or away_season is None:
        return None
    game = Game(
        provider="tool",
        provider_game_id=f"matchup-{home_team_id}-{away_team_id}",
        season=season,
        week=snapshot.week + 1,
        season_type="regular",
        completed=False,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_subdivision=home_season.subdivision,
        away_subdivision=away_season.subdivision,
    )
    return project_game(session, game, snapshot)


def rank_matchup_projection(
    session: Session,
    season: int,
    home_rank: int,
    away_rank: int,
) -> Projection | None:
    """Legacy rank-only projection retained for compatibility/tests.

    The public calculator uses team_matchup_projection so hybrid offense/defense
    information is not silently discarded.
    """
    snapshot = latest_snapshot(session, season)
    if snapshot is None:
        return None
    calibration = fit_calibration(session, season, snapshot.week)
    home_points, away_points, margin, probability = _projection_from_ranks(
        home_rank,
        away_rank,
        calibration,
    )
    rank_gap = float(away_rank - home_rank)
    return Projection(
        home_rank=home_rank,
        away_rank=away_rank,
        home_points=round(home_points, 1),
        away_points=round(away_points, 1),
        margin=round(margin, 2),
        home_win_probability=round(probability, 4),
        sample_size=calibration.sample_size,
        detail={
            "method": LEGACY_RANK_GAP_VERSION,
            "rank_gap": round(rank_gap, 2),
            "rank_slope": round(calibration.rank_slope, 4),
            "average_total": round(calibration.average_total, 2),
            "winner_rule": "legacy_rank_only_tool",
        },
    )
