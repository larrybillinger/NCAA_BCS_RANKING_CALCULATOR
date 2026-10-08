# NCAA BCS Ranking Calculator / D1 Rank

A transparent, auditable NCAA Division I football ranking and prediction system with a PostgreSQL-backed public website.

**Current version: 0.11.1**

The historical repository name is retained from the original BCS-era project. The production system ranks all NCAA Division I football teams in one field and publishes the **D1 Rank Weekbook** website.

## What the website does

The home page is the complete weekly Division I ranking. The site also provides:

- current-week and future-week hybrid game predictions;
- FBS, FCS, and conference ranking views derived from the same national Division I order;
- locked historical pregame predictions;
- team pages with complete schedules and hybrid projections;
- week-by-week ranking history;
- official hybrid accuracy and leakage-safe historical hybrid retrocasts;
- team-specific prediction accuracy;
- a team-vs-team hybrid matchup calculator;
- team comparison;
- transparent method and data-source notes;
- an admin-only manual score desk for provider outages or corrections.

The visual design is intentionally simple: white background, plain text navigation, generous whitespace, and no ornamental outlined buttons.

## Production ranking rules

The ranking formula remains separate from the prediction model.

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

There is no separate +10 win bonus. Actual scoring margin is used directly. A road win earns seven additional ranking points; a home loss loses seven additional ranking points.

### Season ranking value

Individual game scores remain frozen once earned. The value used to rank a team is its average frozen game score:

```text
ranking_score = sum(frozen_game_scores) / games_played
```

This removes the built-in advantage of playing more games and makes bye weeks neutral. The raw cumulative total remains stored for audit. Exact average-score ties use head-to-head, then win percentage, then average opponent strength, followed by a deterministic fallback.

Every Division I team enters its first current-season game tied at the same neutral T-1 baseline because there is no evidence separating teams yet. For scoring, the baseline uses:

```text
Week 1 neutral scoring rank = (N + 1) / 2
```

Provider Week 0 is normalized into ranking Week 1. A team remains on the neutral scoring baseline until it completes its first game; after that, later opponents use the immediately preceding completed week's current-season scoring rank. Old games are never recursively revalued.

### FCS modifier

```text
FBS vs FBS       = 100%
FBS vs FCS       = 100%
FCS vs FCS       = 50%
FCS loss to FBS  = 50%
FCS win over FBS = 100%
```

FCS is NCAA Division I. The FCS percentage applies to opponent-rank points and scoring margin. The seven-point road-win/home-loss adjustment is applied afterward at full value.

There is no conference-strength value, previous-season carryover, preseason seed, or same-week recursive revaluation.

## Official prediction model — hybrid_core_v1

Beginning with v0.11.0, `hybrid_core_v1` is the official Game Book predictor. The production ranking remains `division_i_weighted_v5`.

The hybrid combines two current-season signals:

```text
official projected margin
    = 40% calibrated rank-gap margin
    + 60% shrunk offense/defense matchup margin
```

The rank-gap component uses the existing positive current-season points-per-rank calibration. The offense/defense component uses only completed current-season Division I games and shrinks each team's scoring profile toward the Division I scoring mean with three pseudo-games. That shrinkage keeps a single early-season result from dominating the model.

For a matchup, the model combines each team's shrunk offense with the opponent's shrunk defense to estimate the scoring total and offense/defense margin. The blended margin is then split around that total into projected team scores and a win probability.

Unlike retired `rank_gap_v3`, the official hybrid is not forced to choose the higher-ranked team. A lower-ranked team may be projected to win when its current-season matchup profile outweighs the ranking-gap signal. This changes predictions only; it does not alter ranking points, ranking order, or frozen weekly rankings.

Projected integer scores use a winner-consistent display rule. Scores are rounded half-up; if both scores would display equal while the modeled margin is non-zero, the modeled winner receives one additional display point. A true zero-margin projection may still display a tie. This display rule does not change the continuous projected margin, win probability, or model evaluation inputs.

Home-field, stadium-demand, travel, time-zone, altitude, weather, and other context adjustments are not part of base `hybrid_core_v1`. They remain research-only until separately validated and approved.

## Prediction integrity and history

For each future game the site stores:

- ranks used;
- projected team scores;
- projected margin;
- win probability;
- calibration sample size;
- ranking snapshot and predictor version.

The newest eligible hybrid projection available before kickoff becomes the official locked prediction and is never replaced after the result is known.

Previously locked `rank_gap_v3` predictions remain in PostgreSQL exactly as they were. They are retired historical records and are not rewritten into hybrid predictions or mixed into the active hybrid accuracy ledger.

