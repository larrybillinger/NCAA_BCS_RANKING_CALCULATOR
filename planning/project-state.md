# Project state

## Current release
v0.5.2

## Production model
division_i_weighted_v2

## Production website
Weekbook-style FastAPI/Jinja site with PostgreSQL and a background CFBD sync worker.

## Production predictor
rank_gap_v3 — projected winner always follows ranking order; projected margin is based directly on rank gap.

## Current bundled ranking data
- 2026 Week 1 recalculated v0.5.0 ranking
- 2026 Week 2 recalculated v0.5.0 final ranking

## Deployment target
Synology Container Manager under `/volume1/rankings`.

## Current next milestone
Deploy v0.5.2, verify the valid CFBD API key is syncing, verify Week 3 schedule ingestion, and create the first pregame locked rank_gap_v3 predictions.
