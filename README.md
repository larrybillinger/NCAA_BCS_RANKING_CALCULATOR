# NCAA BCS Ranking Calculator

A transparent, auditable ranking system for **all NCAA Division I college-football teams**.

The repository keeps the historical `BCS` name because that is the name of the original project, but the modern production ranking pool combines **FBS and FCS in one Division I ranking**.

## Primary goal

The objective is to build a simple, season-only ranking in which every Division I team's position can be explained game by game and tested against postseason results.

## Project status

**Version: 0.3.1 — Unified Division I pool with FCS scoring modifier**

### Scope rule

- **Published ranking target:** all NCAA Division I football teams.
- **FBS and FCS share one ranking pool and one opponent-rank scale.**
- **FBS teams always receive 100% of their normal Division I game score.**
- **FCS-vs-FCS game scores are multiplied by 0.5.**
- **An FCS loss to an FBS team is multiplied by 0.5.**
- **An FCS win over an FBS team receives full credit.**
- **Conference affiliation has no ranking strength.**
- **No previous-season ranking or statistics carry into a new season.**
- **There is no preseason ranking.**
- **Week 1 creates the first current-season ranking.**
- **Week 2 and later use the immediately preceding completed week's ranking for opponent-rank points.**

Teams below Division I remain outside the active ranking pool.

## Core formula

Every team's unscaled score is built from three game-level values:

1. **Opponent Rank Score** — beginning in Week 2, reward or penalty based on the opponent's prior-week Division I rank.
2. **Win Score** — reward for winning.
3. **Spread Score** — reward or penalty based on scoring margin.

```text
Normal Game Score = Opponent Rank Score + Win Score + Spread Score
```

For a ranking pool containing `N` teams and an opponent ranked `R`:

```text
Win:
    opponent_rank_score = (N + 1) - R
    win_score = 10

Loss:
    opponent_rank_score = -R
    win_score = 0

spread_score = points_for - points_against
```

## FCS scoring modifier

The live production model is `division_i_weighted_v1`.

After the normal game score is calculated, the FCS team's components are scaled as follows:

```text
FBS team vs any Division I opponent = 100%
FCS team vs FCS opponent            = 50%
FCS team loses to FBS opponent      = 50%
FCS team beats FBS opponent         = 100%
```

The multiplier applies to opponent-rank points, win points, and margin points so the audit trail remains transparent.

An FCS upset over an FBS team therefore receives full credit, while routine FCS-vs-FCS results have half the ranking impact.

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

### Kansas State vs Nicholls

Kansas State 71, Nicholls 3:

Kansas State is FBS, so it receives the full score:

```text
Opponent Rank Score = 0
Win Score           = 10
Spread Score        = 68
Kansas State Score  = 78
```

Nicholls is FCS and lost to an FBS team, so its negative score is halved:

```text
Normal Score        = -68
FCS Multiplier      = 0.5
Nicholls Score      = -34
```

### FCS vs FCS

If an FCS team wins 30-10 over another FCS team in Week 1:

```text
Normal Score        = 10 + 20 = 30
FCS Multiplier      = 0.5
Final Score         = 15
```

## Week 2 and later

Beginning in Week 2, games use the opponent's ranking from the immediately preceding completed week of the same season.

FBS and FCS opponents occupy the same ranking scale. Beating the #25 FCS team and beating the #25 FBS team therefore start with the same base opponent-rank value. The FCS scoring modifier applies only to the ranked team's own game score when the ranked team is FCS.

Earlier games are not retroactively rescored when an opponent moves later in the season.

## Outside-Division-I opponents

Division II, Division III, NAIA, and other opponents outside the active Division I ranking pool receive no opponent-rank points.

The current profile may use a reduced margin scale for true out-of-pool games. That treatment is separate from the FCS scoring modifier.

## Conference rule

Conference membership is metadata only.

No SEC, Big Ten, Big 12, ACC, Sun Belt, Missouri Valley Football Conference, Big Sky, CAA, or other conference receives any ranking bonus, penalty, multiplier, inherited prestige, or strength adjustment.

## Weekly ranking behavior

The production engine is `WeeklySeasonRankingEngine`.

Conceptually:

1. Start the new season with no rankings.
2. Score Week 1 only from current-season results, with zero opponent-rank points.
3. Apply the FCS modifier where required.
4. Publish the Week 1 Division I ranking.
5. Score Week 2 games using Week 1 opponent ranks.
6. Continue week by week through the season.

The live ranking does not use same-week recursive recalculation and does not import a previous-season seed.

## Historical research

The repository preserves historical FBS and FCS workbook reconstructions so the old formulas remain reproducible and testable.

The historical `LegacyFBSModel` remains unchanged. The FCS scoring modifier lives only in the production `DivisionIWeightedModel`, which prevents current rules from rewriting the recovered legacy baseline.

## Ranking profiles

Current profiles include:

```text
legacy_fbs_2012_original        # historical reproduction
legacy_fbs_2012_later           # historical formula source
modern_legacy_candidate_v1      # research candidate family
division_i_weighted_v1          # production scoring model
current_season_v1               # production weekly rules
division_i_current_v1           # scope-first production alias
```

## Data model

### Teams

- stable team ID
- school name
- aliases
- Division I subdivision for that season (`FBS` or `FCS`)

### Games

- season
- week
- date/time
- home team
- away team
- neutral-site flag
- team subdivision
- opponent subdivision
- scores
- season type
- completed status

### Ranking snapshots

- model/version
- season
- week/cutoff
- Division I team
- subdivision
- score
- rank
- wins/losses

### Game scoring audit

- team
- opponent
- team subdivision
- opponent subdivision
- prior-week opponent rank used
- opponent-rank points
- win points
- margin points
- FCS multiplier
- game total

## Documentation

- [`docs/DIVISION_I_SCOPE.md`](docs/DIVISION_I_SCOPE.md) — authoritative FBS + FCS production scope.
- [`docs/CURRENT_SEASON_RULES.md`](docs/CURRENT_SEASON_RULES.md) — weekly season-only ranking rules.
- [`docs/SCORING_EXAMPLES.md`](docs/SCORING_EXAMPLES.md) — worked scoring examples.
- [`docs/LEGACY_FBS_2012.md`](docs/LEGACY_FBS_2012.md) — reconstruction of the historical FBS workbooks.
- [`docs/LEGACY_FCS_2012.md`](docs/LEGACY_FCS_2012.md) — reconstruction of the historical FCS workbook.
- [`docs/MODERN_V1_RESEARCH.md`](docs/MODERN_V1_RESEARCH.md) — model-research contract.
- [`configs/current_season_v1.yaml`](configs/current_season_v1.yaml) — authoritative production configuration.
- [`configs/division_i_current_v1.yaml`](configs/division_i_current_v1.yaml) — scope-first production alias.

## Guiding rule

**Rank all Division I teams together, but give FCS teams half game points against FCS opponents and on losses to FBS opponents while preserving full credit for an FCS win over FBS.**
