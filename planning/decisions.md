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
