# Project state

## Current release
v0.9.0

## Production model
division_i_weighted_v5

## Production website
Weekbook-style FastAPI/Jinja site with PostgreSQL and a background CFBD sync worker.

## Production predictor
rank_gap_v3 — projected winner always follows ranking order; projected margin is based directly on rank gap.

## Current bundled ranking data
- Week 1/2 CSVs are archived division_i_weighted_v3 snapshots.
- division_i_weighted_v4 rebuilds completed weeks from synced PostgreSQL game data; old CSV values are never relabeled as v4.

## Deployment target
Synology Container Manager under `/volume1/rankings`.

## Ranking-model freeze through Week 4
Do not change the production ranking formula before Week 4 is complete.

Keep `division_i_weighted_v5` as the production control model through the end of Week 4 so the early-season results can accumulate without moving the goalposts. During this period, collect ranking snapshots, game results, and prediction-accuracy data, but do not introduce new ranking weights, shrinkage, margin caps, recursive opponent adjustments, chain-win bonuses, or other scoring changes into production.

After Week 4 is complete, review the accumulated evidence before deciding whether any experimental ideas should move into a separate research model. Candidate experiments may include early-season stabilization, capped or damped scoring margin, prediction from rating-score gaps rather than ordinal rank gaps, and a small one-hop frozen opponent-strength term. None of these are approved production changes yet.

## Current sync state
v0.9.0 keeps division_i_weighted_v5 unchanged. The CFBD worker is quota-aware, prediction locking is independent of provider success, the site exposes sync health, and live-window pages auto-refresh from PostgreSQL. Provider polling is once per day Sunday-Friday and once per hour Saturday, using the configured local timezone.

The admin-only manual score desk at `/admin/games` can supply scores during a provider outage or correction. Manual overrides are audited, survive provider syncs until released, and cannot alter a week after the production ranking snapshot is frozen.

## Current next milestone
Deploy v0.9.0, configure/retrieve the generated admin score-desk credential, verify manual Week 4 score entry and CFBD recovery on Synology, then continue running division_i_weighted_v5 unchanged through the Week 4 review checkpoint.
