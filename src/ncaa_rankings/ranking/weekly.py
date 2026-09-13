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


class WeeklySeasonRankingEngine:
    """Rank NCAA Division I football using only the current season.

    The production pool contains FBS and FCS teams together. Subdivision does
    not affect scoring. There is no preseason ranking, previous-season
    carryover, or conference strength.

    Week 1 creates the first ranking from Week 1 game totals alone. Beginning
    in Week 2, each game uses the opponent's rank from the immediately preceding
    completed week. Published weekly rankings are never recursively rewritten
    by later weeks.
    """

    def __init__(self, model: RankingModel) -> None:
        self.model = model

    def rank(
        self,
        games: Iterable[TeamGame],
        *,
        teams: Iterable[str] | None = None,
        initial_ranks: Mapping[str, int] | None = None,
        freeze_date: date | None = None,
        through_week: int | None = None,
    ) -> RankingResult:
        if initial_ranks:
            raise ValueError(
                "Previous-season or preseason rankings are not allowed in "
                "WeeklySeasonRankingEngine"
            )

        snapshots = self.rank_by_week(
            games,
            teams=teams,
            freeze_date=freeze_date,
            through_week=through_week,
        )
        if not snapshots:
            return RankingResult((), 0, True, False)
        return snapshots[max(snapshots)]

    def rank_by_week(
        self,
        games: Iterable[TeamGame],
        *,
        teams: Iterable[str] | None = None,
        freeze_date: date | None = None,
        through_week: int | None = None,
    ) -> dict[int, RankingResult]:
        game_list = tuple(games)
        if any(game.week is None for game in game_list):
            raise ValueError(
                "Every game must have a current-season week for weekly rankings"
            )
        if any(game.week is not None and game.week < 1 for game in game_list):
            raise ValueError("Game weeks must be 1 or greater")

        eligible_games = tuple(
            game
            for game in game_list
            if through_week is None or (game.week is not None and game.week <= through_week)
        )

        # No ranking exists before at least one current-season game is complete.
        if not eligible_games:
            return {}

        team_set = set(teams or ())
        team_set.update(game.team for game in eligible_games)
        team_set.update(
            game.opponent
            for game in eligible_games
            if game.opponent_in_rank_pool
        )
        if not team_set:
            return {}

        ordered_teams = sorted(team_set)
        team_count = len(ordered_teams)

        totals: dict[str, float] = defaultdict(float)
        wins: dict[str, int] = defaultdict(int)
        losses: dict[str, int] = defaultdict(int)
        opponent_strength: dict[str, float] = defaultdict(float)
        h2h_wins: dict[tuple[str, str], int] = defaultdict(int)

        previous_ranks: dict[str, int] | None = None
        snapshots: dict[int, RankingResult] = {}

        weeks = sorted({game.week for game in eligible_games if game.week is not None})
        for week in weeks:
            week_games = [game for game in eligible_games if game.week == week]
            for game in week_games:
                opponent_rank = (
                    previous_ranks.get(game.opponent)
                    if previous_ranks is not None
                    else None
                )
                age_weeks = self._age_weeks(game, freeze_date)
                component = self.model.score_game(
                    game,
                    opponent_rank,
                    team_count,
                    age_weeks=age_weeks,
                )
                totals[game.team] += component.total

                if opponent_rank is not None:
                    opponent_strength[game.team] += (team_count + 1) - opponent_rank

                if game.won:
                    wins[game.team] += 1
                    h2h_wins[(game.team, game.opponent)] += 1
                elif game.lost:
                    losses[game.team] += 1

            new_order = self._order_teams(
                ordered_teams,
                totals,
                wins,
                opponent_strength,
                h2h_wins,
            )
            current_ranks = {
                team: index + 1 for index, team in enumerate(new_order)
            }
            standings = tuple(
                TeamStanding(
                    team=team,
                    score=totals[team],
                    rank=current_ranks[team],
                    wins=wins[team],
                    losses=losses[team],
                    opponent_strength=opponent_strength[team],
                )
                for team in new_order
            )
            snapshots[week] = RankingResult(
                standings=standings,
                iterations=1,
                converged=True,
                cycle_detected=False,
            )
            previous_ranks = current_ranks

        return snapshots

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
        opponent_strength: Mapping[str, float],
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
                    -opponent_strength.get(team, 0.0),
                    team,
                )
            )
            result.extend(tied)
        return result
