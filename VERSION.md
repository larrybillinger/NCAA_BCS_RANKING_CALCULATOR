# Version history

## 0.3.1 — FCS scoring modifier

- Keep FBS and FCS together in one NCAA Division I ranking pool.
- FBS teams always receive 100% of their normal Division I game score.
- FCS-vs-FCS game scores are multiplied by 0.5 for the FCS team.
- An FCS loss to an FBS team is multiplied by 0.5.
- An FCS win over an FBS team receives 100% of the normal score.
- The multiplier applies to opponent-rank points, win points, and margin points.
- Keep conferences at zero ranking strength.
- Keep all prior-season and preseason carryover forbidden.
- Preserve the historical legacy models unchanged for reproducibility.

## 0.3.0 — Unified Division I pool

- Rank FBS and FCS together in one NCAA Division I field.
- Initially scored FBS and FCS identically.
- Removed the historical FCS half-margin treatment from Division I games.
- Kept no conference-strength value.
- Kept no previous-season or preseason carryover.
- Week 1 starts with zero opponent-rank points.
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
