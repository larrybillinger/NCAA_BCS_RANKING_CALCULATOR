from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Game, RankingEntry, RankingSnapshot, Team, TeamSeason
from .prediction_service import latest_prediction, retrocast_game
from .ranking_service import latest_snapshot


def available_ranking_weeks(session: Session, season: int) -> list[int]:
    settings = get_settings()
    return list(session.scalars(
        select(RankingSnapshot.week)
        .where(
            RankingSnapshot.season == season,
            RankingSnapshot.model_version == settings.model_version,
            RankingSnapshot.official.is_(True),
        )
        .order_by(RankingSnapshot.week)
    ))


def ranking_rows(
    session: Session,
    snapshot: RankingSnapshot,
    *,
    subdivision: str | None = None,
    search: str | None = None,
) -> list[dict]:
    query = (
        select(RankingEntry, Team, TeamSeason)
        .join(Team, Team.id == RankingEntry.team_id)
        .join(TeamSeason, (TeamSeason.team_id == Team.id) & (TeamSeason.season == snapshot.season))
        .where(RankingEntry.snapshot_id == snapshot.id)
        .order_by(RankingEntry.rank)
    )
    if subdivision in {"FBS", "FCS"}:
        query = query.where(TeamSeason.subdivision == subdivision)
    if search:
        query = query.where(Team.name.ilike(f"%{search.strip()}%"))

    rows = []
    for entry, team, team_season in session.execute(query):
        rows.append({
            "rank": entry.rank,
            "team": team,
            "subdivision": team_season.subdivision,
            "conference": team_season.conference,
            "record": f"{entry.wins}-{entry.losses}",
            "score": entry.score,
            "movement": entry.movement,
            "opponent_strength": entry.opponent_strength,
        })
    return rows


def _team_name(session: Session, team_id: int) -> Team | None:
    return session.get(Team, team_id)


def game_rows_for_week(
    session: Session,
    season: int,
    week: int,
    *,
    as_of_week: int | None = None,
) -> list[dict]:
    games = list(session.scalars(
        select(Game)
        .where(
            Game.season == season,
            Game.week == week,
            or_(Game.home_subdivision.in_(("FBS", "FCS")), Game.away_subdivision.in_(("FBS", "FCS"))),
        )
        .order_by(Game.start_time, Game.id)
    ))
    rows: list[dict] = []
    now = datetime.now(timezone.utc)
    for game in games:
        home = _team_name(session, game.home_team_id)
        away = _team_name(session, game.away_team_id)
        prediction = None
        prediction_kind = None
        prediction_source_week = None

        if game.completed or (game.start_time and game.start_time <= now):
            prediction = latest_prediction(session, game.id, official_only=True)
            if prediction is not None:
                prediction_kind = "official"
                prediction_source_week = prediction.ranking_snapshot.week

        if prediction is None and not game.completed:
            prediction = latest_prediction(session, game.id, as_of_week=as_of_week)
            if prediction is not None:
                prediction_kind = "current"
                prediction_source_week = prediction.ranking_snapshot.week

        if prediction is None and game.completed:
            prediction = retrocast_game(session, game)
            if prediction is not None:
                prediction_kind = "retrocast"
                prediction_source_week = game.week - 1

        rows.append({
            "game": game,
            "home": home,
            "away": away,
            "prediction": prediction,
            "prediction_kind": prediction_kind,
            "prediction_source_week": prediction_source_week,
            "actual_margin": (game.home_points - game.away_points if game.home_points is not None and game.away_points is not None else None),
        })
    return rows


def team_schedule_rows(
    session: Session,
    team: Team,
    season: int,
    *,
    as_of_week: int | None = None,
) -> list[dict]:
    games = list(session.scalars(
        select(Game)
        .where(Game.season == season, or_(Game.home_team_id == team.id, Game.away_team_id == team.id))
        .order_by(Game.week, Game.start_time, Game.id)
    ))
    now = datetime.now(timezone.utc)
    rows = []
    for game in games:
        is_home = game.home_team_id == team.id
        opponent_id = game.away_team_id if is_home else game.home_team_id
        opponent = _team_name(session, opponent_id)
        prediction = None
        prediction_kind = None
        prediction_source_week = None
        official_prediction = latest_prediction(session, game.id, official_only=True)

        if game.completed or (game.start_time and game.start_time <= now):
            prediction = official_prediction
            if prediction is not None:
                prediction_kind = "official"
                prediction_source_week = prediction.ranking_snapshot.week

        if prediction is None and not game.completed:
            prediction = latest_prediction(session, game.id, as_of_week=as_of_week)
            if prediction is not None:
                prediction_kind = "current"
                prediction_source_week = prediction.ranking_snapshot.week

        if prediction is None and game.completed:
            prediction = retrocast_game(session, game)
            if prediction is not None:
                prediction_kind = "retrocast"
                prediction_source_week = game.week - 1

        rows.append({
            "game": game,
            "opponent": opponent,
            "is_home": is_home,
            "prediction": prediction,
            "prediction_kind": prediction_kind,
            "prediction_source_week": prediction_source_week,
            "official_prediction": official_prediction,
        })
    return rows


def team_ranking_history(session: Session, team_id: int, season: int) -> list[dict]:
    settings = get_settings()
    rows = session.execute(
        select(RankingSnapshot, RankingEntry)
        .join(RankingEntry, RankingEntry.snapshot_id == RankingSnapshot.id)
        .where(
            RankingSnapshot.season == season,
            RankingSnapshot.model_version == settings.model_version,
            RankingSnapshot.official.is_(True),
            RankingEntry.team_id == team_id,
        )
        .order_by(RankingSnapshot.week)
    )
    return [{
        "week": snapshot.week,
        "rank": entry.rank,
        "score": entry.score,
        "record": f"{entry.wins}-{entry.losses}",
        "movement": entry.movement,
    } for snapshot, entry in rows]


def team_current_entry(session: Session, team_id: int, season: int) -> RankingEntry | None:
    snapshot = latest_snapshot(session, season)
    if snapshot is None:
        return None
    return session.scalar(select(RankingEntry).where(
        RankingEntry.snapshot_id == snapshot.id,
        RankingEntry.team_id == team_id,
    ))


def all_teams(session: Session, season: int) -> list[tuple[Team, TeamSeason]]:
    return list(session.execute(
        select(Team, TeamSeason)
        .join(TeamSeason, TeamSeason.team_id == Team.id)
        .where(TeamSeason.season == season, TeamSeason.subdivision.in_(("FBS", "FCS")))
        .order_by(Team.name)
    ).all())
