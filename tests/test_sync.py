from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ncaa_rankings.web import worker
from ncaa_rankings.web.cfbd import (
    CFBDClient,
    CFBDRateLimitError,
    sync_games,
    sync_team_context,
)
from ncaa_rankings.web.db import Base
from ncaa_rankings.web.models import Game, Team, TeamSeason
from ncaa_rankings.web import models as _models  # noqa: F401
from ncaa_rankings.web.sync_schedule import (
    LIVE_WINDOW,
    poll_delay_minutes,
    schedule_state,
    stale_after,
)


def test_cfbd_429_is_exposed_as_rate_limit(monkeypatch):
    request = httpx.Request("GET", "https://api.collegefootballdata.com/games")
    response = httpx.Response(
        429,
        request=request,
        headers={"Retry-After": "120"},
    )

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    client = CFBDClient(api_key="test-key")
    with pytest.raises(CFBDRateLimitError) as caught:
        client.games(2026, week=4)

    assert caught.value.retry_after_seconds == 120


def test_games_sync_uses_one_unfiltered_provider_call():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    class FakeClient:
        calls = 0

        def games(
            self,
            year,
            *,
            week=None,
            classification=None,
            season_type="regular",
        ):
            self.calls += 1
            assert classification is None
            return []

    client = FakeClient()
    with SessionFactory() as session:
        sync_games(session, client, 2026, week=4)

    assert client.calls == 1


def test_rate_limit_backoff_grows_and_caps():
    settings = SimpleNamespace(
        sync_rate_limit_base_minutes=360,
        sync_rate_limit_max_minutes=1440,
    )

    assert worker._rate_limit_delay_minutes(1, settings) == 360
    assert worker._rate_limit_delay_minutes(2, settings) == 720
    assert worker._rate_limit_delay_minutes(3, settings) == 1440
    assert worker._rate_limit_delay_minutes(10, settings) == 1440
    assert worker._rate_limit_delay_minutes(1, settings, retry_after_seconds=30_000) == 500


def test_prediction_locking_happens_before_provider_failure(monkeypatch):
    order = []

    class FakeSessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeClient:
        configured = True

    monkeypatch.setattr(worker, "SessionLocal", lambda: FakeSessionContext())
    monkeypatch.setattr(worker, "bootstrap_bundled_rankings", lambda session: None)
    monkeypatch.setattr(
        worker,
        "lock_started_predictions",
        lambda session: order.append("lock") or 0,
    )
    monkeypatch.setattr(worker, "CFBDClient", lambda: FakeClient())

    def fail_sync(*args, **kwargs):
        order.append("sync")
        raise CFBDRateLimitError()

    monkeypatch.setattr(worker, "sync_games", fail_sync)

    with pytest.raises(CFBDRateLimitError):
        worker._sync_cycle(full_schedule=True)

    assert order == ["lock", "sync"]



CENTRAL = ZoneInfo("America/Chicago")
CADENCE = SimpleNamespace(sync_live_minutes=60, sync_idle_minutes=1440)


