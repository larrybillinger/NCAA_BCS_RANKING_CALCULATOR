# Legacy FCS 2012 Workbook Notes

This document records what has been recovered from the first historical workbook, `NCAA FCS Rankings.xlsx`.

These notes describe the workbook as found. They are not yet the final specification for the new calculator because additional historical workbooks still need to be compared.

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

This appears intended to treat games against opponents outside the active ranking list differently. The exact intended meaning should be confirmed against other workbook versions before the new engine treats it as fixed behavior.

There is no visible margin cap in this workbook.

## Weekly opponent rankings

Opponent Rank is not static. The team worksheets look up an opponent's ranking from the ranking table for the **previous completed ranking period**.

Examples from the formulas:

- Week 1 uses the `2011 Season` ranking columns.
- Week 2 uses the Week 1 ranking columns.
- Week 3 uses the Week 2 ranking columns.
- Later weeks continue the same pattern.

This produces a recursive schedule-strength effect without a complex strength-of-schedule formula.

## Cumulative score

The `N` column stores cumulative ranking points.

Examples from the template:

```text
Week 1 total = SUM(all game sums in Week 1)
Week 2 total = Week 1 total + SUM(all game sums in Week 2)
Week 3 total = Week 2 total + SUM(all game sums in Week 3)
...
```

The season score is therefore a running total, not a per-game average.

## Example from Montana

The Montana worksheet provides useful examples of the scoring model.

### Win over Liberty

The sheet records:

- Montana 34, Liberty 14
- Opponent rank: 83
- Rank Score: 1
- Win Score: 10
- Spread: +20
- Game Sum: 31

So:

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

A close loss therefore hurts less than a large loss, while a large win helps more than a narrow win.

## Ranking-table behavior

The `rankings` sheet is organized as repeating three-column groups:

```text
Team | Rank | Pts
```

Each week reads cumulative points from the appropriate cell on each team's worksheet. The next week's team sheets then use that ranking as opponent strength.

This design is conceptually useful but operationally fragile because it depends on:

- Repeated team worksheets.
- `INDIRECT` references to worksheet names.
- Manual or semi-manual weekly ordering.
- Fixed calendar rows.
- Fixed season structure.

The workbook also contains broken `#REF!` formulas in its final ranking area. The new calculator should never depend on copied worksheet references for ranking generation.

## Important design conclusions

The modern version should preserve these concepts independently:

1. **Raw game result** — score and opponent.
2. **Opponent rank used** — frozen to the ranking available before that game/week calculation.
3. **Opponent-rank bonus** — awarded according to an explicit lookup table.
4. **Win bonus** — separate from opponent quality.
5. **Margin value** — separate from the other two components.
6. **Game total** — sum of the three components.
7. **Cumulative total** — running season score.
8. **Weekly rank** — generated by sorting cumulative totals.

Separating these fields will make it possible to explain every ranking and test any future rule change without rewriting the whole system.

## Items to verify with additional workbooks

- Whether the half-spread rule always means an opponent outside the ranked subdivision.
- How FBS-vs-FCS games were intended to be scored in each version.
- Whether preseason/previous-season rankings were always used for Week 1.
- Whether prior-season influence changed or disappeared after a certain week.
- Whether later versions capped margin of victory.
- Whether home/away/neutral status ever affected points.
- How ties were intended to score.
- How postseason and playoff games were handled.
- Whether FBS and FCS used identical rank-point brackets.
- How teams entering or leaving a subdivision were handled.

Until those questions are answered, this document should be treated as a faithful reconstruction of the first workbook rather than the final rules contract.