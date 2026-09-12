# NCAA BCS Ranking Calculator

A transparent, auditable ranking system for **NCAA FBS college-football teams**.

The repository keeps the historical `BCS` name because that is the name of the original project, but the modern ranking pool is the current **Football Bowl Subdivision (FBS)**. This is not an FCS ranking project.

## Primary goal

The objective is:

> **At the end of the pre-bowl portion of the FBS season, the higher-ranked FBS team should win postseason head-to-head matchups as often as possible.**

Every ranking must remain explainable game by game.

## Project status

**Version: 0.2.1 — Current-season-only weekly ranking engine**

The recovered historical workbooks remain valuable for formula reconstruction, but the live calculator now has explicit season-reset rules:

- No previous-season ranking carries forward.
- No previous-season statistics carry forward.
- No preseason AP, Coaches, CFP, power-rating, or other seed is used.
- Conferences have **zero ranking strength** and never receive bonus points.
- There is no preseason ranking.
- Week 1 creates the first ranking using only Week 1 results.
- Beginning in Week 2, games use the opponent's rank from the immediately preceding completed week of the same season.

This makes every published ranking a product of the current season only.

## Scope rule

- **Published ranking target:** FBS teams.
- **Primary validation target:** FBS bowls and College Football Playoff games.
- **FCS role:** opponent context when an FBS team plays an FCS team.
- **Conference:** metadata only; conference identity contributes no ranking points.
- **No separate FCS production ranking is required.**

## Core scoring philosophy

Every team's score is built from three game-level values:

1. **Opponent Rank Score** — reward or penalty based on current-season opponent quality.
2. **Win Score** — reward for winning.
3. **Spread Score** — reward or penalty based on scoring margin.

```text
Game Score = Opponent Rank Score + Win Score + Spread Score
```

Game scores accumulate into the team's current-season score.

## Season bootstrap

### Before Week 1

There is **no ranking**.

All FBS teams begin the season with:

```text
ranking points = 0
previous-season rank influence = 0
previous-season statistical influence = 0
conference-strength influence = 0
```

### Week 1

Because no current-season opponent rankings exist yet, Week 1 has:

```text
Opponent Rank Score = 0
```

The Week 1 ranking is therefore established from current-season game results only:

```text
FBS opponent:
    Game Score = Win Score + full scoring margin

FCS / out-of-pool opponent:
    Game Score = Win Score + scaled scoring margin
```

With the recovered legacy defaults:

```text
win bonus = 10
FBS margin scale = 1.0
FCS/out-of-pool margin scale = 0.5
```

Once Week 1 is complete, those totals create the first actual ranking of the season.

### Week 2 and later

The ranking published after the previous completed week becomes the opponent-rank input for the next week.

For an FBS ranking pool containing `N` teams and an opponent ranked `R` in the previous completed week:

```text
Win:
    opponent_rank_score = (N + 1) - R
    win_score = 10

Loss:
    opponent_rank_score = -R
    win_score = 0
```

The new week's game scores are added to the existing current-season totals, then the teams are re-ranked.

Conceptually:

```text
Week 1 games
    -> Week 1 totals
    -> Week 1 ranking

Week 2 games use Week 1 opponent ranks
    -> cumulative Week 2 totals
    -> Week 2 ranking

Week 3 games use Week 2 opponent ranks
    -> cumulative Week 3 totals
    -> Week 3 ranking

...and so on through the season.
```

Later weeks do not import information from a prior season and do not retroactively rewrite older weekly opponent ranks.

## Why the weekly structure matters

The original later FBS workbook used recursive current rankings and could revalue older games. That historical behavior remains available for legacy research, but it is no longer the live-season ranking policy.

The production approach is now **causal by week**:

- only information available in the current season is used;
- Week 1 establishes the first current-season order;
- Week 2 begins full opponent-rank scoring;
- each later week uses the immediately preceding current-season ranking;
- no recursive same-week cycle is required.

This also removes the early-season two-ordering cycle observed when the 2026 Week 1 data was run through the recursive engine.

## Margin of victory

Against an FBS opponent in the active ranking pool:

```text
spread_score = points_for - points_against
```

Against an opponent outside the active FBS ranking pool:

```text
spread_score = (points_for - points_against) / 2
```

The one-half treatment is the recovered historical default for FBS-vs-FCS/out-of-pool games. It remains testable in the modern research model because FCS treatment is part of evaluating an FBS team's schedule.

## Conference policy

Conference identity may be stored for display and historical records, but it has **no mathematical strength value**.

