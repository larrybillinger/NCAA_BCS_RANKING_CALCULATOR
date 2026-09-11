# NCAA BCS Ranking Calculator Roadmap

## Project scope

The production ranking is for **FBS teams**. The repository keeps the historical BCS name, but FCS is not a parallel ranking target.

FCS data is used only when it helps score an FBS team's schedule, especially FBS-vs-FCS games. The old FCS workbook remains an archival reference.

The primary success test is:

> At the pre-bowl freeze point, the higher-ranked FBS team should win postseason head-to-head matchups as often as possible.

## v0.1 — Recover the old system

Goal: understand the historical spreadsheets before replacing them.

- [x] Review the historical FCS workbook as archival context.
- [x] Review both historical FBS workbooks.
- [x] Recover the FBS win-rank formula.
- [x] Recover the later FBS loss penalty.
- [x] Recover win-score behavior.
- [x] Recover margin/scoring-spread behavior.
- [x] Identify the dynamic FBS opponent-rank loop.
- [x] Identify the historical FBS-vs-out-of-pool half-margin treatment.
- [x] Confirm that the later FBS workbook disabled the conference bonus.
- [x] Document structural problems in the old workbook.

## v0.2 — Executable FBS parity engine

Goal: reproduce the historical FBS formula without spreadsheet-specific logic.

The calculation engine should accept normalized FBS game data and produce:

- Per-game score components.
- Running team records.
- Cumulative ranking points.
- Overall FBS rankings.
- Opponent ranks used by the recursive calculation.
- Cycle detection and deterministic termination.
- A full audit trail showing how every point was earned.

Reference profiles:

```text
legacy_fbs_2012_original
legacy_fbs_2012_later
```

Acceptance target:

> Given the same game results, FBS ranking pool, seed, and rule settings, the engine reproduces the recovered legacy game calculations and expected ranking behavior.

The later FBS model remains the control model for modernization.

## v0.3 — Modernize the FBS data layer

Goal: remove 2012-specific team, conference, schedule, and worksheet assumptions.

Create a provider-neutral import layer for:

- FBS teams by season.
- FBS/FCS classification by season.
- Historical conference membership.
- Schedules.
- Completed scores.
- Home/away/neutral status.
- Conference championships.
- Bowls and CFP games.
- Stable game/team IDs.

Primary automated source: CollegeFootballData.

NCAA, school, and conference records are reconciliation sources when data conflicts.

Important rules:

- Historical membership belongs to the season record.
- FBS team count is season-specific.
- FCS opponents may affect an FBS team's score but are not published in the production ranking.
- Raw provider data should be cached before normalization.

## v0.4 — Historical FBS baseline backtest

Goal: measure how well the recovered later FBS formula predicts postseason winners.

Primary seasons:

```text
2014 2015 2016 2017 2018 2019 2022 2023 2024 2025
```

Rules:

- Exclude 2020 and 2021 from the primary comparable sample.
- Keep 2021 as a sensitivity test.
- Use one frozen pre-postseason ranking for every postseason game in a season.
- Never update the ranking with bowl or CFP results.
- Include conference championship games in the primary freeze definition; retain a sensitivity mode that excludes them.
- Keep 2025 locked as the final holdout.

Primary metric:

```text
Postseason Accuracy = higher-ranked FBS team wins / postseason games predicted
```

Secondary metrics:

- Brier score.
- Log loss.
- Calibration.
- Accuracy by rank gap.
- CFP-only accuracy.
- Season-by-season stability.

## v0.5 — Transparent FBS rule research

Goal: improve postseason prediction while keeping the formula simple and auditable.

Starting candidate:

```text
Game Score = Opponent Quality + Win Bonus + Adjusted Margin
```

Test one family at a time:

1. FBS team-count normalization.
2. Margin saturation (`cap`, `sqrt`, `log1p`, `tanh`).
3. Home-field adjustment.
4. End-of-season opponent rank versus prior-week rank.
5. FBS-vs-FCS/out-of-pool treatment.
6. Recency.

Only after those tests should the project consider:

- conference-strength adjustments;
- preseason carryover;
- efficiency statistics;
- transparent Elo-like models;
- SRS-like challengers; or
- ensembles.

No rule becomes the default because it sounds reasonable. It has to improve out-of-sample postseason prediction.

## v0.6 — Model selection and locked holdout

Goal: select the simplest candidate that survives time-ordered testing.

Selection order:

1. Highest walk-forward postseason accuracy.
2. Lower Brier score among near-ties.
3. Better calibration among near-ties.
4. Simpler formula among near-ties.

Promotion gate:

- Beat `legacy_fbs_2012_later` out of sample.
- Target at least +2 percentage points absolute postseason accuracy as a practical benchmark.
- Do not materially worsen probability quality.
- Do not rely on one anomalous season.
- Do not collapse on CFP games.
- Remain explainable game by game.

Then evaluate the frozen choice on 2025 exactly once.

## v0.7 — Current-season FBS rankings

Goal: calculate and publish a current FBS season automatically.

Outputs:

- Overall FBS ranking table.
- Top 25 / Top 50 / full FBS ranking.
- Week-by-week movement.
- Team detail page/table.
- Game-by-game point breakdown.
- Strength-of-opponent information.
- Record and conference information.
- Clear notation for FCS/out-of-pool opponents.

The ranking engine remains independent of the display layer.

## v0.8 — User interface

Goal: make the FBS rankings easy to browse without hiding the math.

Possible views:

- Current Top 25 / Top 50 / full FBS ranking.
- Team page with every game's point calculation.
- Weekly movement chart.
- Historical season selector.
- Side-by-side comparison with AP, Coaches, CFP, and external benchmarks.
- Postseason prediction history.
- Methodology page generated from the active rule configuration.

## Long-term principles

### Rank FBS teams

FBS is the product. FCS is supporting opponent context only.

### Keep the scoring engine deterministic

The same inputs and rule configuration must always produce the same rankings.

### Keep data ingestion replaceable

A schedule/results provider may disappear or change its API. The ranking engine should not care where a normalized game record came from.

### Keep every point explainable

A user should be able to inspect an FBS team and answer:

> Why is this team ranked here?

without reading source code.

### Preserve historical reproducibility

Rule changes should be versioned. A ranking generated with one scoring version should remain reproducible later.

### Prevent postseason leakage

The ranking used to judge postseason prediction accuracy must be frozen before postseason games begin.

### Prefer simple improvements

A small rule that consistently improves FBS postseason prediction is preferable to a complicated formula that is difficult to audit.