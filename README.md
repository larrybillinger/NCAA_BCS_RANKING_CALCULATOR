# NCAA BCS Ranking Calculator

A transparent, auditable ranking system for **all NCAA Division I college-football teams**.

The repository keeps the historical `BCS` name because that is the name of the original project, but the modern production ranking pool now combines **FBS and FCS in one Division I ranking**.

## Primary goal

The main objective is not to imitate the AP Poll, Coaches Poll, CFP committee, betting markets, or another power rating.

The objective is to build a simple, season-only ranking in which every Division I team's position can be explained game by game and tested against postseason results.

## Project status

**Version: 0.3.0 — Unified Division I ranking pool**

The live production rules now use one ranking pool containing both FBS and FCS teams.

### Scope rule

- **Published ranking target:** all NCAA Division I football teams.
- **FBS and FCS are scored identically.**
- **Conference affiliation has no ranking strength.**
- **No previous-season ranking or statistics carry into a new season.**
- **There is no preseason ranking.**
- **Week 1 creates the first current-season ranking.**
- **Week 2 and later use the immediately preceding completed week's ranking for opponent-rank points.**

Teams below Division I remain outside the active ranking pool.

## Core philosophy

Every team's score is built from a small number of game-level values:

1. **Opponent Rank Score** — beginning in Week 2, reward or penalty based on the opponent's prior-week Division I rank.
2. **Win Score** — reward for winning.
3. **Spread Score** — reward or penalty based on scoring margin.

```text
Game Score = Opponent Rank Score + Win Score + Spread Score
```

Those game scores accumulate into the team's season score.

## Season reset

Every season starts completely from zero.

The live calculator does **not** use:

- previous-season rankings;
- previous-season win/loss records;
- previous-season statistics;
- preseason polls;
- preseason power ratings;
- conference-strength bonuses or penalties.

There is no published preseason ranking.

## Week 1

Week 1 establishes the first ranking of the season.

Because there is no prior current-season ranking yet:

```text
Opponent Rank Score = 0
```

for every Division I opponent.

For any FBS-vs-FBS, FBS-vs-FCS, FCS-vs-FBS, or FCS-vs-FCS game:

```text
Win Score = 10 on a win
Spread Score = points_for - points_against
```

Subdivision membership does not alter the score.

Example:

```text
Kansas State 71, Nicholls 3
Opponent Rank Score = 0
Win Score           = 10
Spread Score        = 68
Game Score          = 78
```

Nicholls is FCS, but FCS is now part of the same active Division I ranking pool, so the margin is not halved.

## Week 2 and later

Beginning in Week 2, games use the opponent's ranking from the immediately preceding completed week of the same season.

For a Division I ranking pool containing `N` teams and an opponent ranked `R`:

```text
Win:
    opponent_rank_score = (N + 1) - R
    win_score = 10

Loss:
    opponent_rank_score = -R
    win_score = 0

spread_score = points_for - points_against
```

FBS and FCS use exactly the same formula.

Earlier games are not retroactively rescored when an opponent moves later in the season.

## Outside-Division-I opponents

Division II, Division III, NAIA, and other opponents outside the active Division I ranking pool receive no opponent-rank points.

The current legacy-derived profile may use a reduced margin scale for true out-of-pool games. That distinction is based on whether the opponent is in NCAA Division I, not whether the opponent is FBS or FCS.

## Conference rule

Conference membership is metadata only.

No SEC, Big Ten, Big 12, ACC, Sun Belt, Missouri Valley Football Conference, Big Sky, CAA, or other conference receives any ranking bonus, penalty, multiplier, inherited prestige, or strength adjustment.

## Why the formula still resembles the old FBS workbook

The original FBS spreadsheet supplied the most useful recovered opponent-rank formula:

```text
Win over rank R  = (N + 1) - R
Loss to rank R   = -R
Win bonus        = 10
```

