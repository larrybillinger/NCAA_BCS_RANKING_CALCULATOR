from __future__ import annotations

import argparse
import logging
import math
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .bootstrap import bootstrap_bundled_rankings
from .cfbd import (
    CFBDClient,
    CFBDRateLimitError,
    sync_game_team_stats,
    sync_games,
    sync_team_context,
)
from .config import Settings, get_settings
from .db import SessionLocal, init_db
from .models import Game
from .prediction_service import generate_predictions_for_snapshot, lock_started_predictions
from .ranking_service import calculate_all_new_complete_weeks, latest_snapshot
from .research_prediction_ledger import (
    generate_research_predictions_for_snapshot,
    lock_started_research_predictions,
)
from .sync_schedule import poll_delay_minutes, schedule_state

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


def _next_delay_minutes(settings: Settings, now: datetime | None = None) -> int:
    """Poll on the live cadence while any game is in progress, else idle.

    The schedule in PostgreSQL decides the cadence, not the day of the week, so
    weeknight games and Saturday games that finish after local midnight are
    covered the same way.
    """
    now = now or datetime.now(timezone.utc)
    try:
        with SessionLocal() as session:
            state = schedule_state(session, settings.season, now)
    except Exception:
        LOGGER.exception("Could not read the schedule; using the live cadence")
        return settings.sync_live_minutes
    if state.live_games:
        LOGGER.info("%s Division I games in progress", state.live_games)
    return poll_delay_minutes(now, state, settings)


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


def _sync_cycle(full_schedule: bool = False) -> None:
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

        # Research shadow locking is also local-only and runs before provider
        # access. Experimental failures must never block the official worker.
        try:
            research_locked = lock_started_research_predictions(session)
            if research_locked:
                LOGGER.info(
                    "Locked %s pregame research predictions",
                    research_locked,
                )
        except Exception:
            LOGGER.exception("Research prediction locking failed")

        if not client.configured:
            LOGGER.warning(
                "CFBD_API_KEY is not configured. Bundled rankings are available, "
                "but automatic schedules, scores, stats, and predictions are paused."
            )
            return None

        rate_limit_error: CFBDRateLimitError | None = None
        if full_schedule:
            count = sync_games(session, client, settings.season)
            LOGGER.info("Full %s schedule sync: %s games", settings.season, count)
            synced_week = None
            try:
                context_rows = sync_team_context(
                    session,
                    client,
                    settings.season,
                )
                LOGGER.info(
                    "Season %s team venue context sync: %s teams",
                    settings.season,
                    context_rows,
                )
            except CFBDRateLimitError as exc:
                # Static context is research-only. Preserve local ranking and
                # prediction work, then hand the 429 to normal cooldown logic.
                rate_limit_error = exc
            except Exception:
                LOGGER.exception(
                    "Team venue context sync failed; official work remains valid"
                )
        else:
            synced_week = _nearest_schedule_week(session, settings.season)
            count = sync_games(session, client, settings.season, week=synced_week)
            LOGGER.info("Week %s game sync: %s games", synced_week, count)

        # A successful score/schedule refresh may make one or more sequential
        # weeks complete. Ranking rules themselves are unchanged.
        created_weeks = calculate_all_new_complete_weeks(session, settings.season)
        if created_weeks and rate_limit_error is None:
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
            try:
                research_created = generate_research_predictions_for_snapshot(
                    session,
                    current_snapshot,
                )
                if research_created:
                    LOGGER.info(
                        "Created %s hybrid research projections from Week %s ranking",
                        research_created,
                        current_snapshot.week,
                    )
            except Exception:
                LOGGER.exception("Research prediction generation failed")

        if rate_limit_error is not None:
            raise rate_limit_error

        return None


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
        sleep_minutes = _next_delay_minutes(settings, now)

        try:
            _sync_cycle(full_schedule=full_schedule)
            if full_schedule:
                last_full_schedule_at = now
            consecutive_rate_limits = 0
            sleep_minutes = _next_delay_minutes(settings)
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
            sleep_minutes = _next_delay_minutes(settings)

        if args.once:
            return

        LOGGER.info("Next worker cycle in %s minutes", sleep_minutes)
        time.sleep(sleep_minutes * 60)


if __name__ == "__main__":
    main()
