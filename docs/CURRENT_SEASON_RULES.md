# Current-Season Ranking Rules

## Production scope

The live calculator ranks **all NCAA Division I football teams together**.

The active ranking pool contains:

- FBS teams
- FCS teams

Both subdivisions share one ranking table and one opponent-rank scale. FCS teams use a limited scoring modifier described below.

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

## Core game formula

Before any FCS modifier is applied, the normal Division I game score is:

```text
Game Score = Opponent Rank Points + Win Bonus + Margin
```

Beginning in Week 2, for a Division I pool of `N` teams and an opponent ranked `R`:

```text
Win opponent points  = (N + 1) - R
Loss opponent points = -R
Win bonus            = 10 for a win, 0 for a loss
Margin               = points_for - points_against
```

## FCS scoring modifier

FBS and FCS remain in the same ranking pool, but FCS teams receive a scoring multiplier based on the matchup result.

```text
FBS team vs any Division I opponent = 100% of normal game points
FCS team vs FCS opponent            = 50% of normal game points
FCS team loses to FBS opponent      = 50% of normal negative game points
FCS team beats FBS opponent         = 100% of normal game points
```

The multiplier applies to the visible game-score components:

- opponent-rank points;
- win points;
- margin points.

This means an FCS upset over an FBS team receives full credit, while ordinary FCS-vs-FCS results have half the ranking impact.

## Week 1

Week 1 establishes the first ranking.

There is no previous current-season rank to use yet, so every in-pool Division I opponent receives:

```text
Opponent Rank Points = 0
```

The normal Week 1 score is therefore:

```text
Normal Week 1 Game Score = Win Bonus + Margin
```

The FCS modifier is then applied when appropriate.

### FBS over FCS example

Kansas State 71, Nicholls 3

Kansas State is FBS, so its score is not reduced:

```text
Opponent Rank Points = 0
Win Bonus            = 10
Margin               = 68
Kansas State Score   = 78
```

Nicholls is FCS and lost to an FBS team, so its negative score is halved:

```text
Opponent Rank Points = 0
Win Bonus            = 0
Margin               = -68
Normal Score         = -68
FCS Multiplier       = 0.5
Nicholls Score       = -34
```

### FCS vs FCS example

If an FCS team wins 30-10 over another FCS team in Week 1:

```text
Opponent Rank Points = 0
Win Bonus            = 10
Margin               = 20
Normal Score         = 30
FCS Multiplier       = 0.5
Final Game Score     = 15
```

## Week 2 and later

Beginning in Week 2, each game uses the opponent's rank from the immediately preceding completed week of the same season.

The opponent-rank formula uses the full combined Division I ranking. An FCS opponent ranked #25 and an FBS opponent ranked #25 therefore supply the same base opponent-rank value before any FCS-team scoring modifier is applied.

Earlier games are not retroactively rescored when an opponent moves up or down later.

Week 2 uses Week 1 ranks. Week 3 uses Week 2 ranks. This continues through the season.

## Teams that have not played yet

Before a team completes its first current-season game, it has zero current-season points.

It may appear at the bottom of the full pool for completeness, but that placement is not a preseason opinion or inherited ranking.

## Outside-Division-I games

Division II, Division III, NAIA, and other opponents outside the active Division I pool do not receive an opponent rank.

The active profile may apply its configured out-of-pool margin scale to those games. That treatment is separate from the FCS-vs-FCS / FCS-vs-FBS modifier.

## Tie handling

If teams have identical season scores, deterministic tiebreaking is used so the same inputs always produce the same order.

The engine can consider, in order:

1. head-to-head wins among the tied teams;
2. number of wins;
3. prior-week opponent-strength information accumulated during the current season;
4. deterministic team name/ID fallback.

No conference reputation or prior-season result is used as a tiebreaker.

## Production engine and model

The live current-season engine is:

```text
WeeklySeasonRankingEngine
```

The live scoring model is:

```text
division_i_weighted_v1
```

The older recursive engine and legacy FBS model remain available for historical reproduction and research.

## Guiding rule

**Rank FBS and FCS together, give FCS teams half credit for FCS-vs-FCS games and FCS losses to FBS, and give FCS teams full credit when they beat FBS teams.**
