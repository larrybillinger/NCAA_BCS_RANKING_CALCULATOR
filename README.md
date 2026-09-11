# NCAA BCS Ranking Calculator

A transparent, auditable ranking system for **NCAA FBS college-football teams**.

The repository keeps the historical `BCS` name because that is the name of the original project, but the modern ranking pool is the current **Football Bowl Subdivision (FBS)**. This is not an FCS ranking project.

## Primary goal

The main objective is not to imitate the AP Poll, Coaches Poll, CFP committee, betting markets, or another power rating.

The objective is:

> **At the end of the pre-bowl portion of the FBS season, the higher-ranked FBS team should win postseason head-to-head matchups as often as possible.**

Every ranking should still be explainable game by game.

## Project status

**Version: 0.2.0 — Executable FBS legacy engine + modern research candidate**

Three historical workbooks were used to recover the original system:

- `NCAA FBS Rankings 2011.xlsx`
- `NCAA FBS Rankings.xlsx`
- `NCAA FCS Rankings.xlsx`

The FBS workbooks are the primary formula source. The FCS workbook is retained only as historical evidence and as useful context for how the old system handled teams outside the active ranking pool.

### Scope rule

- **Published ranking target:** FBS teams.
- **Primary validation target:** FBS bowls and College Football Playoff games.
- **FCS role:** opponent context when an FBS team plays an FCS team.
- **No separate FCS production ranking is required.**

## Core philosophy

The historical system worked because every team's score could be explained from a small number of game-level values:

1. **Opponent Rank Score** — reward or penalty based on opponent quality.
2. **Win Score** — reward for winning.
3. **Spread Score** — reward or penalty based on scoring margin.

```text
Game Score = Opponent Rank Score + Win Score + Spread Score
```

Those game scores accumulate into the team's season score.

## Primary legacy FBS baseline

The later 2012 FBS model is the reference baseline.

For an FBS ranking pool containing `N` teams and an opponent ranked `R`:

```text
Win:
    opponent_rank_score = (N + 1) - R
    win_score = 10

Loss:
    opponent_rank_score = -R
    win_score = 0
```

For the original 124-team workbook, `(N + 1) - R` is exactly the historical `125 - R` rule.

Examples from the old 124-team scale:

```text
beat #1   = +124 rank points
beat #25  = +100 rank points
beat #124 =   +1 rank point

lose to #1   =   -1 rank point
lose to #25  =  -25 rank points
lose to #124 = -124 rank points
```

This creates a simple symmetry: elite wins matter greatly, elite losses hurt little, weak wins add little opponent credit, and bad losses hurt greatly.

## Margin of victory

Against an FBS opponent in the active ranking pool:

```text
spread_score = points_for - points_against
```

The historical FBS workbook gives an opponent outside the ranking pool zero opponent-rank points and scales the margin by one-half:

```text
spread_score = (points_for - points_against) / 2
```

Historically, this appears to be how FBS-vs-FCS games were handled.

FCS treatment is therefore part of the FBS scoring problem, not a second ranking product.

## Dynamic opponent strength

The later FBS model recursively revalues games using an opponent's current overall FBS rank.

Conceptually:

1. Rank every FBS team.
2. Score every completed eligible game using those opponent ranks.
3. Recalculate season totals.
4. Re-rank the teams.
5. Repeat until the order settles, a cycle is detected, or the iteration limit is reached.

This lets a September win become more valuable if that opponent proves strong by December.

## Conference adjustment

The older FBS workbook experimented with a conference-strength bonus.

The later workbook sets every conference bonus to **zero**. The modern project therefore begins with no conference reputation adjustment. A conference term can return only if historical out-of-sample testing shows repeatable predictive value.

## Modern research candidate

The first modern challenger keeps the same three-part idea:

```text
Game Score = Opponent Quality + Win Bonus + Adjusted Margin
```

The main research changes are:

1. Normalize opponent quality for the number of active FBS teams.
2. Test saturated margin-of-victory functions so extreme blowouts do not dominate the season score.
3. Test home/away adjustment.
4. Improve FBS-vs-FCS treatment only if doing so improves FBS postseason prediction.

