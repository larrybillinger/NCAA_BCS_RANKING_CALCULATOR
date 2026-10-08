from types import SimpleNamespace

from ncaa_rankings.web.display_scores import (
    display_scores_for_prediction,
    winner_consistent_display_scores,
)
from ncaa_rankings.web.stats_service import _metrics


def test_nonzero_home_margin_cannot_display_a_tie():
    assert winner_consistent_display_scores(30.4, 30.3, 0.1) == (31, 30)


def test_nonzero_away_margin_cannot_display_a_tie():
    assert winner_consistent_display_scores(24.2, 24.4, -0.2) == (24, 25)


def test_true_zero_margin_may_display_a_tie():
    assert winner_consistent_display_scores(27.4, 27.4, 0.0) == (27, 27)


def test_projection_adapter_uses_same_display_rule():
    prediction = SimpleNamespace(
        projected_home_points=30.4,
        projected_away_points=30.3,
        projected_margin=0.1,
    )
    assert display_scores_for_prediction(prediction) == (31, 30)


def test_accuracy_display_tie_rate_uses_winner_consistent_scores():
    nonzero = SimpleNamespace(
        projected_home_points=30.4,
        projected_away_points=30.3,
        projected_margin=0.1,
        home_win_probability=0.51,
        home_rank=20,
        away_rank=21,
    )
    true_tie = SimpleNamespace(
        projected_home_points=27.4,
        projected_away_points=27.4,
        projected_margin=0.0,
        home_win_probability=0.5,
        home_rank=20,
        away_rank=20,
    )
    game_a = SimpleNamespace(home_points=31, away_points=30)
    game_b = SimpleNamespace(home_points=28, away_points=27)

    metrics = _metrics([(nonzero, game_a), (true_tie, game_b)])

    assert metrics.display_tie_rate == 0.5
