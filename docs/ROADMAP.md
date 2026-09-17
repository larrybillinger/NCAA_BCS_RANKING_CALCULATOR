# NCAA BCS Ranking Calculator Roadmap

## Current production rules

The live system ranks all NCAA Division I football teams in one field while applying the v0.3.1 FCS modifier:

- FBS game scores use 100% of the normal formula.
- FCS-vs-FCS scores use 50%.
- FCS losses to FBS use 50%.
- FCS wins over FBS receive full credit.
- Conference affiliation has no ranking value.
- No previous-season or preseason seed is allowed.
- Week 1 creates the first ranking.
- Week 2+ uses the previous completed week's current-season ranking.
- Old games are never recursively revalued.

## v0.1 — Historical recovery
- [x] Recover legacy workbook behavior and formulas.

## v0.2 — Executable legacy and weekly engines
- [x] Historical parity engine.
- [x] Current-season weekly engine.

## v0.3 — Division I production model
- [x] One FBS+FCS ranking pool.
- [x] Season-only weekly ranking behavior.
- [x] v0.3.1 FCS scoring modifier.

## v0.4 — Data layer + Weekbook website
- [x] PostgreSQL production database.
- [x] Season-specific team/subdivision metadata.
- [x] CFBD schedules, scores and team-game-stat ingestion.
- [x] Immutable weekly ranking snapshots.
- [x] Game-level scoring audit storage.
- [x] Weekbook ranking UI.
- [x] Team schedule and prediction pages.
- [x] Current/future/past Game Book.
- [x] Locked pregame predictions.
- [x] Rank-to-score calculator.
- [x] Overall and team-specific model accuracy.
- [x] Synology Container Manager deployment under `/volume1/rankings`.

## v0.5 — Historical prediction baseline
Goal: backtest the rank-gap prediction layer without contaminating current official prediction history.

- [ ] Build historical season imports.
- [ ] Reconstruct week-by-week ranking snapshots for selected seasons.
- [ ] Measure winner accuracy, margin MAE/RMSE, score MAE, Brier score and calibration.
- [ ] Separate FBS postseason, FCS playoff and regular-season samples.
- [ ] Lock 2025 as a holdout where appropriate.

## v0.6 — Prediction research
Goal: improve the score/probability layer while keeping the ranking itself transparent and unchanged.

Potential prediction-only research:
- nonlinear rank-gap transforms;
- rank-score difference versus ordinal rank gap;
- home-field calibration;
- uncertainty by rank gap and season week;
- subdivision matchup slices;
- calibration by favorite strength.

No prediction research may silently change the ranking formula.

## v0.7 — Operations and resilience
- [ ] Admin-only provider sync status page.
- [ ] Manual postponement/cancellation override.
- [ ] Database migration framework.
- [ ] Automated PostgreSQL backup retention.
- [ ] Provider fallback/import path for outages.

## v0.8 — Historical/public exploration
- [ ] Season selector.
- [ ] Full historical team pages.
- [ ] Locked-vs-retrocast explorer.
- [ ] Postseason prediction archive.
- [ ] Optional external poll comparisons as benchmarks only.

## Long-term principles

1. Keep every ranking point explainable.
2. Keep official predictions immutable after kickoff.
3. Keep current-season facts separate from later hindsight.
4. Keep source data private and derived public output transparent.
5. Prefer simple improvements that survive historical testing.
