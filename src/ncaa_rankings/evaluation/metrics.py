from __future__ import annotations

from math import log
from typing import Iterable

from .backtest import Prediction


def accuracy(predictions: Iterable[Prediction]) -> float:
    values = tuple(predictions)
    if not values:
        return float("nan")
    return sum(p.correct for p in values) / len(values)


def brier_score(probabilities: Iterable[tuple[float, int]]) -> float:
    values = tuple(probabilities)
    if not values:
        return float("nan")
    return sum((p - y) ** 2 for p, y in values) / len(values)


def log_loss(probabilities: Iterable[tuple[float, int]], eps: float = 1e-15) -> float:
    values = tuple(probabilities)
    if not values:
        return float("nan")
    total = 0.0
    for p, y in values:
        p = min(1.0 - eps, max(eps, p))
        total += -(y * log(p) + (1 - y) * log(1 - p))
    return total / len(values)
