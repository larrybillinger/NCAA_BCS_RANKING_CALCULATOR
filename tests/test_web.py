from ncaa_rankings.web.prediction_service import Calibration, _projection_from_ranks
from ncaa_rankings.web.utils import slugify, subdivision


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
