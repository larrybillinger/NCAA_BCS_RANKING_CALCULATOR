# Changelog

## v0.6.0 — 2026-09-17

### Ranking
- Provider Week 0 is normalized into ranking Week 1.
- A Division I team with no completed current-season game remains on the neutral T-1 scoring baseline for opponent-value purposes, even if the calendar has advanced.
- After that team's first completed game, later opponents use the immediately preceding completed week's scoring rank.
- Production ranking model is now `division_i_weighted_v3`.

### Weekbook
- Team schedules now show projected points beside the team that owns each score instead of an ambiguous bare score pair.
- Game Book projections now show each team's projected score by name and identify the projected winner and win chance.
- Rank history now begins with the season-start T-1 baseline and labels snapshots as "After Week 1", "After Week 2", and so on.
- Ranking pages now explicitly say they are post-week snapshots.
- Future week numbers in the Weekbook dock open Game Book rather than silently falling back to the latest ranking.

### Research validation
- Added leakage-safe historical retrocasts for completed games that never had an actual locked pregame prediction.
- Retrocasts use only the ranking snapshot that existed before the game and are labeled RESEARCH/RETROCAST.
- Added separate overall and team retrocast accuracy metrics while preserving the official locked-prediction ledger unchanged.
- Official-pending ticker now links to the separate research statistics rather than presenting blank metric placeholders.

### Deployment
- Fixed the updater's temporary environment-file handling and added a health wait so SSH deployment does not report success before the rebuilt site is ready.

### Tests
- Added Week 0 normalization coverage.
- Added coverage proving an unplayed opponent remains on the neutral first-game baseline.

## v0.5.2 — 2026-09-17

### Changed
- Rebuilt the prediction layer so the projected winner always follows the ranking order.
- Projected scoring margin is now directly proportional to the rank gap.
- Current-season calibration now fits only a positive points-per-rank scale through the origin, blends toward a conservative early-season fallback, and is constrained to a reasonable range.
- Removed intercept and home-field effects from projected margin so they cannot reverse the ranking result.
- Production predictor is now `rank_gap_v3`.

### Tests
- Added tests confirming that the higher-ranked team is always projected to win, larger rank gaps produce larger margins, and equal ranks project an even game.

## v0.5.1 — 2026-09-17

### Fixed
- Synology's ordinary updater now synchronizes the active non-secret ranking and predictor model identifiers from GitHub instead of silently preserving a stale `MODEL_VERSION`.
- This prevents a new code deployment from continuing to display older ranking snapshots such as `division_i_weighted_v1`.

### Added
- The Weekbook sidebar now shows the running application version, ranking model version, and predictor version.
- The `/health` endpoint now reports those same versions for deployment verification.

## v0.5.0 — 2026-09-17

### Changed
- Before Week 1, all NCAA Division I teams are treated as one tied pool because no current-season evidence exists yet.
- The tied Week 1 pool uses the average occupied scoring rank, `(N + 1) / 2`; with 266 teams the neutral rank is 133.5.
- Exact score ties after a completed week share the average rank of the positions occupied by the tie for the next week's opponent scoring.
- Deterministic display ordering remains separate from mathematical scoring rank.
- Production model version is now `division_i_weighted_v2` and predictor version is `rank_gap_v2`.
- Recalculated the bundled 2026 Week 1 and Week 2 ranking snapshots under the new rules.

### Database
- `ranking_game_audits.opponent_rank_used` now stores floating-point ranks so ties such as 10.5 or 133.5 are preserved.
- Existing PostgreSQL installs migrate that column automatically at startup.

### 2026 sanity check
- Kansas State is #40 at 2-0 with 298.5 points after Week 2.
- Tulane is #105 at 1-1 with 72.0 points after Week 2.

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
