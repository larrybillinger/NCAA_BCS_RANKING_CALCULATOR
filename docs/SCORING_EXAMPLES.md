# Current-Season Scoring Examples

These examples use the unified NCAA Division I ranking pool with the v0.5.0 tied-pool baseline and FCS scoring modifier.

## Week 1: FBS beats FCS

Kansas State 71, Nicholls 3

Kansas State receives the full score:

```text
Neutral Scoring Rank = 133.5
Opponent Rank Points  = 267 - 133.5 = 133.5
Win Bonus             = 10
Margin                = 68
Kansas State Score    = 211.5
```

Nicholls is FCS and lost to an FBS team, so its negative score is halved:

```text
Neutral Scoring Rank = 133.5
Opponent Rank Points  = -133.5
Win Bonus             = 0
Margin                = -68
Normal Score          = -201.5
FCS Multiplier        = 0.5
Nicholls Score        = -100.75
```

## Week 1: FBS vs FBS

Alabama 48, East Carolina 10

```text
Neutral Scoring Rank = 133.5
Opponent Rank Points  = 133.5
Win Bonus             = 10
Margin                = 38
Game Score            = 181.5
```

FBS teams always use 100% of the normal Division I game score.

## Week 1: FCS vs FCS

Suppose FCS Team A beats FCS Team B 30-10:

```text
Neutral Scoring Rank = 133.5
Opponent Rank Points  = 133.5
Win Bonus             = 10
Margin                = 20
Normal Score          = 163.5
FCS Multiplier        = 0.5
Final Score           = 81.75
```

The losing FCS team also receives half of its normal negative score:

```text
Opponent Rank Points = -133.5
Margin               = -20
Normal Score         = -153.5
FCS Multiplier       = 0.5
Final Score          = -76.75
```

## Week 2 and later: FCS beats FBS

If the combined Division I ranking has `N = 266` teams and an FCS team beats the prior-week #40 FBS team 31-17:

```text
Opponent Rank Points = (266 + 1) - 40 = 227
Win Bonus            = 10
Margin               = 14
Normal Score         = 251
FCS Multiplier       = 1.0
Final Score          = 251
```

An FCS upset over an FBS team receives full credit.

## Week 2 and later: FCS loses to FBS

If that FCS team instead loses 17-31 to the prior-week #40 FBS team:

```text
Opponent Rank Points = -40
Win Bonus            = 0
Margin               = -14
Normal Score         = -54
FCS Multiplier       = 0.5
Final Score          = -27
```

## Non-Division-I opponent

If a ranked Division I team plays a Division II, Division III, NAIA, or other team outside the active ranking pool, that opponent has no ranking value. The configured out-of-pool treatment remains separate from the FCS scoring modifier.


## Exact score ties

If three teams finish a completed week with exactly the same season score and occupy display positions 10, 11, and 12, they all carry the same opponent-scoring rank into the next week:

```text
Average Occupied Rank = (10 + 11 + 12) / 3 = 11
```

The deterministic display tiebreakers can still order the three teams for presentation, but the ranking formula does not pretend one tied score is mathematically stronger than another.
