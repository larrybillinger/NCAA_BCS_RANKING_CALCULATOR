from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import logging
import math
import time

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .bootstrap import bootstrap_bundled_rankings
from .cfbd import (
    CFBDClient,
    CFBDRateLimitError,
    sync_game_team_stats,
    sync_games,
)
from .config import Settings, get_settings
from .db import SessionLocal, init_db
from .models import Game
from .prediction_service import generate_predictions_for_snapshot, lock_started_predictions
from .ranking_service import calculate_all_new_complete_weeks, latest_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("rankings-worker")

DIVISION_I = ("FBS", "FCS")


def _nearest_schedule_week(
    session: Session,
    season: int,
    now: datetime | None = None,
) -> int:
    """Choose the ranking week whose scheduled games are closest to now.

    This deliberately does not depend only on the latest frozen ranking. If a
    postponed or unusual game delays a ranking snapshot, schedule and score
    syncing can still move on to the calendar week that is actually being
    played.
    """
    now = now or datetime.now(timezone.utc)
    lower = now - timedelta(hours=36)
    upper = now + timedelta(hours=36)
    rows = list(
        session.execute(
            select(Game.week, Game.start_time).where(
                Game.season == season,
                Game.season_type == "regular",
                Game.start_time.is_not(None),
                Game.start_time >= lower,
                Game.start_time <= upper,
                or_(
                    Game.home_subdivision.in_(DIVISION_I),
                    Game.away_subdivision.in_(DIVISION_I),
                ),
            )
        )
    )
    if rows:
        def distance(row) -> float:
            start = row.start_time
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            return abs((start - now).total_seconds())

        week, _ = min(rows, key=distance)
        return int(week)

    snapshot = latest_snapshot(session, season)
    return (snapshot.week + 1) if snapshot else 1


def _active_game_window(
    session: Session,
    season: int,
    now: datetime | None = None,
) -> bool:
    """Return true when a Division I game is near kickoff or in a normal game window."""
    now = now or datetime.now(timezone.utc)
    lower = now - timedelta(hours=6)
    upper = now + timedelta(hours=2)
    game = session.scalar(
        select(Game.id)
        .where(
            Game.season == season,
            Game.season_type == "regular",
            Game.start_time.is_not(None),
            Game.start_time >= lower,
            Game.start_time <= upper,
            Game.completed.is_(False),
            or_(
                Game.home_subdivision.in_(DIVISION_I),
                Game.away_subdivision.in_(DIVISION_I),
            ),
        )
        .limit(1)
    )
    return game is not None


def _rate_limit_delay_minutes(
    consecutive_rate_limits: int,
    settings: Settings,
    retry_after_seconds: int | None = None,
) -> int:
    """Exponential 429 cooldown capped at the configured maximum.

    A Retry-After header from CFBD is always honored even when it is longer
    than the configured exponential backoff.
    """
    exponent = max(consecutive_rate_limits - 1, 0)
    calculated = min(
        settings.sync_rate_limit_base_minutes * (2 ** min(exponent, 8)),
        settings.sync_rate_limit_max_minutes,
    )
    if retry_after_seconds is not None:
        calculated = max(calculated, math.ceil(retry_after_seconds / 60))
    return calculated


def _sync_cycle(full_schedule: bool = False) -> bool:
    settings = get_settings()
    client = CFBDClient()
    with SessionLocal() as session:
        bootstrap_bundled_rankings(session)

        # Prediction integrity is local database work and must not depend on the
        # upstream provider being reachable. This also catches up correctly
        # after an outage by selecting only predictions created before kickoff.
        locked = lock_started_predictions(session)
        if locked:
            LOGGER.info("Locked %s pregame predictions", locked)

        if not client.configured:
            LOGGER.warning(
                "CFBD_API_KEY is not configured. Bundled rankings are available, "
                "but automatic schedules, scores, stats, and predictions are paused."
            )
            return _active_game_window(session, settings.season)

        if full_schedule:
            count = sync_games(session, client, settings.season)
            LOGGER.info("Full %s schedule sync: %s games", settings.season, count)
            synced_week = None
        else:
            synced_week = _nearest_schedule_week(session, settings.season)
            count = sync_games(session, client, settings.season, week=synced_week)
            LOGGER.info("Week %s game sync: %s games", synced_week, count)

        # A successful score/schedule refresh may make one or more sequential
        # weeks complete. Ranking rules themselves are unchanged.
        created_weeks = calculate_all_new_complete_weeks(session, settings.season)
        rate_limit_error: CFBDRateLimitError | None = None
        if created_weeks:
            LOGGER.info("Created official ranking snapshots: %s", created_weeks)
            for week in created_weeks:
                try:
                    stats = sync_game_team_stats(session, client, settings.season, week)
                    LOGGER.info("Week %s team stats sync: %s rows", week, stats)
                except CFBDRateLimitError as exc:
                    # Team stats are optional. Finish local prediction work
                    # before handing the 429 to the outer cooldown logic.
                    rate_limit_error = exc
                    break
                except Exception:
                    LOGGER.exception(
                        "Week %s team-stat sync failed; rankings remain valid",
                        week,
                    )

        current_snapshot = latest_snapshot(session, settings.season)
        if current_snapshot is not None:
            created = generate_predictions_for_snapshot(session, current_snapshot)
            if created:
                LOGGER.info(
                    "Created %s projections from Week %s ranking",
                    created,
                    current_snapshot.week,
                )

        if rate_limit_error is not None:
            raise rate_limit_error

        return _active_game_window(session, settings.season)


def main() -> None:
    parser = argparse.ArgumentParser(description="CFBD sync and ranking worker")
    parser.add_argument("--once", action="store_true", help="Run one sync cycle and exit")
    args = parser.parse_args()
    settings = get_settings()
    init_db()

    last_full_schedule_at: datetime | None = None
    consecutive_rate_limits = 0

    while True:
        now = datetime.now(timezone.utc)
        full_schedule = (
            last_full_schedule_at is None
            or now - last_full_schedule_at
            >= timedelta(hours=settings.sync_full_schedule_hours)
        )
        sleep_minutes = settings.sync_idle_minutes

        try:
            active = _sync_cycle(full_schedule=full_schedule)
            if full_schedule:
                last_full_schedule_at = now
            consecutive_rate_limits = 0
            sleep_minutes = (
                settings.sync_active_minutes
                if active
                else settings.sync_idle_minutes
            )
        except CFBDRateLimitError as exc:
            consecutive_rate_limits += 1
            sleep_minutes = _rate_limit_delay_minutes(
                consecutive_rate_limits,
                settings,
                exc.retry_after_seconds,
            )
            LOGGER.warning(
                "CFBD quota/rate limit reached. Pausing provider requests for "
                "%s minutes (consecutive 429s: %s).",
                sleep_minutes,
                consecutive_rate_limits,
            )
        except Exception:
            LOGGER.exception("Automatic sync cycle failed")
            sleep_minutes = settings.sync_idle_minutes

        if args.once:
            return

        LOGGER.info("Next worker cycle in %s minutes", sleep_minutes)
        time.sleep(sleep_minutes * 60)


if __name__ == "__main__":
    main()
