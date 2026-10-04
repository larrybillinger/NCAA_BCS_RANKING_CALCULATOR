# Sprint 002 acceptance criteria — Manual score desk

- [ ] Public pages remain read-only.
- [ ] `/admin/games` requires configured admin credentials.
- [ ] Admin password is never committed or rendered back to the browser.
- [ ] POST writes require a valid CSRF token.
- [ ] Admin can select a week and search by team.
- [ ] Admin can save home/away scores and final/in-progress state.
- [ ] Admin can add an optional note.
- [ ] Every manual write creates an audit row.
- [ ] Active manual overrides survive later CFBD syncs.
- [ ] Admin can release an override back to CFBD before the week is frozen.
- [ ] Official frozen ranking weeks reject score edits/releases.
- [ ] A completed manual result participates in the normal week-complete calculation.
- [ ] Ranking formula remains `division_i_weighted_v5`.
- [ ] Predictor remains `rank_gap_v3`.
- [ ] Existing tests plus new manual-score tests pass in GitHub Actions.
- [ ] VERSION, CHANGELOG, release notes, permissions, architecture, and validation docs are updated.