Version 0.3.0 keeps that transparent math but applies it to the complete active Division I ranking pool rather than FBS alone.

The old FCS workbook remains historical evidence, not a separate production scoring system.

## Weekly ranking behavior

The production engine is `WeeklySeasonRankingEngine`.

Conceptually:

1. Start the new season with no rankings.
2. Score Week 1 only from current-season results, with zero opponent-rank points.
3. Publish the Week 1 Division I ranking.
4. Score Week 2 games using Week 1 opponent ranks.
5. Publish Week 2.
6. Continue week by week through the season.

The live ranking does not use same-week recursive recalculation and does not import a previous-season seed.

## Historical research

The repository still preserves historical FBS and FCS workbook reconstructions so the old formulas remain reproducible and testable.

The legacy recursive FBS engine is retained for historical parity research only. It is not the live current-season ranking method.

## Postseason research direction

The ranking can be evaluated against postseason head-to-head results while preserving the no-leakage rule: a postseason evaluation must use a ranking frozen before those postseason games are played.

Historical FBS bowl/CFP prediction remains an important benchmark because the original project's purpose was BCS/FBS ranking. With the unified Division I pool, future research can also evaluate FCS playoff prediction without changing the live scoring rules.

## Ranking profiles

Current profiles include:

```text
legacy_fbs_2012_original        # historical reproduction
legacy_fbs_2012_later           # historical formula source / current scoring base
modern_legacy_candidate_v1      # research candidate family
current_season_v1               # production weekly Division I rules
division_i_current_v1           # clearly named production alias
```

## Data model

### Teams

- stable team ID
- school name
- aliases
- Division I subdivision for that season (`FBS` or `FCS`)

### Team seasons

- season
- team ID
- Division I classification
- FBS/FCS subdivision
- conference for display/metadata only

### Games

- season
- week
- date/time
- home team
- away team
- neutral-site flag
- classification for both teams
- scores
- season type
- completed status

### Ranking snapshots

- model/version
- season
- week/cutoff
- Division I team
- score
- rank
- wins/losses

### Game scoring audit

- team
- opponent
- prior-week opponent rank used
- opponent-rank points
- win points
- margin points
- game total

## Development plan

1. Preserve the recovered historical formulas for reproducibility.
2. Maintain the live week-by-week, season-only Division I engine.
3. Ingest complete FBS and FCS team/schedule/result data by season.
4. Publish Week 1 only after the first current-season games establish the order.
5. Use prior-week current-season rankings beginning with Week 2.
6. Keep conference strength and previous-season carryover permanently out of production scoring.
7. Backtest transparent scoring changes before promoting them.
8. Keep every ranking auditable down to the individual game.

## Documentation

- [`docs/DIVISION_I_SCOPE.md`](docs/DIVISION_I_SCOPE.md) — authoritative FBS + FCS production scope.
- [`docs/CURRENT_SEASON_RULES.md`](docs/CURRENT_SEASON_RULES.md) — weekly season-only ranking rules.
- [`docs/SCORING_EXAMPLES.md`](docs/SCORING_EXAMPLES.md) — worked scoring examples.
- [`docs/LEGACY_FBS_2012.md`](docs/LEGACY_FBS_2012.md) — reconstruction of the historical FBS workbooks.
- [`docs/LEGACY_FCS_2012.md`](docs/LEGACY_FCS_2012.md) — reconstruction of the historical FCS workbook.
- [`docs/MODERN_V1_RESEARCH.md`](docs/MODERN_V1_RESEARCH.md) — model-research contract.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — implementation and validation plan.
- [`configs/current_season_v1.yaml`](configs/current_season_v1.yaml) — authoritative production configuration.
- [`configs/division_i_current_v1.yaml`](configs/division_i_current_v1.yaml) — scope-first production alias.

## Guiding rule

**If a team is NCAA Division I football, rank it in the same pool and score it by the same rules.**

Added complexity has to prove that it helps.