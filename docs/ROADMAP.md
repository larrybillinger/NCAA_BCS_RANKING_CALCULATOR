# NCAA BCS Ranking Calculator Roadmap

## v0.1 — Recover the old system

Goal: understand the historical spreadsheets before replacing them.

- [x] Review the first FCS workbook.
- [x] Document the rank-score table.
- [x] Document win-score behavior.
- [x] Document margin/scoring-spread behavior.
- [x] Document the weekly recursive ranking loop.
- [x] Identify structural problems in the old workbook.
- [ ] Review the remaining historical XLSX files.
- [ ] Compare scoring rules across workbook versions.
- [ ] Write one final legacy-scoring specification.

## v0.2 — Build a parity engine

Goal: reproduce the historical formula without spreadsheet-specific logic.

The first calculation engine should accept normalized game data and produce:

- Per-game score components.
- Running team records.
- Cumulative ranking points.
- Weekly rankings.
- The opponent rank actually used for each game.
- A full audit trail showing how every point was earned.

Acceptance target:

> Given the same game results, seeds, and rule settings, the engine should reproduce selected historical workbook results.

This version should not contain experimental improvements. It is the control model.

## v0.3 — Modernize the data layer

Goal: remove 2012-specific team, conference, schedule, and worksheet assumptions.

Create a provider-neutral import layer for:

- Teams.
- Current subdivision.
- Conference membership by season.
- Schedules.
- Completed scores.
- Neutral-site status.
- Postseason games.

Important rule: historical conference membership must belong to the season record. A team changing conferences in a later year must not rewrite its earlier seasons.

## v0.4 — Current-season rankings

Goal: calculate an entire current season automatically.

Outputs:

- Overall ranking table.
- Week-by-week rankings.
- Team detail page/table.
- Game-by-game point breakdown.
- Movement from the prior week.
- Strength-of-victory information.
- Record and conference information.

The ranking engine should remain independent of the display layer.

## v0.5 — Validation and tuning

Goal: determine whether any simple changes improve the historical results.

The legacy formula should remain available as a baseline while testing possible changes such as:

- Preseason seed handling.
- Treatment of opponents outside the ranking pool.
- FBS/FCS cross-subdivision games.
- Margin caps.
- Home/away/neutral adjustments.
- Handling of teams with unequal games played.

No change should become the default because it merely sounds better. It should improve results across multiple seasons and remain easy to explain.

## v0.6 — User interface

Goal: make the rankings easy to browse without hiding the math.

Possible views:

- Current Top 25 / Top 50 / full ranking.
- Team page with every game's point calculation.
- Weekly movement chart.
- Historical season selector.
- Side-by-side comparison with AP, Coaches, CFP, or other applicable rankings.
- Methodology page generated directly from the active rule configuration.

## Long-term principles

### Keep the scoring engine deterministic

The same inputs and rule configuration must always produce the same rankings.

### Keep data ingestion replaceable

A schedule/results provider may disappear or change its API. The ranking engine should not care where a normalized game record came from.

### Keep every point explainable

A user should be able to click or inspect a team and answer:

> Why does this team have this many points?

without reading source code.

### Preserve historical reproducibility

Rule changes should be versioned. A ranking generated with one scoring version should remain reproducible later.

### Prefer simple improvements

A small rule that consistently improves ranking quality is preferable to a complicated formula that is difficult to audit.