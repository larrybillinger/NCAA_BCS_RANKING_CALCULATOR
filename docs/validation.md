# Validation

## Current release checks
- [x] GitHub Actions runs the repository pytest suite on every push and pull request.
- [x] Manual-score tests cover admin credentials and CSRF validation.
- [x] Manual-score tests cover score writes, audit rows, and normal weekly snapshot creation.
- [x] Manual-score tests verify that active manual overrides survive CFBD updates.
- [x] Manual-score tests verify that releasing an override returns the game to provider control.
- [x] Manual-score tests verify that a frozen ranking week rejects later score edits.
- [x] CFBD tests cover 429 handling, one-call game syncing, and rate-limit backoff.
- [x] Worker tests verify prediction locking occurs before provider access.
- [x] Worker tests verify Saturday-hourly and Sunday-Friday daily polling.
- [x] `.env` is ignored by Git.
- [x] VERSION, CHANGELOG, and release notes are maintained per release.
- [ ] Docker Compose v0.9.0 must be smoke-tested on the target Synology after deployment.
- [ ] The production `/admin/games` page must be smoke-tested over HTTPS with the generated admin credentials.
- [ ] A live CFBD sync should be confirmed after the Tier 1 quota upgrade is active.

## Production invariants
- A completed week creates at most one official ranking snapshot.
- A started game receives at most one official locked prediction per predictor version.
- Later projections never overwrite an official prediction.
- Public web routes remain read-only.
- Manual score writes require admin credentials and a valid CSRF token.
- An active manual override prevents CFBD from replacing that game's score/final fields.
- A manual score cannot be edited or released after the active production ranking model has frozen that week.
- Every manual score save/release creates an audit row.
- `/health` verifies the database connection and reports ranking and data-sync state.
