# Sprint 001 blueprint

## UI
FastAPI server-rendered Jinja templates with a fixed desktop reference sidebar, persistent bottom week spine, persistent accuracy ticker, and responsive mobile layout.

## Services
- `web`: public HTTP application
- `worker`: scheduled data sync, week freezing, prediction generation and locking
- `db`: PostgreSQL

## Data flow
CFBD -> PostgreSQL games/team stats -> ranking snapshot -> prediction snapshots -> public pages.

## Ranking
Do not alter `division_i_weighted_v1` scoring rules.

## Prediction
Fit current-season game margins against prior-week rank gaps. Store every projection by ranking snapshot. At kickoff mark the latest pregame projection official and immutable.
