# AGENTS.md

This repository is the source of truth for the NCAA BCS Ranking Calculator and D1 Rank website.

## Required read order
1. `AGENTS.md`
2. `README.md`
3. `VERSION`
4. `CHANGELOG.md`
5. `planning/project-state.md`
6. `planning/decisions.md`
7. `planning/risks.md`
8. `planning/questions.md`
9. `docs/architecture.md`
10. `docs/permissions.md`
11. `docs/validation.md`
12. Active sprint under `planning/sprints/`

## Protected ranking rules
Do not change these without an explicit approved decision:
- one Division I ranking pool containing FBS and FCS;
- season starts from zero;
- no preseason or prior-season seed;
- no conference-strength scoring;
- Week 2+ uses the previous completed week's ranking;
- old games do not get recursively revalued;
- FCS-vs-FCS score multiplier is 0.5;
- FCS loss to FBS multiplier is 0.5;
- FCS win over FBS receives full credit;
- FBS games use full scoring.

## Website rules
- White background and text-first interface.
- Primary navigation is plain text.
- Avoid outlined decorative buttons.
- The Weekbook week spine is persistent navigation.
- Official predictions lock at kickoff and may never be rewritten by later information.
- Retrocasts must be visibly separate from official prediction accuracy.

## Data rules
- PostgreSQL is the production database.
- CFBD API data is accessed server-side only.
- Never commit API keys or database passwords.
- Do not publish a bulk mirror of CFBD raw data.

## Deployment rules
- GitHub is the source of truth for all application, ranking-model, website, script, and documentation changes.
- Make and commit changes in GitHub first; do not treat the live Synology app folder as the primary development copy.
- Production updates must be deployed to Synology from GitHub over SSH using the repository's install/update/upgrade scripts.
- Do not manually patch files under `/volume1/rankings/app` except for emergency diagnosis. If an emergency live edit is unavoidable, reproduce and commit the same change to GitHub immediately before the next deployment.
- Synology production root: `/volume1/rankings`.
- App code: `/volume1/rankings/app`.
- PostgreSQL data: `/volume1/rankings/postgres`.
- Secrets: `/volume1/rankings/.env`.
- Backups: `/volume1/rankings/backups`.

## Release rules
Every meaningful release updates `VERSION`, `VERSION.md`, `CHANGELOG.md`, and release notes.
