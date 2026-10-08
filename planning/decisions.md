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
Production no longer awards a separate +10 for a win. The actual scoring margin remains a direct game-score component. An away win receives +7 ranking points, and a home loss receives -7 ranking points. Home wins, away losses, and neutral-site results receive no site adjustment. FBS-vs-FBS and FBS-vs-FCS are both explicitly 100%; FCS remains part of Division I. The FCS percentage applies to opponent-rank points and scoring margin. The ±7 site adjustment is applied afterward at full value for every team.

## 2026-09-18 — Rank by average frozen game score
Production ranking position is based on the arithmetic mean of each team's frozen game scores rather than the cumulative point total. This removes the automatic advantage of playing more games and makes bye weeks neutral. Raw cumulative points remain available for auditing. Exact average-score ties use head-to-head, then win percentage, then average opponent strength per game, then deterministic team-name fallback.

## 2026-10-04 — Admin-only manual score desk
Add a secure operational score desk at `/admin/games` so Larry can enter or correct game scores when CFBD is unavailable, delayed, or wrong. The public site remains read-only. The score desk uses environment-backed admin credentials plus CSRF protection. A manual score becomes authoritative over the provider score fields until explicitly released back to CFBD. Manual score writes and releases are audited. An official ranking week remains immutable: once the active production model has frozen a week, the score desk may not edit or release that week's results.

## 2026-10-05 — Scoped ranking views are display derivatives
Keep one canonical Division I national ranking. FBS rank, FCS rank, and conference rank are sequential display derivatives of that national order and are calculated before page filtering or team search. Conference order follows national ranking order rather than conference record. These views do not create separate ranking models or scoring pools.

## 2026-10-05 — Context-aware predictions remain a separate shadow system
Keep rank_gap_v3 as the official predictor under the protected monotonic rule. Experimental hybrid offense/defense and context-aware predictions may select a different winner, but they must be stored in a separate research ledger, clearly labeled, and locked only from information captured before kickoff. Research failures may not block official prediction locking or provider synchronization. No research model becomes official without a later explicit decision.

## 2026-10-08 — Duplicate team identities are fixed going forward
Published official ranking snapshots and the predictions locked against them are not deleted or rebuilt to correct a duplicate team identity. The legacy Penn row (bundled data, no games) is merged into the provider-backed Pennsylvania row and removed from the active pool, so rankings calculated after the repair use the corrected pool, while every published week and the official prediction ledger stay as they were. This is consistent with the rule that old games are not recursively revalued. If a duplicate ever carries results in frozen rankings, the repair refuses; rebuilding published weeks would need its own explicit decision.

## 2026-10-08 — Promote hybrid_core_v1 to the official predictor
Larry explicitly approved moving forward with the hybrid predictor across the production site. Beginning with v0.11.0, `hybrid_core_v1` supersedes the 2026-10-05 decision that kept it shadow-only and supersedes the 2026-09-17 rule that required the projected winner to follow ranking order. The national ranking formula remains `division_i_weighted_v5` and is unchanged.

The official hybrid prediction blends 40% of the calibrated rank-gap margin with 60% of a shrunk current-season offense/defense matchup margin. Offense/defense profiles use completed current-season Division I games only and shrink toward the season scoring mean with three pseudo-games. The hybrid may project a lower-ranked team to win when the matchup profile outweighs the rank-gap component.

All new Game Book predictions, team-page predictions, active Accuracy metrics, historical retrocasts, and the public matchup calculator use the hybrid predictor. Existing locked `rank_gap_v3` rows remain immutable historical records and are never rewritten as hybrid predictions. Existing pre-promotion hybrid shadow rows also remain stored as research history. Context adjustments such as home field, travel, altitude, weather, and stadium demand remain research-only until separately approved.
