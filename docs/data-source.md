# Data source

## Provider
CollegeFootballData.com (CFBD) REST API.

## Server-side usage
The worker uses bearer authentication from the `CFBD_API_KEY` environment variable. The key must never be committed or sent to the browser.

## Data stored privately in PostgreSQL
- schedules and game status;
- final scores;
- home/away classifications;
- team IDs and current-season subdivisions;
- ordinary game-team statistics;
- source sync audit metadata.

## Public output
The site publishes ordinary factual game displays plus independently derived rankings, projections, probabilities, model statistics, and visualizations. It does not expose stored raw API responses as a bulk dataset, mirror, or substitute API.

## API endpoints used
- `GET /games`
- `GET /games/teams`

The integration deliberately avoids scraping NCAA, ESPN, school websites, or search-engine result pages for routine operation.


## Quota-aware production polling

Starting with v0.8.1, D1 Rank is deliberately conservative with CollegeFootballData calls.

- one unfiltered `/games` request replaces separate FBS and FCS requests;
- Saturday polls every 60 minutes by default;
- Sunday through Friday poll once every 1440 minutes (24 hours);
- if a daily sleep would cross into Saturday, the worker wakes at local Saturday midnight and switches immediately to the hourly cadence;
- the complete season schedule refreshes at least once every 24 hours;
- HTTP 429 responses trigger exponential cooldowns beginning at 360 minutes and capped at 1440 minutes unless CFBD supplies a longer `Retry-After` value;
- prediction locking occurs before any provider request and therefore still works during CFBD outages or quota exhaustion;
- schedule/score syncing follows the calendar games nearest the current time rather than depending only on the latest frozen ranking snapshot;
- a daily full-schedule pull catches moved or rescheduled games.

The polling settings can be overridden in `.env`:

```text
SYNC_SATURDAY_MINUTES=60
SYNC_OTHER_DAYS_MINUTES=1440
SYNC_FULL_SCHEDULE_HOURS=24
SYNC_RATE_LIMIT_BASE_MINUTES=360
SYNC_RATE_LIMIT_MAX_MINUTES=1440
```

The ranking formula is not affected by these operational settings.
