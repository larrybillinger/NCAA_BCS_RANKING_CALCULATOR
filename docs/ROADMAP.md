# NCAA BCS Ranking Calculator Roadmap

## Project scope

The production ranking is for **FBS teams**. FCS is opponent context only.

The primary success test is:

> At the pre-bowl freeze point, the higher-ranked FBS team should win postseason head-to-head matchups as often as possible.

## Permanent ranking-policy rules

These are project rules, not tunable parameters:

- Conferences have **no strength value**.
- Previous-season rankings never carry forward.
- Previous-season team statistics never carry forward.
- Preseason polls and external power ratings never seed the live ranking.
- There is no preseason ranking.
- Week 1 creates the first ranking from Week 1 current-season results only.
- Week 2 uses Week 1 opponent ranks.
- Each later week uses the immediately preceding completed current-season ranking.
- Historical seasons are used to improve the formula, never to give a team a new-season head start.

## v0.1 — Recover the old system

Goal: understand the historical spreadsheets before replacing them.

- [x] Review the historical FCS workbook as archival context.
- [x] Review both historical FBS workbooks.
- [x] Recover the FBS win-rank formula.
- [x] Recover the later FBS loss penalty.
- [x] Recover win-score behavior.
- [x] Recover margin/scoring-spread behavior.
- [x] Identify the historical dynamic opponent-rank loop.
- [x] Identify the historical FBS-vs-out-of-pool half-margin treatment.
- [x] Confirm that the later FBS workbook disabled the conference bonus.
- [x] Document structural problems in the old workbook.

## v0.2 — Executable engines

Goal: preserve historical behavior while establishing the production season-only path.

### Historical engine

`RecursiveRankingEngine` remains available for reconstructing and testing the old FBS workbook behavior.

### Production engine

`WeeklySeasonRankingEngine` is the live-ranking path.

It must:

- refuse previous-season/preseason ranking seeds;
- require a current-season week for every game;
- publish no ranking before current-season games exist;
- create Week 1 with no opponent-rank component;
- use full scoring margin for Week 1 FBS-vs-FBS games;
- retain configured out-of-pool/FCS treatment;
- use Week 1 ranks to score Week 2 opponents;
- use each completed week's ranking for the next week;
- accumulate only current-season points and records;
- never use conference identity as a score component.

Acceptance target:

> Given only the current season's completed games, the engine produces the same result regardless of any prior-season information available elsewhere in the data system.

## v0.3 — Modernize the FBS data layer

Goal: remove 2012-specific team, conference, schedule, and worksheet assumptions.

Create a provider-neutral import layer for:

- FBS teams by season.
- FBS/FCS classification by season.
- Conference membership for display/history only.
- Schedules and completed scores.
- Week number.
- Home/away/neutral status.
- Conference championships.
- Bowls and CFP games.
- Stable game/team IDs.

Important rules:

- Conference membership must never produce ranking points.
- FBS team count is season-specific.
- FCS opponents may affect an FBS team's score but are not published in the production ranking.
- No provider field containing a prior-season rank/power rating may enter the live scoring engine.
- Raw provider data should be cached before normalization.

## v0.4 — Historical FBS backtest

Goal: measure how well the season-only weekly calculator predicts postseason winners.

Primary seasons:

```text
2014 2015 2016 2017 2018 2019 2022 2023 2024 2025
```

Every historical season must be simulated exactly like a fresh live season:

1. Start every team at zero.
2. Do not publish a preseason ranking.
3. Build Week 1 from Week 1 games only.
4. Use Week 1 ranks for Week 2 opponent scoring.
5. Continue week by week using only that season.
6. Freeze the final pre-postseason ranking.
7. Predict the postseason without feeding postseason outcomes back into the ranking.

Other rules:

- Exclude 2020 and 2021 from the primary comparable sample.
- Keep 2021 as a sensitivity test.
- Include conference championship games in the primary freeze definition.
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

## v0.5 — Transparent FBS scoring research

Goal: improve postseason prediction while keeping the formula simple and auditable.

Starting structure:

```text
Game Score = Opponent Quality + Win Bonus + Adjusted Margin
```

The weekly season structure is fixed. Research may tune scoring inside that structure.

Allowed research families:

1. FBS team-count normalization.
2. Opponent-strength curve/weight.
3. Loss-strength curve/weight.
4. Win bonus.
5. Margin saturation (`cap`, `sqrt`, `log1p`, `tanh`).
6. Home-field adjustment.
7. FBS-vs-FCS/out-of-pool treatment.
8. Current-season recency weighting.

Permanently excluded from the live ranking:

- conference-strength bonuses;
- previous-season rankings;
- previous-season team statistics;
- preseason poll or power-rating seeds.

No rule becomes the default because it sounds reasonable. It has to improve out-of-sample postseason prediction.

## v0.6 — Model selection and locked holdout

Goal: select the simplest scoring formula that survives time-ordered testing.

Selection order:

1. Highest walk-forward postseason accuracy.
2. Lower Brier score among near-ties.
3. Better calibration among near-ties.
4. Simpler formula among near-ties.

Promotion gate:

- Beat the current production scoring baseline out of sample.
- Target at least +2 percentage points absolute postseason accuracy as a practical benchmark.
- Do not materially worsen probability quality.
- Do not rely on one anomalous season.
- Do not collapse on CFP games.
- Remain explainable game by game.

Then evaluate the frozen choice on 2025 exactly once.

## v0.7 — Current-season FBS rankings

Goal: calculate and publish the current FBS season automatically.

Outputs:

- No preseason ranking.
- Week 1 first ranking.
- Overall FBS ranking table.
- Top 25 / Top 50 / full FBS ranking.
- Week-by-week movement.
- Team detail page/table.
- Game-by-game point breakdown.
- Prior-week opponent rank used for each game.
- Record and conference information, with conference shown only as metadata.
- Clear notation for FCS/out-of-pool opponents.

## v0.8 — User interface

Goal: make the FBS rankings easy to browse without hiding the math.

Possible views:

- Current Top 25 / Top 50 / full FBS ranking.
- Team page with every game's point calculation.
- Weekly movement chart.
- Historical season selector.
- Side-by-side comparison with AP, Coaches, CFP, and external benchmarks.
- Postseason prediction history.
- Methodology page generated directly from the active rule configuration.

## Long-term principles

### Rank FBS teams

FBS is the product. FCS is supporting opponent context only.

### Reset every season

Every FBS team begins every season at zero. Reputation from the previous year has no mathematical value.

### Conferences are labels, not strength multipliers

Conference membership may be displayed but does not affect points.

### Keep the scoring engine deterministic

The same current-season inputs and rule configuration must always produce the same rankings.

### Keep every point explainable

A user should be able to inspect an FBS team and answer:

> Why is this team ranked here?

without reading source code.

### Prevent postseason leakage

The ranking used to judge postseason prediction accuracy must be frozen before postseason games begin.

### Prefer simple improvements

A small rule that consistently improves FBS postseason prediction is preferable to a complicated formula that is difficult to audit.
