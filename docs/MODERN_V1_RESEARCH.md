# Modern v1 FBS Research Contract

## Project scope

This project ranks **FBS teams**. FCS teams are opponent context only.

## Primary objective

The calculator is optimized for one question:

> At the end of the pre-bowl portion of the FBS season, how often does the higher-ranked FBS team win a postseason matchup?

The ranking must remain explainable game by game.

## Fixed season structure

The research program is not allowed to change these production rules:

- every season starts from zero;
- no previous-season rankings carry forward;
- no previous-season team statistics carry forward;
- no preseason poll or power-rating seed is used;
- conference identity has no mathematical strength value;
- no ranking is published before current-season games exist;
- Week 1 creates the first ranking from Week 1 results only;
- Week 1 has zero opponent-rank points because no current-season ranking exists yet;
- Week 2 uses Week 1 ranks;
- each later week uses the immediately preceding completed current-season ranking.

Historical data is used to improve scoring rules, not to seed teams in a future season.

## Baseline game formula

The recovered later FBS scoring relationship remains the reference scoring baseline:

```text
Game Score = Opponent Rank Score + Win Bonus + Margin
```

For an FBS pool of `N` teams and a prior-week opponent ranked `R`:

```text
win over FBS rank R = (N + 1 - R) + 10 + margin
loss to FBS rank R  = -R + margin
```

For Week 1:

```text
opponent-rank points = 0
```

because there is no previous current-season ranking.

For an out-of-pool opponent:

```text
opponent-rank points = 0
margin = raw margin * out_of_pool_margin_scale
```

The recovered default out-of-pool margin scale is `0.5`.

## Modern candidate family

The modern candidate keeps the same three ideas:

```text
Game Score = Opponent Quality + Win Bonus + Adjusted Margin
```

For a ranked FBS opponent from the previous completed week:

```text
q_win  = (N + 1 - opponent_rank) / N
q_loss = opponent_rank / N

win opponent points  = rank_weight * N * q_win^win_rank_gamma
loss opponent points = -loss_weight * N * q_loss^loss_rank_gamma
```

Margin may be transformed with `linear`, `cap`, `sqrt`, `log1p`, or `tanh`.

## FCS and other out-of-pool opponents

FCS teams are outside the published FBS ranking pool.

The legacy FBS default gives an out-of-pool opponent zero rank points and scales scoring margin by `0.5`. Modern research may test the out-of-pool scale or another transparent FCS treatment, but only to improve the **FBS ranking**.

## Conference policy

Conference strength is permanently excluded from the live ranking.

Conference membership may be retained as metadata for display, schedule grouping, and historical analysis. It cannot contribute points, penalties, priors, or seeds.

## Previous-season policy

Previous-season information is permanently excluded from the live ranking.

This includes:

- previous final rank;
- prior record;
- prior scoring margin;
- prior schedule strength;
- preseason polls;
- preseason power ratings.

Research may use older seasons as training/backtest samples, but every simulated season must start independently at zero.

## No-leakage postseason rule

For each season:

1. Start every team at zero.
2. Build Week 1 from Week 1 results only.
3. Build each later week using the preceding current-season ranking.
4. Freeze the final pre-postseason ranking.
5. Predict every bowl and CFP game from that same snapshot.
6. Never feed a postseason result into a later postseason prediction.

## Seasons

Primary ten-season sample:

```text
2014 2015 2016 2017 2018 2019 2022 2023 2024 2025
```

Primary research excludes 2020 and 2021. The 2021 season remains a sensitivity test. The 2026 season is the live season and is not part of historical tuning.

## Validation

Development uses time-ordered walk-forward tests. The 2025 season is the locked final holdout.

Selection order:

1. Highest walk-forward postseason accuracy.
2. Lower Brier score among near-ties.
3. Better calibration among near-ties.
4. Simpler formula among near-ties.

## Acceptance gate

A modern scoring rule is promoted only if it:

- improves out-of-sample FBS postseason accuracy;
- targets at least a 2 percentage-point absolute improvement as a practical benchmark;
- avoids a material decline in probability quality;
- improves results across seasons rather than one exceptional year;
- avoids a major collapse in CFP games; and
- remains explainable game by game.

## Allowed ablations

The weekly causal structure is fixed. Research may test scoring inside it:

1. FBS team-count normalization.
2. Opponent-rank curve and weight.
3. Bad-loss curve and weight.
4. Win bonus.
5. Margin saturation.
6. Home-field adjustment.
7. FBS-vs-FCS/out-of-pool treatment.
8. Current-season recency.

## Forbidden ablations

These are not research candidates:

```text
conference-strength adjustment
previous-season carryover
preseason ranking seed
final/current recursive opponent-rank rewriting
```

The live ranking uses the opponent rank that existed after the previous completed week.

## Historical engine distinction

`RecursiveRankingEngine` is retained only for reconstructing the old workbook and measuring historical differences.

`WeeklySeasonRankingEngine` is the production structure and the structure used for modern formula research.

## Data source direction

Historical and live data ingestion should provide:

- FBS membership by season;
- week number;
- completed game scores;
- FBS/FCS opponent classification;
- home/away/neutral site;
- postseason identification.

Conference may be stored for display, but no conference-strength field should enter scoring.

## Central design principle

> **Every season begins at zero, and every team earns its place only through games played in that season.**
