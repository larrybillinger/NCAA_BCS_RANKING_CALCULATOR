from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ncaa_rankings.web.db import Base
from ncaa_rankings.web.models import Game, RankingEntry, Team, TeamSeason
from ncaa_rankings.web.ranking_service import calculate_week_snapshot, latest_snapshot
from ncaa_rankings.web.repair_team_identity import repair_known_team_identities


def test_duplicate_team_repair_rebuilds_active_model_without_legacy_team():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    with SessionFactory() as session:
        legacy = Team(name="Penn", slug="penn")
        canonical = Team(name="Pennsylvania", slug="pennsylvania", cfbd_id=219)
        opponent = Team(name="Opponent", slug="opponent", cfbd_id=999)
        session.add_all([legacy, canonical, opponent])
        session.flush()
        session.add_all(
            [
                TeamSeason(
                    team_id=legacy.id,
                    season=2026,
                    subdivision="FCS",
                    conference=None,
                    active=True,
                ),
                TeamSeason(
                    team_id=canonical.id,
                    season=2026,
                    subdivision="FCS",
                    conference="Ivy League",
                    active=True,
                ),
                TeamSeason(
                    team_id=opponent.id,
                    season=2026,
                    subdivision="FCS",
                    conference="Test",
                    active=True,
                ),
            ]
        )
        session.add(
            Game(
                provider="cfbd",
                provider_game_id="repair-week-1",
                season=2026,
                week=1,
                season_type="regular",
                start_time=datetime(2026, 9, 5, 18, 0, tzinfo=timezone.utc),
                completed=True,
                home_team_id=canonical.id,
                away_team_id=opponent.id,
                home_subdivision="FCS",
                away_subdivision="FCS",
                home_points=24,
                away_points=17,
            )
        )
        session.commit()

        corrupted = calculate_week_snapshot(session, 2026, 1)
        corrupted_team_ids = set(
            session.scalars(
                select(RankingEntry.team_id).where(
                    RankingEntry.snapshot_id == corrupted.id
                )
            )
        )
        assert legacy.id in corrupted_team_ids
        assert len(corrupted_team_ids) == 3

        results = repair_known_team_identities(
            session,
            season=2026,
            model_version="division_i_weighted_v5",
        )
        assert len(results) == 1
        assert results[0].first_affected_week == 1
        assert results[0].removed_weeks == [1]
        assert results[0].rebuilt_weeks == [1]

        rebuilt = latest_snapshot(session, 2026)
        rebuilt_team_ids = set(
            session.scalars(
                select(RankingEntry.team_id).where(
                    RankingEntry.snapshot_id == rebuilt.id
                )
            )
        )
        assert legacy.id not in rebuilt_team_ids
        assert rebuilt_team_ids == {canonical.id, opponent.id}

        legacy_season = session.scalar(
            select(TeamSeason).where(
                TeamSeason.team_id == legacy.id,
                TeamSeason.season == 2026,
            )
        )
        assert legacy_season.active is False


def test_duplicate_team_repair_is_idempotent_after_first_run():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    with SessionFactory() as session:
        legacy = Team(name="Penn", slug="penn")
        canonical = Team(name="Pennsylvania", slug="pennsylvania", cfbd_id=219)
        session.add_all([legacy, canonical])
        session.flush()
        session.add_all(
            [
                TeamSeason(
                    team_id=legacy.id,
                    season=2026,
                    subdivision="FCS",
                    active=True,
                ),
                TeamSeason(
                    team_id=canonical.id,
                    season=2026,
                    subdivision="FCS",
                    conference="Ivy League",
                    active=True,
                ),
            ]
        )
        session.commit()

        first = repair_known_team_identities(
            session,
            season=2026,
            model_version="division_i_weighted_v5",
        )
        second = repair_known_team_identities(
            session,
            season=2026,
            model_version="division_i_weighted_v5",
        )

        assert len(first) == 1
        assert len(second) == 1
        assert first[0].removed_weeks == []
        assert second[0].removed_weeks == []
