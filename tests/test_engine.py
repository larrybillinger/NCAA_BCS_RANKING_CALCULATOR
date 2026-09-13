from datetime import date

import pytest

from ncaa_rankings.evaluation import PostseasonMatchup, accuracy, frozen_postseason_backtest
from ncaa_rankings.models import DivisionIWeightedModel, LegacyFBSModel, TeamGame
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


def test_week_one_creates_first_ranking_with_fcs_modifier():
    games = [
        TeamGame(
            "A", "B", 21, 14,
            week=1,
            team_subdivision="FBS",
            opponent_subdivision="FBS",
        ),
        TeamGame(
            "B", "A", 14, 21,
            week=1,
            team_subdivision="FBS",
            opponent_subdivision="FBS",
        ),
        TeamGame(
            "C", "D", 40, 0,
            week=1,
            team_subdivision="FCS",
            opponent_subdivision="FCS",
        ),
        TeamGame(
            "D", "C", 0, 40,
            week=1,
            team_subdivision="FCS",
            opponent_subdivision="FCS",
        ),
    ]
    engine = WeeklySeasonRankingEngine(DivisionIWeightedModel())
    result = engine.rank(games, teams=["A", "B", "C", "D"])

    # Week 1 has no opponent-rank points. A's FBS win scores normally:
    # +10 win +7 margin = 17. C's FCS-vs-FCS win is halved:
    # (+10 win +40 margin) * 0.5 = 25.
    assert result.scores["C"] == 25
    assert result.scores["A"] == 17
    assert result.scores["B"] == -7
    assert result.scores["D"] == -20
    assert result.ranks == {"C": 1, "A": 2, "B": 3, "D": 4}


def test_week_two_uses_week_one_ranks_and_full_fcs_upset_points():
    games = [
        TeamGame(
            "A", "B", 21, 14,
            week=1,
            team_subdivision="FBS",
            opponent_subdivision="FBS",
        ),
        TeamGame(
            "B", "A", 14, 21,
            week=1,
            team_subdivision="FBS",
            opponent_subdivision="FBS",
        ),
        TeamGame(
            "C", "D", 40, 0,
            week=1,
            team_subdivision="FCS",
            opponent_subdivision="FCS",
        ),
        TeamGame(
            "D", "C", 0, 40,
            week=1,
            team_subdivision="FCS",
            opponent_subdivision="FCS",
        ),
        TeamGame(
            "D", "A", 20, 17,
            week=2,
            team_subdivision="FCS",
            opponent_subdivision="FBS",
        ),
        TeamGame(
            "A", "D", 17, 20,
            week=2,
            team_subdivision="FBS",
            opponent_subdivision="FCS",
        ),
    ]
    engine = WeeklySeasonRankingEngine(DivisionIWeightedModel())
    snapshots = engine.rank_by_week(games, teams=["A", "B", "C", "D"])

    assert snapshots[1].ranks == {"C": 1, "A": 2, "B": 3, "D": 4}

    # D is FCS and beats the Week 1 #2 FBS team A. With N=4:
    # opponent points = 5 - 2 = 3, win = 10, margin = 3, total = 16.
    # FCS-over-FBS wins are not halved, so D rises from -20 to -4.
    assert snapshots[2].scores["D"] == -4
    assert snapshots[2].ranks["D"] == 3


def test_weekly_engine_rejects_previous_season_seed():
    games = [
        TeamGame("A", "B", 21, 14, week=1),
        TeamGame("B", "A", 14, 21, week=1),
    ]
    engine = WeeklySeasonRankingEngine(DivisionIWeightedModel())
    with pytest.raises(ValueError, match="Previous-season or preseason rankings"):
        engine.rank(games, initial_ranks={"A": 1, "B": 2})


def test_weekly_engine_has_no_ranking_before_current_season_games():
    engine = WeeklySeasonRankingEngine(DivisionIWeightedModel())
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
