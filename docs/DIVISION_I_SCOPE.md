# Division I Ranking Scope

## Production ranking pool

The live NCAA BCS Ranking Calculator ranks **all NCAA Division I football teams together in one pool**:

- Football Bowl Subdivision (FBS)
- Football Championship Subdivision (FCS)

FBS and FCS share the same ranking table and opponent-rank scale. The only subdivision-specific production rule is the limited FCS game-score multiplier documented below.

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

The normal Week 1 calculation is:

```text
Week 1 Game Score = Win Bonus + Scoring Margin
win bonus = 10
margin = points_for - points_against
```

The FCS modifier is then applied to the FCS team's own game score when required.

Example: Kansas State 71, Nicholls 3

Kansas State is FBS and receives the full normal score:

```text
opponent-rank points = 0
win bonus            = 10
margin               = 68
game score           = 78
```

Nicholls is FCS and lost to an FBS team, so its negative score is halved:

```text
normal score = -68
FCS scale    = 0.5
final score  = -34
```

## FCS scoring modifier

The production model uses these subdivision rules:

```text
FBS team vs any Division I opponent = 100% of normal game points
FCS team vs FCS opponent            = 50% of normal game points
FCS team loses to FBS opponent      = 50% of normal negative game points
FCS team beats FBS opponent         = 100% of normal game points
```

The 50% or 100% multiplier applies to opponent-rank points, win points, and margin points together.

## Week 2 and later

Beginning in Week 2, each completed game uses the opponent's ranking from the immediately preceding completed week of the same season.

For a Division I opponent ranked `R` in a ranking pool of `N` teams, the normal unscaled calculation is:

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
Normal Game Score = Opponent Rank Points + Win Bonus + Margin
```

The FCS multiplier is then applied when the ranked team is FCS and the matchup falls into one of the FCS cases above.

## Outside Division I

Teams below Division I remain outside the active ranking pool. Games against Division II, Division III, NAIA, or other out-of-pool opponents can retain a separate out-of-pool treatment because those teams are not being ranked by this project.

That treatment is separate from the FCS scoring modifier.

## Conference rule

Conference affiliation is metadata only.

No conference receives a ranking bonus, penalty, multiplier, seed, or inherited strength value.

## Guiding principle

**FBS and FCS share one Division I ranking pool. FCS teams receive half game points against FCS opponents and on losses to FBS opponents, but full game points when they beat FBS opponents.**
