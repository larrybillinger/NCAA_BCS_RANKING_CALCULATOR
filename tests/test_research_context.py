from ncaa_rankings.web.research_context import (
    ContextVariant,
    ResearchGameContext,
    apply_context_adjustments,
    stadium_demand_grades,
)


def test_neutral_site_disables_stadium_points_but_keeps_travel():
    result = apply_context_adjustments(
        28.0,
        28.0,
        ResearchGameContext(
            neutral_site=True,
            stadium_grade="A",
            home_timezone_crossings=1,
            away_timezone_crossings=2,
        ),
    )

    assert result.detail["stadium_points"] == 0.0
    assert result.home_points == 21.0
    assert result.away_points == 14.0
    assert result.margin == 7.0


def test_larry_context_applies_stadium_travel_altitude_and_weather():
    result = apply_context_adjustments(
        28.0,
        28.0,
        ResearchGameContext(
            neutral_site=False,
            stadium_grade="B",
            away_timezone_crossings=2,
            away_altitude_disadvantage=True,
            rain_or_snow=True,
        ),
    )

    # Home: 28 + 5 stadium - 7 weather = 26.
    assert result.home_points == 26.0
    # Away: 28 - 14 travel - 7 altitude - 7 weather = 0.
    assert result.away_points == 0.0
    assert result.margin == 26.0


def test_context_negative_score_uses_equal_shift():
    result = apply_context_adjustments(
        7.0,
        14.0,
        ResearchGameContext(away_timezone_crossings=3),
    )

    # Away falls to -7, then both teams are translated upward by 7.
    assert result.home_points == 14.0
    assert result.away_points == 0.0
    assert result.detail["score_shift"] == 7.0
    assert result.margin == 14.0


def test_timezone_cap_is_variant_specific():
    result = apply_context_adjustments(
        28.0,
        28.0,
        ResearchGameContext(away_timezone_crossings=5),
        variant=ContextVariant(
            name="capped_travel",
            stadium=False,
            timezone=True,
            altitude=False,
            weather=False,
            timezone_cap=2,
        ),
    )

    assert result.away_points == 14.0
    assert result.detail["away_timezone_crossings"] == 2


def test_stadium_grades_are_conference_relative_and_missing_stays_missing():
    grades = stadium_demand_grades({
        1: 1.00,
        2: 0.90,
        3: 0.80,
        4: 0.70,
        5: 0.60,
        6: None,
    })

    assert grades == {
        1: "A",
        2: "B",
        3: "C",
        4: "D",
        5: "F",
        6: None,
    }
