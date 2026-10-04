from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from ncaa_rankings.web import app as web_app
from ncaa_rankings.web.cfbd import upsert_game
from ncaa_rankings.web.db import Base
from ncaa_rankings.web.manual_score_service import (
    ManualScoreError,
    release_manual_score,
    set_manual_score,
)
from ncaa_rankings.web.models import (
    Game,
    ManualScoreAudit,
    RankingSnapshot,
    Team,
    TeamSeason,
)


def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def add_game(session: Session, *, week: int = 1, completed: bool = False) -> Game:
    home = Team(cfbd_id=1, name="Home Team", slug="home-team")
    away = Team(cfbd_id=2, name="Away Team", slug="away-team")
    session.add_all([home, away])
    session.flush()
    session.add_all([
        TeamSeason(team_id=home.id, season=2026, subdivision="FBS", active=True),
        TeamSeason(team_id=away.id, season=2026, subdivision="FBS", active=True),
    ])
    game = Game(
        provider="cfbd",
        provider_game_id="1001",
        season=2026,
        week=week,
        season_type="regular",
        start_time=datetime(2026, 9, 5, 18, 0, tzinfo=timezone.utc),
        completed=completed,
        home_team_id=home.id,
        away_team_id=away.id,
        home_subdivision="FBS",
        away_subdivision="FBS",
    )
    session.add(game)
    session.commit()
    return game


def test_manual_final_score_creates_override_audit_and_week_snapshot():
    SessionFactory = session_factory()
    with SessionFactory() as session:
        game = add_game(session)

        updated, created_weeks = set_manual_score(
            session,
            game_id=game.id,
            home_points=24,
            away_points=17,
            completed=True,
            note="CFBD unavailable",
            actor="admin",
        )

        assert updated.manual_score_override is True
        assert updated.home_points == 24
        assert updated.away_points == 17
        assert updated.completed is True
        assert created_weeks == [1]
        assert session.scalar(select(func.count()).select_from(ManualScoreAudit)) == 1

        snapshot = session.scalar(
            select(RankingSnapshot).where(
                RankingSnapshot.season == 2026,
                RankingSnapshot.week == 1,
                RankingSnapshot.model_version == "division_i_weighted_v5",
            )
        )
        assert snapshot is not None


def test_cfbd_does_not_overwrite_active_manual_score_override():
    SessionFactory = session_factory()
    with SessionFactory() as session:
        game = add_game(session)
        game.manual_score_override = True
        game.home_points = 24
        game.away_points = 17
        game.completed = True
        session.add(game)
        session.commit()

        upsert_game(session, {
            "id": 1001,
            "season": 2026,
            "week": 1,
            "seasonType": "regular",
            "startDate": "2026-09-05T18:00:00Z",
            "completed": True,
            "neutralSite": False,
            "conferenceGame": False,
            "homeId": 1,
            "homeTeam": "Home Team",
            "homeClassification": "fbs",
            "homeConference": "Test",
            "homePoints": 99,
            "awayId": 2,
            "awayTeam": "Away Team",
            "awayClassification": "fbs",
            "awayConference": "Test",
            "awayPoints": 0,
            "venue": "Test Field",
        })
        session.commit()
        refreshed = session.get(Game, game.id)

        assert refreshed.manual_score_override is True
        assert refreshed.home_points == 24
        assert refreshed.away_points == 17


def test_release_override_returns_game_to_provider_control():
    SessionFactory = session_factory()
    with SessionFactory() as session:
        game = add_game(session, week=2)
        game.manual_score_override = True
        game.home_points = 10
        game.away_points = 7
        session.add(game)
        session.commit()

        released = release_manual_score(
            session,
            game_id=game.id,
            note="Provider recovered",
            actor="admin",
        )

        assert released.manual_score_override is False
        audits = list(
            session.scalars(
                select(ManualScoreAudit).where(ManualScoreAudit.game_id == game.id)
            )
        )
        assert audits[-1].action == "release_override"


def test_frozen_week_rejects_manual_score_change():
    SessionFactory = session_factory()
    with SessionFactory() as session:
        game = add_game(session)
        session.add(
            RankingSnapshot(
                season=2026,
                week=1,
                model_version="division_i_weighted_v5",
                official=True,
            )
        )
        session.commit()

        with pytest.raises(ManualScoreError, match="already frozen"):
            set_manual_score(
                session,
                game_id=game.id,
                home_points=24,
                away_points=17,
                completed=True,
                note=None,
                actor="admin",
            )


def test_admin_basic_credentials_and_csrf(monkeypatch):
    fake_settings = SimpleNamespace(
        admin_username="admin",
        admin_password="score-secret",
    )
    monkeypatch.setattr(web_app, "settings", fake_settings)

    actor = web_app._require_admin(
        HTTPBasicCredentials(username="admin", password="score-secret")
    )
    assert actor == "admin"

    token = web_app._admin_csrf_token()
    web_app._verify_admin_csrf(token)

    with pytest.raises(HTTPException) as bad_password:
        web_app._require_admin(
            HTTPBasicCredentials(username="admin", password="wrong")
        )
    assert bad_password.value.status_code == 401

    with pytest.raises(HTTPException) as bad_csrf:
        web_app._verify_admin_csrf("wrong-token")
    assert bad_csrf.value.status_code == 403
