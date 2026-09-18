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


## 2026-09-17 — Monotonic rank-gap predictions
The projected winner must follow the ranking order. The higher-ranked team is always the projected winner, and the projected scoring margin is based directly on the numerical gap between team ranks. Current-season results may calibrate the positive points-per-rank scale and uncertainty, but no intercept, home-field adjustment, or unconstrained regression may reverse the projected winner.


## 2026-09-17 — First-game neutral baseline and Week 0
A team remains on the neutral T-1 scoring baseline until it completes its first current-season game, even if the calendar has advanced beyond ranking Week 1. Provider Week 0 is normalized into ranking Week 1. Once a team has a completed result, later opponent scoring uses the immediately preceding completed week's scoring rank.

## 2026-09-17 — Historical retrocasts
Completed games that never had an actual locked pregame prediction may be shown with a research retrocast generated only from the ranking information available before that game. Retrocasts must be visibly labeled and must never be mixed into official locked-prediction accuracy.


## 2026-09-18 — Remove win bonus and add site adjustment
Production no longer awards a separate +10 for a win. The actual scoring margin remains a direct game-score component. An away win receives +7 ranking points, and a home loss receives -7 ranking points. Home wins, away losses, and neutral-site results receive no site adjustment. FBS-vs-FBS and FBS-vs-FCS are both explicitly 100%; FCS remains part of Division I. The FCS percentage applies to opponent-rank points, scoring margin, and site adjustment.
