from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ncaa_rankings.web.db import Base
from ncaa_rankings.web.models import Game, Team, TeamSeason
from ncaa_rankings.web.research_context_service import (
    build_static_game_context,
    timezone_crossings,
)


def test_timezone_crossings_uses_kickoff_date_offsets():
    kickoff = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)

    assert timezone_crossings(
        "America/Chicago",
        "America/Denver",
        kickoff,
    ) == 1
    assert timezone_crossings(
        "America/New_York",
        "America/Los_Angeles",
        kickoff,
    ) == 3


def test_normal_home_game_penalizes_only_traveling_team_static_context():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        home = Team(name="High Home", slug="high-home")
        away = Team(name="Low Away", slug="low-away")
        session.add_all([home, away])
        session.flush()
        session.add_all([
            TeamSeason(
                team_id=home.id,
                season=2026,
                subdivision="FBS",
                conference="Test",
                home_venue_id=10,
                home_venue="High Field",
                home_timezone="America/Denver",
                home_elevation_ft=5280.0,
                home_context_source="cfbd:/teams",
            ),
            TeamSeason(
                team_id=away.id,
                season=2026,
                subdivision="FBS",
                conference="Test",
                home_venue_id=20,
                home_venue="Low Field",
                home_timezone="America/Chicago",
                home_elevation_ft=500.0,
                home_context_source="cfbd:/teams",
            ),
        ])
        game = Game(
            provider="test",
            provider_game_id="ctx1",
            season=2026,
            week=6,
            start_time=datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc),
            neutral_site=False,
            home_team_id=home.id,
            away_team_id=away.id,
            home_subdivision="FBS",
            away_subdivision="FBS",
            venue_id=10,
            venue="High Field",
        )
        session.add(game)
        session.commit()

        snapshot = build_static_game_context(session, game)

        assert snapshot.context.home_timezone_crossings == 0
        assert snapshot.context.away_timezone_crossings == 1
        assert snapshot.context.home_altitude_disadvantage is False
        assert snapshot.context.away_altitude_disadvantage is True
        assert snapshot.features["venue_resolution"] == "home_venue_match"


def test_close_high_altitude_matchup_has_no_altitude_penalty():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        colorado = Team(name="Colorado", slug="colorado")
        byu = Team(name="BYU", slug="byu")
        session.add_all([colorado, byu])
        session.flush()
        session.add_all([
            TeamSeason(
                team_id=colorado.id,
                season=2026,
                subdivision="FBS",
                conference="Big 12",
                home_venue_id=30,
                home_timezone="America/Denver",
                home_elevation_ft=5300.0,
            ),
            TeamSeason(
                team_id=byu.id,
                season=2026,
                subdivision="FBS",
                conference="Big 12",
                home_venue_id=40,
                home_timezone="America/Denver",
                home_elevation_ft=4500.0,
            ),
        ])
        game = Game(
            provider="test",
            provider_game_id="ctx2",
            season=2026,
            week=7,
            start_time=datetime(2026, 10, 17, 18, 0, tzinfo=timezone.utc),
            neutral_site=False,
            home_team_id=colorado.id,
            away_team_id=byu.id,
            home_subdivision="FBS",
            away_subdivision="FBS",
            venue_id=30,
        )
        session.add(game)
        session.commit()

        snapshot = build_static_game_context(session, game)

        assert snapshot.context.away_altitude_disadvantage is False
