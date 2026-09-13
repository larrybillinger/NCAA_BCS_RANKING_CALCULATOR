# NCAA BCS Ranking Calculator Roadmap

## Project scope

The production ranking now covers **all NCAA Division I football teams in one pool**.

That means:

- FBS and FCS teams are ranked together.
- FBS and FCS use the same scoring formula.
- Conference affiliation has no ranking strength.
- No previous-season rankings or statistics carry into a new season.
- No preseason ranking is published.
- Week 1 establishes the first current-season order.
- Week 2 and later use the immediately preceding completed week's current-season ranking.

Teams below Division I remain outside the active ranking pool.

## v0.1 — Recover the old system

Goal: understand the historical spreadsheets before replacing them.

- [x] Review the historical FCS workbook.
- [x] Review both historical FBS workbooks.
- [x] Recover the FBS win-rank formula.
- [x] Recover the later FBS loss penalty.
- [x] Recover win-score behavior.
- [x] Recover margin behavior.
- [x] Identify the old recursive FBS opponent-rank loop.
- [x] Recover the old out-of-pool half-margin treatment.
- [x] Confirm that the later FBS workbook disabled conference bonuses.

## v0.2 — Executable historical parity + weekly season engine

Goal: reproduce the historical formula while separating historical behavior from the live production system.

- [x] Implement historical FBS scoring.
- [x] Implement recursive historical parity engine.
- [x] Add cycle detection.
- [x] Add deterministic tiebreaking.
- [x] Add `WeeklySeasonRankingEngine` for live current-season rankings.
- [x] Ban preseason/previous-season seeds from the weekly engine.
- [x] Make Week 1 establish the first current-season ranking.

## v0.3 — Unified NCAA Division I ranking pool

Goal: rank FBS and FCS together with no subdivision scoring distinction.

- [x] Put FBS and FCS in the same active ranking pool.
- [x] Remove the old FCS half-margin rule for Division I games.
- [x] Give all Division I games full margin value.
- [x] Keep Week 1 opponent-rank points at zero.
- [x] Use prior-week current-season Division I ranks beginning in Week 2.
- [x] Keep conference strength permanently at zero.
- [x] Keep previous-season/preseason carryover permanently disabled.
- [x] Add tests proving FBS and FCS score identically.

## v0.4 — Complete Division I data layer

Goal: ingest authoritative season-specific FBS and FCS data.

Create a provider-neutral import layer for:

- all Division I teams by season;
- FBS/FCS subdivision by season;
- conference membership for metadata only;
- schedules and completed scores;
- home/away/neutral status;
- conference championships;
- FCS playoffs;
- bowls and CFP games;
- stable game/team IDs;
- classification changes between seasons.

Important rules:

- FBS and FCS membership must be season-specific.
- Division I team count `N` must be season-specific.
- FBS/FCS subdivision cannot alter the production score.
- Lower-division opponents remain outside the ranked pool.
- Raw provider data should be cached before normalization.

## v0.5 — Historical baseline backtest

Goal: measure how the unified weekly formula performs historically.

Primary FBS postseason sample remains:

```text
2014 2015 2016 2017 2018 2019 2022 2023 2024 2025
```

The historical ranking calculation itself should include every available Division I FBS and FCS team for those seasons.

Primary FBS evaluation:

```text
Postseason Accuracy = higher-ranked team wins / FBS postseason games predicted
```

Future secondary evaluation:

- FCS playoff accuracy;
- accuracy by rank gap;
- CFP-only accuracy;
- bowl accuracy;
- season-by-season stability;
- Brier score and calibration if probabilities are added.

## v0.6 — Transparent rule research

Goal: improve predictive usefulness without violating the production philosophy.

Rules that are fixed and are **not** research knobs:

- one Division I FBS+FCS ranking pool;
- no conference strength;
- no previous-season carryover;
- no preseason seed;
- Week 1 starts from current-season results only;
- Week 2+ uses prior-week current-season rank;
- no same-week recursive production recalculation.

Variables that may be tested:

1. margin transformation or cap;
2. home-field adjustment;
3. win bonus size;
4. opponent-rank weighting;
5. loss-penalty weighting;
6. treatment of opponents below Division I;
7. recency, only if it remains transparent and improves out-of-sample prediction.

## v0.7 — Current-season publication

Goal: automatically publish the live NCAA Division I ranking.

Outputs:

- overall Division I ranking table;
- Top 25 / Top 50 / full ranking;
- FBS/FCS subdivision column for information only;
- week-by-week movement;
- team detail page/table;
- game-by-game point breakdown;
- prior-week opponent rank used for each game;
- record and conference metadata.

## v0.8 — User interface

Goal: make the rankings easy to browse without hiding the math.

Possible views:

- current Top 25 / Top 50 / full Division I ranking;
- filter by FBS, FCS, conference, or team while retaining the single shared ranking;
- team page with every game's calculation;
- weekly movement chart;
- historical season selector;
- comparison with AP, Coaches, CFP, and FCS polls as external benchmarks only;
- postseason prediction history.

## Long-term principles

### One Division I field

If a school plays NCAA Division I football, it belongs in the same ranking pool.

### Same math for FBS and FCS

Subdivision status does not change opponent-rank points, win points, or margin points.

### Current season only

A team must earn every point again each season.

### Conferences are metadata

Conference reputation never contributes points.

### Keep the engine deterministic

The same games and same rules must always produce the same ranking.

### Keep every point explainable

A user should be able to inspect any team and understand exactly why it is ranked where it is.

### Preserve historical reproducibility

Historical workbook behavior stays available as a separate legacy profile even when production rules change.

### Prefer simple improvements

A small transparent improvement that survives out-of-sample testing is better than a complicated model that cannot be audited.
