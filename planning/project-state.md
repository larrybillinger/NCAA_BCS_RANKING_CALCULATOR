# Project state

## Current release
v0.8.0

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

## Current next milestone
Run the existing v0.8.0 / division_i_weighted_v5 system unchanged through Week 4, verify each completed weekly snapshot, track prediction accuracy, and conduct the next ranking-method review only after Week 4 is complete.