def _schedule_session(*games):
    """In-memory DB holding (kickoff, completed) Division I games."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)()
    home, away = Team(name="Home", slug="home"), Team(name="Away", slug="away")
    session.add_all([home, away])
    session.flush()
    for index, (kickoff, completed) in enumerate(games):
        session.add(Game(
            provider="cfbd",
            provider_game_id=str(index),
            season=2026,
            week=6,
            season_type="regular",
            start_time=kickoff.astimezone(timezone.utc),
            completed=completed,
            home_team_id=home.id,
            away_team_id=away.id,
            home_subdivision="FBS",
            away_subdivision="FBS",
        ))
    session.commit()
    return session


def _delay(session, now):
    now = now.astimezone(timezone.utc)
    return poll_delay_minutes(now, schedule_state(session, 2026, now), CADENCE)


def test_weeknight_game_in_progress_uses_live_cadence():
    kickoff = datetime(2026, 10, 7, 18, 30, tzinfo=CENTRAL)  # Wednesday
    session = _schedule_session((kickoff, False))

    assert _delay(session, kickoff + timedelta(hours=1)) == 60


def test_saturday_game_after_local_midnight_stays_live():
    kickoff = datetime(2026, 10, 10, 21, 30, tzinfo=CENTRAL)  # Saturday night
    session = _schedule_session((kickoff, False))

    sunday_early = datetime(2026, 10, 11, 0, 45, tzinfo=CENTRAL)
    assert _delay(session, sunday_early) == 60


def test_idle_worker_wakes_one_live_interval_after_next_kickoff():
    kickoff = datetime(2026, 10, 7, 18, 30, tzinfo=CENTRAL)
    session = _schedule_session((kickoff, False))

    assert _delay(session, kickoff - timedelta(hours=3)) == 3 * 60 + 60


def test_idle_worker_uses_daily_cadence_with_no_upcoming_games():
    kickoff = datetime(2026, 10, 3, 14, 0, tzinfo=CENTRAL)
    session = _schedule_session((kickoff, True))

    assert _delay(session, kickoff + timedelta(days=1)) == 1440


def test_unfinished_game_stops_counting_as_live_after_window():
    kickoff = datetime(2026, 10, 7, 18, 30, tzinfo=CENTRAL)
    session = _schedule_session((kickoff, False))
    now = (kickoff + LIVE_WINDOW + timedelta(minutes=1)).astimezone(timezone.utc)

    assert schedule_state(session, 2026, now).live_games == 0
    assert _delay(session, now) == 1440


def test_stale_threshold_is_tight_only_while_games_are_live():
    live = SimpleNamespace(live_games=2, next_kickoff=None)
    idle = SimpleNamespace(live_games=0, next_kickoff=None)

    assert stale_after(live, CADENCE) == timedelta(minutes=90)
    assert stale_after(idle, CADENCE) == timedelta(hours=36)


def test_team_context_sync_stores_home_timezone_and_elevation():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    class FakeClient:
        def teams(self, year):
            assert year == 2026
            return [
                {
                    "id": 123,
                    "school": "Context State",
                    "classification": "fbs",
                    "conference": "Test",
                    "location": {
                        "id": 456,
                        "name": "Context Stadium",
                        "timezone": "America/Denver",
                        "elevation": "5280",
                    },
                }
            ]

    with SessionFactory() as session:
        updated = sync_team_context(session, FakeClient(), 2026)
        row = session.query(TeamSeason).one()

        assert updated == 1
        assert row.home_venue_id == 456
        assert row.home_venue == "Context Stadium"
        assert row.home_timezone == "America/Denver"
        assert row.home_elevation_ft == 5280.0
        assert row.home_context_source == "cfbd:/teams"
        assert row.home_context_updated_at is not None



def test_full_schedule_cycle_refreshes_static_team_context(monkeypatch):
    calls = []

    class FakeSessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeClient:
        configured = True

    settings = SimpleNamespace(season=2026)
    snapshot = SimpleNamespace(week=5)

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "SessionLocal", lambda: FakeSessionContext())
    monkeypatch.setattr(worker, "CFBDClient", lambda: FakeClient())
    monkeypatch.setattr(worker, "bootstrap_bundled_rankings", lambda session: None)
    monkeypatch.setattr(worker, "lock_started_predictions", lambda session: 0)
    monkeypatch.setattr(
        worker,
        "lock_started_research_predictions",
        lambda session: 0,
    )
    monkeypatch.setattr(
        worker,
        "sync_games",
        lambda session, client, season: calls.append("games") or 0,
    )
    monkeypatch.setattr(
        worker,
        "sync_team_context",
        lambda session, client, season: calls.append("context") or 1,
    )
    monkeypatch.setattr(
        worker,
        "calculate_all_new_complete_weeks",
        lambda session, season: [],
    )
    monkeypatch.setattr(
        worker,
        "latest_snapshot",
        lambda session, season: snapshot,
    )
    monkeypatch.setattr(
        worker,
        "generate_predictions_for_snapshot",
        lambda session, current: 0,
    )
    monkeypatch.setattr(
        worker,
        "generate_research_predictions_for_snapshot",
        lambda session, current: 0,
    )

    worker._sync_cycle(full_schedule=True)

    assert calls == ["games", "context"]
