from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable, Mapping

from ncaa_rankings.models.base import (
    RankingModel,
    RankingResult,
    TeamGame,
    TeamStanding,
)


class RecursiveRankingEngine:
    """Recalculate FBS season totals until the rank ordering settles.

    Only teams in the active FBS rank pool should be passed in ``teams`` or
    represented by games whose ``opponent_in_rank_pool`` flag is True.

    The engine tracks prior rank permutations so an artificial schedule cannot
    cause an infinite loop. A repeated ordering is reported as a cycle.
    """

    def __init__(self, model: RankingModel, max_iterations: int = 100) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        self.model = model
        self.max_iterations = max_iterations

    def rank(
        self,
        games: Iterable[TeamGame],
        *,
        teams: Iterable[str] | None = None,
        initial_ranks: Mapping[str, int] | None = None,
        freeze_date: date | None = None,
    ) -> RankingResult:
        game_list = tuple(games)
        team_set = set(teams or ())
        team_set.update(g.team for g in game_list)
        team_set.update(g.opponent for g in game_list if g.opponent_in_rank_pool)
        if not team_set:
            return RankingResult((), 0, True, False)

        ordered_teams = sorted(team_set)
        team_count = len(ordered_teams)
        ranks = self._initial_ranks(ordered_teams, initial_ranks)
        seen: set[tuple[str, ...]] = set()

        last_standings: tuple[TeamStanding, ...] = ()
        for iteration in range(1, self.max_iterations + 1):
            order_key = tuple(
                team for team, _ in sorted(ranks.items(), key=lambda item: item[1])
            )
            if order_key in seen:
                return RankingResult(
                    standings=last_standings,
                    iterations=iteration - 1,
                    converged=False,
                    cycle_detected=True,
                )
            seen.add(order_key)

            totals = defaultdict(float)
            wins = defaultdict(int)
            losses = defaultdict(int)
            opp_strength = defaultdict(float)
            h2h_wins: dict[tuple[str, str], int] = defaultdict(int)

            for game in game_list:
                if game.team not in team_set:
                    continue
                opponent_rank = ranks.get(game.opponent)
                age_weeks = self._age_weeks(game, freeze_date)
                component = self.model.score_game(
                    game,
                    opponent_rank,
                    team_count,
                    age_weeks=age_weeks,
                )
                totals[game.team] += component.total
                if opponent_rank is not None:
                    opp_strength[game.team] += (team_count + 1) - opponent_rank
                if game.won:
                    wins[game.team] += 1
                    h2h_wins[(game.team, game.opponent)] += 1
                elif game.lost:
                    losses[game.team] += 1

            new_order = self._order_teams(
                ordered_teams,
                totals,
                wins,
                opp_strength,
                h2h_wins,
            )
            new_ranks = {team: idx + 1 for idx, team in enumerate(new_order)}
            last_standings = tuple(
                TeamStanding(
                    team=team,
                    score=totals[team],
                    rank=new_ranks[team],
                    wins=wins[team],
                    losses=losses[team],
                    opponent_strength=opp_strength[team],
                )
                for team in new_order
            )

            if new_ranks == ranks:
                return RankingResult(
                    standings=last_standings,
                    iterations=iteration,
                    converged=True,
                    cycle_detected=False,
                )
            ranks = new_ranks

        return RankingResult(
            standings=last_standings,
            iterations=self.max_iterations,
            converged=False,
            cycle_detected=False,
        )

    @staticmethod
    def _initial_ranks(
        teams: list[str], initial_ranks: Mapping[str, int] | None
    ) -> dict[str, int]:
        if not initial_ranks:
            return {team: idx + 1 for idx, team in enumerate(teams)}

        return {
            team: rank
            for rank, team in enumerate(
                sorted(
                    teams,
                    key=lambda team: (initial_ranks.get(team, 10**9), team),
                ),
                start=1,
            )
        }

    @staticmethod
    def _age_weeks(game: TeamGame, freeze_date: date | None) -> float:
        if freeze_date is None or game.played_on is None:
            return 0.0
        return max((freeze_date - game.played_on).days / 7.0, 0.0)

    @staticmethod
    def _order_teams(
        teams: list[str],
        totals: Mapping[str, float],
        wins: Mapping[str, int],
        opp_strength: Mapping[str, float],
        h2h_wins: Mapping[tuple[str, str], int],
    ) -> list[str]:
        groups: dict[float, list[str]] = defaultdict(list)
        for team in teams:
            groups[totals.get(team, 0.0)].append(team)

        result: list[str] = []
        for score in sorted(groups, reverse=True):
            tied = groups[score]
            tied_set = set(tied)
            tied.sort(
                key=lambda team: (
                    -sum(
                        h2h_wins.get((team, opponent), 0)
                        for opponent in tied_set
                        if opponent != team
                    ),
                    -wins.get(team, 0),
                    -opp_strength.get(team, 0.0),
                    team,
                )
            )
            result.extend(tied)
        return result
