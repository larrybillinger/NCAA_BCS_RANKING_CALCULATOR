from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import statistics

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Game, PredictionSnapshot, RankingEntry, RankingSnapshot
from .ranking_service import get_snapshot, latest_snapshot

DIVISION_I = {"FBS", "FCS"}


@dataclass(frozen=True, slots=True)
class Calibration:
    intercept: float
    rank_slope: float
    neutral_adjustment: float
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


def _entry_map(session: Session, snapshot_id: int) -> dict[int, RankingEntry]:
    return {
        entry.team_id: entry
        for entry in session.scalars(
            select(RankingEntry).where(RankingEntry.snapshot_id == snapshot_id)
        )
    }


def _solve3(matrix: list[list[float]], vector: list[float]) -> list[float]:
    augmented = [matrix[i][:] + [vector[i]] for i in range(3)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda row: abs(augmented[row][col]))
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        divisor = augmented[col][col]
        if abs(divisor) < 1e-9:
            continue
        for j in range(col, 4):
            augmented[col][j] /= divisor
        for row in range(3):
            if row == col:
                continue
            factor = augmented[row][col]
            for j in range(col, 4):
                augmented[row][j] -= factor * augmented[col][j]
    return [augmented[i][3] for i in range(3)]


def fit_calibration(session: Session, season: int, through_week: int) -> Calibration:
    samples: list[tuple[float, float, float, float]] = []
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
            neutral = 1.0 if game.neutral_site else 0.0
            actual_margin = float(game.home_points - game.away_points)
            samples.append((1.0, rank_gap, neutral, actual_margin))
            totals.append(float(game.home_points + game.away_points))

    fallback = Calibration(
        intercept=2.5,
        rank_slope=0.22,
        neutral_adjustment=-2.5,
        average_total=52.0,
        residual_sd=14.0,
        sample_size=len(samples),
    )
    if len(samples) < 5:
        return fallback

    xtx = [[0.0] * 3 for _ in range(3)]
    xty = [0.0] * 3
    for x0, x1, x2, y in samples:
        x = [x0, x1, x2]
        for i in range(3):
            xty[i] += x[i] * y
            for j in range(3):
                xtx[i][j] += x[i] * x[j]

    for i in range(3):
        xtx[i][i] += 0.25
    fitted = _solve3(xtx, xty)

    blend = min(1.0, len(samples) / 80.0)
    intercept = fallback.intercept * (1.0 - blend) + fitted[0] * blend
    rank_slope = fallback.rank_slope * (1.0 - blend) + fitted[1] * blend
    neutral_adjustment = fallback.neutral_adjustment * (1.0 - blend) + fitted[2] * blend
    average_total = statistics.fmean(totals) if totals else fallback.average_total

    residuals: list[float] = []
    for x0, x1, x2, y in samples:
        predicted = intercept + rank_slope * x1 + neutral_adjustment * x2
        residuals.append(y - predicted)
    residual_sd = statistics.pstdev(residuals) if len(residuals) > 1 else 14.0
    residual_sd = max(residual_sd, 7.0)

    return Calibration(
        intercept=intercept,
        rank_slope=rank_slope,
        neutral_adjustment=neutral_adjustment,
        average_total=average_total,
        residual_sd=residual_sd,
        sample_size=len(samples),
    )


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def project_game(session: Session, game: Game, snapshot: RankingSnapshot) -> Projection | None:
    settings = get_settings()
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
    neutral = 1.0 if game.neutral_site else 0.0
    margin = calibration.intercept + calibration.rank_slope * rank_gap + calibration.neutral_adjustment * neutral
    total = min(max(calibration.average_total, 34.0), 76.0)
    margin = min(max(margin, -45.0), 45.0)
    home_points = max(0.0, (total + margin) / 2.0)
    away_points = max(0.0, (total - margin) / 2.0)
    probability = _normal_cdf(margin / calibration.residual_sd)
    probability = min(max(probability, 0.02), 0.98)

    return Projection(
        home_rank=home_rank,
        away_rank=away_rank,
        home_points=round(home_points, 1),
        away_points=round(away_points, 1),
        margin=round(margin, 2),
        home_win_probability=round(probability, 4),
        sample_size=calibration.sample_size,
        detail={
            "method": settings.predictor_version,
            "rank_gap": round(rank_gap, 2),
            "intercept": round(calibration.intercept, 4),
            "rank_slope": round(calibration.rank_slope, 4),
            "neutral_adjustment": round(calibration.neutral_adjustment, 4),
            "average_total": round(calibration.average_total, 2),
            "residual_sd": round(calibration.residual_sd, 2),
        },
    )


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
        session.add(PredictionSnapshot(
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
        ))
        created += 1
    session.commit()
    return created


def lock_started_predictions(session: Session, now: datetime | None = None) -> int:
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    games = list(session.scalars(select(Game).where(
        Game.start_time.is_not(None),
        Game.start_time <= now,
        or_(Game.home_subdivision.in_(tuple(DIVISION_I)), Game.away_subdivision.in_(tuple(DIVISION_I))),
    )))
    locked = 0
    for game in games:
        already = session.scalar(select(PredictionSnapshot).where(
            PredictionSnapshot.game_id == game.id,
            PredictionSnapshot.predictor_version == settings.predictor_version,
            PredictionSnapshot.official.is_(True),
        ))
        if already is not None:
            continue
        candidate = session.scalar(
            select(PredictionSnapshot)
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
    return session.scalar(query.order_by(RankingSnapshot.week.desc(), PredictionSnapshot.created_at.desc()).limit(1))


def rank_matchup_projection(
    session: Session,
    season: int,
    home_rank: int,
    away_rank: int,
    *,
    neutral: bool = False,
) -> Projection | None:
    snapshot = latest_snapshot(session, season)
    if snapshot is None:
        return None
    calibration = fit_calibration(session, season, snapshot.week)
    rank_gap = float(away_rank - home_rank)
    neutral_value = 1.0 if neutral else 0.0
    margin = calibration.intercept + calibration.rank_slope * rank_gap + calibration.neutral_adjustment * neutral_value
    total = min(max(calibration.average_total, 34.0), 76.0)
    margin = min(max(margin, -45.0), 45.0)
    home_points = max(0.0, (total + margin) / 2.0)
    away_points = max(0.0, (total - margin) / 2.0)
    probability = min(max(_normal_cdf(margin / calibration.residual_sd), 0.02), 0.98)
    return Projection(
        home_rank=home_rank,
        away_rank=away_rank,
        home_points=round(home_points, 1),
        away_points=round(away_points, 1),
        margin=round(margin, 2),
        home_win_probability=round(probability, 4),
        sample_size=calibration.sample_size,
        detail={
            "method": get_settings().predictor_version,
            "rank_slope": round(calibration.rank_slope, 4),
            "average_total": round(calibration.average_total, 2),
        },
    )
