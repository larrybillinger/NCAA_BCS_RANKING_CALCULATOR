from datetime import date

import pytest

from ncaa_rankings.evaluation import PostseasonMatchup, accuracy, frozen_postseason_backtest
from ncaa_rankings.models import LegacyFBSModel, TeamGame
from ncaa_rankings.ranking import RecursiveRankingEngine, WeeklySeasonRankingEngine


def test_legacy_recursive_engine_ranks_simple_round_robin():
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


def test_week_one_creates_first_ranking_from_current_season_only():
    games = [
        TeamGame("A", "B", 21, 14, week=1),
        TeamGame("B", "A", 14, 21, week=1),
        TeamGame(
            "C",
            "FCS Opponent",
            40,
            0,
            opponent_in_rank_pool=False,
            week=1,
        ),
    ]
    engine = WeeklySeasonRankingEngine(LegacyFBSModel())
    result = engine.rank(games, teams=["A", "B", "C"])

    # Week 1 has no opponent-rank points. C receives +10 plus half of its
    # 40-point margin because the opponent is outside the FBS ranking pool.
    assert result.scores["C"] == 30
    assert result.scores["A"] == 17
    assert result.scores["B"] == -7
    assert result.ranks == {"C": 1, "A": 2, "B": 3}


def test_week_two_uses_week_one_current_season_ranks():
    games = [
        TeamGame("A", "B", 21, 14, week=1),
        TeamGame("B", "A", 14, 21, week=1),
        TeamGame(
            "C",
            "FCS Opponent",
            40,
            0,
            opponent_in_rank_pool=False,
            week=1,
        ),
        TeamGame("A", "C", 20, 17, week=2),
        TeamGame("C", "A", 17, 20, week=2),
    ]
    engine = WeeklySeasonRankingEngine(LegacyFBSModel())
    snapshots = engine.rank_by_week(games, teams=["A", "B", "C"])

    assert snapshots[1].ranks == {"C": 1, "A": 2, "B": 3}

    # A beats the Week 1 #1 team C: +3 opponent points, +10 win, +3 margin.
    # A had 17 Week 1 points, so it reaches 33 and moves to #1.
    assert snapshots[2].scores["A"] == 33
    assert snapshots[2].ranks["A"] == 1


def test_weekly_engine_rejects_previous_season_seed():
    games = [
        TeamGame("A", "B", 21, 14, week=1),
        TeamGame("B", "A", 14, 21, week=1),
    ]
    engine = WeeklySeasonRankingEngine(LegacyFBSModel())
    with pytest.raises(ValueError, match="Previous-season or preseason rankings"):
        engine.rank(games, initial_ranks={"A": 1, "B": 2})


def test_weekly_engine_has_no_ranking_before_current_season_games():
    engine = WeeklySeasonRankingEngine(LegacyFBSModel())
    result = engine.rank([], teams=["A", "B", "C"])
    assert result.standings == ()


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
