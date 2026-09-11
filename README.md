# NCAA BCS Ranking Calculator

A transparent college-football ranking calculator based on the spreadsheet system I used previously.

The goal is not to make the formula complicated. The goal is to make a small number of understandable scoring rules work well across an entire season, while keeping every team's ranking auditable game by game.

## Project status

**Version: 0.1.1 — Legacy model reconstruction**

Three historical workbooks have now been reviewed:

- `NCAA FCS Rankings.xlsx`
- `NCAA FBS Rankings 2011.xlsx`
- `NCAA FBS Rankings.xlsx`

The FBS workbooks are actually built around the 2012 season. The `2011 Season` data serves as an initial ranking seed/reference.

The historical files show that the FCS and FBS calculators were related but not identical. The project will therefore preserve the recovered rules as separate ranking profiles before choosing a modern default.

## Core philosophy

The old system worked because every team's score could be explained from a small number of game-level values:

1. **Opponent Rank Score** — reward or penalty based on opponent quality.
2. **Win Score** — a flat reward for winning.
3. **Spread Score** — reward or penalty based on scoring margin.

The central relationship is:

```text
Game Score = Opponent Rank Score + Win Score + Spread Score
```

Those game scores accumulate into the team's season score.

## Recovered FCS model

The 2012 FCS workbook uses bracketed opponent-rank bonuses on wins:

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

The FCS workbook also uses historical weekly rankings: each new week values opponents using the ranking snapshot from the previous completed ranking period.

## Recovered FBS model

The FBS workbooks reveal a more granular system.

For a 124-team FBS ranking, the later version uses:

```text
Win against opponent ranked R:
    opponent_rank_score = 125 - R

Loss to opponent ranked R:
    opponent_rank_score = -R
```

Examples:

```text
beat #1   = +124 rank points
beat #25  = +100 rank points
beat #124 =   +1 rank point

lose to #1   =   -1 rank point
lose to #25  =  -25 rank points
lose to #124 = -124 rank points
```

That creates a simple symmetry: elite wins matter greatly, elite losses hurt little, weak wins are worth little, and bad losses hurt greatly.

The older FBS version used the same win scale but gave zero rank points on losses.

### Win bonus

Both FBS and FCS models use:

- Win: **+10**
- Loss: **0**

### Scoring margin

Against an opponent with a usable rank:

```text
spread_score = points_for - points_against
```

When the opponent is outside the active ranking pool, the historical spreadsheets halve the margin:

```text
spread_score = (points_for - points_against) / 2
```

In the FBS workbook this appears to be the treatment for FCS opponents.

There is no recovered margin-of-victory cap.

## Dynamic opponent strength

The FBS model contains an especially useful idea.

Instead of permanently freezing a game's value to the opponent's rank on game day, the FBS team sheets use the opponent's **current overall rank**. That means an earlier win can become more valuable later if the opponent proves to be strong.

Conceptually:

1. Rank every team.
2. Score every game using those opponent ranks.
3. Recalculate season totals.
4. Re-rank the teams.
5. Repeat until the ordering settles or the configured iteration limit is reached.

The old spreadsheet required manual ranking/sorting steps. The new calculator can perform this automatically.

## Conference-strength experiment

The older FBS workbook added a conference-strength bonus based on the average rank of each conference's opponents.

The later FBS workbook sets every conference bonus to **zero**, effectively disabling the feature while keeping the formulas in place.

That later simplification is important. It suggests the ranking system evolved toward letting actual game results and opponent strength do the work rather than adding a separate conference reputation adjustment.

## Historical data sources

The FBS files preserve an Excel web connection to the Sports Illustrated AP poll:

```text
http://sportsillustrated.cnn.com/football/ncaa/polls/ap
```

No StatSheet URL or live StatSheet connection survives in the saved XLSX files. The raw schedule/result tables are present, however, and StatSheet may still have been the source used to populate them originally.

The modern project will not depend on a single provider. Schedule/result ingestion should use a replaceable data-source adapter.

## What will change in the new calculator

The scoring philosophy can stay simple while the implementation becomes much cleaner.

The historical spreadsheets use one worksheet per team, repeated formulas, manually maintained ranking tables, fixed dates, and obsolete conference membership. The new version should instead use normalized game/team data and calculate every team through one ranking engine.

The new calculator should:

- Support current FBS and FCS teams without hard-coded conference membership.
- Keep historical seasons reproducible even when teams change conferences or subdivisions.
- Import schedules/results through replaceable data-source adapters.
- Produce weekly and final rankings automatically.
- Preserve every scoring component for auditing.
- Support multiple legacy ranking profiles.
- Make preseason seeding configurable.
- Automate recursive/dynamic rank recalculation.
- Avoid one-sheet-per-team logic.
- Keep the ranking formula understandable enough to calculate by hand.

## Proposed ranking profiles

The first implementation should keep the recovered systems separate:

```text
legacy_fcs_2012
legacy_fbs_2012_original
legacy_fbs_2012_later
```

The later FBS model is currently the strongest candidate for the default legacy profile because it rewards strong wins, distinguishes good and bad losses, and removes the separate conference bonus while remaining extremely simple.

## Proposed data model

The calculator will eventually work from normalized records instead of hundreds of worksheet formulas.

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
- opponent-rank points
- win points
- spread points
- game total
- cumulative total

## Development plan

1. **Finish reverse-engineering the historical workbooks.** Preserve every confirmed rule and variant.
2. **Build legacy-compatible calculation profiles.** Reproduce historical results from normalized game data.
3. **Automate iterative FBS recalculation.** Replace manual ranking/sorting with a deterministic ranking loop.
4. **Replace the spreadsheet data plumbing.** Import current schedules, scores, teams, and conferences from a replaceable provider.
5. **Generate weekly and final rankings automatically.**
6. **Validate the models.** Compare historical output with the original workbooks and major national ranking systems.
7. **Choose a modern default formula.** Only change legacy rules when testing shows a clear improvement.
8. **Add a usable interface.** Expose rankings, team breakdowns, game-level scoring, and season history.

## Documentation

- [`docs/LEGACY_FCS_2012.md`](docs/LEGACY_FCS_2012.md) — reverse-engineering notes from the FCS workbook.
- [`docs/LEGACY_FBS_2012.md`](docs/LEGACY_FBS_2012.md) — comparison and reconstruction of both FBS workbooks.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phased plan for turning the spreadsheet model into a maintainable ranking calculator.

## Guiding rule

**Do not make the ranking formula more complicated unless testing shows that the added complexity materially improves the rankings.**

The old system's strongest feature was transparency. The new version should keep that strength.