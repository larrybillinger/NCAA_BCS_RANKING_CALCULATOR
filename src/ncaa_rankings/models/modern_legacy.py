from __future__ import annotations

from dataclasses import dataclass
from math import log1p, sqrt, tanh

from .base import GameScore, TeamGame


@dataclass(frozen=True, slots=True)
class ModernLegacyModel:
    """Research candidate derived from the recovered FBS model.

    This class is intentionally parameterized. It is a candidate family, not
    a claim that any one parameter set has already beaten the legacy model.

    Production season logic supplies only current-season prior-week ranks.
    Week 1 therefore has no opponent-rank component, but FBS opponents still
    use the full scoring margin. Only out-of-pool opponents use the configured
    reduced margin scale.
    """

    rank_weight: float = 1.0
    loss_weight: float = 1.0
    win_rank_gamma: float = 1.0
    loss_rank_gamma: float = 1.0
    win_bonus: float = 10.0
    margin_transform: str = "tanh"
    margin_cap: float = 28.0
    margin_weight: float = 1.0
    home_field_points: float = 0.0
    recency_half_life: float | None = None
    out_of_pool_margin_scale: float = 0.5

    name: str = "modern_legacy_candidate_v1"

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
        if self.margin_cap <= 0:
            raise ValueError("margin_cap must be positive")

        usable_rank = (
            game.opponent_in_rank_pool
            and opponent_rank is not None
            and 1 <= opponent_rank <= team_count
        )

        opponent_points = 0.0
        if usable_rank:
            if game.won:
                q = ((team_count + 1) - opponent_rank) / team_count
                opponent_points = (
                    self.rank_weight
                    * team_count
                    * (q ** self.win_rank_gamma)
                )
            elif game.lost:
                badness = opponent_rank / team_count
                opponent_points = -(
                    self.loss_weight
                    * team_count
                    * (badness ** self.loss_rank_gamma)
                )

        win_points = self.win_bonus if game.won else 0.0

        neutralized_margin = float(game.margin) - (
            self.home_field_points * game.site.sign
        )
        margin_points = self.margin_weight * self._transform_margin(
            neutralized_margin
        )
        if not game.opponent_in_rank_pool:
            margin_points *= self.out_of_pool_margin_scale

        recency_weight = 1.0
        if self.recency_half_life is not None:
            if self.recency_half_life <= 0:
                raise ValueError("recency_half_life must be positive or None")
            recency_weight = 2 ** (-max(age_weeks, 0.0) / self.recency_half_life)

        return GameScore(
            opponent_points=opponent_points,
            win_points=win_points,
            margin_points=margin_points,
            recency_weight=recency_weight,
        )

    def _transform_margin(self, margin: float) -> float:
        transform = self.margin_transform.lower()
        c = self.margin_cap

        if transform == "linear":
            return margin
        if transform == "cap":
            return max(-c, min(c, margin))
        if transform == "sqrt":
            return (1 if margin >= 0 else -1) * sqrt(abs(margin))
        if transform == "log1p":
            return (1 if margin >= 0 else -1) * log1p(abs(margin))
        if transform == "tanh":
            return c * tanh(margin / c)

        raise ValueError(f"Unknown margin transform: {self.margin_transform}")
