from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ncaa_rankings.web import worker
from ncaa_rankings.web.cfbd import (
    CFBDClient,
    CFBDRateLimitError,
    sync_games,
    sync_team_context,
    upsert_team,
)
from ncaa_rankings.web.db import Base
from ncaa_rankings.web.models import (
    Game,
    PredictionSnapshot,
    RankingSnapshot,
    Team,
    TeamSeason,
)
from ncaa_rankings.web import models as _models  # noqa: F401
from ncaa_rankings.web.prediction_service import (
    HYBRID_PREDICTOR_VERSION,
    lock_started_predictions,
)
from ncaa_rankings.web.sync_schedule import (
    LIVE_WINDOW,
    poll_delay_minutes,
    schedule_state,
    stale_after,
)
from ncaa_rankings.web.team_identity import reconcile_active_roster
from ncaa_rankings.web.utils import as_utc


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


def test_prediction_lock_and_generation_happen_before_provider_failure(monkeypatch):
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
    monkeypatch.setattr(
        worker,
        "_generate_active_predictions",
        lambda session, settings: order.append("generate"),
    )
    monkeypatch.setattr(worker, "CFBDClient", lambda: FakeClient())

    def fail_sync(*args, **kwargs):
        order.append("sync")
        raise CFBDRateLimitError()

    monkeypatch.setattr(worker, "sync_games", fail_sync)

    with pytest.raises(CFBDRateLimitError):
        worker._sync_cycle(full_schedule=True)

    assert order == ["lock", "generate", "sync"]


CENTRAL = ZoneInfo("America/Chicago")
CADENCE = SimpleNamespace(sync_live_minutes=60, sync_idle_minutes=1440)


def _schedule_session(*games):
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
    kickoff = datetime(2026, 10, 7, 18, 30, tzinfo=CENTRAL)
    session = _schedule_session((kickoff, False))
    assert _delay(session, kickoff + timedelta(hours=1)) == 60


def test_saturday_game_after_local_midnight_stays_live():
    kickoff = datetime(2026, 10, 10, 21, 30, tzinfo=CENTRAL)
    session = _schedule_session((kickoff, False))
    sunday_early = datetime(2026, 10, 11, 0, 45, tzinfo=CENTRAL)
    assert _delay(session, sunday_early) == 60


def test_idle_worker_wakes_at_next_kickoff():
    kickoff = datetime(2026, 10, 7, 18, 30, tzinfo=CENTRAL)
    session = _schedule_session((kickoff, False))
    assert _delay(session, kickoff - timedelta(hours=3)) == 3 * 60


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


def test_kickoff_cycle_locks_pregame_prediction_immediately():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    kickoff = datetime(2026, 10, 7, 23, 30, tzinfo=timezone.utc)

    with SessionFactory() as session:
        home = Team(name="Kickoff Home", slug="kickoff-home")
        away = Team(name="Kickoff Away", slug="kickoff-away")
        session.add_all([home, away])
        session.flush()
        game = Game(
            provider="cfbd",
            provider_game_id="kickoff-lock",
            season=2026,
            week=6,
            season_type="regular",
            start_time=kickoff,
            completed=False,
            home_team_id=home.id,
            away_team_id=away.id,
            home_subdivision="FBS",
            away_subdivision="FBS",
        )
        snapshot = RankingSnapshot(
            season=2026,
            week=5,
            model_version="division_i_weighted_v5",
            official=True,
        )
        session.add_all([game, snapshot])
        session.flush()
        prediction = PredictionSnapshot(
            game_id=game.id,
            ranking_snapshot_id=snapshot.id,
            predictor_version=HYBRID_PREDICTOR_VERSION,
            created_at=kickoff - timedelta(hours=2),
            locks_at=kickoff,
            projected_home_points=24.0,
            projected_away_points=17.0,
            projected_margin=7.0,
            home_win_probability=0.7,
        )
        session.add(prediction)
        session.commit()

        assert lock_started_predictions(session, now=kickoff) == 1
        session.refresh(prediction)
        assert prediction.official is True
        assert as_utc(prediction.locked_at) == as_utc(game.start_time)


def test_known_provider_alias_reuses_legacy_team_row():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    with SessionFactory() as session:
        legacy = Team(name="Penn", slug="penn")
        session.add(legacy)
        session.flush()
        session.add(
            TeamSeason(
                team_id=legacy.id,
                season=2026,
                subdivision="FCS",
                conference="Ivy League",
                active=True,
            )
        )
        session.commit()

        resolved = upsert_team(
            session,
            cfbd_id=219,
            name="Pennsylvania",
            season=2026,
            classification="fcs",
            conference="Ivy League",
        )
        session.commit()

        teams = list(session.scalars(select(Team)))
        assert len(teams) == 1
        assert resolved.id == legacy.id
        assert resolved.cfbd_id == 219
        assert resolved.name == "Pennsylvania"


def test_roster_reconciliation_deactivates_only_missing_team_with_safe_coverage():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    with SessionFactory() as session:
        teams = [Team(name=f"Team {index}", slug=f"team-{index}") for index in range(10)]
        session.add_all(teams)
        session.flush()
        rows = [
            TeamSeason(
                team_id=team.id,
                season=2026,
                subdivision="FCS",
                active=True,
            )
            for team in teams
        ]
        session.add_all(rows)
        session.commit()

        deactivated = reconcile_active_roster(
            session,
            season=2026,
            seen_team_ids={team.id for team in teams[:9]},
        )
        session.commit()

        assert deactivated == 1
        assert rows[-1].active is False
        assert all(row.active for row in rows[:9])