Recency, conference strength, preseason carryover, efficiency statistics, Elo-like components, and ensembles are challengers that must earn their place through testing.

The modern formula is **not** promoted merely because it looks better mathematically.

## Postseason research contract

Every postseason test uses one frozen pre-postseason ranking.

For each season:

1. Use only games completed by the freeze point.
2. Calculate the final pre-bowl FBS ranking.
3. Freeze it.
4. Predict every bowl and CFP matchup from that same ranking.
5. Never feed a bowl, first-round, quarterfinal, semifinal, or championship result back into the ranking used for later predictions.

That prevents postseason result leakage.

### Primary ten-season sample

```text
2014 2015 2016 2017 2018 2019 2022 2023 2024 2025
```

- 2020 and 2021 are excluded from the primary comparable sample.
- 2021 remains a sensitivity test.
- 2025 is the locked final holdout.
- 2026 is not part of the historical backtest because the season is in progress.

## Model-selection rule

A modern rule becomes the default only if it:

- beats `legacy_fbs_2012_later` on out-of-sample postseason accuracy;
- does not materially worsen probability quality;
- improves results across seasons rather than because of one unusual year;
- does not collapse on CFP games; and
- remains easy to explain from a team's schedule.

A practical target is at least a **2 percentage-point absolute improvement** in postseason accuracy, but that is a target rather than a promised result.

## Ranking profiles

Current and planned profiles:

```text
legacy_fbs_2012_original
legacy_fbs_2012_later
modern_legacy_candidate_v1
```

The historical FCS rules remain documented for archival purposes but are not a production ranking target.

## Data direction

The modern data layer should use normalized season-specific records rather than one worksheet per team.

CollegeFootballData is the preferred primary automated source for:

- FBS teams by season;
- schedules and scores;
- home/away/neutral status;
- historical conference membership;
- classification changes;
- polls and CFP metadata;
- optional rating benchmarks.

NCAA, school, and conference records should be used to reconcile disputed or missing records.

Betting data may be used as an external benchmark but **never as an input to the core ranking formula**.

## Proposed data model

### Teams

- stable team ID
- school name
- aliases

### Team seasons

- season
- team ID
- FBS/FCS classification for that season
- conference for that season
- optional preseason seed

### Games

- season
- week
- date/time
- home team
- away team
- neutral-site flag
- classifications for both teams
- scores
- season type
- completed status

### Ranking snapshots

- model/version
- season
- cutoff timestamp
- FBS team
- score
- rank
- wins/losses

### Game scoring audit

- team
- opponent
- opponent rank/quality used
- opponent points
- win points
- margin points
- location adjustment
- recency weight if enabled
- game total

### Postseason predictions

- frozen ranking run
- postseason game
- two FBS ranks/scores
- predicted winner
- actual winner
- optional calibrated win probability
- CFP/bowl round

## Development plan

1. **Preserve the recovered FBS formulas exactly.**
2. **Build and test the recursive FBS ranking engine.**
3. **Ingest normalized historical FBS schedules/results.**
4. **Backtest the legacy FBS baseline across the ten-season research sample.**
5. **Test one transparent rule family at a time.**
6. **Use walk-forward validation and keep 2025 locked until the model is frozen.**
7. **Promote the simplest formula that materially improves FBS postseason prediction.**
8. **Add the current-season ranking interface and full game-level audit trail.**

## Documentation

- [`docs/LEGACY_FBS_2012.md`](docs/LEGACY_FBS_2012.md) — reconstruction of the two historical FBS workbooks.
- [`docs/LEGACY_FCS_2012.md`](docs/LEGACY_FCS_2012.md) — archival reference only; useful for historical cross-subdivision behavior.
- [`docs/MODERN_V1_RESEARCH.md`](docs/MODERN_V1_RESEARCH.md) — postseason-prediction research contract and acceptance rules.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phased implementation and validation plan.
- [`configs/modern_v1_search.yaml`](configs/modern_v1_search.yaml) — versioned search space for transparent formula testing.

## Guiding rule

**Rank FBS teams using the simplest transparent formula that best predicts future FBS postseason winners.**

Added complexity has to prove that it helps.