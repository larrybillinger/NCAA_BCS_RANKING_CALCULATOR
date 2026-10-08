# Changelog

## v0.10.3 — 2026-10-08

### Team identity repair
- The Penn/Pennsylvania repair no longer deletes and rebuilds `division_i_weighted_v5` snapshots. Rebuilding would have deleted every official prediction locked against those weeks; predictions recreated afterwards are dated after kickoff and can never lock, so the official accuracy ledger and the hybrid shadow ledger would have restarted from zero.
- The repair now merges the empty legacy `Penn` row (bundled data, no games) into `Pennsylvania` going forward: it leaves the active pool, game and stat references are repointed, and rankings calculated after the repair use the corrected pool. Published weeks and locked predictions are untouched, consistent with "old games are not recursively revalued".
- The repair refuses if a legacy row has results in any frozen snapshot, since a forward merge would drop them.
- Repair results report `repaired: false` when there is nothing left to change.

### Deployment
- If the repair refuses or fails, `synology-update.sh` prints a warning and continues to restart web and worker instead of exiting with the site stopped. A refused repair changes no data.

### Tests
- Repair tests verify frozen snapshots and locked official predictions survive, the next ranking excludes the duplicate, a second run changes nothing, and the refusal case leaves the legacy row active.

### Production safety
- No ranking or prediction formula changes: `division_i_weighted_v5` / `rank_gap_v3`.

## v0.10.2 — 2026-10-08

### Live score sync
- The worker's cadence now comes from the schedule in PostgreSQL, not the day of the week. It wakes at the next Division I kickoff so eligible pregame predictions lock immediately, then polls every `SYNC_LIVE_MINUTES` (default 60) while any Division I game is in progress.
- A game counts as live for up to 8 hours after kickoff, so late Saturday games keep live polling after midnight Central until CFBD marks them final, and a cancelled or never-finalized game cannot keep the worker in live mode indefinitely.
- With no upcoming or live game, the worker sleeps no longer than `SYNC_IDLE_MINUTES` (default 1440).
- New settings `SYNC_LIVE_MINUTES` and `SYNC_IDLE_MINUTES` replace `SYNC_SATURDAY_MINUTES` and `SYNC_OTHER_DAYS_MINUTES`. The old names are still read as fallbacks, and the Synology updater copies existing values to the new names.
- Browser auto-refresh on Game Book and team pages uses the same live window.

### Team identity and ranking repair
- Provider team resolution now prefers the durable CFBD ID and supports known historical aliases, preventing a legacy `Penn` row from coexisting with provider name `Pennsylvania` as two active FCS teams.
- Full-season schedule syncs reconcile the active Division I roster. Reconciliation fails closed if more than roughly 2% of the existing active pool is absent from the provider schedule, preventing a partial response from mass-deactivating teams.
- Team Index and Compare Teams now exclude inactive current-season teams.
- The production repair preserves retired-model history, deactivates the legacy Penn season row, repoints current game/stat references, removes contaminated active `division_i_weighted_v5` snapshots from the first affected week forward, and rebuilds them from corrected data.
- Predictions derived from removed corrupted snapshots are removed rather than being retroactively presented as official corrected predictions.

### Deployment safety
- The ordinary Synology update now creates a PostgreSQL dump and protected `.env` backup in addition to the application backup before the identity/ranking repair runs.
- Web and worker containers are stopped during the controlled repair so old code cannot write rankings concurrently.

### Sync status
- The sidebar marks CFBD data stale after 1.5 live intervals (90 minutes by default) while games are in progress, and after 36 hours otherwise. Previously a weeknight game could run for a day with the sidebar still showing "CFBD OK".
- `/health` reports `live_games`.

### Ranking page
- The conference dropdown lists only conferences in the selected subdivision.
- "All" is highlighted only when no subdivision or conference filter is active.
- Invalid `subdivision` values are ignored instead of emptying the conference list.

### Tools and navigation
- The rank calculator rejects ranks outside the current Division I pool instead of accepting anything up to 400.
- The week dock lists every scheduled regular-season week; the "…" link, which pointed back to the next week, is gone.

### Tests
- Worker schedule tests cover weeknight games, Saturday games after midnight, exact-kickoff wake-up, immediate kickoff locking, the 8-hour cap, and stale thresholds.
- Team-identity tests cover alias reuse, guarded roster reconciliation, inactive-team filtering, and rebuilding a contaminated active-model ranking without the duplicate.
- Site tests cover the conference dropdown, the "All" highlight, calculator validation, the week dock, and the sidebar going stale during a live game.

### Production safety
- No ranking or prediction formula changes: `division_i_weighted_v5` / `rank_gap_v3`.

## v0.10.1 — 2026-10-06

### Ranking page
- The default view shows national rank only; subdivision and conference rank columns appear only when FBS, FCS, or a conference is selected.
- FBS/FCS views show the subdivision rank plus a D-I column; conference views show the conference rank, the conference's FBS or FCS rank, and the D-I rank.
- The redundant Div. column is hidden in filtered views.

