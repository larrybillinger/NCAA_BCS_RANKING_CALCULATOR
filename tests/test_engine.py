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

    # Before Week 1 all four teams are tied, so the scoring rank is the
    # average occupied position: (1 + 4) / 2 = 2.5.
    # A: (5 - 2.5) + 7 = 9.5.
    # C is FCS vs FCS, so ((5 - 2.5) + 40) * 0.5 = 21.25.
    assert result.scores["C"] == 21.25
    assert result.scores["A"] == 9.5
    assert result.scores["B"] == -9.5
    assert result.scores["D"] == -21.25
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
    # opponent points = 5 - 2 = 3, margin = 3, total = 6.
    # FCS-over-FBS wins are not halved, so D rises from -21.25 to -15.25.
    assert snapshots[2].scores["D"] == -15.25
    assert snapshots[2].ranks["D"] == 4



def test_tied_previous_week_scores_use_average_occupied_rank():
    games = [
        TeamGame("A", "C", 20, 10, week=1),
        TeamGame("C", "A", 10, 20, week=1),
        TeamGame("B", "D", 20, 10, week=1),
        TeamGame("D", "B", 10, 20, week=1),
        TeamGame("C", "A", 14, 13, week=2),
        TeamGame("A", "C", 13, 14, week=2),
    ]
    engine = WeeklySeasonRankingEngine(DivisionIWeightedModel())
    snapshots = engine.rank_by_week(games, teams=["A", "B", "C", "D"])

    # A and B tie on Week 1 score and occupy display positions 1 and 2.
    # Both therefore carry scoring rank 1.5 into Week 2. C starts Week 2
    # at -12.5 and earns (5 - 1.5) + 1 = 4.5, finishing at -8.0.
    assert snapshots[1].scores["A"] == snapshots[1].scores["B"] == 12.5
    assert snapshots[2].scores["C"] == -8.0



def test_week_zero_is_folded_into_first_ranking_period():
    games = [
        TeamGame("A", "B", 20, 10, week=0),
        TeamGame("B", "A", 10, 20, week=0),
        TeamGame("C", "D", 17, 7, week=1),
        TeamGame("D", "C", 7, 17, week=1),
    ]
    engine = WeeklySeasonRankingEngine(DivisionIWeightedModel())
    snapshots = engine.rank_by_week(games, teams=["A", "B", "C", "D"])

    assert list(snapshots) == [1]
    assert snapshots[1].scores["A"] == snapshots[1].scores["C"]


def test_unplayed_opponent_keeps_neutral_rank_until_first_game():
    games = [
        TeamGame(
            "A",
            "Outside",
            20,
            10,
            week=1,
            opponent_in_rank_pool=False,
        ),
        TeamGame("B", "C", 7, 0, week=2),
        TeamGame("C", "B", 0, 7, week=2),
    ]
    engine = WeeklySeasonRankingEngine(DivisionIWeightedModel())
    snapshots = engine.rank_by_week(games, teams=["A", "B", "C"])

    # N=3 -> neutral scoring rank is 2.0. B and C had not played before
    # Week 2, so C remains neutral for B's first game even though the
    # post-Week-1 display order would otherwise give the idle pair a tie rank.
    # B Week 2 = (4 - 2) + 7 = 9.
    assert snapshots[2].scores["B"] == 9.0


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
