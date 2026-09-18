# Current-Season Ranking Rules

## Production scope

The live calculator ranks **all NCAA Division I football teams together**.

The active ranking pool contains both:

- FBS teams;
- FCS teams.

FBS and FCS therefore share one opponent-rank scale. FCS teams use the limited scoring modifier described below.

## New-season reset

Every season starts from zero. Production does not import previous-season rankings, records, statistics, preseason polls, preseason power ratings, or conference-strength values.

Conference membership may be displayed, but contributes zero ranking points.

## Neutral first-game baseline

Every Division I team enters its first current-season game in the same neutral T-1 state because no current-season evidence separates it yet.

For a pool of `N` teams, the neutral scoring rank is:

```text
Neutral scoring rank = (N + 1) / 2
```

Provider Week 0 is treated as ranking Week 1. A team remains on the neutral scoring baseline until it completes its first game. After that first result, the immediately preceding completed week's scoring rank is used.

Exact season-score ties use the average occupied rank for next-week opponent scoring. For example, teams tied across positions 10, 11, and 12 each carry scoring rank 11.0.

Old games never get retroactively revalued.

## Core production game formula

For a Division I opponent ranked `R` in a pool of `N` teams:

```text
Win opponent points  = (N + 1) - R
Loss opponent points = -R

Scoring margin = points_for - points_against
```

There is **no separate win bonus**.

The site adjustment is:

```text
Away win   = +7
Home loss  = -7
Home win   = 0
Away loss  = 0
Neutral    = 0
```

Therefore:

```text
Home or neutral win = (N + 1 - R) + scoring margin
Away win            = (N + 1 - R) + scoring margin + 7

Away or neutral loss = (-R) + scoring margin
Home loss            = (-R) + scoring margin - 7
```

This deliberately makes actual scoring margin the direct win/loss margin component. Winning on the road earns extra credit; losing at home receives an extra penalty.

## FCS scoring modifier

FCS is Division I. The production percentage is based on the team being scored and the matchup:

```text
FBS vs FBS       = 100%
FBS vs FCS       = 100%
FCS vs FCS       = 50%
FCS loss to FBS  = 50%
FCS win over FBS = 100%
FCS tie with FBS = 50%
```

The FCS percentage applies to the whole normal production game score:

- opponent-rank points;
- scoring-margin points;
- seven-point site adjustment.

There are no production win-bonus points to scale.

## First-game example

Suppose the current Division I pool contains `267` teams. The neutral scoring rank is:

```text
(267 + 1) / 2 = 134
```

If an FBS team beats an FCS team 71-3 at home:

```text
Opponent rank points = 268 - 134 = 134
Scoring margin       = +68
Home-win adjustment  = 0
Normal score         = 202
FBS multiplier       = 100%
Final game score     = 202
```

For the FCS team losing 3-71 on the road:

```text
Opponent rank points = -134
Scoring margin       = -68
Away-loss adjustment = 0
Normal score         = -202
FCS-loss-to-FBS      = 50%
Final game score     = -101
```

## Road-win example

If a visiting FBS team beats an opponent whose prior-week scoring rank is #40 by 31-17 in a 267-team pool:

```text
Opponent rank points = 268 - 40 = 228
Scoring margin       = +14
Road-win adjustment  = +7
Game score           = 249
```

Separately, if a home team loses 17-31 to an opponent whose prior-week scoring rank is #40:

```text
Opponent rank points = -40
Scoring margin       = -14
Home-loss adjustment = -7
Game score           = -61
```

## Outside-Division-I games

Division II, Division III, NAIA, and other opponents outside the active Division I pool have no opponent-rank value.

The configured out-of-pool margin scale remains separate from the FBS/FCS modifier. The production site adjustment still reflects road win/home loss.

## Tie handling

If teams have identical season scores, deterministic display tiebreaking is used so the same inputs always produce the same display order. The engine can consider:

1. head-to-head wins among the tied teams;
2. number of wins;
3. accumulated current-season opponent strength;
4. deterministic team name/ID fallback.

Display ordering does not change the average scoring rank assigned to an exact score tie.

## Production engine and model

```text
Engine: WeeklySeasonRankingEngine
Model:  division_i_weighted_v4
```

The older recursive engine and legacy FBS model remain available for historical reproduction and are not modified by the production formula change.

## Guiding rule

**Use current-season opponent rank plus the actual scoring margin, reward road wins by seven, penalize home losses by seven, keep every unplayed team on the neutral first-game baseline, and never retroactively rewrite old games.**
