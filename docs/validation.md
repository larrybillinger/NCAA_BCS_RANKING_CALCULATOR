# Validation

## Current release checks
- [x] FBS/FCS and conference display ranks are derived from national D-I order before filtering/search.
- [x] Research predictions use a table separate from official prediction snapshots.
- [x] Shadow locking ignores rows created after kickoff.
- [x] Hybrid score normalization preserves margin when a projected score would be negative.
- [x] Hybrid display rounding cannot show a tie against a non-zero modeled margin.
- [x] Research context tests cover neutral sites, travel, altitude/weather stacking, capped travel, and conference-relative stadium grades.
- [x] GitHub Actions runs the repository pytest suite on every push and pull request.
- [x] Manual-score tests cover admin credentials and CSRF validation.
- [x] Manual-score tests cover score writes, audit rows, and normal weekly snapshot creation.
- [x] Manual-score tests verify that active manual overrides survive CFBD updates.
- [x] Manual-score tests verify that releasing an override returns the game to provider control.
- [x] Manual-score tests verify that a frozen ranking week rejects later score edits.
- [x] CFBD tests cover 429 handling, one-call game syncing, and rate-limit backoff.
- [x] Worker tests verify prediction locking occurs before provider access.
- [x] Worker tests verify game-aware polling: live cadence for weeknight games and Saturday games past local midnight, wake-up at the next kickoff, the 8-hour live cap, and the live/idle staleness thresholds.
- [x] Kickoff regression coverage proves an eligible pregame prediction locks on the kickoff cycle.
- [x] Team-identity tests prove a legacy Penn row is reused rather than duplicated when Pennsylvania arrives with a CFBD ID.
- [x] Roster reconciliation tests prove one stale row can be deactivated while materially incomplete provider coverage fails closed.
- [x] Production-repair tests rebuild contaminated active-model ranking snapshots without the legacy duplicate.
- [x] Inactive current-season teams are excluded from Team Index and Compare Teams.
- [x] `.env` is ignored by Git.
- [x] VERSION, CHANGELOG, and release notes are maintained per release.
- [ ] Docker Compose v0.10.2 must be smoke-tested on the target Synology after deployment.
- [ ] Confirm the production Penn/Pennsylvania repair output and rebuilt active ranking pool after deployment.
- [ ] Confirm kickoff locking plus live CFBD polling during the next weeknight or Saturday game.
- [ ] The production `/admin/games` page must be smoke-tested over HTTPS with the generated admin credentials.

## Production invariants
- Research/shadow predictions never set the official Game Book flag and never replace official prediction snapshots.
- Research context adjustments do not change division_i_weighted_v5 or rank_gap_v3.
- A completed week creates at most one official ranking snapshot per active model version.
- A started game receives at most one official locked prediction per active model/predictor combination.
- Later projections never overwrite an official prediction.
- Current Division I membership is reconciled only from a sufficiently complete full-season schedule; targeted weekly polls never deactivate teams.
- Provider team identity prefers durable CFBD IDs; known legacy aliases cannot create a second active current-season school.
- Public web routes remain read-only.
- Manual score writes require admin credentials and a valid CSRF token.
- An active manual override prevents CFBD from replacing that game's score/final fields.
- A manual score cannot be edited or released after the active production ranking model has frozen that week.
- Every manual score save/release creates an audit row.
- `/health` verifies the database connection and reports ranking, live-game, and data-sync state.
