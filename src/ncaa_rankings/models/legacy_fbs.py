from __future__ import annotations

from dataclasses import dataclass

from .base import GameScore, TeamGame


@dataclass(frozen=True, slots=True)
class LegacyFBSModel:
    """Recovered 2012 FBS formula.

    The later profile adds the rank-based loss penalty. The original profile
    gives zero opponent-rank points on losses. Opponents outside the FBS rank
    pool receive no opponent-rank points and use the configured margin scale.
    """

    loss_rank_penalty: bool = True
    win_bonus: float = 10.0
    out_of_pool_margin_scale: float = 0.5

    @property
    def name(self) -> str:
        return (
            "legacy_fbs_2012_later"
            if self.loss_rank_penalty
            else "legacy_fbs_2012_original"
        )

    def score_game(
        self,
        game: TeamGame,
        opponent_rank: int | None,
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

        win_points = self.win_bonus if game.won else 0.0
        margin_points = float(game.margin)
        if not usable_rank:
            margin_points *= self.out_of_pool_margin_scale

        return GameScore(
            opponent_points=opponent_points,
            win_points=win_points,
            margin_points=margin_points,
        )
