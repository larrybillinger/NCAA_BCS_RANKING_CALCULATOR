# Sprint 002 acceptance criteria — Manual score desk

- [x] Public pages remain read-only.
- [x] `/admin/games` requires configured admin credentials.
- [x] Admin password is never committed or rendered back to the browser.
- [x] POST writes require a valid CSRF token.
- [x] Admin can select a week and search by team.
- [x] Admin can save home/away scores and final/in-progress state.
- [x] Admin can add an optional note.
- [x] Every manual write creates an audit row.
- [x] Active manual overrides survive later CFBD syncs.
- [x] Admin can release an override back to CFBD before the week is frozen.
- [x] Official frozen ranking weeks reject score edits/releases.
- [x] A completed manual result participates in the normal week-complete calculation.
- [x] Ranking formula remains `division_i_weighted_v5`.
- [x] Predictor remains `rank_gap_v3`.
- [x] Existing tests plus new manual-score tests pass in GitHub Actions.
- [x] VERSION, CHANGELOG, release notes, permissions, architecture, and validation docs are updated.
