# Version history

## 0.6.1 — Reliable Synology deployment

- Build the D1 Rank application image once for both web and worker.
- Extend Docker/Compose timeouts for slower Synology systems.
- Force-recreate application containers after a successful build.
- Verify the running app, model, and predictor versions from `/health`.
- Fix temporary environment-file handling in the updater.

## 0.6.0 — First-game baseline and Weekbook completion

- Normalize provider Week 0 into ranking Week 1.
- Keep unplayed teams on the neutral T-1 scoring baseline until their first completed game.
- Move production ranking model to `division_i_weighted_v3`.
- Make score ownership explicit throughout team schedules and Game Book.
- Label ranking history as season start T-1 followed by post-week snapshots.
- Add clearly separated pregame-information retrocasts and retrocast accuracy.
- Keep official locked predictions and official accuracy immutable and separate.

## 0.5.2 — Monotonic rank-gap predictor

- Make the higher-ranked team the projected winner in every matchup.
- Base projected scoring margin directly on rank gap.
- Calibrate only the positive points-per-rank scale from current-season completed games.
- Remove free intercept and home-field terms from projected margin.
- Move production predictor to `rank_gap_v3`.
- Add tests for winner direction, gap magnitude, and equal-rank games.

## 0.5.1 — Deployment version visibility and model sync

- Show application, ranking-model, and predictor versions in the website sidebar.
- Return those versions from `/health`.
- Make the normal Synology updater synchronize committed model identifiers from GitHub while preserving secrets.
- Prevent the NAS from continuing to select stale v1 ranking snapshots after a GitHub update.

## 0.5.0 — Neutral tied Week 1 baseline

- Treat all Division I teams as tied before Week 1.
- Use the average occupied rank of the full tie, `(N + 1) / 2`, for Week 1 opponent scoring.
- Use average occupied rank for exact score ties in all later weekly opponent scoring.
- Preserve deterministic display ordering while separating display rank from scoring rank.
- Recalculate 2026 Week 1 and Week 2 under the new rules.
- Upgrade the PostgreSQL audit field to retain fractional opponent ranks.
- Move production to `division_i_weighted_v2` and `rank_gap_v2`.

## 0.4.0 — Weekbook web application

- Added a PostgreSQL-backed FastAPI website using the selected Weekbook design.
- Added full ranking, prediction, statistics, team, method, compare, and rank-calculator pages.
- Added immutable weekly ranking snapshots and locked pregame prediction snapshots.
- Added current-season rank-gap score prediction calibration.
- Added automatic CollegeFootballData schedule, score, classification, and team-stat ingestion.
- Added a background worker for polling, week locking, ranking generation, and prediction generation.
- Added Synology Container Manager deployment using `/volume1/rankings`.
- Added bundled official Week 1 and final Week 2 2026 ranking snapshots.

## 0.3.1 — Unified Division I pool with FCS scoring modifier

- FBS teams receive 100% of normal Division I game points.
- FCS-vs-FCS game scores are multiplied by 0.5.
- FCS losses to FBS teams are multiplied by 0.5.
- FCS wins over FBS teams receive full credit.

## 0.3.0 — Unified Division I pool

- Ranked FBS and FCS together in one NCAA Division I field.
- Removed conference strength and prior-season/preseason carryover.
- Week 1 starts with zero opponent-rank points.

## 0.2.1 — Season-only weekly rankings

- Added weekly season ranking engine.
- Removed previous-season/preseason inputs from production.

## 0.2.0 — Executable legacy engine

- Added recovered FBS formula and historical recursive engine.

## 0.1.1 — Legacy reconstruction

- Documented historical FBS and FCS workbook behavior.
