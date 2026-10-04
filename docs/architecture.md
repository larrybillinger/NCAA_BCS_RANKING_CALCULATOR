# Architecture

## Components

### Web
FastAPI + Jinja renders the public Weekbook UI. It performs read-heavy database queries and exposes `/health` for Container Manager health checks.

The public routes remain read-only. `/admin/games` is a separate operational score desk protected by environment-backed HTTP Basic credentials and CSRF protection. Manual writes are handled by the manual-score service and recorded in an audit table.

### Worker
A separate Python process:

1. imports bundled ranking snapshots on a fresh database;
2. synchronizes the season schedule/results from CFBD;
3. polls once per day Sunday-Friday and once per hour Saturday;
4. locks predictions independently of provider availability;
5. syncs team game stats after a week is complete;
6. creates the next immutable ranking snapshot;
7. generates a new set of future projections from that snapshot.

### PostgreSQL
PostgreSQL is the production source of truth for normalized external facts, manual operational overrides, audit history, and all derived snapshots.

An active manual score override has precedence over CFBD for `completed`, `home_points`, and `away_points`. CFBD continues to update non-score schedule metadata.

## Immutable state

`ranking_snapshots` are official completed-week states. `prediction_snapshots` preserve the ranking snapshot and predictor version used for each projection. The latest pregame projection is marked official at kickoff and is not overwritten.

## Prediction model

The ranking model and score predictor are separate systems. Rankings remain governed by the documented BCS-derived formula. Score predictions fit current-season actual margins to prior-week rank gaps and current-season average total scoring.

## No client-side API key

All CFBD calls occur in the worker container. The browser never sees the provider API key.
