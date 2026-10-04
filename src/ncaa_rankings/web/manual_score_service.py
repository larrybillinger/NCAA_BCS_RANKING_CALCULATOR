from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from .models import Game, ManualScoreAudit, Team
from .prediction_service import generate_predictions_for_snapshot, lock_started_predictions
from .ranking_service import (
    calculate_all_new_complete_weeks,
    get_snapshot,
    latest_snapshot,
)


class ManualScoreError(ValueError):
    """Raised when an administrator attempts an unsafe manual score change."""


def admin_game_rows(
    session: Session,
    season: int,
    week: int,
    *,
    search: str | None = None,
) -> list[dict]:
    home = aliased(Team)
    away = aliased(Team)
    query = (
        select(Game, home, away)
        .join(home, home.id == Game.home_team_id)
        .join(away, away.id == Game.away_team_id)
        .where(
            Game.season == season,
            Game.week == week,
            Game.season_type == "regular",
        )
        .order_by(Game.start_time, away.name, home.name)
    )
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(or_(home.name.ilike(pattern), away.name.ilike(pattern)))

    frozen = get_snapshot(session, season, week) is not None
    return [
        {
            "game": game,
            "home": home_team,
            "away": away_team,
            "week_frozen": frozen,
        }
        for game, home_team, away_team in session.execute(query)
    ]


def _editable_game(session: Session, game_id: int) -> Game:
    game = session.get(Game, game_id)
    if game is None:
        raise ManualScoreError("Game not found.")
    if get_snapshot(session, game.season, game.week) is not None:
        raise ManualScoreError(
            f"Week {game.week} is already frozen for the active ranking model. "
            "Its game scores cannot be changed from the score desk."
        )
    return game


def _validated_score(value: int | None, label: str) -> int | None:
    if value is None:
        return None
    if value < 0 or value > 255:
        raise ManualScoreError(f"{label} must be between 0 and 255.")
    return value


def set_manual_score(
    session: Session,
    *,
    game_id: int,
    home_points: int | None,
    away_points: int | None,
    completed: bool,
    note: str | None,
    actor: str,
) -> tuple[Game, list[int]]:
    """Save a manual score and run the normal post-result pipeline.

    Prediction locking happens before the score changes so the official
    pregame ledger remains independent of the result being entered.
    """
    lock_started_predictions(session)
    game = _editable_game(session, game_id)

    home_points = _validated_score(home_points, "Home score")
    away_points = _validated_score(away_points, "Away score")

    if (home_points is None) != (away_points is None):
        raise ManualScoreError("Enter both team scores or leave both blank.")
    if completed and (home_points is None or away_points is None):
        raise ManualScoreError("A final game must have both team scores.")

    clean_note = (note or "").strip()[:1000] or None
    previous_home = game.home_points
    previous_away = game.away_points
    previous_completed = bool(game.completed)

    game.home_points = home_points
    game.away_points = away_points
    game.completed = completed
    game.manual_score_override = True
    game.manual_score_updated_at = datetime.now(timezone.utc)
    game.manual_score_note = clean_note
    game.manual_score_actor = actor
    session.add(game)
    session.add(
        ManualScoreAudit(
            game_id=game.id,
            action="set_override",
            actor=actor,
            note=clean_note,
            previous_home_points=previous_home,
            previous_away_points=previous_away,
            previous_completed=previous_completed,
            new_home_points=home_points,
            new_away_points=away_points,
            new_completed=completed,
        )
    )
    session.commit()

    created_weeks = calculate_all_new_complete_weeks(session, game.season)
    current_snapshot = latest_snapshot(session, game.season)
    if current_snapshot is not None:
        generate_predictions_for_snapshot(session, current_snapshot)

    return game, created_weeks


def release_manual_score(
    session: Session,
    *,
    game_id: int,
    note: str | None,
    actor: str,
) -> Game:
    """Return a game to CFBD control without changing its current score immediately."""
    game = _editable_game(session, game_id)
    clean_note = (note or "").strip()[:1000] or None

    session.add(
        ManualScoreAudit(
            game_id=game.id,
            action="release_override",
            actor=actor,
            note=clean_note,
            previous_home_points=game.home_points,
            previous_away_points=game.away_points,
            previous_completed=bool(game.completed),
            new_home_points=game.home_points,
            new_away_points=game.away_points,
            new_completed=bool(game.completed),
        )
    )
    game.manual_score_override = False
    game.manual_score_updated_at = datetime.now(timezone.utc)
    game.manual_score_note = clean_note
    game.manual_score_actor = actor
    session.add(game)
    session.commit()
    return game
