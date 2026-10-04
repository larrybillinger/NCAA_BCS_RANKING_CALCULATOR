# Sprint 002 requirements — Manual score desk

## What I understand we are building

Larry needs a secure operational way to enter or correct game scores manually when CollegeFootballData is unavailable, delayed, or wrong.

## In scope
- admin-only web page for manual score entry;
- select a week and find its games;
- enter home score, away score, and final/in-progress state;
- optional operational note;
- mark a manually edited game so later CFBD syncs do not silently overwrite it;
- allow the admin to release an override back to provider control before the ranking week is frozen;
- preserve an audit record of manual score changes;
- run the normal completed-week ranking/prediction pipeline after a manual update;
- keep public pages read-only;
- keep all ranking and prediction formulas unchanged.

## Out of scope
- public write access;
- user-account system or multiple admin roles;
- retroactively rewriting a week whose official ranking snapshot already exists;
- changing ranking math, prediction math, or week-complete rules;
- deleting official ranking or prediction snapshots from the admin page.

## Files expected to change
- settings/environment documentation;
- PostgreSQL models and migration path;
- CFBD upsert logic;
- new manual-score service;
- FastAPI admin routes;
- new admin template and minimal CSS;
- Synology install/update scripts;
- tests;
- permissions/architecture/validation documentation;
- version/changelog/release notes.

## Risks or unclear items
- A manual score must not be overwritten by a later provider sync until the admin explicitly releases the override.
- A score change after an official weekly snapshot would conflict with immutable ranking history; the admin page must reject that edit.
- Admin credentials must remain in `.env` and the page should only be used over HTTPS.

## Test plan
- manual score update writes the game and audit record;
- provider sync preserves an active manual override;
- releasing an override permits provider data to resume;
- frozen weeks reject edits;
- completed manual scores can trigger the normal next ranking snapshot;
- unauthenticated/incorrect admin credentials are rejected;
- CSRF token is required for write actions;
- existing ranking tests remain unchanged.