### Accuracy page
- Fixed the page timing out. Rank-gap calibration, ranking lookups, and hybrid scoring profiles are now computed once per request instead of once per game (about 17 s down to under 1 s with five completed weeks).
- Season and weekly retrocast metrics come from one pass over the games instead of two.
- Unknown `metric` values fall back to winner accuracy; added a rank-correlation tile.
- The duplicated chart markup is now one template macro.

### Official ledger
- Official accuracy (Accuracy page, footer ticker, team pages) now counts only predictions built from the active `MODEL_VERSION` ranking snapshots. Locked rows from retired models (v1–v4) remain stored but no longer mix into v5 results.
- Kickoff locking now considers only the active model's prediction rows, so a retired model's earlier lock no longer prevents the active model's pregame prediction from locking.

### Cleanup
- Game Book kickoff times use the configured local timezone instead of UTC.
- Unplayed games show UPCOMING or IN PROGRESS instead of the calibration sample size.
- Removed the rank calculator's neutral-site checkbox; the v3 predictor ignores site by design.
- Fixed a CSS rule that forced the four-column Game Book layout onto phones; the Accuracy metric strip now wraps cleanly.
- Renamed the ranking page's "Model stats" tab to "Accuracy" to match the sidebar.
- Method notes explain how FBS, FCS, and conference views are derived.
- Kickoff comparisons are timezone-safe for local SQLite development.

### Tests
- Added `tests/test_site.py`: every public page renders, ranking columns follow the selected view, retired-model predictions stay out of the official ledger and locking, and the request cache resets on commit.

### Production safety
- No ranking or prediction formula changes: `division_i_weighted_v5` / `rank_gap_v3`.

## v0.10.0 — 2026-10-05

### Ranking views
- Added sequential FBS and FCS ranks derived from the canonical combined Division I ordering.
- Added conference ranks derived from national ordering rather than conference record.
- Added conference filtering while retaining combined D-I and subdivision rank context.
- Scope ranks are calculated before search/filtering, so hidden teams do not create numbering gaps.

### Research prediction foundation
- Added research-only `hybrid_core_v1`, blending the existing rank-gap margin with shrunk current-season offense/defense scoring profiles.
- Added equal-shift nonnegative score normalization so a negative projected score never changes the modeled margin.
- Added winner-consistent integer score rendering so rounding cannot display a tie against a non-zero modeled margin.
- Added a separate research prediction table; shadow rows cannot become official Game Book predictions.
- Shadow locking runs before provider access and accepts only rows created before kickoff.
- Experimental failures are isolated from the official worker path.

### Research context variants
- Added shadow-only stadium A/B/C/D/F adjustments based on conference-relative sell-through rank inputs.
- Added time-zone, altitude, rain/snow, neutral-site, capped-travel, and single-factor variant support.
- These context rules are research infrastructure only; no context adjustment is promoted to the official predictor.

### Accuracy
- Added total-score MAE and displayed-tie-rate metrics.
- Added a separate hybrid shadow-model section on the Accuracy page.

### Production safety
- Production ranking remains `division_i_weighted_v5`.
- Official predictor remains `rank_gap_v3` and its protected monotonic winner rule is unchanged.

## v0.9.0 — 2026-10-04

### Manual score desk
- Added an admin-only manual score page at `/admin/games`.
- Admin can enter home/away scores, mark a game final or in progress, and add an operational note.
- Manual overrides take precedence over CFBD score/final fields until explicitly released.
- Admin can release an override back to CFBD control before the ranking week is frozen; release clears the local score/final state until CFBD repopulates it.
- Public Game Book and team pages label active manual final scores.

### Integrity and audit
- Every manual score save/release creates an append-only audit record.
- Prediction locking runs before a manual score is applied.
- Manual edits/releases are rejected after the active production ranking model has frozen the week.
- A completed manual result runs through the same normal week-complete ranking/prediction pipeline as provider results.
- Ranking and prediction formulas are unchanged: `division_i_weighted_v5` / `rank_gap_v3`.

### Security
- Added environment-backed HTTP Basic credentials for the score desk.
- Added CSRF protection for admin write forms.
- Fresh Synology installs generate a score-desk password automatically.
- Existing Synology installs receive a generated score-desk password on update if one is not already configured.
- Public website routes remain read-only.

### Database and deployment
- Added manual override metadata to `games` with automatic PostgreSQL migration.
- Added `manual_score_audits`.
- Added `python-multipart` for form handling.
- Updated Synology install/update scripts and project documentation.

## v0.8.2 — 2026-09-27

### Simpler polling cadence
- CFBD schedule/score syncing now runs once per day Sunday through Friday.
- Saturday syncing runs once per hour.
- The configured `TZ` determines the local day; production remains America/Chicago.
- A Friday sleep that would cross into Saturday is shortened so the worker wakes at local midnight and switches immediately to hourly polling.
- Full-season schedule refresh remains at least once every 24 hours.
- Live Game Book and team pages refresh from PostgreSQL every five minutes without consuming CFBD API calls.

