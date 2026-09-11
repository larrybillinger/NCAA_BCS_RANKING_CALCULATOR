# Legacy FCS 2012 Workbook Notes

> **Scope note:** This document is archival research. The production project ranks **FBS teams**, not FCS teams. The FCS workbook is retained because it helps reconstruct the history of the original spreadsheet system and may inform how FBS-vs-FCS games are scored. It is not a specification for a separate production FCS ranking.

This document records what was recovered from `NCAA FCS Rankings.xlsx`.

## Why this file still matters

Although FCS is outside the production ranking pool, the workbook remains useful for three reasons:

1. It confirms the original three-part scoring philosophy: opponent quality, win bonus, and margin.
2. It shows an earlier weekly-snapshot approach to opponent strength that can be tested as a challenger to the later FBS recursive approach.
3. It helps interpret how the old spreadsheets treated opponents outside an active ranking pool.

The later FBS workbooks remain the primary source for the production ranking formula.

## Workbook structure

The workbook contains:

- Raw FCS game data in `DIVISIONC`.
- Raw FBS game data in `DIVISIONB (1)`.
- A rank-to-points lookup table in `RankTable`.
- A transformed game lookup table in `d1teams`.
- A season ranking table in `rankings`.
- A reusable team sheet in `Template`.
- One copied worksheet for almost every FCS team.

The individual team worksheets contain a daily calendar with rows grouped into ranking weeks. Game data is looked up by team name plus game date.

## Per-game scoring

The key team-sheet columns are:

| Column | Meaning |
|---|---|
| C | Opponent rank used for that week |
| D | Home/Away/Neutral location |
| E | Opponent |
| F | Points scored |
| G | Points allowed |
| H | Win/Loss |
| I | Running record |
| J | Rank Score |
| K | Win Score |
| L | Spread |
| M | Game Sum |
| N | Cumulative weekly/season score |

The central relationship is:

`Game Sum = Rank Score + Win Score + Spread`

### Rank Score

The workbook's `RankTable` maps opponent rank to points as follows:

| Opponent Rank | Rank Score |
|---:|---:|
| 1–5 | 30 |
| 6–10 | 24 |
| 11–15 | 18 |
| 16–20 | 12 |
| 21–30 | 6 |
| 31–40 | 3 |
| 41–50 | 2 |
| 51–124 | 1 |

The team-sheet formula gives **zero Rank Score on a loss**, regardless of the opponent's rank.

Conceptually:

```text
if loss:
    rank_score = 0
else if opponent has a usable rank:
    rank_score = RankTable[opponent_rank]
else:
    rank_score = 0
```

### Win Score

The workbook awards:

```text
win  = 10
loss = 0
```

### Spread

The normal spread value is:

```text
points_for - points_against
```

The formula also contains this special case:

```text
if opponent-rank cell is text:
    spread = (points_for - points_against) / 2
else:
    spread = points_for - points_against
```

This appears intended to treat games against opponents outside the active ranking list differently.

There is no visible margin cap in this workbook.

## Weekly opponent rankings

Opponent Rank is not static. The team worksheets look up an opponent's ranking from the ranking table for the **previous completed ranking period**.

Examples from the formulas:

- Week 1 uses the `2011 Season` ranking columns.
- Week 2 uses the Week 1 ranking columns.
- Week 3 uses the Week 2 ranking columns.
- Later weeks continue the same pattern.

This produces a recursive schedule-strength effect without a complex strength-of-schedule formula.

For the modern FBS research program, this prior-week philosophy is a challenger to the later FBS model's end-of-regular-season recursive opponent rank. It is not the default.

## Cumulative score

The `N` column stores cumulative ranking points.

```text
Week 1 total = SUM(all game sums in Week 1)
Week 2 total = Week 1 total + SUM(all game sums in Week 2)
Week 3 total = Week 2 total + SUM(all game sums in Week 3)
...
```

The season score is therefore a running total, not a per-game average.

## Example from Montana

### Win over Liberty

The sheet records:

- Montana 34, Liberty 14
- Opponent rank: 83
- Rank Score: 1
- Win Score: 10
- Spread: +20
- Game Sum: 31

```text
1 + 10 + 20 = 31
```

### Loss to Appalachian State

The sheet records:

- Montana 27, Appalachian State 35
- Opponent rank: 82
- Rank Score: 0 because Montana lost
- Win Score: 0
- Spread: -8
- Game Sum: -8

## Ranking-table behavior

The `rankings` sheet is organized as repeating three-column groups:

```text
Team | Rank | Pts
```

Each week reads cumulative points from the appropriate cell on each team's worksheet. The next week's team sheets then use that ranking as opponent strength.

The spreadsheet implementation is operationally fragile because it depends on:

- repeated team worksheets;
- `INDIRECT` references to worksheet names;
- manual or semi-manual weekly ordering;
- fixed calendar rows; and
- fixed season structure.

The workbook also contains broken `#REF!` formulas in its final ranking area.

## What carries forward to the FBS project

The useful ideas to preserve are structural rather than an FCS production ranking:

1. Keep raw game results separate from calculated ranking values.
2. Store the opponent strength actually used for a calculation.
3. Keep opponent points, win points, and margin points separate for auditing.
4. Version the rule that determines opponent strength.
5. Test whether weekly historical rank or final recursive rank better predicts FBS postseason winners.
6. Keep treatment of opponents outside the FBS ranking pool explicit and configurable.

## Production-scope conclusion

This workbook should remain available as historical evidence and as a source of challenger ideas.

It should **not** cause the project to publish or optimize an FCS ranking. The production objective remains a transparent FBS ranking whose higher-ranked team wins FBS postseason games as often as possible.