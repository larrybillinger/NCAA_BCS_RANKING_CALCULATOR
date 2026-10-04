# Permissions

The public D1 Rank website remains read-only. Public visitors cannot create, edit, or delete teams, games, rankings, predictions, or source data.

## Manual score administrator

A single operational score desk is available at:

```text
/admin/games
```

It is protected with HTTP Basic credentials stored only in the production `.env`:

```text
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<secret>
```

If `ADMIN_PASSWORD` is blank, the score desk is disabled. The admin password is never committed to GitHub or rendered back into HTML. Write forms also require a server-derived CSRF token.

The score administrator may:

- enter or correct home/away scores;
- mark a game final or in progress;
- add an operational note;
- place the game under manual score override;
- release an override back to CFBD control before that ranking week is frozen.

The score administrator may not:

- rewrite an official frozen ranking week from this page;
- change ranking or prediction formulas;
- delete official ranking snapshots;
- rewrite official locked predictions;
- expose API/database secrets.

## Provider precedence

While a game has an active manual score override, CFBD may still update ordinary schedule metadata, but it may not overwrite that game's:

- final/in-progress state;
- home score;
- away score.

After the admin releases the override, CFBD resumes authority over those fields on the next successful provider sync.

## Audit

Every manual score save and override release creates an append-only audit record containing the actor, timestamp, optional note, and before/after score state.

## Transport security

Use the admin score desk only through the production HTTPS endpoint. HTTP Basic credentials must not be sent over an unencrypted public connection.
