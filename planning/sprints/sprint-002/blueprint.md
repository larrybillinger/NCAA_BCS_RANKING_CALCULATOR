# Sprint 002 blueprint — Manual score desk

## Security
Use HTTP Basic authentication backed by `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `.env`. If no admin password is configured, the admin score page is disabled. POST actions also require an HMAC CSRF token derived from the admin secret.

The public site remains read-only.

## Data model
Add manual-override metadata to each game:
- `manual_score_override`;
- `manual_score_updated_at`;
- `manual_score_note`;
- `manual_score_actor`.

Add an append-only `manual_score_audits` table that records before/after score state and whether an override was set or released.

## Provider precedence
CFBD may continue updating schedule metadata. While `manual_score_override` is true it may not overwrite:
- `completed`;
- `home_points`;
- `away_points`.

Releasing the override restores provider authority over those fields on the next sync.

## Admin workflow
`/admin/games`
- protected by admin credentials;
- defaults to the current/next unfinished week;
- supports week navigation and team search;
- shows current scores and manual/provider status;
- each game has plain-text controls for home score, away score, final state, note, and Save;
- manually overridden games also have Release to CFBD.

## Snapshot integrity
Manual score edits are allowed only while the active production model has no official snapshot for that game week. Once the week is frozen, the score desk becomes read-only for those games.

After a successful manual update:
1. lock any eligible pregame predictions;
2. save the game and audit row;
3. run normal completed-week detection;
4. create any newly completed ranking snapshot(s);
5. generate projections from the latest ranking.

No ranking formula is changed.