For earlier completed games that lack an official hybrid lock, the site calculates a clearly labeled hybrid retrocast using only the prior weekly ranking snapshot and completed-game scoring information available before that game. Retrocasts never count as official locked predictions.

Pre-promotion `hybrid_core_v1` shadow rows also remain stored for audit. Once hybrid is official, the worker no longer creates a duplicate base-hybrid shadow row.

## Automatic data source

The production pipeline uses the CollegeFootballData REST API server-side for schedules, scores, classifications, and game-team statistics.

A normal targeted score refresh uses one unfiltered `/games` request. The cadence follows the schedule rather than the day of the week: while idle, the worker wakes at the next Division I kickoff so eligible predictions lock immediately; while any Division I game is in progress it polls every `SYNC_LIVE_MINUTES` (default 60); otherwise it sleeps no longer than `SYNC_IDLE_MINUTES` (default 1440). A full schedule refresh is performed at least once every 24 hours, and HTTP 429 responses use quota backoff.

Prediction locking is local database work and runs before any provider request, so an upstream outage or exhausted API quota cannot prevent an eligible pregame prediction from becoming official on the kickoff cycle.

Full-season schedule syncs reconcile current Division I membership using provider classifications. Provider identity is anchored to CFBD team IDs, with explicit historical aliases where a legacy row predates its durable provider ID. Reconciliation fails closed if provider coverage is materially incomplete.

The API key is stored only in `.env`. The public application displays ordinary factual game information and independently derived rankings/predictions; it does not expose a raw provider database mirror.

## Manual score desk

When CFBD is delayed, unavailable, or incorrect, the administrator can use:

```text
/admin/games
```

The page uses HTTP Basic credentials stored in the production `.env`:

```text
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<secret>
```

A manual score can be saved as in-progress or final and can include an operational note. An active manual override takes precedence over provider score/final fields until explicitly released. Every manual save/release is audited. Once the active ranking model has frozen a week, the score desk becomes read-only for those games.

Public visitors have no write permissions.

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

```bash
sudo -i
curl -fsSL https://raw.githubusercontent.com/larrybillinger/NCAA_BCS_RANKING_CALCULATOR/main/scripts/synology-install.sh -o /tmp/install-rankings.sh
sh /tmp/install-rankings.sh
```

Default local port: **8765**.

### Production update workflow

GitHub is the source of truth. Normal changes are committed here first, then production is updated from GitHub over SSH. Avoid editing `/volume1/rankings/app` directly.

Ordinary updates use:

```bash
sudo sh /volume1/rankings/app/scripts/synology-update.sh
```

For major updates, it is safest to download the newest updater from `main` first:

```bash
sudo -i
curl -fsSL https://raw.githubusercontent.com/larrybillinger/NCAA_BCS_RANKING_CALCULATOR/main/scripts/synology-update.sh -o /tmp/update-rankings.sh
sh /tmp/update-rankings.sh
```

The updater preserves secrets, synchronizes the committed `MODEL_VERSION` and `PREDICTOR_VERSION`, backs up the application/PostgreSQL/protected `.env` as applicable, rebuilds the shared application image, recreates web/worker, and verifies `/health` reports the exact expected application/model/predictor versions.

For v0.11.1 production must report:

```text
app_version       0.11.1
model_version     division_i_weighted_v5
predictor_version hybrid_core_v1
```

### Back up

```bash
sudo sh /volume1/rankings/app/scripts/synology-backup.sh
```

## Docker services

```text
ncaa-rankings-db       PostgreSQL 17
ncaa-rankings-web      FastAPI + Jinja website
ncaa-rankings-worker   CFBD sync, ranking freeze, hybrid predictions, kickoff locks
```

Useful commands:

```bash
cd /volume1/rankings/app
docker compose --env-file /volume1/rankings/.env ps
docker compose --env-file /volume1/rankings/.env logs -f web
docker compose --env-file /volume1/rankings/.env logs -f worker
```

## Database behavior

PostgreSQL stores:

- teams and season-specific subdivisions;
- schedules/results;
- team game statistics;
- immutable weekly ranking snapshots;
- per-game ranking scoring audits;
- provisional production prediction snapshots;
- official locked predictions by predictor version;
- a separate research/shadow prediction ledger;
- source sync history.

The bundled `rankings/2026/week_01.csv` and `week_02.csv` remain archived `division_i_weighted_v3` snapshots. They are not relabeled as newer models. Production `division_i_weighted_v5` ranking snapshots are calculated from the synced PostgreSQL game database using the documented current-season rules.

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
