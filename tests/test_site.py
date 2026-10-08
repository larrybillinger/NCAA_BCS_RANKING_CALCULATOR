import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ncaa_rankings.web.app import app
from ncaa_rankings.web.cfbd import upsert_game
from ncaa_rankings.web.config import get_settings
from ncaa_rankings.web.db import Base, get_session
from ncaa_rankings.web.memo import session_memo
from ncaa_rankings.web.models import Game, PredictionSnapshot, RankingSnapshot
from ncaa_rankings.web.prediction_service import (
    HYBRID_PREDICTOR_VERSION,
    generate_predictions_for_snapshot,
    lock_started_predictions,
    retrocast_game,
)
from ncaa_rankings.web.ranking_service import (
    calculate_all_new_complete_weeks,
    latest_snapshot,
)
from ncaa_rankings.web.stats_service import overall_metrics
from ncaa_rankings.web.view_service import game_rows_for_week

SEASON = 2026
KICKOFF = datetime(2026, 9, 5, 18, 0, tzinfo=timezone.utc)
TEAMS = {
    "Alpha": ("fbs", "SEC"),
    "Bravo": ("fbs", "SEC"),
    "Charlie": ("fbs", "Big Ten"),
    "Delta": ("fbs", "Big Ten"),
    "Echo": ("fcs", "Big Sky"),
    "Foxtrot": ("fcs", "Big Sky"),
}
TEAM_IDS = {name: index + 1 for index, name in enumerate(TEAMS)}
SCHEDULE = [
    (1, "Alpha", "Echo", 42, 10),
    (1, "Charlie", "Bravo", 17, 24),
    (1, "Foxtrot", "Delta", 13, 31),
    (2, "Bravo", "Delta", 28, 21),
    (2, "Echo", "Charlie", 20, 27),
    (2, "Alpha", "Foxtrot", 35, 3),
    (3, "Delta", "Alpha", None, None),
    (3, "Bravo", "Echo", None, None),
    (3, "Charlie", "Foxtrot", None, None),
]


def _payload(game_id: int, week: int, home: str, away: str, hp, ap) -> dict:
    return {
        "id": game_id,
        "season": SEASON,
        "week": week,
        "seasonType": "regular",
        "completed": hp is not None,
        "homeTeam": home,
        "awayTeam": away,
        "homeId": TEAM_IDS[home],
        "awayId": TEAM_IDS[away],
        "homeClassification": TEAMS[home][0],
        "awayClassification": TEAMS[away][0],
        "homeConference": TEAMS[home][1],
        "awayConference": TEAMS[away][1],
        "homePoints": hp,
        "awayPoints": ap,
        "startDate": (KICKOFF + timedelta(days=7 * (week - 1))).isoformat(),
    }


@pytest.fixture()
def season_db():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    with factory() as session:
        for game_id, row in enumerate(SCHEDULE, start=100):
            upsert_game(session, _payload(game_id, *row))
        session.commit()
        calculate_all_new_complete_weeks(session, SEASON)
        snapshot = latest_snapshot(session, SEASON)
        generate_predictions_for_snapshot(session, snapshot)
        session.execute(
            update(PredictionSnapshot).values(created_at=KICKOFF + timedelta(days=10))
        )
        session.commit()

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield factory
    app.dependency_overrides.pop(get_session, None)


def _header_cells(html: str) -> list[str]:
    head = re.search(r"<thead>(.*?)</thead>", html, re.S).group(1)
    return re.findall(r"<th[^>]*>([^<]*)</th>", head)


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/?week=1",
        "/?subdivision=FBS",
        "/?subdivision=FCS",
        "/?conference=SEC",
        "/?conference=SEC&subdivision=FCS",
        "/?q=alp",
        "/predictions",
        "/predictions?week=2",
        "/stats",
        "/stats?metric=brier",
        "/stats?metric=not-a-metric",
        "/teams",
        "/teams/alpha",
        "/teams/echo?as_of=1",
        "/method",
        "/tools/rank-calculator",
        "/tools/rank-calculator?home=alpha&away=echo",
        "/compare",
        "/compare?a=alpha&b=echo",
        "/health",
    ],
)
def test_public_pages_render(season_db, path):
    response = TestClient(app).get(path)
    assert response.status_code == 200, response.text[:500]


def test_all_teams_view_hides_scope_rank_columns(season_db):
    html = TestClient(app).get("/").text
    assert _header_cells(html) == ["Rank", "Team", "Div.", "Record", "Avg score", "Move"]


def test_subdivision_view_shows_subdivision_and_national_rank(season_db):
    html = TestClient(app).get("/?subdivision=FCS").text
    assert _header_cells(html) == ["FCS rank", "D-I", "Team", "Record", "Avg score", "Move"]
    ranks = re.findall(r'<td class="rank">(\d+)</td>', html)
    assert ranks == ["1", "2"]


def test_conference_view_shows_conference_subdivision_and_national_rank(season_db):
    html = TestClient(app).get("/?conference=Big Sky").text
    assert _header_cells(html) == [
        "Conf. rank", "FCS", "D-I", "Team", "Record", "Avg score", "Move",
    ]


def test_active_predictor_is_hybrid(season_db):
    assert get_settings().predictor_version == HYBRID_PREDICTOR_VERSION
    with season_db() as session:
        rows = session.scalars(select(PredictionSnapshot)).all()
        assert rows
        assert {row.predictor_version for row in rows} == {HYBRID_PREDICTOR_VERSION}


