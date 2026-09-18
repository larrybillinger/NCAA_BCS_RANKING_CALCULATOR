from __future__ import annotations

from dataclasses import dataclass

from .base import GameScore, TeamGame
from .legacy_fbs import LegacyFBSModel


@dataclass(frozen=True, slots=True)
class DivisionIWeightedModel:
    """Live Division I scoring model.

    FBS and FCS are both NCAA Division I and share one ranking pool. The
    opponent-rank formula is unchanged, but the old +10 win bonus is removed.
    Actual scoring margin is used directly, with a seven-point site adjustment:

    - away win: +7
    - home loss: -7
    - home win, away loss, neutral-site result: 0

    FCS-side scaling remains:
    - FBS vs FBS: 100%
    - FBS vs FCS: 100%
    - FCS vs FCS: 50%
    - FCS loss to FBS: 50%
    - FCS win over FBS: 100%

    The scale applies to the whole production game score, including opponent
    rank points, margin points, and the site adjustment. Historical legacy
    models remain unchanged and still retain their recovered +10 win bonus.
    """

    loss_rank_penalty: bool = True
    out_of_pool_margin_scale: float = 0.5
    road_win_bonus: float = 7.0
    home_loss_penalty: float = 7.0
    fcs_vs_fcs_scale: float = 0.5
    fcs_loss_to_fbs_scale: float = 0.5
    fcs_win_over_fbs_scale: float = 1.0
    fcs_tie_vs_fbs_scale: float = 0.5

    name: str = "division_i_weighted_v4"

    def score_game(
        self,
        game: TeamGame,
        opponent_rank: float | None,
        team_count: int,
        *,
        age_weeks: float = 0.0,
    ) -> GameScore:
        if team_count < 1:
            raise ValueError("team_count must be positive")

        usable_rank = (
            game.opponent_in_rank_pool
            and opponent_rank is not None
            and 1 <= opponent_rank <= team_count
        )

        opponent_points = 0.0
        if usable_rank:
            if game.won:
                opponent_points = float((team_count + 1) - opponent_rank)
            elif game.lost and self.loss_rank_penalty:
                opponent_points = float(-opponent_rank)

        margin_points = float(game.margin)
        if not game.opponent_in_rank_pool:
            margin_points *= self.out_of_pool_margin_scale

        site_points = 0.0
        if game.won and game.site is Site.AWAY:
            site_points = self.road_win_bonus
        elif game.lost and game.site is Site.HOME:
            site_points = -self.home_loss_penalty

        scale = self._game_scale(game)

        return GameScore(
            opponent_points=opponent_points * scale,
            win_points=0.0,
            margin_points=margin_points * scale,
            site_points=site_points * scale,
        )

    def _game_scale(self, game: TeamGame) -> float:
        team_subdivision = game.team_subdivision.strip().upper()
        opponent_subdivision = game.opponent_subdivision.strip().upper()

        if team_subdivision != "FCS":
            return 1.0

        if opponent_subdivision == "FCS":
            return self.fcs_vs_fcs_scale

        if opponent_subdivision == "FBS":
            if game.won:
                return self.fcs_win_over_fbs_scale
            if game.lost:
                return self.fcs_loss_to_fbs_scale
            return self.fcs_tie_vs_fbs_scale

        return 1.0
