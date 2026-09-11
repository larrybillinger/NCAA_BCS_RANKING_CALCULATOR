# NCAA BCS Ranking Calculator

A transparent college-football ranking calculator based on the spreadsheet system I used previously.

The goal is not to make the formula complicated. The goal is to make a small number of understandable scoring rules work well across an entire season, while keeping every team's ranking auditable game by game.

## Project status

**Version: 0.1.0 — Legacy model reconstruction**

The first reference workbook reviewed is `NCAA FCS Rankings.xlsx`, built around the 2012 FCS season. Additional historical workbooks will be reviewed before the legacy scoring rules are frozen.

The current repository is intentionally starting with documentation rather than hard-coding the 2012 spreadsheet structure into a new application.

## What the old system did well

The workbook used three simple components for each game:

1. **Opponent Rank Score** — extra credit for beating a highly ranked opponent.
2. **Win Score** — a flat reward for winning.
3. **Spread Score** — reward or penalty based on scoring margin.

Those game values accumulated through the season. Each week's team rankings then became the opponent rankings used by the following week. That gave the system a simple feedback loop: beating a team that had proven itself became increasingly valuable.

### Legacy opponent-rank bonus

The first workbook uses the following table when the team wins:

| Opponent Rank | Points |
|---:|---:|
| 1–5 | 30 |
| 6–10 | 24 |
| 11–15 | 18 |
| 16–20 | 12 |
| 21–30 | 6 |
| 31–40 | 3 |
| 41–50 | 2 |
| 51+ | 1 |
| Unranked / unavailable | 0 |

A loss receives no opponent-rank bonus.

### Legacy win bonus

- Win: **10 points**
- Loss: **0 points**

### Legacy scoring margin

The basic spreadsheet formula uses the score differential:

`points scored - points allowed`

The workbook also contains a special case that divides the margin by two when the opponent-ranking value is text/unavailable. That behavior needs to be checked against the other historical workbooks before it becomes a permanent rule in the new calculator.

### Weekly ranking loop

The workbook is recursive by week:

- Week 1 looks at a preseason/previous-season ranking.
- Week 2 uses the Week 1 ranking of each opponent.
- Week 3 uses the Week 2 ranking.
- The pattern continues through the season.

The team's season score is cumulative rather than an average of individual games.

## What will change in the new calculator

The scoring philosophy can stay simple while the implementation becomes much cleaner.

The old workbook has one worksheet per team, repeated formulas, manually arranged weekly ranking tables, hard-coded 2012 dates, and team/conference information that is now obsolete. The new version should instead use normalized game and team data and calculate every team from the same ranking engine.

The new calculator should:

- Support current FBS and/or FCS teams without hard-coded conference membership.
- Keep historical seasons reproducible even when teams change conferences or subdivisions.
- Import schedules/results from a replaceable data-source adapter.
- Produce weekly rankings automatically.
- Preserve every scoring component for auditing.
- Allow the legacy formula to be run exactly before experimental changes are introduced.
- Make preseason seeding configurable.
- Avoid one-file-per-team or one-sheet-per-team logic.
- Keep the ranking formula understandable enough to calculate by hand.

## Proposed data model

The calculator will eventually work from records like these instead of hundreds of worksheet formulas:

### Teams

- season
- team ID
- team name
- subdivision
- conference

### Games

- season
- week
- date
- home team
- away team
- neutral-site flag
- home score
- away score
- game status

### Weekly rankings

- season
- week
- team
- wins
- losses
- cumulative points
- rank

### Game scoring audit

- team
- opponent
- opponent rank used
- rank-score points
- win-score points
- spread points
- game total
- cumulative total

## Development plan

1. **Reverse-engineer the historical workbooks.** Document every rule and any differences between versions.
2. **Build a legacy-compatible calculation engine.** It should reproduce known historical worksheet results from raw game data.
3. **Replace the spreadsheet data plumbing.** Current schedules, scores, team membership, and conference data should be imported rather than maintained manually.
4. **Generate weekly rankings automatically.** Ranking tables should never require manual sorting or copied formulas.
5. **Validate the model.** Compare historical output with the original workbooks and national ranking systems.
6. **Add a usable interface.** Once the engine is correct, expose rankings, team breakdowns, and season history through a simple UI.

## Documentation

- [`docs/LEGACY_FCS_2012.md`](docs/LEGACY_FCS_2012.md) — reverse-engineering notes from the first uploaded workbook.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phased plan for turning the spreadsheet model into a maintainable ranking calculator.

## Guiding rule

**Do not make the ranking formula more complicated unless testing shows that the added complexity materially improves the rankings.**

The old system worked because a person could understand why a team gained or lost points. The new version should keep that strength.