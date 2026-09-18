from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
import statistics

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Game, PredictionSnapshot, SourceSyncRun


@dataclass(frozen=True, slots=True)
class AccuracyMetrics:
    games: int = 0
    winner_accuracy: float | None = None
    spread_mae: float | None = None
    spread_rmse: float | None = None
    score_mae: float | None = None
    brier: float | None = None
    upset_hit_rate: float | None = None
    rank_result_correlation: float | None = None


def _prediction_rows(
    session: Session,
    season: int,
    *,
    team_id: int | None = None,
) -> list[tuple[PredictionSnapshot, Game]]:
    settings = get_settings()
    query = (
        select(PredictionSnapshot, Game)
        .join(Game, Game.id == PredictionSnapshot.game_id)
        .where(
            Game.season == season,
            Game.completed.is_(True),
            PredictionSnapshot.predictor_version == settings.predictor_version,
            PredictionSnapshot.official.is_(True),
            Game.home_points.is_not(None),
            Game.away_points.is_not(None),
        )
    )
    if team_id is not None:
        query = query.where(or_(Game.home_team_id == team_id, Game.away_team_id == team_id))
    return list(session.execute(query).all())


def _corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return numerator / (dx * dy)


def _metrics(rows: list[tuple[PredictionSnapshot, Game]]) -> AccuracyMetrics:
    if not rows:
        return AccuracyMetrics()

    winner_correct = 0
    spread_errors: list[float] = []
    score_errors: list[float] = []
    brier_values: list[float] = []
    rank_gaps: list[float] = []
    actual_margins: list[float] = []
    actual_upsets = 0
    predicted_actual_upsets = 0

    for prediction, game in rows:
        actual_margin = float(game.home_points - game.away_points)
        predicted_home_win = prediction.home_win_probability >= 0.5
        actual_home_win = actual_margin > 0
        if predicted_home_win == actual_home_win:
            winner_correct += 1

        spread_errors.append(abs(prediction.projected_margin - actual_margin))
        score_errors.append(
            (
                abs(prediction.projected_home_points - float(game.home_points))
                + abs(prediction.projected_away_points - float(game.away_points))
            ) / 2.0
        )
        outcome = 1.0 if actual_home_win else 0.0
        brier_values.append((prediction.home_win_probability - outcome) ** 2)

        if prediction.home_rank is not None and prediction.away_rank is not None:
            rank_gap = float(prediction.away_rank - prediction.home_rank)
            rank_gaps.append(rank_gap)
            actual_margins.append(actual_margin)
            better_home = prediction.home_rank < prediction.away_rank
            actual_better_rank_lost = (better_home and not actual_home_win) or (not better_home and actual_home_win)
            if actual_better_rank_lost:
                actual_upsets += 1
                predicted_underdog = (better_home and prediction.home_win_probability < 0.5) or (not better_home and prediction.home_win_probability >= 0.5)
                if predicted_underdog:
                    predicted_actual_upsets += 1

    rmse = math.sqrt(statistics.fmean(error**2 for error in spread_errors))
    return AccuracyMetrics(
        games=len(rows),
        winner_accuracy=winner_correct / len(rows),
        spread_mae=statistics.fmean(spread_errors),
        spread_rmse=rmse,
        score_mae=statistics.fmean(score_errors),
        brier=statistics.fmean(brier_values),
        upset_hit_rate=(predicted_actual_upsets / actual_upsets) if actual_upsets else None,
        rank_result_correlation=_corr(rank_gaps, actual_margins),
    )


def overall_metrics(session: Session, season: int) -> AccuracyMetrics:
    return _metrics(_prediction_rows(session, season))


def team_metrics(session: Session, season: int, team_id: int) -> AccuracyMetrics:
    return _metrics(_prediction_rows(session, season, team_id=team_id))


def weekly_metrics(session: Session, season: int) -> list[dict]:
    grouped: dict[int, list[tuple[PredictionSnapshot, Game]]] = defaultdict(list)
    for prediction, game in _prediction_rows(session, season):
        grouped[game.week].append((prediction, game))
    results: list[dict] = []
    for week in sorted(grouped):
        metric = _metrics(grouped[week])
        results.append({"week": week, "metrics": metric})
    return results


def last_sync(session: Session) -> SourceSyncRun | None:
    return session.scalar(
        select(SourceSyncRun)
        .where(SourceSyncRun.status == "ok")
        .order_by(SourceSyncRun.finished_at.desc())
        .limit(1)
    )
