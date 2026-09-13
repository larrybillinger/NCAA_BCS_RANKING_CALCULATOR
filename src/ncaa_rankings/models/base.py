from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Mapping, Protocol


class Site(str, Enum):
    HOME = "home"
    AWAY = "away"
    NEUTRAL = "neutral"

    @property
    def sign(self) -> int:
        if self is Site.HOME:
            return 1
        if self is Site.AWAY:
            return -1
        return 0


@dataclass(frozen=True, slots=True)
class TeamGame:
    """One completed game from one ranked Division I team's point of view.

    ``opponent_in_rank_pool`` should be True for any NCAA Division I football
    opponent in the active season ranking pool, whether that opponent is FBS
    or FCS. It should be False only for opponents outside the active Division I
    pool, such as Division II, Division III, NAIA, or other classifications.
    """

    team: str
    opponent: str
    points_for: int
    points_against: int
    site: Site = Site.NEUTRAL
    played_on: date | None = None
    opponent_in_rank_pool: bool = True
    season_type: str = "regular"
    week: int | None = None

    @property
    def won(self) -> bool:
        return self.points_for > self.points_against

    @property
    def lost(self) -> bool:
        return self.points_for < self.points_against

    @property
    def tied(self) -> bool:
        return self.points_for == self.points_against

    @property
    def margin(self) -> int:
        return self.points_for - self.points_against


@dataclass(frozen=True, slots=True)
class GameScore:
    opponent_points: float
    win_points: float
    margin_points: float
    recency_weight: float = 1.0

    @property
    def total(self) -> float:
        return (
            self.opponent_points
            + self.win_points
            + self.margin_points
        ) * self.recency_weight


class RankingModel(Protocol):
    name: str

    def score_game(
        self,
        game: TeamGame,
        opponent_rank: int | None,
        team_count: int,
        *,
        age_weeks: float = 0.0,
    ) -> GameScore: ...


@dataclass(frozen=True, slots=True)
class TeamStanding:
    team: str
    score: float
    rank: int
    wins: int
    losses: int
    opponent_strength: float


@dataclass(frozen=True, slots=True)
class RankingResult:
    standings: tuple[TeamStanding, ...]
    iterations: int
    converged: bool
    cycle_detected: bool

    @property
    def ranks(self) -> Mapping[str, int]:
        return {standing.team: standing.rank for standing in self.standings}

    @property
    def scores(self) -> Mapping[str, float]:
        return {standing.team: standing.score for standing in self.standings}
