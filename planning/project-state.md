# Project state

## Current release
v0.11.0

## Production model
division_i_weighted_v5

## Production website
Weekbook-style FastAPI/Jinja site with PostgreSQL and a background CFBD sync worker.

## Production predictor
hybrid_core_v1 — 40% calibrated rank-gap margin + 60% shrunk current-season offense/defense matchup margin.

## Current bundled ranking data
- Week 1/2 CSVs are archived division_i_weighted_v3 snapshots.
- division_i_weighted_v4 rebuilds completed weeks from synced PostgreSQL game data; old CSV values are never relabeled as v4.

## Deployment target
Synology Container Manager under `/volume1/rankings`.

## Ranking model state
The production ranking remains `division_i_weighted_v5`. The v0.11.0 predictor promotion changes only score/winner prediction behavior; it does not change ranking points, ranking order, FBS/FCS modifiers, frozen weekly snapshots, or prior ranking history.

## Prediction state
Beginning with v0.11.0, `hybrid_core_v1` is the official Game Book predictor. It uses the calibrated rank-gap margin as 40% of the signal and a shrunk current-season offense/defense matchup margin as 60%. Team offense/defense profiles use only completed current-season Division I games and shrink toward the current-season scoring mean with three pseudo-games.

Because the hybrid is no longer constrained to follow ranking order, it can project the lower-ranked team to win when matchup evidence outweighs the rank gap. Existing `rank_gap_v3` official predictions remain stored exactly as locked but are retired from the active Accuracy ledger and Game Book. Historical hybrid retrocasts use only pregame-available weekly information and remain separate from official locked accuracy.

The pre-v0.11.0 `hybrid_core_v1` research rows remain in the research ledger for audit. The worker no longer writes a duplicate shadow copy of hybrid_core_v1 now that the same model is official. Context-adjusted variants remain research-only.

## Current sync and data-integrity state
Provider polling is game-aware: the worker wakes at the next Division I kickoff so eligible predictions lock immediately, polls every SYNC_LIVE_MINUTES (default 60) while games are in progress, and otherwise sleeps no longer than SYNC_IDLE_MINUTES (default 1440). Prediction locking remains local and runs before provider access.

Provider team identity prefers the durable CFBD ID. Since v0.10.3 the known legacy Penn/Pennsylvania duplicate is merged going forward during the Synology update: the empty legacy row leaves the active pool, while frozen weekly rankings and the predictions locked against them stay exactly as published. Full-season schedule reconciliation fails closed when provider coverage is materially incomplete.

The admin-only manual score desk at `/admin/games` can supply scores during a provider outage or correction. Manual overrides are audited, survive provider syncs until released, and cannot alter a week after the production ranking snapshot is frozen.

## Current next milestone
Deploy v0.11.0 on Synology and confirm `/health` reports `predictor_version=hybrid_core_v1`. Verify current/future Game Book rows are hybrid projections, Accuracy retrocasts reproduce the expected hybrid historical advantage on Weeks 3–5, and new official hybrid rows lock at kickoff. Continue collecting live hybrid results before considering any context-adjusted variant for production.
