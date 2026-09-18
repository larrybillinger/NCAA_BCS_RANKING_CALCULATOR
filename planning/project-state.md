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

## Current next milestone
Deploy v0.8.0, rebuild completed 2026 weeks under division_i_weighted_v5, verify average-score rankings are neutral to bye weeks and unequal games played, and regenerate rank_gap_v3 projections from the v5 rankings.
