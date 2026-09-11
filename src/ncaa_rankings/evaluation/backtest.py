from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping

from ncaa_rankings.models.base import RankingResult, TeamGame
from ncaa_rankings.ranking.engine import RecursiveRankingEngine


@dataclass(frozen=True, slots=True)
class PostseasonMatchup:
    game_id: str
    team_a: str
    team_b: str
    winner: str
    played_on: date | None = None
    round_name: str = "bowl"


@dataclass(frozen=True, slots=True)
class Prediction:
    game_id: str
    predicted_winner: str
    actual_winner: str
    higher_rank: int
    lower_rank: int
    correct: bool
    round_name: str


def frozen_postseason_backtest(
    engine: RecursiveRankingEngine,
    regular_season_games: Iterable[TeamGame],
    postseason_games: Iterable[PostseasonMatchup],
    *,
    freeze_date: date,
    teams: Iterable[str] | None = None,
    initial_ranks: Mapping[str, int] | None = None,
) -> tuple[RankingResult, tuple[Prediction, ...]]:
    """Rank FBS teams once at the freeze point, then predict the postseason.

    Postseason results are intentionally never supplied to the ranking engine.
    This prevents a bowl or playoff result from leaking into later postseason
    predictions. Every postseason pick for a season uses the same FBS snapshot.
    """

    ranking = engine.rank(
        regular_season_games,
        teams=teams,
        initial_ranks=initial_ranks,
        freeze_date=freeze_date,
    )
    ranks = ranking.ranks

    predictions: list[Prediction] = []
    for matchup in postseason_games:
        if matchup.team_a not in ranks or matchup.team_b not in ranks:
            continue
        rank_a = ranks[matchup.team_a]
        rank_b = ranks[matchup.team_b]
        predicted = matchup.team_a if rank_a < rank_b else matchup.team_b
        predictions.append(
            Prediction(
                game_id=matchup.game_id,
                predicted_winner=predicted,
                actual_winner=matchup.winner,
                higher_rank=min(rank_a, rank_b),
                lower_rank=max(rank_a, rank_b),
                correct=predicted == matchup.winner,
                round_name=matchup.round_name,
            )
        )

    return ranking, tuple(predictions)
