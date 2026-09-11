# Modern v1 FBS Research Contract

## Project scope

This project ranks **FBS teams**. The repository keeps the historical name "NCAA BCS Ranking Calculator," but the modern ranking pool is the current NCAA Football Bowl Subdivision (FBS).

FCS teams are **not** a second production ranking target. FCS data is used only when it helps evaluate an FBS team's schedule, especially FBS-vs-FCS games. The historical FCS workbook remains archival evidence about the earlier spreadsheet system.

## Primary objective

The calculator is optimized for one question:

> At the end of the pre-bowl portion of the FBS season, how often does the higher-ranked FBS team win a postseason matchup?

The ranking must remain explainable game by game. A complicated feature is not accepted merely because it sounds sophisticated.

## Baseline

The main baseline is `legacy_fbs_2012_later`:

```text
win over FBS rank R = (N + 1 - R) + 10 + margin
loss to FBS rank R  = -R + margin
out-of-pool game     = 0 rank points + win bonus + scaled margin
```

`N` is the active FBS ranking pool for that season. This replaces the historical hard-coded `125` while reproducing the 124-team 2012 formula exactly.

Opponent rank is recursively recalculated from the current end-of-regular-season FBS ordering.

## Modern candidate family

The first research candidate keeps the same three ideas:

```text
Game Score = Opponent Quality + Win Bonus + Adjusted Margin
```

For an FBS opponent:

```text
q_win  = (N + 1 - opponent_rank) / N
q_loss = opponent_rank / N

win opponent points  = rank_weight * N * q_win^win_rank_gamma
loss opponent points = -loss_weight * N * q_loss^loss_rank_gamma
```

This is exactly equivalent to the later legacy rank rule when both gamma values and both weights equal `1.0`.

Margin is then optionally neutralized for venue and transformed:

```text
neutralized_margin = raw_margin - home_field_points * site_sign

site_sign = +1 home
            -1 away
             0 neutral
```

Supported margin transforms are `linear`, `cap`, `sqrt`, `log1p`, and `tanh`.

The first serious challenger uses `tanh` margin saturation because huge blowouts should keep adding information without dominating a season score. This is a hypothesis to test, not a predetermined winner.

## FCS and other out-of-pool opponents

FCS teams are outside the published FBS ranking pool.

The legacy FBS model gives an out-of-pool opponent zero rank points and scales scoring margin by `0.5`. Modern research may test better FCS-opponent treatment, including mapping FCS strength or a joint network calculation, but those methods exist only to improve the accuracy of the **FBS ranking**.

No public FCS ranking product is required by this project.

## No-leakage postseason rule

For each season:

1. Use only games completed by the pre-postseason freeze point.
2. Calculate one final FBS regular-season ranking.
3. Freeze it.
4. Predict every bowl and CFP game from that same snapshot.
5. Never feed a bowl, first-round, quarterfinal, semifinal, or championship result back into the ranking used for later postseason predictions.

This rule is enforced by `frozen_postseason_backtest()`.

## Seasons

Primary ten-season sample:

```text
2014 2015 2016 2017 2018 2019 2022 2023 2024 2025
```

Primary research excludes 2020 and 2021. The 2021 season is retained as a sensitivity test. The 2026 season is excluded because it is incomplete.

The sample begins with the first CFP season and includes the expanded CFP era beginning in 2024. Results should therefore be reported both overall and by playoff format.

## Validation

Development uses time-ordered walk-forward tests. The 2025 season is the locked final holdout.

Selection order:

1. Highest walk-forward postseason accuracy.
2. Lower Brier score among near-ties.
3. Better calibration among near-ties.
4. Simpler formula among near-ties.

A single frozen pre-postseason FBS ranking predicts the entire postseason.

## Acceptance gate

A modern rule is not promoted merely because it looks better on the development sample. It must:

- beat `legacy_fbs_2012_later` on out-of-sample FBS postseason accuracy;
- target at least a 2 percentage-point absolute improvement as a practical benchmark;
- avoid a material decline in probability quality;
- show improvement across seasons rather than one exceptional year;
- avoid a major collapse in CFP games; and
- remain explainable from an FBS team's schedule one game at a time.

## First ablations

Test one family at a time before combining them:

1. FBS team-count normalization.
2. Margin saturation.
3. Home-field adjustment.
4. End-of-season opponent rank versus prior-week rank.
5. FBS-vs-FCS / out-of-pool treatment.
6. Recency.

Conference reputation bonuses, preseason carryover, box-score features, Elo-like models, and ensembles are challengers. They stay out of the first production candidate until data shows repeatable predictive value.

## Data source direction

CollegeFootballData is the preferred primary automated source for historical FBS schedules, scores, team identity, classification, historical conference membership, rankings, and CFP metadata. NCAA and school/conference records should be reconciliation sources when data conflicts.

Raw provider responses should be cached before normalization so a research run can be reproduced even if a provider later corrects historical data.

## Important distinction

`modern_legacy_candidate_v1` is a research candidate, not the production champion. Until the ten-season backtest is run and the acceptance gate is passed, `legacy_fbs_2012_later` remains the reference model.

The central design principle remains:

> Rank FBS teams using the simplest transparent formula that best predicts future FBS postseason winners.