from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .config import Settings
from .models import Game

DIVISION_I = ("FBS", "FCS")

# A game that has kicked off counts as live until it is final or this long
# after kickoff. The cap keeps a cancelled or never-finalized game from holding
# the worker in live polling forever; normal and long/delayed games finish well
# inside it, including late West Coast kickoffs that end after local midnight.
LIVE_WINDOW = timedelta(hours=8)


@dataclass(frozen=True, slots=True)
class ScheduleState:
    live_games: int
    next_kickoff: datetime | None


def _division_i_regular(season: int):
    return (
        Game.season == season,
        Game.season_type == "regular",
        Game.start_time.is_not(None),
        or_(
            Game.home_subdivision.in_(DIVISION_I),
            Game.away_subdivision.in_(DIVISION_I),
        ),
    )


def schedule_state(session: Session, season: int, now: datetime) -> ScheduleState:
    """Count games in progress and find the next kickoff, from PostgreSQL only."""
    live_games = session.scalar(
        select(func.count(Game.id)).where(
            *_division_i_regular(season),
            Game.completed.is_not(True),
            Game.start_time <= now,
            Game.start_time > now - LIVE_WINDOW,
        )
    ) or 0
    next_kickoff = session.scalar(
        select(func.min(Game.start_time)).where(
            *_division_i_regular(season),
            Game.completed.is_not(True),
            Game.start_time > now,
        )
    )
    if next_kickoff is not None and next_kickoff.tzinfo is None:
        next_kickoff = next_kickoff.replace(tzinfo=now.tzinfo)
    return ScheduleState(live_games=int(live_games), next_kickoff=next_kickoff)


def poll_delay_minutes(now: datetime, state: ScheduleState, settings: Settings) -> int:
    """Minutes until the next provider sync.

    While any Division I game is live, poll on the live cadence regardless of
    the day of the week. Otherwise sleep until one live interval after the
    next kickoff (the first moment a score can have changed), but never
    longer than the idle cadence.
    """
    if state.live_games:
        return settings.sync_live_minutes

    delay = settings.sync_idle_minutes
    if state.next_kickoff is not None:
        until_first_update = (
            state.next_kickoff - now
        ).total_seconds() / 60 + settings.sync_live_minutes
        delay = min(delay, max(1, math.ceil(until_first_update)))
    return delay


def stale_after(state: ScheduleState, settings: Settings) -> timedelta:
    """How old the last successful sync may be before the site calls it stale."""
    if state.live_games:
        return timedelta(minutes=math.ceil(settings.sync_live_minutes * 1.5))
    return timedelta(minutes=max(int(settings.sync_idle_minutes * 1.5), 180))
