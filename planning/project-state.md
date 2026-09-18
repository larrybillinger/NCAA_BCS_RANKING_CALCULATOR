# Project state

## Current release
v0.6.2

## Production model
division_i_weighted_v3

## Production website
Weekbook-style FastAPI/Jinja site with PostgreSQL and a background CFBD sync worker.

## Production predictor
rank_gap_v3 — projected winner always follows ranking order; projected margin is based directly on rank gap.

## Current bundled ranking data
- 2026 Week 1 current v0.6.0 / division_i_weighted_v3 ranking
- 2026 Week 2 current v0.6.0 / division_i_weighted_v3 final ranking

## Deployment target
Synology Container Manager under `/volume1/rankings`.

## Current next milestone
Deploy v0.6.1 with the reliable shared-image updater, verify the Weekbook score-label and retrocast views on Synology, verify Week 3 schedule ingestion, and allow rank_gap_v3 predictions to lock before kickoff.
