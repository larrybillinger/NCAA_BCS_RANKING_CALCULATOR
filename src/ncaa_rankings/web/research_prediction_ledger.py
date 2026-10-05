from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .models import (
    Game,
    RankingSnapshot,
    ResearchPredictionSnapshot,
)
from .research_prediction_service import HYBRID_VERSION, hybrid_project_game

DIVISION_I = ("FBS", "FCS")


def generate_research_predictions_for_snapshot(
    session: Session,
    snapshot: RankingSnapshot,
    *,
    now: datetime | None = None,
) -> int:
    """Create provisional hybrid research rows without touching official data."""
    now = now or datetime.now(timezone.utc)
    games = session.scalars(
        select(Game).where(
            Game.season == snapshot.season,
            Game.week > snapshot.week,
            or_(
                Game.home_subdivision.in_(DIVISION_I),
                Game.away_subdivision.in_(DIVISION_I),
            ),
        )
    )

    created = 0
    for game in games:
        # Never create a shadow row after kickoff. Unknown kickoff times may be
        # projected provisionally but cannot be locked until a time is known.
        start_time = game.start_time
        if start_time is not None:
            comparable_start = start_time
            if comparable_start.tzinfo is None:
                comparable_start = comparable_start.replace(tzinfo=timezone.utc)
            if comparable_start <= now:
                continue

        exists = session.scalar(
            select(ResearchPredictionSnapshot).where(
                ResearchPredictionSnapshot.game_id == game.id,
                ResearchPredictionSnapshot.ranking_snapshot_id == snapshot.id,
                ResearchPredictionSnapshot.model_version == HYBRID_VERSION,
            )
        )
        if exists is not None:
            continue

        projection = hybrid_project_game(session, game, snapshot)
        if projection is None:
            continue

        session.add(
            ResearchPredictionSnapshot(
                game_id=game.id,
                ranking_snapshot_id=snapshot.id,
                model_version=HYBRID_VERSION,
                locks_at=game.start_time,
                home_rank=projection.home_rank,
                away_rank=projection.away_rank,
                projected_home_points=projection.projected_home_points,
                projected_away_points=projection.projected_away_points,
                display_home_points=projection.display_home_points,
                display_away_points=projection.display_away_points,
                projected_margin=projection.projected_margin,
                projected_total=projection.projected_total,
                home_win_probability=projection.home_win_probability,
                sample_size=projection.sample_size,
                feature_snapshot={
                    "ranking_week": snapshot.week,
                    "context_version": "none_v1",
                    "pregame_only": True,
                },
                model_detail=projection.detail,
            )
        )
        created += 1

    session.commit()
    return created


def lock_started_research_predictions(
    session: Session,
    now: datetime | None = None,
) -> int:
    """Lock the latest eligible pre-kickoff hybrid row for each started game."""
    now = now or datetime.now(timezone.utc)
    games = list(
        session.scalars(
            select(Game).where(
                Game.start_time.is_not(None),
                Game.start_time <= now,
                or_(
                    Game.home_subdivision.in_(DIVISION_I),
                    Game.away_subdivision.in_(DIVISION_I),
                ),
            )
        )
    )

    locked = 0
    for game in games:
        already = session.scalar(
            select(ResearchPredictionSnapshot).where(
                ResearchPredictionSnapshot.game_id == game.id,
                ResearchPredictionSnapshot.model_version == HYBRID_VERSION,
                ResearchPredictionSnapshot.locked_at.is_not(None),
            )
        )
        if already is not None:
            continue

        candidate = session.scalar(
            select(ResearchPredictionSnapshot)
            .join(
                RankingSnapshot,
                RankingSnapshot.id
                == ResearchPredictionSnapshot.ranking_snapshot_id,
            )
            .where(
                ResearchPredictionSnapshot.game_id == game.id,
                ResearchPredictionSnapshot.model_version == HYBRID_VERSION,
                ResearchPredictionSnapshot.created_at <= game.start_time,
            )
            .order_by(
                RankingSnapshot.week.desc(),
                ResearchPredictionSnapshot.created_at.desc(),
            )
            .limit(1)
        )
        if candidate is None:
            continue

        candidate.locked_at = game.start_time
        session.add(candidate)
        locked += 1

    session.commit()
    return locked


def latest_locked_research_prediction(
    session: Session,
    game_id: int,
    *,
    model_version: str = HYBRID_VERSION,
) -> ResearchPredictionSnapshot | None:
    return session.scalar(
        select(ResearchPredictionSnapshot)
        .join(
            RankingSnapshot,
            RankingSnapshot.id == ResearchPredictionSnapshot.ranking_snapshot_id,
        )
        .where(
            ResearchPredictionSnapshot.game_id == game_id,
            ResearchPredictionSnapshot.model_version == model_version,
            ResearchPredictionSnapshot.locked_at.is_not(None),
        )
        .order_by(
            RankingSnapshot.week.desc(),
            ResearchPredictionSnapshot.created_at.desc(),
        )
        .limit(1)
    )
