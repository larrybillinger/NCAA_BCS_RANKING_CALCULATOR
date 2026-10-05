from ncaa_rankings.web.prediction_service import Calibration, Projection, _projection_from_ranks
from ncaa_rankings.web.utils import slugify, subdivision
from ncaa_rankings.web.view_service import _assign_scope_ranks


def test_slugify_handles_punctuation_and_apostrophes():
    assert slugify("Hawai'i") == "hawai-i"
    assert slugify("Miami (OH)") == "miami-oh"


def test_subdivision_normalization():
    assert subdivision("fbs") == "FBS"
    assert subdivision("FCS") == "FCS"
    assert subdivision("ii") == "II"



def test_rank_gap_always_favors_higher_ranked_team():
    calibration = Calibration(
        rank_slope=0.20,
        average_total=52.0,
        residual_sd=14.0,
        sample_size=20,
    )

    home_points, away_points, margin, probability = _projection_from_ranks(
        40, 105, calibration
    )
    assert margin == 13.0
    assert home_points > away_points
    assert probability > 0.5

    home_points, away_points, margin, probability = _projection_from_ranks(
        105, 40, calibration
    )
    assert margin == -13.0
    assert away_points > home_points
    assert probability < 0.5


def test_larger_rank_gap_produces_larger_projected_margin():
    calibration = Calibration(
        rank_slope=0.20,
        average_total=52.0,
        residual_sd=14.0,
        sample_size=20,
    )

    _, _, small_margin, _ = _projection_from_ranks(20, 30, calibration)
    _, _, large_margin, _ = _projection_from_ranks(20, 80, calibration)

    assert small_margin == 2.0
    assert large_margin == 12.0
    assert large_margin > small_margin


def test_equal_ranks_project_even_game():
    calibration = Calibration(
        rank_slope=0.20,
        average_total=52.0,
        residual_sd=14.0,
        sample_size=20,
    )

    home_points, away_points, margin, probability = _projection_from_ranks(
        25, 25, calibration
    )
    assert margin == 0.0
    assert home_points == away_points
    assert probability == 0.5



def test_retrocast_projection_matches_saved_prediction_field_names():
    projection = Projection(
        home_rank=10,
        away_rank=40,
        home_points=31.5,
        away_points=24.5,
        margin=7.0,
        home_win_probability=0.68,
        sample_size=50,
        detail={"method": "rank_gap_v3"},
    )

    assert projection.projected_home_points == 31.5
    assert projection.projected_away_points == 24.5
    assert projection.projected_margin == 7.0



def test_scope_ranks_follow_national_order_before_filtering():
    rows = [
        {"rank": 1, "subdivision": "FCS", "conference": "Big Sky"},
        {"rank": 2, "subdivision": "FBS", "conference": "SEC"},
        {"rank": 3, "subdivision": "FBS", "conference": "Big Ten"},
        {"rank": 4, "subdivision": "FCS", "conference": "Big Sky"},
        {"rank": 5, "subdivision": "FBS", "conference": "SEC"},
        {"rank": 6, "subdivision": "FCS", "conference": None},
    ]

    ranked = _assign_scope_ranks(rows)

    assert [row["subdivision_rank"] for row in ranked] == [1, 1, 2, 2, 3, 3]
    assert [row["conference_rank"] for row in ranked] == [1, 1, 1, 2, 2, None]
    assert [row["division_i_rank"] for row in ranked] == [1, 2, 3, 4, 5, 6]

    fbs = [row for row in ranked if row["subdivision"] == "FBS"]
    assert [row["subdivision_rank"] for row in fbs] == [1, 2, 3]

    sec = [row for row in ranked if row["conference"] == "SEC"]
    assert [row["conference_rank"] for row in sec] == [1, 2]
    assert [row["division_i_rank"] for row in sec] == [2, 5]
