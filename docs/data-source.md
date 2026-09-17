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
