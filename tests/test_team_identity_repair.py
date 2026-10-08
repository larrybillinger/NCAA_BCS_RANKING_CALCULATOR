from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ncaa_rankings.web.db import Base
from ncaa_rankings.web.models import (
    Game,
    PredictionSnapshot,
    RankingEntry,
    Team,
    TeamSeason,
)
from ncaa_rankings.web.ranking_service import calculate_week_snapshot
from ncaa_rankings.web.repair_team_identity import repair_known_team_identities

MODEL = "division_i_weighted_v5"
KICKOFF = datetime(2026, 9, 5, 18, 0, tzinfo=timezone.utc)


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)()


def _teams(session: Session) -> tuple[Team, Team, Team]:
    legacy = Team(name="Penn", slug="penn")
    canonical = Team(name="Pennsylvania", slug="pennsylvania", cfbd_id=219)
    opponent = Team(name="Opponent", slug="opponent", cfbd_id=999)
    session.add_all([legacy, canonical, opponent])
    session.flush()
    for team, conference in ((legacy, None), (canonical, "Ivy League"), (opponent, "Test")):
        session.add(TeamSeason(
            team_id=team.id,
            season=2026,
            subdivision="FCS",
            conference=conference,
            active=True,
        ))
    return legacy, canonical, opponent


def _game(session: Session, week: int, home: Team, away: Team, *, final: bool = True) -> Game:
    game = Game(
        provider="cfbd",
        provider_game_id=f"repair-{week}-{home.id}-{away.id}",
        season=2026,
        week=week,
        season_type="regular",
        start_time=KICKOFF + timedelta(days=7 * (week - 1)),
        completed=final,
        home_team_id=home.id,
        away_team_id=away.id,
        home_subdivision="FCS",
        away_subdivision="FCS",
        home_points=24 if final else None,
        away_points=17 if final else None,
    )
    session.add(game)
    return game


def _entry_team_ids(session: Session, snapshot_id: int) -> set[int]:
    return set(session.scalars(
        select(RankingEntry.team_id).where(RankingEntry.snapshot_id == snapshot_id)
    ))


def test_repair_keeps_frozen_weeks_and_locked_predictions():
    session = _session()
    legacy, canonical, opponent = _teams(session)
    _game(session, 1, canonical, opponent)
    week_two = _game(session, 2, opponent, canonical, final=False)
    session.commit()

    week_one = calculate_week_snapshot(session, 2026, 1)
    assert legacy.id in _entry_team_ids(session, week_one.id)
    locked = PredictionSnapshot(
        game_id=week_two.id,
        ranking_snapshot_id=week_one.id,
        predictor_version="rank_gap_v3",
        created_at=week_two.start_time - timedelta(days=2),
        official=True,
        locked_at=week_two.start_time,
        projected_home_points=20.0,
        projected_away_points=24.0,
        projected_margin=-4.0,
        home_win_probability=0.4,
    )
    session.add(locked)
    session.commit()

    results = repair_known_team_identities(session, season=2026, model_version=MODEL)

    assert len(results) == 1
    assert results[0].repaired is True
    assert results[0].preserved_weeks == [1]

    # The published week and the prediction locked against it are untouched.
    session.refresh(week_one)
    assert legacy.id in _entry_team_ids(session, week_one.id)
    session.refresh(locked)
    assert locked.official is True
    assert locked.ranking_snapshot_id == week_one.id

    legacy_season = session.scalar(
        select(TeamSeason).where(TeamSeason.team_id == legacy.id)
    )
    assert legacy_season.active is False

    # The next ranking uses the corrected pool.
    week_two.completed, week_two.home_points, week_two.away_points = True, 10, 31
    session.commit()
    next_week = calculate_week_snapshot(session, 2026, 2)
    assert _entry_team_ids(session, next_week.id) == {canonical.id, opponent.id}


def test_repair_is_idempotent():
    session = _session()
    _teams(session)
    session.commit()

    first = repair_known_team_identities(session, season=2026, model_version=MODEL)
    second = repair_known_team_identities(session, season=2026, model_version=MODEL)

    assert [result.repaired for result in first] == [True]
    assert [result.repaired for result in second] == [False]


def test_repair_refuses_when_legacy_row_has_frozen_results():
    session = _session()
    legacy, canonical, opponent = _teams(session)
    _game(session, 1, legacy, opponent)
    session.commit()
    calculate_week_snapshot(session, 2026, 1)

    with pytest.raises(RuntimeError, match="frozen official rankings"):
        repair_known_team_identities(session, season=2026, model_version=MODEL)

    legacy_season = session.scalar(
        select(TeamSeason).where(TeamSeason.team_id == legacy.id)
    )
    assert legacy_season.active is True
