from datetime import date

from ncaa_rankings.evaluation import PostseasonMatchup, accuracy, frozen_postseason_backtest
from ncaa_rankings.models import LegacyFBSModel, TeamGame
from ncaa_rankings.ranking import RecursiveRankingEngine


def test_engine_ranks_simple_round_robin():
    games = [
        TeamGame("A", "B", 30, 10),
        TeamGame("B", "A", 10, 30),
        TeamGame("A", "C", 24, 21),
        TeamGame("C", "A", 21, 24),
        TeamGame("B", "C", 17, 14),
        TeamGame("C", "B", 14, 17),
    ]
    engine = RecursiveRankingEngine(LegacyFBSModel(), max_iterations=20)
    result = engine.rank(games)
    assert result.ranks["A"] == 1
    assert result.ranks["B"] == 2
    assert result.ranks["C"] == 3


def test_postseason_backtest_uses_frozen_snapshot():
    regular = [
        TeamGame("A", "B", 30, 10, played_on=date(2025, 11, 1)),
        TeamGame("B", "A", 10, 30, played_on=date(2025, 11, 1)),
        TeamGame("A", "C", 24, 21, played_on=date(2025, 11, 8)),
        TeamGame("C", "A", 21, 24, played_on=date(2025, 11, 8)),
        TeamGame("B", "C", 17, 14, played_on=date(2025, 11, 15)),
        TeamGame("C", "B", 14, 17, played_on=date(2025, 11, 15)),
    ]
    postseason = [
        PostseasonMatchup("semi", "A", "B", "A", round_name="semifinal"),
        PostseasonMatchup("title", "A", "C", "A", round_name="championship"),
    ]
    engine = RecursiveRankingEngine(LegacyFBSModel())
    ranking, predictions = frozen_postseason_backtest(
        engine,
        regular,
        postseason,
        freeze_date=date(2025, 12, 15),
    )
    assert ranking.ranks["A"] == 1
    assert len(predictions) == 2
    assert accuracy(predictions) == 1.0
