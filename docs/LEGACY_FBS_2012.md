# Legacy FBS 2012 Workbook Notes

This document records the rules recovered from `NCAA FBS Rankings 2011.xlsx` and `NCAA FBS Rankings.xlsx`.

Both workbooks are built around the **2012 FBS season**, even though one filename contains `2011`. The `rankings` sheet begins with a `2011 Season` seed, while the raw game data runs through the 2012 regular season and bowls. The older workbook was created October 22, 2012.

## Important conclusion

The FBS model was not identical to the FCS model.

The FBS calculator used a much more granular opponent-rank score and, in the later version, penalized losses based on the quality of the opponent. It also used the current overall opponent rank throughout the workbook rather than freezing each game's value permanently to the rank that existed when the game was played.

That distinction should be preserved when rebuilding the legacy models.

## Workbook structure

Both FBS workbooks contain 124 FBS team worksheets plus working sheets including:

- `d1teams` — normalized schedule and game-result data.
- `RankTable` — rank-to-points conversion.
- `rankingtotal` — current overall team totals and ranks.
- `rankings` — historical ranking snapshots.
- `ConfRank` — conference-strength calculations.
- `Sosched` — strength-of-schedule reporting.
- `RoleRecord` — total-score reporting.
- `Template` — source worksheet copied for each team.

`Streak Table`, `ScheduleTable`, `Playground`, `Sosched`, and `RoleRecord` appear to be supporting/reporting areas. The core team-sheet scoring formulas depend on `d1teams`, `rankingtotal`, `RankTable`, and `ConfRank`.

## Raw game data

The `d1teams` sheet contains fields equivalent to:

- Institution ID
- Opponent ID
- Institution
- Game Date
- Location
- Opponent Name
- Score For
- Score Against

The 2012 data includes 124 FBS teams and approximately 1,572 scored team-game rows.

## External data clues

Both FBS workbooks preserve an Excel web connection named `Connection` pointing to:

`http://sportsillustrated.cnn.com/football/ncaa/polls/ap`

This appears to have been used for AP-poll information or initial ranking data.

No StatSheet URL, external `.xlsx` link, or surviving StatSheet web connection is embedded in these saved files. That does **not** rule out StatSheet as the original source of schedule/results data. The most likely explanation is that StatSheet data was imported or pasted into the workbook and the original import mechanism was not preserved in the saved XLSX package.

## FBS per-game scoring

The same basic three-part structure appears as in the FCS model:

`Game Sum = Rank Score + Win Score + Spread`

However, the FBS Rank Score is substantially different.

### Opponent Rank Score — older FBS version

`NCAA FBS Rankings 2011.xlsx` maps a 124-team ranking directly to points:

```text
rank 1   = 124 points
rank 2   = 123 points
rank 3   = 122 points
...
rank 123 =   2 points
rank 124 =   1 point
```

Conceptually, on a win:

```text
rank_score = 125 - opponent_rank
```

A loss receives zero opponent-rank points in this version.

This is more granular than the FCS bracket system. Beating #1 is worth much more than beating #25, and every ranking position matters.

### Opponent Rank Score — later FBS version

`NCAA FBS Rankings.xlsx` retains the same win calculation but adds a loss column to `RankTable`:

```text
loss to #1   =  -1
loss to #2   =  -2
loss to #3   =  -3
...
loss to #124 = -124
```

Conceptually:

```text
if win:
    rank_score = 125 - opponent_rank
else if loss:
    rank_score = -opponent_rank
```

This gives a useful symmetry:

- Beating a highly ranked team is rewarded heavily.
- Losing to a highly ranked team has only a small rank penalty.
- Beating a weak team earns little opponent-rank credit.
- Losing to a weak team is punished heavily.

The later workbook therefore contains a more informative strength-of-opponent rule without adding a complicated formula.

## Win Score

Both FBS workbooks use:

```text
win  = 10
loss = 0
```

## Spread Score

For a ranked FBS opponent:

```text
spread = points_for - points_against
```

If the opponent does not have a usable FBS rank, the workbook halves the margin:

```text
spread = (points_for - points_against) / 2
```

This strongly suggests that the half-spread rule was intended for games against opponents outside the active FBS ranking pool, such as FCS opponents.

There is no visible margin-of-victory cap.

## Example of the later FBS formula

Using Alabama's 2012 game against Michigan with Michigan stored at rank 26:

```text
Opponent Rank Score = 125 - 26 = 99
Win Score           = 10
Spread              = 41 - 14 = 27
Game Sum            = 99 + 10 + 27 = 136
```

For Alabama's loss to Texas A&M with Texas A&M stored at rank 8:

