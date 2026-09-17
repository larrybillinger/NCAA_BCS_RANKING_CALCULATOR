# Validation

## Release checks
- [x] New web utility tests pass locally (`2 passed`).
- [x] Python web modules compile locally.
- [x] App starts locally with a fresh SQLite validation database.
- [x] Bundled Week 1 and Week 2 rankings import with 266 entries each.
- [x] Home, predictions, stats, teams, team detail, method, calculator, compare, and health routes returned HTTP 200 in local TestClient validation.
- [x] Worker without a CFBD key stays operational and reports that automatic sync is paused.
- [x] `.env` is ignored by Git.
- [x] `VERSION`, `CHANGELOG.md`, and release notes match v0.4.0.
- [ ] Full pre-existing repository test suite was not run in the isolated build environment because the full repository could not be cloned there.
- [ ] Docker Compose must be smoke-tested on the target Synology after installation.
- [ ] Live CFBD sync must be smoke-tested after a valid API key is entered on the NAS.

## Production invariants
- A completed week creates at most one official ranking snapshot.
- A started game receives at most one official locked prediction per predictor version.
- Later projections never overwrite an official prediction.
- `/health` verifies the database connection and reports the latest ranking week.
