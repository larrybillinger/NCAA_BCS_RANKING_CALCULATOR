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
4. locks eligible official predictions locally before provider access;
5. polls every `SYNC_LIVE_MINUTES` while any Division I game is in progress, on any day;
6. syncs team game stats after a week is complete;
7. creates the next immutable ranking snapshot;
8. generates a new set of future `hybrid_core_v1` projections from that snapshot.

A full-season schedule refresh also reconciles active FBS/FCS membership. Team identity prefers the durable CFBD team ID, with explicit aliases for historical local names that predate that ID. Reconciliation fails closed when provider coverage is materially incomplete.

### PostgreSQL
PostgreSQL is the production source of truth for normalized external facts, manual operational overrides, audit history, and all derived snapshots.

An active manual score override has precedence over CFBD for `completed`, `home_points`, and `away_points`. CFBD continues to update non-score schedule metadata.

## Immutable state

`ranking_snapshots` are official completed-week states. `prediction_snapshots` preserve the ranking snapshot and predictor version used for each projection. The latest eligible pregame projection for the active predictor is marked official at kickoff and is not overwritten.

Official ranking snapshots are immutable, and so are the predictions locked against them. The Penn/Pennsylvania repair (v0.10.3) follows that rule: after a PostgreSQL backup it merges the empty legacy row into the provider-backed school going forward, so only rankings calculated after the repair use the corrected pool. It refuses to run if the legacy row has results in any frozen snapshot, because a forward merge would drop them.

The v0.11.0 predictor promotion follows the same immutability rule. Existing official `rank_gap_v3` prediction rows remain in PostgreSQL exactly as locked. They are retired from active display/metrics by the configured `PREDICTOR_VERSION`; they are not rewritten into hybrid predictions.

## Prediction model

The ranking model and score predictor are separate systems. Rankings remain governed by `division_i_weighted_v5` and are unchanged by predictor promotion.

The active production predictor is `hybrid_core_v1`. For each matchup it computes:

- a rank-gap margin using the existing current-season positive points-per-rank calibration;
- shrunk offense and defense scoring profiles from completed current-season Division I games;
- an offense/defense matchup margin and matchup scoring total;
- a blended margin using 40% rank-gap and 60% offense/defense weight;
- projected home/away scores and win probability from the blended result.

Offense/defense profiles shrink toward the current-season mean team score using three pseudo-games. This stabilizes small early-season samples. Because the offense/defense component is allowed to outweigh the rank-gap component, the official hybrid predictor may select a lower-ranked team to win. This affects predictions only; it never changes ranking order or ranking points.

### Historical and research prediction data

`prediction_snapshots` contains official/current production predictions keyed by predictor version. Active views filter to the configured predictor, currently `hybrid_core_v1`.

`research_prediction_snapshots` retains the pre-promotion hybrid shadow rows and remains available for future research variants. The worker no longer creates a duplicate base `hybrid_core_v1` shadow row after promotion because the same model is now official.

Historical hybrid retrocasts are computed from the prior weekly ranking snapshot plus only completed-game scoring information available through that prior week. They are shown separately from official locked accuracy and never write or replace official rows.

Stadium-demand, time-zone, altitude, weather, home-field, and other context adjustments remain research-only. Dynamic context must be captured before kickoff with provenance before it can be evaluated, and no context-adjusted variant becomes official without a separate explicit decision.

## No client-side API key

All CFBD calls occur in the worker container. The browser never sees the provider API key.
