# Current-Season FBS Ranking Rules

This document is the authoritative policy for the live NCAA BCS Ranking Calculator.

Historical workbook behavior may differ. When legacy behavior conflicts with this document, the live/current-season calculator follows this document.

## 1. Ranking pool

Only FBS teams are ranked.

FCS and other out-of-pool teams may appear as opponents on an FBS schedule, but they do not receive a published ranking in this project.

## 2. Every season starts from zero

At the start of a new season:

```text
team ranking points = 0
team wins = 0
team losses = 0
team opponent strength = 0
```

No information from a previous season is loaded into the live ranking calculation.

Forbidden carryover includes:

- final ranking;
- wins/losses;
- scoring margin;
- strength of schedule;
- conference performance;
- AP/Coaches/CFP ranking;
- external power rating;
- any preseason seed derived from prior performance.

Historical seasons may be analyzed to improve formula coefficients, but they cannot give a team points or rank position in a new season.

## 3. Conferences have no strength

Conference membership is metadata only.

```text
conference bonus = 0
conference penalty = 0
conference prior = 0
```

A team's conference can be displayed, filtered, or used for schedule context. It cannot directly change the team's ranking score.

## 4. No preseason ranking

Before current-season games have been completed, the calculator publishes no ranking.

There is no artificial #1 through #N ordering before Week 1 provides evidence.

## 5. Week 1 establishes the first ranking

There is no prior current-season opponent ranking available in Week 1.

Therefore:

```text
Week 1 Opponent Rank Score = 0
```

The first ranking is determined entirely by Week 1 current-season game totals.

With the recovered default scoring rules:

### FBS-vs-FBS

```text
win bonus = 10 on a win
margin = points_for - points_against
opponent-rank points = 0
```

### FBS-vs-FCS/out-of-pool

```text
win bonus = 10 on a win
margin = (points_for - points_against) * 0.5
opponent-rank points = 0
```

A loss receives no win bonus. Margin remains negative when the FBS team loses.

Once all eligible Week 1 results are entered, cumulative Week 1 totals are sorted to create the first ranking.

## 6. Week 2 begins full opponent-rank scoring

Week 2 uses the ranking produced after Week 1.

For an FBS pool of `N` teams and a Week 1 opponent rank `R`:

```text
Win opponent points  = (N + 1) - R
Loss opponent points = -R
```

The normal win bonus and scoring-margin rules are then added.

Example with 138 FBS teams:

```text
beat Week 1 #1   -> +138 opponent points
beat Week 1 #25  -> +114 opponent points
beat Week 1 #138 ->   +1 opponent point

lose to Week 1 #1   ->   -1 opponent point
lose to Week 1 #25  ->  -25 opponent points
lose to Week 1 #138 -> -138 opponent points
```

## 7. Each week uses the previous completed week

The live ranking is causal and sequential:

```text
Week 1 results -> Week 1 ranking
Week 2 uses Week 1 ranks -> Week 2 ranking
Week 3 uses Week 2 ranks -> Week 3 ranking
...
```

A later week does not rewrite the opponent rank used to score an earlier game.

This means the audit record for every game can permanently state exactly which opponent rank was known and used at the time.

## 8. Scores accumulate only within the current season

Each game adds to the same current-season cumulative total.

```text
Season Score after Week K
    = sum of Game Scores from Weeks 1 through K
```

At no point is a prior-season score added.

## 9. Ties in ranking points

When teams have identical cumulative ranking points, the engine uses current-season information only, in this order:

1. head-to-head wins among the tied teams;
2. current-season wins;
3. accumulated current-season opponent-strength value;
4. school name as a final deterministic ordering rule.

The final alphabetical fallback has no strength meaning; it only ensures reproducible output when all football-based tiebreakers are identical.

## 10. Historical recursive engine

The repository retains `RecursiveRankingEngine` because it is useful for reconstructing and comparing the old workbook.

It is not the production live-season engine.

The production engine is:

```text
WeeklySeasonRankingEngine
```

## 11. Postseason freeze

At the end of the pre-postseason schedule, the final current-season ranking is frozen.

That one frozen ranking predicts all bowl and CFP games for research purposes. Postseason outcomes are not fed back into the ranking used to predict later postseason games.

## 12. Formula research boundary

Historical backtesting may tune transparent current-season scoring terms such as:

- opponent-rank weighting;
- bad-loss weighting;
- win bonus;
- margin treatment;
- home/away adjustment;
- FCS/out-of-pool treatment;
- current-season recency.

The following remain forbidden regardless of backtest results:

```text
conference-strength bonuses
previous-season ranking carryover
previous-season statistical carryover
preseason poll/power-rating seeds
```

## Guiding principle

> **A team starts every season with nothing and earns its ranking only through games played that season.**
