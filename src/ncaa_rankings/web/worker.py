from __future__ import annotations

import argparse
import logging
import time

from .bootstrap import bootstrap_bundled_rankings
from .cfbd import CFBDClient, sync_game_team_stats, sync_games
from .config import get_settings
from .db import SessionLocal, init_db
from .prediction_service import generate_predictions_for_snapshot, lock_started_predictions
from .ranking_service import calculate_all_new_complete_weeks, latest_snapshot, week_is_complete

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("rankings-worker")


def _sync_cycle(full_schedule: bool = False) -> None:
    settings = get_settings()
    client = CFBDClient()
    with SessionLocal() as session:
        bootstrap_bundled_rankings(session)
        if not client.configured:
            LOGGER.warning(
                "CFBD_API_KEY is not configured. Bundled rankings are available, "
                "but automatic schedules, scores, stats, and predictions are paused."
            )
            return

        if full_schedule:
            count = sync_games(session, client, settings.season)
            LOGGER.info("Full %s schedule sync: %s games", settings.season, count)

        current_snapshot = latest_snapshot(session, settings.season)
        next_week = (current_snapshot.week + 1) if current_snapshot else 1
        count = sync_games(session, client, settings.season, week=next_week)
        LOGGER.info("Week %s game sync: %s games", next_week, count)

        locked = lock_started_predictions(session)
        if locked:
            LOGGER.info("Locked %s pregame predictions", locked)

        if week_is_complete(session, settings.season, next_week):
            try:
                stats = sync_game_team_stats(session, client, settings.season, next_week)
                LOGGER.info("Week %s team stats sync: %s rows", next_week, stats)
            except Exception:
                LOGGER.exception("Team-stat sync failed; rankings can still continue from scores")

            created_weeks = calculate_all_new_complete_weeks(session, settings.season)
            if created_weeks:
                LOGGER.info("Created official ranking snapshots: %s", created_weeks)

        current_snapshot = latest_snapshot(session, settings.season)
        if current_snapshot is not None:
            created = generate_predictions_for_snapshot(session, current_snapshot)
            if created:
                LOGGER.info(
                    "Created %s projections from Week %s ranking",
                    created,
                    current_snapshot.week,
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="CFBD sync and ranking worker")
    parser.add_argument("--once", action="store_true", help="Run one sync cycle and exit")
    args = parser.parse_args()
    settings = get_settings()
    init_db()

    full_schedule = True
    while True:
        try:
            _sync_cycle(full_schedule=full_schedule)
        except Exception:
            LOGGER.exception("Automatic sync cycle failed")
        if args.once:
            return
        full_schedule = False
        time.sleep(settings.sync_minutes * 60)


if __name__ == "__main__":
    main()
