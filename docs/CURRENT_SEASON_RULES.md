# Current-Season Ranking Rules

## Production scope

The live calculator ranks **all NCAA Division I football teams together**.

The active ranking pool contains:

- FBS teams
- FCS teams

FBS and FCS are subdivisions for identification and display only. They do not receive different ranking formulas.

## New season reset

Every season begins with a blank slate.

The production ranking does not import:

- previous-season rankings;
- previous-season statistics;
- previous-season records;
- preseason polls;
- preseason power ratings;
- conference-strength values.

No ranking is published before current-season games are played.

## Conference rule

Conferences have no mathematical strength value.

Conference membership may be displayed, filtered, or used for reporting, but it contributes zero ranking points.

## Week 1

Week 1 establishes the first ranking.

There is no previous current-season rank to use yet, so every in-pool Division I opponent receives:

```text
Opponent Rank Points = 0
```

Every Division I game is then scored as:

```text
Game Score = Win Bonus + Full Margin
```

where:

```text
Win Bonus = 10 for a win, 0 for a loss
Full Margin = points_for - points_against
```

This is identical for:

- FBS vs FBS
- FBS vs FCS
- FCS vs FBS
- FCS vs FCS

Example:

```text
Kansas State 71, Nicholls 3
Opponent Rank Points = 0
Win Bonus = 10
Margin = 68
Game Score = 78
```

Nicholls being FCS does not reduce the score because Nicholls is part of the same Division I ranking pool.

## Week 2 and later

Beginning in Week 2, each game uses the opponent's rank from the immediately preceding completed week of the same season.

For a Division I pool of `N` teams and an opponent ranked `R`:

```text
Win opponent points  = (N + 1) - R
Loss opponent points = -R
```

The complete game score is:

```text
Game Score = Opponent Rank Points + Win Bonus + Margin
```

The same equations apply to FBS and FCS teams.

## Cumulative season score

A team's ranking score is the sum of the game scores it has earned so far in the current season.

Earlier games are not retroactively rescored when an opponent moves up or down later.

Week 2 uses Week 1 ranks. Week 3 uses Week 2 ranks. This continues through the season.

## Teams that have not played yet

Before a team completes its first current-season game, it has zero current-season points.

It may appear at the bottom of the full pool for completeness, but that placement is not a preseason opinion or inherited ranking.

## Outside-Division-I games

Division II, Division III, NAIA, and other opponents outside the active Division I pool do not receive an opponent rank.

The active profile may apply its configured out-of-pool margin scale to those games. This is the only remaining classification-based scoring distinction.

## Tie handling

If teams have identical season scores, deterministic tiebreaking is used so the same inputs always produce the same order.

The engine can consider, in order:

1. head-to-head wins among the tied teams;
2. number of wins;
3. prior-week opponent-strength information accumulated during the current season;
4. deterministic team name/ID fallback.

No conference reputation or prior-season result is used as a tiebreaker.

## Production engine

The live current-season engine is:

```text
WeeklySeasonRankingEngine
```

The older recursive engine remains only for reproducing and studying historical spreadsheets.

## Guiding rule

**All NCAA Division I football teams are ranked together, and FBS and FCS are scored exactly the same.**
