from __future__ import annotations

import math


def _round_half_up(value: float) -> int:
    return int(math.floor(float(value) + 0.5))


def winner_consistent_display_scores(
    home_points: float,
    away_points: float,
    margin: float,
) -> tuple[int, int]:
    """Round projected scores without inventing a tie against the model winner.

    Scores use ordinary football-style half-up rounding. If both rounded scores
    are equal but the modeled margin is non-zero, the modeled winner receives
    one additional display point. A true zero-margin projection may still show
    a tie.
    """
    home = max(0, _round_half_up(home_points))
    away = max(0, _round_half_up(away_points))

    if margin > 0.0 and home <= away:
        home = away + 1
    elif margin < 0.0 and away <= home:
        away = home + 1

    return home, away


def display_scores_for_prediction(prediction: object) -> tuple[int, int]:
    """Return winner-consistent integer scores for any projection-like object."""
    return winner_consistent_display_scores(
        float(getattr(prediction, "projected_home_points")),
        float(getattr(prediction, "projected_away_points")),
        float(getattr(prediction, "projected_margin")),
    )