### Deployment
- Existing Synology installs automatically receive `SYNC_SATURDAY_MINUTES=60` and `SYNC_OTHER_DAYS_MINUTES=1440` if those settings are absent.
- Fixed the updater's temporary environment-file suffix while adjusting the sync settings.

### Ranking model
- No ranking or prediction formula changes.
- Production remains `division_i_weighted_v5` and `rank_gap_v3`.

## v0.8.1 — 2026-09-27

### CFBD reliability
- Reduced normal game syncing from separate FBS/FCS requests to one unfiltered `/games` request.
- Reduced game-team-stat syncing to one unfiltered request per completed ranking week.
- Added quota-aware polling defaults: hourly near active games, every three hours when idle, and one full-schedule refresh per day.
- Added exponential HTTP 429 cooldowns from six hours up to one day, while honoring longer provider `Retry-After` values.
- Changed targeted score syncing to follow the schedule week nearest the current time rather than depending only on the latest frozen ranking snapshot.
- Daily full-schedule refreshes catch rescheduled or moved games.

### Prediction integrity
- Prediction locking now runs before any provider request, so CFBD outages or exhausted quota cannot stop eligible pregame predictions from becoming official.
- If optional team-stat ingestion hits a rate limit after a ranking snapshot is created, local prediction generation completes before the worker enters cooldown.

### Website
- Sidebar now reports CFBD OK/stale/error state, last successful sync, latest attempt, and a short provider error.
- `/health` now reports data-sync health and freshness details.
- Game Book and team pages auto-refresh every two minutes only while a scheduled game is in its normal live window.
- Sync timestamps are displayed in the configured local timezone.

### Quality
- Added regression tests for HTTP 429 handling, one-call game syncing, exponential backoff, and prediction locking before provider failure.
- Added GitHub Actions pytest workflow.
- Added `*.egg-info/` to `.gitignore`.

### Ranking model
- No ranking formula changes. Production remains `division_i_weighted_v5` under the Week 4 model freeze.

## v0.8.0 — 2026-09-18

### Ranking aggregation
- Ranking position now uses average frozen game score rather than cumulative points.
- A bye week adds neither score nor a game to the denominator.
- Playing more games no longer creates an automatic cumulative-points advantage.
- Raw cumulative game-score total is retained for audit only.
- Exact average-score ties use head-to-head, win percentage, average opponent strength, then deterministic fallback.
- Production ranking model is now `division_i_weighted_v5`.

### Database
- Added `raw_score` and `games_played` to ranking entries.
- Existing PostgreSQL installs add those fields automatically.

### Website
- Ranking tables, team pages, and compare views now label the production value as average score.

## v0.7.0 — 2026-09-18

### Ranking formula
- Removed the production +10 win bonus.
- Actual scoring margin remains a direct scoring component.
- Added a +7 site adjustment for an away win.
- Added a -7 site adjustment for a home loss.
- Home wins, away losses, and neutral-site results receive no site points.
- Production ranking model is now `division_i_weighted_v4`.

### Division I / FCS clarity
- FBS vs FBS is explicitly 100%.
- FBS vs FCS is explicitly 100%.
- FCS vs FCS remains 50%.
- FCS loss to FBS remains 50%.
- FCS win over FBS remains 100%.
- FCS multipliers apply to opponent-rank points and scoring margin; the ±7 site adjustment remains full value for every team.

### Database and audit
- Added `site_points` to per-game ranking audits.
- Existing PostgreSQL installs add the new audit column automatically.

### Snapshot integrity
- Archived v3 Week 1/2 CSVs are no longer imported under a newer model identifier.
- v4 completed-week rankings are rebuilt from the synced PostgreSQL game database instead of relabeling older snapshots.

### Documentation and tests
- Updated Method Notes, README, current-season rules, scoring examples, configs, and protected project rules.
- Added tests for no win bonus, road-win reward, home-loss penalty, away-loss neutrality, and FCS scaling of site points.

## v0.6.2 — 2026-09-18

### Fixed
- Fixed HTTP 500 errors on team pages, Game Book retrocasts, and Accuracy caused by the in-memory research projection using different field names from persisted prediction snapshots.
- Research retrocasts now expose the same `projected_home_points`, `projected_away_points`, and `projected_margin` interface used by saved predictions.
- Added regression coverage for the shared projection interface.

## v0.6.1 — 2026-09-18

### Deployment
- Fixed Synology updater temporary environment-file handling.
- Increased Docker/Compose client timeouts for slow Container Manager builds.
- Web and worker now use one shared `ncaa-rankings-app:latest` image instead of building the same application twice.
- Update flow now builds once, keeps PostgreSQL running, force-recreates web and worker, waits for health, and verifies the exact application/model/predictor versions before reporting success.
- Fresh installs use the same shared-image deployment path.

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
