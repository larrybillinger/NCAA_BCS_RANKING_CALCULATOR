from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ncaa_rankings.web.db import Base
from ncaa_rankings.web.models import (
    Game,
    RankingSnapshot,
    ResearchPredictionSnapshot,
    Team,
)
from ncaa_rankings.web.research_prediction_ledger import (
    lock_started_research_predictions,
)
from ncaa_rankings.web.research_prediction_service import (
    HYBRID_VERSION,
    normalize_nonnegative_scores,
    winner_consistent_display_scores,
)


def test_equal_shift_preserves_margin_when_score_would_be_negative():
    home, away, shift = normalize_nonnegative_scores(-7.0, 14.0)

    assert (home, away, shift) == (0.0, 21.0, 7.0)
    assert home - away == -21.0


def test_display_rounding_never_ties_against_nonzero_margin():
    assert winner_consistent_display_scores(27.4, 26.6, 0.8) == (27, 26)
    assert winner_consistent_display_scores(26.6, 27.4, -0.8) == (26, 27)

    # Both continuous scores round to 27, but the modeled winner is retained.
    assert winner_consistent_display_scores(26.6, 26.5, 0.1) == (28, 27)
    assert winner_consistent_display_scores(26.5, 26.6, -0.1) == (27, 28)

    # A truly even model is allowed to display a tie.
    assert winner_consistent_display_scores(26.5, 26.5, 0.0) == (27, 27)


def test_shadow_lock_uses_only_prediction_created_before_kickoff():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    kickoff = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)

    with Session(engine) as session:
        home = Team(name="Home", slug="home")
        away = Team(name="Away", slug="away")
        session.add_all([home, away])
        session.flush()

        game = Game(
            provider="test",
            provider_game_id="g1",
            season=2026,
            week=6,
            start_time=kickoff,
            completed=False,
            home_team_id=home.id,
            away_team_id=away.id,
            home_subdivision="FBS",
            away_subdivision="FBS",
        )
        snapshot_4 = RankingSnapshot(
            season=2026,
            week=4,
            model_version="division_i_weighted_v5",
            official=True,
        )
        snapshot_5 = RankingSnapshot(
            season=2026,
            week=5,
            model_version="division_i_weighted_v5",
            official=True,
        )
        session.add_all([game, snapshot_4, snapshot_5])
        session.flush()

        eligible = ResearchPredictionSnapshot(
            game_id=game.id,
            ranking_snapshot_id=snapshot_4.id,
            model_version=HYBRID_VERSION,
            created_at=kickoff - timedelta(hours=2),
            locks_at=kickoff,
            home_rank=10,
            away_rank=20,
            projected_home_points=28.2,
            projected_away_points=25.8,
            display_home_points=28,
            display_away_points=26,
            projected_margin=2.4,
            projected_total=54.0,
            home_win_probability=0.57,
            sample_size=100,
        )
        late = ResearchPredictionSnapshot(
            game_id=game.id,
            ranking_snapshot_id=snapshot_5.id,
            model_version=HYBRID_VERSION,
            created_at=kickoff + timedelta(minutes=1),
            locks_at=kickoff,
            home_rank=8,
            away_rank=20,
            projected_home_points=30.0,
            projected_away_points=24.0,
            display_home_points=30,
            display_away_points=24,
            projected_margin=6.0,
            projected_total=54.0,
            home_win_probability=0.65,
            sample_size=120,
        )
        session.add_all([eligible, late])
        session.commit()

        locked = lock_started_research_predictions(
            session,
            now=kickoff + timedelta(minutes=5),
        )

        assert locked == 1
        rows = list(
            session.scalars(
                select(ResearchPredictionSnapshot).order_by(
                    ResearchPredictionSnapshot.created_at
                )
            )
        )
        assert rows[0].locked_at is not None
        assert rows[1].locked_at is None