def test_official_ledger_ignores_retired_ranking_models_and_predictors(season_db):
    with season_db() as session:
        game = session.scalar(select(Game).where(Game.week == 3).order_by(Game.id))
        game.completed, game.home_points, game.away_points = True, 10, 30
        retired = RankingSnapshot(season=SEASON, week=2, model_version="division_i_weighted_v4")
        session.add(retired)
        session.flush()
        session.add(PredictionSnapshot(
            game_id=game.id,
            ranking_snapshot_id=retired.id,
            predictor_version="rank_gap_v3",
            created_at=KICKOFF,
            official=True,
            locked_at=game.start_time,
            projected_home_points=40.0,
            projected_away_points=0.0,
            projected_margin=40.0,
            home_win_probability=0.99,
        ))
        active_snapshot = latest_snapshot(session, SEASON)
        session.add(PredictionSnapshot(
            game_id=game.id,
            ranking_snapshot_id=active_snapshot.id,
            predictor_version="rank_gap_v3",
            created_at=KICKOFF,
            official=True,
            locked_at=game.start_time,
            projected_home_points=45.0,
            projected_away_points=0.0,
            projected_margin=45.0,
            home_win_probability=0.99,
        ))
        session.commit()

        assert lock_started_predictions(session, now=game.start_time) >= 1
        active = session.scalars(
            select(PredictionSnapshot)
            .join(RankingSnapshot, RankingSnapshot.id == PredictionSnapshot.ranking_snapshot_id)
            .where(
                PredictionSnapshot.game_id == game.id,
                PredictionSnapshot.predictor_version == HYBRID_PREDICTOR_VERSION,
                PredictionSnapshot.official.is_(True),
                RankingSnapshot.model_version == "division_i_weighted_v5",
            )
        ).all()
        assert len(active) == 1

        metrics = overall_metrics(session, SEASON)
        assert metrics.games == 1
        assert metrics.spread_mae == pytest.approx(abs(active[0].projected_margin - -20))


def test_hybrid_retrocast_is_the_active_historical_projection(season_db):
    with season_db() as session:
        game = session.scalar(select(Game).where(Game.week == 2).order_by(Game.id))
        projection = retrocast_game(session, game)
        assert projection is not None
        assert projection.detail["method"] == HYBRID_PREDICTOR_VERSION
        assert projection.detail["rank_weight"] == pytest.approx(0.4)
        assert projection.detail["offdef_weight"] == pytest.approx(0.6)


def test_session_memo_is_dropped_on_commit(season_db):
    calls = []
    with season_db() as session:
        def factory():
            calls.append(1)
            return len(calls)

        assert session_memo(session, "key", factory) == 1
        assert session_memo(session, "key", factory) == 1
        session.commit()
        assert session_memo(session, "key", factory) == 2


def test_conference_dropdown_follows_subdivision(season_db):
    html = TestClient(app).get("/?subdivision=FBS").text
    options = re.findall(r'<option value="([^"]+)"', html)
    assert options == ["Big Ten", "SEC"]


def test_all_filter_is_not_highlighted_inside_a_conference(season_db):
    html = TestClient(app).get("/?conference=SEC").text
    assert 'class="active" href="/?week=2">All' not in html
    assert 'class="active" href="/?week=2">All' in TestClient(app).get("/").text


def test_matchup_calculator_uses_hybrid_team_profiles(season_db):
    html = TestClient(app).get("/tools/rank-calculator?home=alpha&away=echo").text
    assert "Matchup calculator" in html
    assert "hybrid_core_v1" in html
    assert "calculator-result" in html
    assert "Alpha" in html
    assert "Echo" in html


def test_game_rows_never_display_a_tie_for_nonzero_hybrid_margin(season_db):
    with season_db() as session:
        game = session.scalar(select(Game).where(Game.week == 3).order_by(Game.id))
        prediction = session.scalar(
            select(PredictionSnapshot)
            .where(PredictionSnapshot.game_id == game.id)
            .order_by(PredictionSnapshot.id.desc())
        )
        prediction.projected_home_points = 30.4
        prediction.projected_away_points = 30.3
        prediction.projected_margin = 0.1
        prediction.home_win_probability = 0.51
        session.commit()

        rows = game_rows_for_week(session, SEASON, 3, as_of_week=2)
        row = next(item for item in rows if item["game"].id == game.id)
        assert row["display_home_points"] == 31
        assert row["display_away_points"] == 30


def test_week_dock_lists_scheduled_weeks_without_ellipsis(season_db):
    html = TestClient(app).get("/").text
    dock = re.search(r'<div class="week-row">(.*?)</div>', html, re.S).group(1)
    assert re.findall(r'class="week-link[^"]*"[^>]*>(\d+)</a>', dock) == ["1", "2", "3"]
    assert "…" not in dock


def test_sidebar_marks_data_stale_during_a_live_game(season_db, monkeypatch):
    from types import SimpleNamespace

    from ncaa_rankings.web import app as web_app
    from ncaa_rankings.web.models import SourceSyncRun

    monkeypatch.setattr(web_app, "CFBDClient", lambda: SimpleNamespace(configured=True))
    now = datetime.now(timezone.utc)
    with season_db() as session:
        session.add(SourceSyncRun(
            endpoint="/games",
            season=SEASON,
            status="ok",
            started_at=now - timedelta(hours=2),
            finished_at=now - timedelta(hours=2),
        ))
        session.commit()
        assert "CFBD OK" in TestClient(app).get("/").text

        game = session.scalar(select(Game).where(Game.week == 3).order_by(Game.id))
        game.start_time = now - timedelta(hours=1)
        session.commit()
        assert "CFBD stale" in TestClient(app).get("/").text
