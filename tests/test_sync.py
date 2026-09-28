from datetime import datetime
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
)
from ncaa_rankings.web.db import Base
from ncaa_rankings.web import models as _models  # noqa: F401


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



def test_sync_schedule_is_hourly_on_saturday_and_daily_otherwise():
    settings = SimpleNamespace(
        timezone="America/Chicago",
        sync_saturday_minutes=60,
        sync_other_days_minutes=1440,
    )

    saturday_noon = datetime(2026, 9, 26, 12, 0, tzinfo=ZoneInfo("America/Chicago"))
    sunday_noon = datetime(2026, 9, 27, 12, 0, tzinfo=ZoneInfo("America/Chicago"))

    assert worker._scheduled_delay_minutes(saturday_noon, settings) == 60
    assert worker._scheduled_delay_minutes(sunday_noon, settings) == 1440


def test_friday_sleep_wakes_at_saturday_midnight():
    settings = SimpleNamespace(
        timezone="America/Chicago",
        sync_saturday_minutes=60,
        sync_other_days_minutes=1440,
    )

    friday_late = datetime(2026, 9, 25, 23, 30, tzinfo=ZoneInfo("America/Chicago"))

    assert worker._scheduled_delay_minutes(friday_late, settings) == 30
