# Version history

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
