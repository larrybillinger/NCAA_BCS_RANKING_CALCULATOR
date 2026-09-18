# Changelog

## v0.4.1 — 2026-09-17

### Fixed
- Updated all Jinja/Starlette TemplateResponse calls to the current request-first API so the homepage and other HTML routes render instead of returning HTTP 500.
- Made bundled ranking bootstrap safe when the web and worker containers initialize concurrently.
- Improved Synology install/update scripts for both `docker compose` and `docker-compose`.

### Diagnostics
- The CFBD worker can still report HTTP 401 when `CFBD_API_KEY` is missing, expired, or not a CollegeFootballData API key.

## v0.4.0 — 2026-09-16

### Added
- Weekbook-style public ranking website.
- PostgreSQL persistence for teams, schedules, rankings, scoring audits, predictions, game stats, and source sync history.
- Automatic CollegeFootballData REST API ingestion.
- Background worker that polls the active week, freezes completed ranking weeks, generates new predictions, and locks predictions at kickoff.
- Full team schedule pages with current and historical-as-of prediction views.
- Overall and team-specific prediction accuracy metrics.
- Rank matchup calculator and team comparison tool.
- Synology Container Manager Docker deployment and SSH install/update/backup scripts.
- Official final 2026 Week 2 ranking CSV.

### Changed
- Project version moved from 0.3.1 to 0.4.0 because the repository now includes the production website and data service in addition to the ranking engine.

### Security
- CFBD API key and PostgreSQL credentials are stored only in `/volume1/rankings/.env` and are never committed.

### Known limitations
- Official prediction accuracy starts when the deployed application begins creating predictions before kickoff. Historical games are not falsely backfilled as official predictions.
- CFBD data availability and timing remain subject to the provider's service and subscription quota.
