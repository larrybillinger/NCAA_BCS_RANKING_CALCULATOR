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

## Before Week 1 and the neutral tied baseline

Before any current-season game is played, every Division I team is tied for first conceptually because there is no current-season evidence separating them.

That T-1 state is **not a preseason opinion ranking**. It is the neutral mathematical state for a team that has not yet produced a current-season result.

For opponent scoring, a tie uses the average numerical rank of the positions occupied by the tie. Because all `N` teams are tied before Week 1, the neutral Week 1 scoring rank is:

```text
Neutral Week 1 Scoring Rank = (N + 1) / 2
```

For the 2026 pool of 266 teams:

```text
Neutral Week 1 Scoring Rank = 133.5
```

The normal first-game score therefore uses that same neutral rank for an in-pool Division I opponent that has not played yet, before the normal FCS modifier is applied. Provider Week 0 games are normalized into ranking Week 1.

### FBS over FCS example

Kansas State 71, Nicholls 3

Kansas State is FBS, so its score is not reduced:

```text
Opponent Rank Points = 267 - 133.5 = 133.5
Win Bonus            = 10
Margin               = 68
Kansas State Score   = 211.5
```

Nicholls is FCS and lost to an FBS team, so its negative score is halved:

```text
Opponent Rank Points = -133.5
Win Bonus            = 0
Margin               = -68
Normal Score         = -201.5
FCS Multiplier       = 0.5
Nicholls Score       = -100.75
```

### FCS vs FCS example

If an FCS team wins 30-10 over another FCS team in Week 1:

```text
Opponent Rank Points = 133.5
Win Bonus            = 10
Margin               = 20
Normal Score         = 163.5
FCS Multiplier       = 0.5
Final Game Score     = 81.75
```

## Week 2 and later

Beginning after a team has completed its first game, opponents use that team's scoring rank from the immediately preceding completed week of the same season. If the opponent still has not played, it remains at the neutral baseline rather than receiving an artificial rank based only on inactivity.

Display order remains deterministic, but exact score ties do not receive artificial different values for opponent scoring. If three teams tie on score across display positions 10, 11, and 12, each carries scoring rank 11.0 into the next week:

```text
Tie Scoring Rank = (10 + 11 + 12) / 3 = 11
```

The opponent-rank formula uses the full combined Division I ranking. An FCS opponent with scoring rank 25 and an FBS opponent with scoring rank 25 therefore supply the same base opponent-rank value before any FCS-team scoring modifier is applied.

Earlier games are not retroactively rescored when an opponent moves up or down later.

Week 2 uses Week 1 ranks. Week 3 uses Week 2 ranks. This continues through the season.

## Teams that have not played yet

Before a team completes its first current-season game, it has zero current-season points and remains on the neutral T-1 scoring baseline for opponent-value purposes.

The website may list the team for completeness, but any display placement before its first result is not used as its opponent-scoring rank.

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
division_i_weighted_v3
```

The older recursive engine and legacy FBS model remain available for historical reproduction and research.

## Guiding rule

**Every team begins on the same neutral first-game baseline; Week 0 belongs to ranking Week 1; unplayed teams stay neutral until their first result; exact score ties use average occupied ranks; FBS and FCS share one pool; and the documented FCS modifiers apply without retroactively rescoring old games.**
