# Current-Season Scoring Examples

These examples use the unified NCAA Division I ranking pool introduced in v0.3.0.

## Week 1: FBS vs FCS

Kansas State 71, Nicholls 3

Both teams are Division I, so subdivision does not change the scoring.

```text
Opponent Rank Points = 0   # Week 1 has no prior current-season ranking
Win Bonus            = 10
Margin                = 71 - 3 = 68
Game Score            = 78
```

## Week 1: FBS vs FBS

Alabama 48, East Carolina 10

```text
Opponent Rank Points = 0
Win Bonus            = 10
Margin                = 38
Game Score            = 48
```

## Week 1: FCS vs FCS

An FCS-vs-FCS game is scored exactly the same way:

```text
Opponent Rank Points = 0
Win Bonus            = 10 for the winner
Margin                = full scoring margin
```

## Week 2 and later

If the prior completed weekly ranking contains `N` Division I teams and a team beats opponent rank `R`:

```text
Opponent Rank Points = (N + 1) - R
Win Bonus            = 10
Margin                = full scoring margin
```

A loss uses:

```text
Opponent Rank Points = -R
Win Bonus            = 0
Margin                = full scoring margin
```

FBS and FCS use the same equations.

## Non-Division-I opponent

If a ranked Division I team plays a Division II, Division III, NAIA, or other team outside the active ranking pool, that opponent has no ranking value. The current legacy-derived profile may apply the configured out-of-pool margin scale.
