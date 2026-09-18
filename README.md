# NCAA BCS Ranking Calculator / D1 Rank

A transparent, auditable NCAA Division I football ranking and prediction system with a PostgreSQL-backed public website.

**Current version: 0.8.0**

The historical repository name is retained from the original BCS-era project. The production system ranks all NCAA Division I football teams in one field and now includes the **D1 Rank Weekbook** website.

## What the website does

The home page is the complete weekly Division I ranking. The site also provides:

- current-week and future-week game predictions;
- locked historical pregame predictions;
- team pages with complete schedules and projections;
- week-by-week ranking history;
- model accuracy and error statistics;
- team-specific prediction accuracy;
- a rank-to-score matchup calculator;
- team comparison;
- transparent method and data-source notes.

The visual design is intentionally simple: white background, plain text navigation, minimal decoration, and no ornamental outlined buttons.

## Production ranking rules

For a ranking pool containing `N` teams and an opponent ranked `R`:

```text
opponent_rank_score on win  = (N + 1) - R
opponent_rank_score on loss = -R
scoring_margin              = points_for - points_against

home or neutral win = opponent_rank_score + scoring_margin
away win            = opponent_rank_score + scoring_margin + 7

away or neutral loss = opponent_rank_score + scoring_margin
home loss            = opponent_rank_score + scoring_margin - 7
```

There is **no separate +10 win bonus**. Actual scoring margin is used directly. A road win earns seven additional ranking points; a home loss loses seven additional ranking points.

### Season ranking value

Individual game scores remain frozen once earned. The value used to rank a team is their **average game score**, not their cumulative point total:

```text
ranking_score = sum(frozen_game_scores) / games_played
```

This removes the built-in advantage of playing more games and makes bye weeks neutral. The raw cumulative total remains stored for audit purposes. Exact average-score ties use head-to-head, then win percentage, then average opponent strength, followed by a deterministic name fallback.

Every Division I team enters its first current-season game tied at the same neutral T-1 baseline because there is no evidence about that team yet. For scoring, the baseline uses the average occupied rank of the full pool:

```text
Week 1 neutral scoring rank = (N + 1) / 2
```

The live site calculates that neutral rank from the current pool size. For example, with 267 teams the neutral scoring rank is **134.0**. Provider Week 0 is normalized into ranking Week 1. A team remains on the neutral scoring baseline until it completes its first game; after that, the immediately preceding completed week's current-season scoring rank is used. If teams are exactly tied on season score, they share the average rank of the positions occupied by that tie for the next week's opponent scoring.

### FCS modifier

```text
FBS vs FBS       = 100%
FBS vs FCS       = 100%
FCS vs FCS       = 50%
FCS loss to FBS  = 50%
FCS win over FBS = 100%
```

FCS is NCAA Division I. FBS-vs-FBS and FBS-vs-FCS are written separately only to make the multiplier explicit. The FCS percentage applies to opponent-rank points and scoring margin. The seven-point road-win/home-loss adjustment is then applied at full value for every team.

There is no conference-strength value, previous-season carryover, preseason seed, or same-week recursive revaluation.

## Prediction model

Predictions are derived from ranked position, not from an external betting line.

The current predictor is deliberately **monotonic**: the higher-ranked team is always the projected winner, and the projected scoring margin is based directly on the gap between the two ranks. The current-season data calibrates only the positive points-per-rank scale and residual uncertainty. The fit goes through the origin, blends toward a conservative early-season fallback, and is constrained to a documented reasonable range. Home field, an intercept, or another free adjustment may not reverse the ranking order. The season's average scoring total is used only to translate the projected margin into a projected final score.

For each future game the site stores:

- ranks used;
- projected score;
- expected margin;
- win probability;
- calibration sample size;
- ranking snapshot and predictor version.

At kickoff, the latest pregame projection becomes the **official locked prediction**. It is never replaced after the result is known. For earlier completed games that never had a live locked prediction, the website can calculate a **research retrocast using only the ranking available before that game**. Retrocasts are labeled separately and never alter the official accuracy ledger.

## Automatic data source

The production pipeline uses the CollegeFootballData REST API server-side for schedules, scores, classifications, and game-team statistics.

The API key is stored only in `.env`. The public application displays ordinary factual game information and derived rankings/predictions; it does not expose a raw provider database mirror.

See `docs/data-source.md`.

## Synology Container Manager installation

