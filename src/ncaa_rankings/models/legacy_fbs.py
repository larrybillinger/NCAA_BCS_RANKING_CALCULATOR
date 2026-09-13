from __future__ import annotations

from dataclasses import dataclass

from .base import GameScore, TeamGame


@dataclass(frozen=True, slots=True)
class LegacyFBSModel:
    """Recovered 2012 FBS formula, generalized to the active ranking pool.

    The historical formula came from the FBS workbook, but the live project may
    apply it to a larger NCAA Division I pool containing both FBS and FCS teams.

    ``opponent_in_rank_pool`` controls whether the opponent is part of that
    active pool. An in-pool opponent with no rank yet (for example in Week 1)
    receives zero opponent-rank points but still uses the full scoring margin.
    Only a genuinely out-of-pool opponent uses ``out_of_pool_margin_scale``.
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

        # Week 1 in-pool opponents have no prior rank yet, but they are still
        # members of the ranking pool and therefore receive the full margin.
        # The reduced scale is reserved for true out-of-pool opponents only.
        if not game.opponent_in_rank_pool:
            margin_points *= self.out_of_pool_margin_scale

        return GameScore(
            opponent_points=opponent_points,
            win_points=win_points,
            margin_points=margin_points,
        )
