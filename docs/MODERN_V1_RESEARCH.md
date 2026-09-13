# Modern v1 Research Contract

## Production scope

The live calculator ranks **all NCAA Division I football teams together**.

The active pool contains both FBS and FCS. Subdivision membership does not change the scoring formula.

These production principles are fixed and are not research knobs:

- no conference-strength bonus or penalty;
- no previous-season rankings;
- no previous-season statistics;
- no preseason seed;
- no preseason ranking;
- Week 1 starts from current-season game results only;
- Week 1 opponent-rank points are zero;
- Week 2 and later use the immediately preceding completed week's current-season rank;
- no same-week recursive production recalculation;
- no retroactive rescoring of earlier games;
- FBS and FCS use identical in-pool scoring.

## Baseline formula

The current transparent baseline is derived from the later historical FBS workbook but generalized to the active Division I pool.

For a Division I pool containing `N` teams and an opponent ranked `R` in the prior completed week:

```text
Win:
    opponent_rank_points = (N + 1) - R
    win_bonus = 10
    margin = points_for - points_against

Loss:
    opponent_rank_points = -R
    win_bonus = 0
    margin = points_for - points_against
```

```text
Game Score = Opponent Rank Points + Win Bonus + Margin
```

In Week 1, `Opponent Rank Points = 0` because no prior current-season ranking exists yet.

## FBS and FCS

FBS and FCS are both inside the active Division I ranking pool.

A game between FBS and FCS receives the same full-margin treatment as FBS-vs-FBS or FCS-vs-FCS.

The old historical FBS half-margin treatment for FCS opponents is not part of the production system anymore.

Only opponents below Division I are outside the pool.

## Primary research objective

The original project was built to rank BCS/FBS teams, so FBS postseason prediction remains the primary historical benchmark:

> At the final pre-postseason freeze point, how often does the higher-ranked team win an FBS postseason matchup?

The ranking that produces those predictions, however, includes all available Division I FBS and FCS teams for the season.

A secondary benchmark should measure FCS playoff prediction using the same shared Division I ranking.

## Seasons

Primary FBS postseason sample:

```text
2014 2015 2016 2017 2018 2019 2022 2023 2024 2025
```

- 2020 and 2021 are excluded from the primary comparable sample.
- 2021 remains a sensitivity test.
- 2025 is the locked final holdout.
- 2026 is excluded from historical model selection while the season is in progress.

## No-leakage postseason rule

For each season:

1. Use only games completed by the freeze point.
2. Calculate the final weekly Division I ranking.
3. Freeze it.
4. Predict every postseason matchup from that same frozen ranking.
5. Never feed postseason results back into the ranking used for later postseason predictions.

## Candidate family

The first modern candidate keeps the same transparent structure:

```text
Game Score = Opponent Quality + Win Bonus + Adjusted Margin
```

Research may test:

- nonlinear opponent-rank weighting;
- different loss-penalty weighting;
- different win bonus values;
- capped or saturated margin functions;
- home-field adjustment;
- recency weighting;
- treatment of teams below Division I.

Research must not reintroduce:

- conference reputation;
- previous-season carryover;
- preseason polls or power ratings;
- different FBS/FCS scoring;
- same-week recursive production rankings.

## Validation

Development uses time-ordered walk-forward testing, with 2025 held out until the candidate formula is frozen.

Selection order:

1. highest out-of-sample postseason accuracy;
2. lower Brier score among near-ties if probabilities are produced;
3. better calibration among near-ties;
4. simpler formula among near-ties.

## Acceptance gate

A modern rule is promoted only if it:

- improves out-of-sample postseason prediction;
- does not depend on one unusual season;
- does not materially damage CFP performance;
- remains explainable game by game;
- preserves the season-only weekly structure;
- preserves identical FBS/FCS scoring.

A practical target remains at least a 2 percentage-point absolute improvement in FBS postseason accuracy, but that is a benchmark rather than a promised result.

## Data direction

Historical and current data ingestion should include all Division I teams and games, not just FBS.

The normalized data layer should record season-specific:

- team identity;
- FBS/FCS subdivision;
- conference membership for metadata only;
- game week/date;
- score;
- home/away/neutral status;
- postseason classification.

Raw provider data should be cached before normalization so research runs can be reproduced.

## Central design principle

> **Rank all NCAA Division I football teams together with the simplest transparent season-only formula that best predicts future head-to-head winners.**
