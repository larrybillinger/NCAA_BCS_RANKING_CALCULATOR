from __future__ import annotations

from dataclasses import dataclass

from .research_prediction_service import (
    normalize_nonnegative_scores,
    winner_consistent_display_scores,
)

STADIUM_POINTS = {
    "A": 7.0,
    "B": 5.0,
    "C": 3.0,
    "D": 1.0,
    "F": 0.0,
}
TIMEZONE_POINTS_PER_CROSSING = 7.0
ALTITUDE_POINTS = 7.0
WEATHER_POINTS_PER_TEAM = 7.0


@dataclass(frozen=True, slots=True)
class ResearchGameContext:
    neutral_site: bool = False
    stadium_grade: str | None = None
    home_timezone_crossings: int = 0
    away_timezone_crossings: int = 0
    home_altitude_disadvantage: bool = False
    away_altitude_disadvantage: bool = False
    rain_or_snow: bool = False


@dataclass(frozen=True, slots=True)
class ContextVariant:
    name: str
    stadium: bool = True
    timezone: bool = True
    altitude: bool = True
    weather: bool = True
    timezone_cap: int | None = None


@dataclass(frozen=True, slots=True)
class ContextProjection:
    home_points: float
    away_points: float
    margin: float
    total: float
    display_home_points: int
    display_away_points: int
    detail: dict[str, float | int | str | bool | None]


LARRY_CONTEXT_V1 = ContextVariant(name="larry_context_v1")
STADIUM_ONLY = ContextVariant(
    name="stadium_only",
    timezone=False,
    altitude=False,
    weather=False,
)
TRAVEL_ONLY = ContextVariant(
    name="travel_only",
    stadium=False,
    altitude=False,
    weather=False,
)
ALTITUDE_ONLY = ContextVariant(
    name="altitude_only",
    stadium=False,
    timezone=False,
    weather=False,
)
WEATHER_ONLY = ContextVariant(
    name="weather_only",
    stadium=False,
    timezone=False,
    altitude=False,
)


def stadium_grade_from_sell_through_rank(
    position: float,
    team_count: int,
) -> str:
    """Map a conference-relative sell-through position into A/B/C/D/F."""
    if position < 1 or team_count < 1 or position > team_count:
        raise ValueError("Position must be within the conference team count.")
    if team_count == 1:
        return "A"

    percentile = (position - 1) / (team_count - 1)
    if percentile < 0.20:
        return "A"
    if percentile < 0.40:
        return "B"
    if percentile < 0.60:
        return "C"
    if percentile < 0.80:
        return "D"
    return "F"


def stadium_demand_grades(
    sell_through_by_team: dict[int, float | None],
) -> dict[int, str | None]:
    """Grade known sell-through values; missing data stays explicitly missing."""
    known = [
        (team_id, value)
        for team_id, value in sell_through_by_team.items()
        if value is not None
    ]
    known.sort(key=lambda item: (-item[1], item[0]))

    grades: dict[int, str | None] = {
        team_id: None
        for team_id in sell_through_by_team
    }
    # Equal sell-through percentages share the same competition rank so a
    # deterministic team-id fallback never splits identical demand into
    # different letter grades.
    position = 1
    index = 0
    while index < len(known):
        value = known[index][1]
        tied_team_ids: list[int] = []
        while index < len(known) and known[index][1] == value:
            tied_team_ids.append(known[index][0])
            index += 1

        grade = stadium_grade_from_sell_through_rank(
            float(position),
            len(known),
        )
        for team_id in tied_team_ids:
            grades[team_id] = grade
        position += len(tied_team_ids)

    return grades


def _timezone_crossings(value: int, cap: int | None) -> int:
    crossings = max(0, int(value))
    if cap is not None:
        crossings = min(crossings, max(0, cap))
    return crossings


def apply_context_adjustments(
    home_points: float,
    away_points: float,
    context: ResearchGameContext,
    *,
    variant: ContextVariant = LARRY_CONTEXT_V1,
) -> ContextProjection:
    """Apply Larry's context rules to research scores only.

    Stadium points are a home-score benefit at a true home site. Travel and
    altitude penalties reduce the affected traveling team. Rain or snow
    reduces both offenses. Any negative score is corrected by equal translation
    so the adjusted margin is preserved.
    """
    home_delta = 0.0
    away_delta = 0.0

    stadium_points = 0.0
    if variant.stadium and not context.neutral_site:
        stadium_points = STADIUM_POINTS.get(
            (context.stadium_grade or "F").upper(),
            0.0,
        )
        home_delta += stadium_points

    home_crossings = 0
    away_crossings = 0
    if variant.timezone:
        home_crossings = _timezone_crossings(
            context.home_timezone_crossings,
            variant.timezone_cap,
        )
        away_crossings = _timezone_crossings(
            context.away_timezone_crossings,
            variant.timezone_cap,
        )
        home_delta -= TIMEZONE_POINTS_PER_CROSSING * home_crossings
        away_delta -= TIMEZONE_POINTS_PER_CROSSING * away_crossings

    home_altitude_points = 0.0
    away_altitude_points = 0.0
    if variant.altitude:
        if context.home_altitude_disadvantage:
            home_altitude_points = ALTITUDE_POINTS
            home_delta -= home_altitude_points
        if context.away_altitude_disadvantage:
            away_altitude_points = ALTITUDE_POINTS
            away_delta -= away_altitude_points

    weather_points = 0.0
    if variant.weather and context.rain_or_snow:
        weather_points = WEATHER_POINTS_PER_TEAM
        home_delta -= weather_points
        away_delta -= weather_points

    adjusted_home = home_points + home_delta
    adjusted_away = away_points + away_delta
    adjusted_home, adjusted_away, score_shift = normalize_nonnegative_scores(
        adjusted_home,
        adjusted_away,
    )
    margin = adjusted_home - adjusted_away
    display_home, display_away = winner_consistent_display_scores(
        adjusted_home,
        adjusted_away,
        margin,
    )

    return ContextProjection(
        home_points=round(adjusted_home, 2),
        away_points=round(adjusted_away, 2),
        margin=round(margin, 2),
        total=round(adjusted_home + adjusted_away, 2),
        display_home_points=display_home,
        display_away_points=display_away,
        detail={
            "variant": variant.name,
            "neutral_site": context.neutral_site,
            "stadium_grade": context.stadium_grade,
            "stadium_points": stadium_points,
            "home_timezone_crossings": home_crossings,
            "away_timezone_crossings": away_crossings,
            "home_altitude_points": home_altitude_points,
            "away_altitude_points": away_altitude_points,
            "weather_points_each": weather_points,
            "home_delta": round(home_delta, 2),
            "away_delta": round(away_delta, 2),
            "score_shift": round(score_shift, 2),
        },
    )
