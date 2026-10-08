# Architecture

## Components

### Web
FastAPI + Jinja renders the public Weekbook UI. It performs read-heavy database queries and exposes `/health` for Container Manager health checks.

The public routes remain read-only. `/admin/games` is a separate operational score desk protected by environment-backed HTTP Basic credentials and CSRF protection. Manual writes are handled by the manual-score service and recorded in an audit table.

### Worker
A separate Python process:

1. imports bundled ranking snapshots on a fresh database;
2. synchronizes the season schedule/results from CFBD;
3. while idle, wakes at the next Division I kickoff (or the idle deadline, whichever comes first);
4. locks eligible official and research predictions locally before provider access;
5. polls every `SYNC_LIVE_MINUTES` while any Division I game is in progress, on any day;
6. syncs team game stats after a week is complete;
7. creates the next immutable ranking snapshot;
8. generates a new set of future projections from that snapshot.

A full-season schedule refresh also reconciles active FBS/FCS membership. Team identity prefers the durable CFBD team ID, with explicit aliases for historical local names that predate that ID. Reconciliation fails closed when provider coverage is materially incomplete.

### PostgreSQL
PostgreSQL is the production source of truth for normalized external facts, manual operational overrides, audit history, and all derived snapshots.

An active manual score override has precedence over CFBD for `completed`, `home_points`, and `away_points`. CFBD continues to update non-score schedule metadata.

## Immutable state

`ranking_snapshots` are official completed-week states. `prediction_snapshots` preserve the ranking snapshot and predictor version used for each projection. The latest pregame projection is marked official at kickoff and is not overwritten.

Official ranking snapshots are immutable, and so are the predictions locked against them. The Penn/Pennsylvania repair (v0.10.3) follows that rule: after a PostgreSQL backup it merges the empty legacy row into the provider-backed school going forward, so only rankings calculated after the repair use the corrected pool. It refuses to run if the legacy row has results in any frozen snapshot, because a forward merge would drop them.

## Prediction model

The ranking model and score predictor are separate systems. Rankings remain governed by the documented BCS-derived formula. Official score predictions fit current-season actual margins to prior-week rank gaps and current-season average total scoring.

### Research shadow ledger

Research predictors use `research_prediction_snapshots`, a separate table from the official `prediction_snapshots` Game Book ledger. The initial `hybrid_core_v1` model blends the official rank-gap margin component with shrunk current-season offense/defense scoring profiles. The worker locks the latest eligible research row at kickoff only when that row was created before kickoff. Research generation/locking failures are caught separately so they cannot block official prediction work.

Research score rendering keeps continuous scores for evaluation. If a score would be negative, both scores are translated upward by the same amount so the modeled margin is preserved. Integer display scores use winner-consistent rounding when the continuous margin is non-zero.

Stadium-demand, time-zone, altitude, and weather adjustments are implemented as research-only context variants. They are not production ranking inputs and are not allowed to alter the official `rank_gap_v3` ledger. Dynamic context must be captured before kickoff with provenance before it can be used by a locked shadow prediction.

## No client-side API key

All CFBD calls occur in the worker container. The browser never sees the provider API key.
