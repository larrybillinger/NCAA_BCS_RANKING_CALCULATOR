from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Game, TeamSeason
from .research_context import ResearchGameContext

ALTITUDE_THRESHOLD_FT = 2000.0


@dataclass(frozen=True, slots=True)
class StaticContextSnapshot:
    context: ResearchGameContext
    features: dict[str, object]


def timezone_crossings(
    origin_timezone: str | None,
    venue_timezone: str | None,
    kickoff: datetime | None,
) -> int:
    """Return absolute UTC-offset difference at kickoff as time-zone crossings."""
    if not origin_timezone or not venue_timezone or kickoff is None:
        return 0

    instant = kickoff
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)

    try:
        origin_offset = instant.astimezone(ZoneInfo(origin_timezone)).utcoffset()
        venue_offset = instant.astimezone(ZoneInfo(venue_timezone)).utcoffset()
    except ZoneInfoNotFoundError:
        return 0
    if origin_offset is None or venue_offset is None:
        return 0

    hours = abs(
        (venue_offset.total_seconds() - origin_offset.total_seconds()) / 3600.0
    )
    return int(round(hours))


def _team_season(
    session: Session,
    team_id: int,
    season: int,
) -> TeamSeason | None:
    return session.scalar(
        select(TeamSeason).where(
            TeamSeason.team_id == team_id,
            TeamSeason.season == season,
        )
    )


def _venue_context(
    game: Game,
    home: TeamSeason | None,
    away: TeamSeason | None,
) -> tuple[str | None, float | None, str]:
    # Prefer an explicit provider venue-id match. This also handles a neutral
    # game played in one participant's normal stadium without granting stadium
    # points, because neutral_site is kept separately in ResearchGameContext.
    if game.venue_id is not None:
        if home is not None and game.venue_id == home.home_venue_id:
            return home.home_timezone, home.home_elevation_ft, "home_venue_match"
        if away is not None and game.venue_id == away.home_venue_id:
            return away.home_timezone, away.home_elevation_ft, "away_venue_match"

    # For a normal non-neutral game, the listed home team's stored venue is the
    # best static fallback when the schedule does not provide a usable venue id.
    if not game.neutral_site and home is not None:
        return home.home_timezone, home.home_elevation_ft, "home_team_fallback"

    return None, None, "unknown_neutral_venue"


def _altitude_disadvantage(
    origin_elevation_ft: float | None,
    venue_elevation_ft: float | None,
) -> bool:
    if origin_elevation_ft is None or venue_elevation_ft is None:
        return False
    return (
        venue_elevation_ft - origin_elevation_ft
        >= ALTITUDE_THRESHOLD_FT
    )


def build_static_game_context(
    session: Session,
    game: Game,
) -> StaticContextSnapshot:
    """Build leakage-safe static travel/altitude context from stored metadata."""
    home = _team_season(session, game.home_team_id, game.season)
    away = _team_season(session, game.away_team_id, game.season)
    venue_timezone, venue_elevation_ft, venue_resolution = _venue_context(
        game,
        home,
        away,
    )

    home_crossings = 0
    away_crossings = 0
    home_altitude = False
    away_altitude = False

    if game.neutral_site:
        home_crossings = timezone_crossings(
            home.home_timezone if home else None,
            venue_timezone,
            game.start_time,
        )
        away_crossings = timezone_crossings(
            away.home_timezone if away else None,
            venue_timezone,
            game.start_time,
        )
        home_altitude = _altitude_disadvantage(
            home.home_elevation_ft if home else None,
            venue_elevation_ft,
        )
        away_altitude = _altitude_disadvantage(
            away.home_elevation_ft if away else None,
            venue_elevation_ft,
        )
    else:
        # The listed home team is not treated as a traveler at a true home site.
        away_crossings = timezone_crossings(
            away.home_timezone if away else None,
            venue_timezone,
            game.start_time,
        )
        away_altitude = _altitude_disadvantage(
            away.home_elevation_ft if away else None,
            venue_elevation_ft,
        )

    context = ResearchGameContext(
        neutral_site=bool(game.neutral_site),
        home_timezone_crossings=home_crossings,
        away_timezone_crossings=away_crossings,
        home_altitude_disadvantage=home_altitude,
        away_altitude_disadvantage=away_altitude,
    )
    return StaticContextSnapshot(
        context=context,
        features={
            "context": asdict(context),
            "venue_id": game.venue_id,
            "venue_name": game.venue,
            "venue_timezone": venue_timezone,
            "venue_elevation_ft": venue_elevation_ft,
            "venue_resolution": venue_resolution,
            "altitude_threshold_ft": ALTITUDE_THRESHOLD_FT,
            "home_context_source": home.home_context_source if home else None,
            "home_context_updated_at": (
                home.home_context_updated_at.isoformat()
                if home and home.home_context_updated_at
                else None
            ),
            "away_context_source": away.home_context_source if away else None,
            "away_context_updated_at": (
                away.home_context_updated_at.isoformat()
                if away and away.home_context_updated_at
                else None
            ),
        },
    )
