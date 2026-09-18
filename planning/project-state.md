# Project state

## Current release
v0.7.0

## Production model
division_i_weighted_v4

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
Deploy v0.7.0, rebuild completed 2026 weeks under division_i_weighted_v4 from the synced CFBD database, verify the new road-win/home-loss scoring audit, and regenerate rank_gap_v3 projections from the v4 rankings.
