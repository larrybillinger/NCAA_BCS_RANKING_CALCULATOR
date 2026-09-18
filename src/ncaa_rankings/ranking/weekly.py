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

    The production pool contains FBS and FCS teams together. The active model
    may apply the documented FCS modifier, but there is no preseason ranking,
    previous-season carryover, or conference strength.

    Every team begins at the same neutral baseline because the current season
    contains no evidence yet. For scoring, that baseline is the average occupied
    rank of the full pool: (N + 1) / 2. Provider Week 0 is normalized into the
    first ranking period. An opponent stays on the neutral baseline until it has
    completed its first game; after that, the immediately preceding completed
    week's scoring rank is used. Exact score ties share average occupied rank.
    Published weekly rankings are never recursively rewritten by later weeks.
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
        if any(game.week is not None and game.week < 0 for game in game_list):
            raise ValueError("Game weeks must be 0 or greater")

        def ranking_week(game: TeamGame) -> int:
            # Provider Week 0 is part of the first ranking period.
            return max(1, int(game.week or 0))

        eligible_games = tuple(
            game
            for game in game_list
            if through_week is None or ranking_week(game) <= through_week
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

        neutral_rank = (team_count + 1) / 2.0
        previous_scoring_ranks: dict[str, float] = {
            team: neutral_rank for team in ordered_teams
        }
        snapshots: dict[int, RankingResult] = {}
        previously_played: set[str] = set()

        weeks = sorted({ranking_week(game) for game in eligible_games})
        for week in weeks:
            week_games = [game for game in eligible_games if ranking_week(game) == week]
            for game in week_games:
                opponent_rank = None
                if game.opponent_in_rank_pool:
                    opponent_rank = (
                        neutral_rank
                        if game.opponent not in previously_played
                        else previous_scoring_ranks.get(game.opponent)
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
            previous_scoring_ranks = self._scoring_ranks(new_order, totals)
            for game in week_games:
                previously_played.add(game.team)
                if game.opponent_in_rank_pool:
                    previously_played.add(game.opponent)

        return snapshots

    @staticmethod
    def _scoring_ranks(
        ordered_teams: list[str],
        totals: Mapping[str, float],
    ) -> dict[str, float]:
        """Return average occupied rank for every exact score tie.

        Display order remains deterministic, but opponent scoring does not
        pretend that tied teams have different mathematical ranks. For example,
        three teams tied across positions 10, 11, and 12 each receive a scoring
        rank of 11.0.
        """
        ranks: dict[str, float] = {}
        start = 0
        while start < len(ordered_teams):
            score = totals.get(ordered_teams[start], 0.0)
            end = start + 1
            while (
                end < len(ordered_teams)
                and totals.get(ordered_teams[end], 0.0) == score
            ):
                end += 1

            first_position = start + 1
            last_position = end
            average_rank = (first_position + last_position) / 2.0
            for index in range(start, end):
                ranks[ordered_teams[index]] = average_rank
            start = end

        return ranks

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
