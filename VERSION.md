# Version history

## 0.3.0 — Unified Division I pool

- Rank FBS and FCS together in one NCAA Division I field.
- Score FBS and FCS identically.
- Remove the historical FCS half-margin treatment from Division I games.
- Keep no conference-strength value.
- Keep no previous-season or preseason carryover.
- Week 1 starts with zero opponent-rank points and full margin for all Division I games.
- Week 2 and later use the immediately preceding completed week's current-season Division I ranking.
- Keep lower-division opponents outside the active pool.

## 0.2.1 — Season-only weekly rankings

- Added `WeeklySeasonRankingEngine`.
- Removed previous-season/preseason inputs from production.
- Made Week 1 establish the first current-season ranking.

## 0.2.0 — Executable legacy engine

- Added executable recovered FBS formula.
- Added historical recursive engine and postseason backtesting scaffold.

## 0.1.1 — Legacy reconstruction

- Documented historical FBS and FCS workbook behavior.
