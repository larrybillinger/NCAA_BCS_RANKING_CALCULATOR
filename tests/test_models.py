from ncaa_rankings.models import (
    DivisionIWeightedModel,
    LegacyFBSModel,
    ModernLegacyModel,
    Site,
    TeamGame,
)


def test_legacy_alabama_michigan_example():
    model = LegacyFBSModel(loss_rank_penalty=True)
    game = TeamGame(
        team="Alabama",
        opponent="Michigan",
        points_for=41,
        points_against=14,
        site=Site.NEUTRAL,
    )
    score = model.score_game(game, opponent_rank=26, team_count=124)
    assert score.opponent_points == 99
    assert score.win_points == 10
    assert score.margin_points == 27
    assert score.total == 136


def test_legacy_alabama_texas_am_loss_example():
    model = LegacyFBSModel(loss_rank_penalty=True)
    game = TeamGame(
        team="Alabama",
        opponent="Texas A&M",
        points_for=24,
        points_against=29,
    )
    score = model.score_game(game, opponent_rank=8, team_count=124)
    assert score.opponent_points == -8
    assert score.win_points == 0
    assert score.margin_points == -5
    assert score.total == -13


def test_true_out_of_pool_opponent_halves_margin():
    model = LegacyFBSModel(loss_rank_penalty=True)
    game = TeamGame(
        team="Alabama",
        opponent="Division II Opponent",
        points_for=49,
        points_against=0,
        opponent_in_rank_pool=False,
        opponent_subdivision="DII",
    )
    score = model.score_game(game, opponent_rank=None, team_count=266)
    assert score.opponent_points == 0
    assert score.win_points == 10
    assert score.margin_points == 24.5
    assert score.total == 34.5


def test_week1_fbs_over_fcs_keeps_full_score():
    model = DivisionIWeightedModel()
    game = TeamGame(
        team="Kansas State",
        opponent="Nicholls",
        points_for=71,
        points_against=3,
        opponent_in_rank_pool=True,
        week=1,
        team_subdivision="FBS",
        opponent_subdivision="FCS",
    )
    score = model.score_game(game, opponent_rank=None, team_count=266)
    assert score.opponent_points == 0
    assert score.win_points == 10
    assert score.margin_points == 68
    assert score.total == 78


def test_week1_fcs_loss_to_fbs_is_half_negative_score():
    model = DivisionIWeightedModel()
    game = TeamGame(
        team="Nicholls",
        opponent="Kansas State",
        points_for=3,
        points_against=71,
        opponent_in_rank_pool=True,
        week=1,
        team_subdivision="FCS",
        opponent_subdivision="FBS",
    )
    score = model.score_game(game, opponent_rank=None, team_count=266)
    assert score.opponent_points == 0
    assert score.win_points == 0
    assert score.margin_points == -34
    assert score.total == -34


def test_fcs_vs_fcs_scores_half_of_normal_points():
    model = DivisionIWeightedModel()
    game = TeamGame(
        team="FCS A",
        opponent="FCS B",
        points_for=31,
        points_against=17,
        team_subdivision="FCS",
        opponent_subdivision="FCS",
    )
    score = model.score_game(game, opponent_rank=40, team_count=266)
    assert score.opponent_points == 113.5
    assert score.win_points == 5
    assert score.margin_points == 7
    assert score.total == 125.5


def test_fcs_loss_to_fbs_scores_half_of_negative_points():
    model = DivisionIWeightedModel()
    game = TeamGame(
        team="FCS Team",
        opponent="FBS Team",
        points_for=17,
        points_against=31,
        team_subdivision="FCS",
        opponent_subdivision="FBS",
    )
    score = model.score_game(game, opponent_rank=40, team_count=266)
    assert score.opponent_points == -20
    assert score.win_points == 0
    assert score.margin_points == -7
    assert score.total == -27


def test_fcs_win_over_fbs_scores_full_points():
    model = DivisionIWeightedModel()
    game = TeamGame(
        team="FCS Team",
        opponent="FBS Team",
        points_for=31,
        points_against=17,
        team_subdivision="FCS",
        opponent_subdivision="FBS",
    )
    score = model.score_game(game, opponent_rank=40, team_count=266)
    assert score.opponent_points == 227
    assert score.win_points == 10
    assert score.margin_points == 14
    assert score.total == 251


def test_fbs_scores_full_points_against_fcs():
    model = DivisionIWeightedModel()
    game = TeamGame(
        team="FBS Team",
        opponent="FCS Team",
        points_for=31,
        points_against=17,
        team_subdivision="FBS",
        opponent_subdivision="FCS",
    )
    score = model.score_game(game, opponent_rank=40, team_count=266)
    assert score.opponent_points == 227
    assert score.win_points == 10
    assert score.margin_points == 14
    assert score.total == 251


def test_historical_legacy_model_remains_subdivision_neutral():
    model = LegacyFBSModel(loss_rank_penalty=True)
    fbs_game = TeamGame(
        "FBS Team",
        "FCS Team",
        31,
        17,
        team_subdivision="FBS",
        opponent_subdivision="FCS",
    )
    fcs_game = TeamGame(
        "FCS Team",
        "FBS Team",
        31,
        17,
        team_subdivision="FCS",
        opponent_subdivision="FBS",
    )
    fbs_score = model.score_game(fbs_game, opponent_rank=40, team_count=266)
    fcs_score = model.score_game(fcs_game, opponent_rank=40, team_count=266)
    assert fbs_score == fcs_score


def test_modern_linear_defaults_reproduce_legacy_rank_math():
    modern = ModernLegacyModel(margin_transform="linear", home_field_points=0)
    legacy = LegacyFBSModel(loss_rank_penalty=True)
    games = [
        TeamGame("A", "B", 31, 17),
        TeamGame("A", "B", 17, 31),
    ]
    for game in games:
        modern_score = modern.score_game(game, opponent_rank=7, team_count=266)
        legacy_score = legacy.score_game(game, opponent_rank=7, team_count=266)
        assert modern_score.total == legacy_score.total


def test_home_field_neutralization_rewards_same_margin_more_on_road():
    model = ModernLegacyModel(
        margin_transform="linear",
        home_field_points=3,
    )
    home = TeamGame("A", "B", 27, 20, site=Site.HOME)
    road = TeamGame("A", "B", 27, 20, site=Site.AWAY)
    h = model.score_game(home, 20, 266)
    r = model.score_game(road, 20, 266)
    assert r.margin_points - h.margin_points == 6