The calculator must never award or subtract points because a team belongs to the SEC, Big Ten, Big 12, ACC, Mountain West, Conference USA, or any other conference.

Conference strength is not a research parameter in the production model.

## Previous-season policy

Previous-season information is not an input to the live ranking.

The calculator must not use:

- previous-season final rank;
- previous-season wins/losses;
- previous-season scoring margin;
- previous-season strength of schedule;
- preseason polls derived from the previous season;
- external preseason power ratings.

Historical seasons may be used to **test and tune the formula itself**, but never to seed a team's ranking in a new season.

## Historical FBS baseline

The later 2012 FBS model remains preserved as a historical benchmark.

For the original 124-team workbook:

```text
beat #1   = +124 rank points
beat #25  = +100 rank points
beat #124 =   +1 rank point

lose to #1   =   -1 rank point
lose to #25  =  -25 rank points
lose to #124 = -124 rank points
```

The modern generalized form uses `(N + 1) - R` so the rule automatically follows the current FBS team count.

## Modern research candidate

The research formula still keeps the same three-part structure:

```text
Game Score = Opponent Quality + Win Bonus + Adjusted Margin
```

Parameters such as margin saturation, home-field adjustment, FCS treatment, recency, and opponent-strength weighting may be tested historically.

The following are **not** allowed research dimensions for the live ranking:

```text
conference strength
previous-season carryover
preseason ranking seeds
```

Historical testing may improve the formula, but every season must still begin from zero.

## Postseason research contract

Every postseason test uses one frozen pre-postseason ranking.

For each season:

1. Start the season from zero.
2. Build Week 1 from Week 1 results only.
3. Build every later week from the preceding current-season ranking.
4. Freeze the final pre-postseason FBS ranking.
5. Predict every bowl and CFP matchup from that same frozen ranking.
6. Never feed a postseason result back into the ranking used to predict later postseason games.

## Primary ten-season research sample

```text
2014 2015 2016 2017 2018 2019 2022 2023 2024 2025
```

- 2020 and 2021 are excluded from the primary comparable sample.
- 2021 remains a sensitivity test.
- 2025 is the locked final holdout.
- 2026 is the live season, not part of the historical tuning sample.

## Ranking engines

The repository preserves two different purposes:

```text
RecursiveRankingEngine
    Historical parity/research for the recovered legacy FBS behavior.

WeeklySeasonRankingEngine
    Production current-season ranking path.
```

The live ranking should use `WeeklySeasonRankingEngine`.

## Ranking profiles

```text
legacy_fbs_2012_original
legacy_fbs_2012_later
modern_legacy_candidate_v1
```

The historical FCS rules remain archival reference material only.

## Data model

### Teams

- stable team ID
- school name
- aliases

### Team seasons

- season
- team ID
- FBS/FCS classification for that season
- conference for display/history only

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
- completed week
- FBS team
- score
- rank
- wins/losses

### Game scoring audit

- team
- opponent
- week
- prior-week opponent rank used, or `none` for Week 1/out-of-pool
- opponent points
- win points
- margin points
- game total
- cumulative season total

## Development plan

1. **Preserve the recovered FBS formulas for historical comparison.**
2. **Use the season-only weekly engine for live rankings.**
3. **Ingest normalized historical and current FBS schedules/results.**
4. **Backtest the season-only system across the ten-season research sample.**
5. **Test one transparent scoring change at a time.**
6. **Keep conference strength and previous-season carryover permanently at zero.**
7. **Use walk-forward validation and keep 2025 locked until the model is frozen.**
8. **Promote the simplest scoring formula that materially improves FBS postseason prediction.**
9. **Add the current-season ranking interface and full game-level audit trail.**

## Documentation

- [`docs/CURRENT_SEASON_RULES.md`](docs/CURRENT_SEASON_RULES.md) — authoritative live-ranking season-reset and weekly-flow rules.
- [`docs/LEGACY_FBS_2012.md`](docs/LEGACY_FBS_2012.md) — reconstruction of the two historical FBS workbooks.
- [`docs/LEGACY_FCS_2012.md`](docs/LEGACY_FCS_2012.md) — archival cross-subdivision reference only.
- [`docs/MODERN_V1_RESEARCH.md`](docs/MODERN_V1_RESEARCH.md) — postseason-prediction research contract.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — implementation and validation plan.
- [`configs/modern_v1_search.yaml`](configs/modern_v1_search.yaml) — versioned scoring search space with season-reset rules locked.

## Guiding rule

**Rank FBS teams only on what they have earned during the current season.**

Historical data is for improving the formula, not for giving a team a head start in a new season.
