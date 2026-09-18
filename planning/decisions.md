# Decisions

## 2026-09-16 — Website structure
Use the Option 2 Weekbook interaction model as the production website.

## 2026-09-16 — Visual language
Use white background, black/gray text, generous whitespace, and plain-text navigation. Avoid ornamental outlined buttons.

## 2026-09-16 — Database
Use PostgreSQL for all production persistent data.

## 2026-09-16 — External data provider
Use CollegeFootballData REST API server-side for automatic schedules, scores, classifications, and game-team statistics.

## 2026-09-16 — Prediction integrity
Official predictions must be created before kickoff and locked at kickoff. Historical accuracy may not be improved by rewriting old predictions. Later-rank retrocasts are separate research output.

## 2026-09-16 — Score projection
Use current-season rank-gap calibration against completed game margins. The prediction layer may learn from completed current-season games but does not modify the ranking formula.

## 2026-09-16 — Production path
Use `/volume1/rankings` on Synology.


## 2026-09-17 — Week 1 neutral tied baseline
Treat every Division I team as tied for first before the first current-season games because there is no evidence separating them. For scoring, use the average occupied rank of that all-team tie, `(N + 1) / 2`. For exact score ties after a completed week, use the average occupied rank of the tied positions for the following week's opponent scoring. Keep deterministic display order separate from scoring rank.


## 2026-09-17 — GitHub-first production workflow
GitHub is the authoritative source for the D1 Rank application, ranking model, website, deployment scripts, and documentation. All normal changes are committed to GitHub first. The Synology production instance under `/volume1/rankings` is updated from GitHub over SSH using repository deployment scripts rather than by editing the live application directly.
