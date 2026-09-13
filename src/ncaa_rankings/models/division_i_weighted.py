from __future__ import annotations

from dataclasses import dataclass

from .base import GameScore, TeamGame
from .legacy_fbs import LegacyFBSModel


@dataclass(frozen=True, slots=True)
class DivisionIWeightedModel:
    """Live Division I scoring model with a limited FCS point modifier.

    The active ranking pool still contains both FBS and FCS teams. The core
    opponent-rank, win-bonus, and margin formula comes from the recovered later
    FBS model, but live FCS game totals are scaled as follows:

    - FCS vs FCS: 50% of the normal game score for the FCS team.
    - FCS loss to FBS: 50% of the normal negative game score.
    - FCS win over FBS: 100% of the normal game score.
    - FBS teams: 100% of the normal game score regardless of opponent.

    Historical legacy models remain unchanged and can still reproduce the old
    workbook behavior independently of this production model.
    """

    loss_rank_penalty: bool = True
    win_bonus: float = 10.0
    out_of_pool_margin_scale: float = 0.5
    fcs_vs_fcs_scale: float = 0.5
    fcs_loss_to_fbs_scale: float = 0.5
    fcs_win_over_fbs_scale: float = 1.0
    fcs_tie_vs_fbs_scale: float = 0.5

    name: str = "division_i_weighted_v1"

    def score_game(
        self,
        game: TeamGame,
        opponent_rank: int | None,
        team_count: int,
        *,
        age_weeks: float = 0.0,
    ) -> GameScore:
        base_model = LegacyFBSModel(
            loss_rank_penalty=self.loss_rank_penalty,
            win_bonus=self.win_bonus,
            out_of_pool_margin_scale=self.out_of_pool_margin_scale,
        )
        base_score = base_model.score_game(
            game,
            opponent_rank,
            team_count,
            age_weeks=age_weeks,
        )
        scale = self._game_scale(game)

        return GameScore(
            opponent_points=base_score.opponent_points * scale,
            win_points=base_score.win_points * scale,
            margin_points=base_score.margin_points * scale,
            recency_weight=base_score.recency_weight,
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

        # Games against teams outside FBS/FCS retain the normal legacy-derived
        # out-of-pool handling rather than receiving an additional FCS penalty.
        return 1.0
