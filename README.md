# NCAA BCS Ranking Calculator / D1 Rank

A transparent, auditable NCAA Division I football ranking and prediction system with a PostgreSQL-backed public website.

**Current version: 0.5.0**

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
Win:
    opponent_rank_score = (N + 1) - R
    win_score = 10

Loss:
    opponent_rank_score = -R
    win_score = 0

spread_score = points_for - points_against
```

Before Week 1, every Division I team is tied because the current season contains no evidence yet. The tie is conceptually T-1, but for scoring it uses the average occupied rank of the full pool:

```text
Week 1 neutral scoring rank = (N + 1) / 2
```

With 266 teams, every in-pool Week 1 opponent therefore has scoring rank **133.5**. Week 2 and later use the immediately preceding completed week's current-season scoring rank. If teams are exactly tied on season score, they share the average rank of the positions occupied by that tie for the next week's opponent scoring.

### FCS modifier

```text
FBS vs Division I opponent = 100%
FCS vs FCS                 = 50%
FCS loss to FBS            = 50%
FCS win over FBS           = 100%
```

There is no conference-strength value, previous-season carryover, preseason seed, or same-week recursive revaluation.

## Prediction model

Predictions are derived from ranked position, not from an external betting line.

The current predictor fits the relationship between **pregame rank gap and actual scoring margin** using completed games from the current season. It also learns the season's average scoring total and residual uncertainty. Early in the season the model blends toward a documented conservative fallback because the sample is small.

For each future game the site stores:

- ranks used;
- projected score;
- expected margin;
- win probability;
- calibration sample size;
- ranking snapshot and predictor version.

At kickoff, the latest pregame projection becomes the **official locked prediction**. It is never replaced after the result is known. Later rankings can produce research retrocasts, but those do not alter the official accuracy ledger.

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

### Update later

After v0.5.0 is installed, ordinary source updates use:

```bash
sudo sh /volume1/rankings/app/scripts/synology-update.sh
```

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

The bundled `rankings/2026/week_01.csv` and `week_02.csv` are the recalculated v0.5.0 snapshots using the tied-pool Week 1 baseline and averaged scoring ranks for exact ties. They are imported on a fresh install so the ranking pages work before the first API sync.

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
