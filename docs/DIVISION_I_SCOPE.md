# Division I Ranking Scope

## Production ranking pool

The live NCAA BCS Ranking Calculator ranks **all NCAA Division I football teams together in one pool**:

- Football Bowl Subdivision (FBS)
- Football Championship Subdivision (FCS)

FBS and FCS do not receive different scoring rules merely because of subdivision membership.

## Season reset

Every season begins from zero.

The production ranking must not use:

- previous-season rankings;
- previous-season statistics;
- preseason polls;
- preseason power ratings;
- conference strength or conference reputation bonuses.

There is no preseason ranking.

## Week 1

Week 1 creates the first ranking of the season.

Because no current-season ranking exists before Week 1, every Division I opponent receives zero opponent-rank points in Week 1.

For an FBS-vs-FBS, FBS-vs-FCS, FCS-vs-FBS, or FCS-vs-FCS game:

```text
Week 1 Game Score = Win Bonus + Full Scoring Margin
```

With the current legacy-derived scoring constants:

```text
win bonus = 10
margin = points_for - points_against
```

Subdivision does not change the margin value.

Example: Kansas State 71, Nicholls 3

```text
opponent-rank points = 0
win bonus            = 10
margin               = 68
game score           = 78
```

Nicholls is FCS, but because FCS is now in the same Division I ranking pool, the margin is not halved.

## Week 2 and later

Beginning in Week 2, each completed game uses the opponent's ranking from the immediately preceding completed week of the same season.

For a Division I opponent ranked `R` in a ranking pool of `N` teams:

```text
Win:
    opponent-rank points = (N + 1) - R
    win bonus = 10
    margin = points_for - points_against

Loss:
    opponent-rank points = -R
    win bonus = 0
    margin = points_for - points_against
```

The game total is:

```text
Game Score = Opponent Rank Points + Win Bonus + Margin
```

The same formula applies to every FBS and FCS team.

## Outside Division I

Teams below Division I remain outside the active ranking pool. Games against Division II, Division III, NAIA, or other out-of-pool opponents can retain a separate out-of-pool treatment because those teams are not being ranked by this project.

That distinction is based on whether a team is in the active Division I pool, not whether it is FBS or FCS.

## Conference rule

Conference affiliation is metadata only.

No conference receives a ranking bonus, penalty, multiplier, seed, or inherited strength value.

## Guiding principle

**If a team is NCAA Division I football, it is ranked in the same pool and scored by the same rules.**