Production path:

```text
/volume1/rankings
├── .env
├── app/
├── postgres/
└── backups/
```

### One-time SSH install

SSH into the Synology, become root, and run:

```bash
sudo -i
curl -fsSL https://raw.githubusercontent.com/larrybillinger/NCAA_BCS_RANKING_CALCULATOR/main/scripts/synology-install.sh -o /tmp/install-rankings.sh
sh /tmp/install-rankings.sh
```

The installer will:

1. create `/volume1/rankings`;
2. ask for the CFBD API key;
3. generate a PostgreSQL password;
4. download the latest repository source;
5. build the web/worker containers;
6. start PostgreSQL;
7. wait for the `/health` endpoint;
8. print the local site URL.

Default local port: **8765**.

### Upgrade an existing pre-v0.5.0 installation

The v0.5.0 ranking change requires switching the model identifier and preserving fractional tied ranks in PostgreSQL:

```bash
sudo -i
curl -fsSL https://raw.githubusercontent.com/larrybillinger/NCAA_BCS_RANKING_CALCULATOR/main/scripts/upgrade-v0.5.0.sh -o /tmp/upgrade-rankings-v050.sh
sh /tmp/upgrade-rankings-v050.sh
```

### Production update workflow

GitHub is the source of truth. Normal changes are committed to this repository first, then the Synology website is updated from GitHub over SSH. Avoid editing `/volume1/rankings/app` directly.

Ordinary source updates use the GitHub-backed updater:

```bash
sudo sh /volume1/rankings/app/scripts/synology-update.sh
```

The updater synchronizes the active non-secret `MODEL_VERSION` and `PREDICTOR_VERSION` from GitHub's committed `.env.example`, while preserving the NAS's API keys and database credentials. Starting with v0.6.1, Synology builds one shared application image for both web and worker, uses extended Docker/Compose timeouts, force-recreates the application containers, and verifies that `/health` reports the exact GitHub application/model/predictor versions before declaring success.

### Back up

```bash
sudo sh /volume1/rankings/app/scripts/synology-backup.sh
```

## Docker services

```text
ncaa-rankings-db       PostgreSQL 17
ncaa-rankings-web      FastAPI + Jinja website
ncaa-rankings-worker   CFBD sync, ranking freeze, predictions, locks
```

Useful commands:

```bash
cd /volume1/rankings/app
docker compose --env-file /volume1/rankings/.env ps
docker compose --env-file /volume1/rankings/.env logs -f web
docker compose --env-file /volume1/rankings/.env logs -f worker
docker compose --env-file /volume1/rankings/.env up -d --build
```

## Database behavior

PostgreSQL stores:

- teams and season-specific subdivisions;
- schedules/results;
- team game statistics;
- immutable weekly ranking snapshots;
- per-game ranking scoring audits;
- provisional prediction snapshots;
- official locked predictions;
- source sync history.

The bundled `rankings/2026/week_01.csv` and `week_02.csv` are retained as archived `division_i_weighted_v3` snapshots. They are **not** relabeled as newer models. When `division_i_weighted_v5` is active, the worker rebuilds completed weekly snapshots from the synced PostgreSQL game data using the no-win-bonus, road-win/home-loss, and average-game-score rules.

## Project structure

```text
src/ncaa_rankings/
  models/                 Ranking formulas
  ranking/                Ranking engines
  evaluation/             Historical evaluation
  web/                    FastAPI website and data pipeline
    templates/            Server-rendered Weekbook pages
    static/               Minimal CSS
rankings/2026/            Official frozen ranking exports
scripts/                   Synology install/update/backup
planning/                  Decisions, risks, sprint plans
docs/                      Architecture, deployment, validation
notes/release-notes/       Release notes
```

## Development run

With PostgreSQL available and `.env` populated:

```bash
pip install -e '.[dev]'
uvicorn ncaa_rankings.web.app:app --reload
python -m ncaa_rankings.web.worker --once
pytest
```

## Security

Never commit `.env`, CFBD keys, database passwords, reverse-proxy credentials, or other secrets.

## Documentation

- `docs/architecture.md`
- `docs/data-source.md`
- `docs/deployment-synology.md`
- `docs/validation.md`
- `docs/CURRENT_SEASON_RULES.md`
- `docs/DIVISION_I_SCOPE.md`
- `docs/SCORING_EXAMPLES.md`
