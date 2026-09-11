from ncaa_rankings.models import LegacyFBSModel, ModernLegacyModel, Site, TeamGame


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


def test_legacy_out_of_pool_opponent_halves_margin():
    model = LegacyFBSModel(loss_rank_penalty=True)
    game = TeamGame(
        team="Alabama",
        opponent="Western Carolina",
        points_for=49,
        points_against=0,
        opponent_in_rank_pool=False,
    )
    score = model.score_game(game, opponent_rank=None, team_count=124)
    assert score.opponent_points == 0
    assert score.win_points == 10
    assert score.margin_points == 24.5
    assert score.total == 34.5


def test_modern_linear_defaults_reproduce_legacy_rank_math():
    modern = ModernLegacyModel(margin_transform="linear", home_field_points=0)
    legacy = LegacyFBSModel(loss_rank_penalty=True)
    games = [
        TeamGame("A", "B", 31, 17),
        TeamGame("A", "B", 17, 31),
    ]
    for game in games:
        modern_score = modern.score_game(game, opponent_rank=7, team_count=134)
        legacy_score = legacy.score_game(game, opponent_rank=7, team_count=134)
        assert modern_score.total == legacy_score.total


def test_home_field_neutralization_rewards_same_margin_more_on_road():
    model = ModernLegacyModel(
        margin_transform="linear",
        home_field_points=3,
    )
    home = TeamGame("A", "B", 27, 20, site=Site.HOME)
    road = TeamGame("A", "B", 27, 20, site=Site.AWAY)
    h = model.score_game(home, 20, 134)
    r = model.score_game(road, 20, 134)
    assert r.margin_points - h.margin_points == 6