```text
Opponent Rank Score = -8
Win Score           = 0
Spread              = 24 - 29 = -5
Game Sum            = -8 + 0 - 5 = -13
```

For Alabama's win over FCS Western Carolina, which has no FBS rank:

```text
Opponent Rank Score = 0
Win Score           = 10
Spread              = (49 - 0) / 2 = 24.5
Game Sum            = 34.5
```

## Dynamic opponent rank behavior

This is one of the most important differences from the FCS workbook.

The FBS team worksheets look up the opponent's rank from:

`rankingtotal!A:C`

They do this for games throughout the entire season.

That means the current rank of an opponent can change the value of an earlier game. If a September opponent proves to be excellent by November, the September win becomes more valuable when the rankings are recalculated.

The `rankings` sheet stores week-by-week snapshots, but the FBS team scoring formulas do **not** use those historical ranking columns as their primary game-value source.

This produces a simple recursive model:

1. Assign/rank every FBS team.
2. Score every game using those opponent ranks.
3. Recalculate team totals.
4. Re-sort/re-rank teams.
5. Repeat as needed.

The modern implementation should automate this process rather than depend on manually sorted worksheet tables.

## Conference-strength bonus — older version

The older FBS workbook also adds a conference-strength bonus.

Each team sheet calculates the average rank of its opponents. `ConfRank` then averages those values by conference and orders the conferences by schedule strength.

The saved 2012 conference bonus table was:

| Conference | Bonus |
|---|---:|
| Big 12 | 143 |
| Pac-12 | 133 |
| SEC | 123 |
| Independent Notre Dame | 113 |
| Big Ten | 103 |
| ACC | 93 |
| Big East | 83 |
| Independent BYU | 73 |
| Independent Army | 63 |
| Independent Navy | 53 |
| Sun Belt | 43 |
| WAC | 33 |
| MAC | 23 |
| C-USA | 13 |
| Mountain West | 3 |

A team total was calculated as:

```text
final_total = cumulative_game_points + conference_bonus
```

For example, Alabama's older workbook total was:

```text
cumulative game points = 1194.5
SEC bonus              = 123
final total            = 1317.5
```

## Conference-strength bonus — later version

In `NCAA FBS Rankings.xlsx`, the conference bonus column is set to **0 for every conference**.

The formulas remain in place, but the effect is disabled:

```text
final_total = cumulative_game_points + 0
```

This appears to be an intentional simplification of the model and should be treated as a significant legacy rule change.

## Relationship between the two FBS files

The two files share the same basic workbook architecture and 2012 game data.

The later `NCAA FBS Rankings.xlsx` version changes at least two important ranking rules:

1. **Losses receive a rank-based penalty** instead of zero Rank Score.
2. **Conference bonus is disabled** instead of adding 3–143 points.

The later workbook was saved through Excel Online in November 2022. Many cached formula results in that copy are `#VALUE!`, apparently because formulas relying on worksheet filename/sheet-name behavior did not survive that save cleanly. The underlying formulas, lookup tables, raw game data, and manually stored rank order are still recoverable.

The broken cached values should not be interpreted as evidence that the ranking logic itself was invalid.

## Reconstruction check

Using the later workbook's saved 124-team rank map and 1,572 game-result rows, the recovered formula produces an ordering very close to the manually stored ranking order:

- 23 teams land in the exact same position.
- 113 of 124 teams land within five positions.
- Average absolute movement is about 2.37 ranking places.
- Alabama and Oregon reproduce as #1 and #2.

The remaining differences are consistent with the workbook's rank column being a manually maintained snapshot rather than an automatically sorted fixed point.

This is strong evidence that the recovered scoring formula is substantially correct.

## FBS vs. FCS legacy models

The historical files now show at least two distinct philosophies:

### FCS 2012

- Bracketed opponent-rank bonuses.
- No opponent-rank penalty on a loss.
- Weekly historical opponent rankings are used.
- No recovered conference-strength bonus.

### FBS 2012 — later version

- Every FBS rank has a distinct value.
- Wins: `125 - opponent_rank`.
- Losses: `-opponent_rank`.
- Win bonus: `+10`.
- Full margin against ranked FBS teams.
- Half margin against opponents outside the FBS ranking pool.
- Current opponent rank retroactively values all games.
- Conference bonus disabled.

The later FBS model is a strong candidate for the primary legacy formula to reproduce first in the new calculator.

## Implementation implication

The new engine should support ranking profiles rather than hard-code one formula.

At minimum:

```text
legacy_fcs_2012
legacy_fbs_2012_original
legacy_fbs_2012_later
```

This will let us reproduce the historical workbooks exactly, compare them against one another, and determine which legacy behavior should become the default modern ranking formula.