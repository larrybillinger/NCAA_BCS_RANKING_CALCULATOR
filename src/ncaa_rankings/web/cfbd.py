from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import hashlib
import json
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Game, GameTeamStat, SourceSyncRun, Team, TeamSeason
from .utils import parse_iso_datetime, slugify, subdivision

LOGGER = logging.getLogger(__name__)
DIVISION_I = {"FBS", "FCS"}


class CFBDClient:
    """Small server-side client for the CollegeFootballData REST API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self.api_key = (api_key if api_key is not None else settings.cfbd_api_key).strip()
        self.base_url = (base_url or settings.cfbd_base_url).rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str, params: dict | None = None) -> list | dict:
        if not self.api_key:
            raise RuntimeError(
                "CFBD_API_KEY is not configured. Add a CollegeFootballData API key to .env."
            )
        response = httpx.get(
            f"{self.base_url}{path}",
            params=params or {},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()

    def games(
        self,
        year: int,
        *,
        week: int | None = None,
        classification: str | None = None,
        season_type: str = "regular",
    ) -> list[dict]:
        params: dict[str, object] = {"year": year, "seasonType": season_type}
        if week is not None:
            params["week"] = week
        if classification:
            params["classification"] = classification.lower()
        result = self._get("/games", params)
        return list(result) if isinstance(result, list) else []

    def game_team_stats(
        self,
        year: int,
        week: int,
        *,
        classification: str | None = None,
    ) -> list[dict]:
        params: dict[str, object] = {
            "year": year,
            "week": week,
            "seasonType": "regular",
        }
        if classification:
            params["classification"] = classification.lower()
        result = self._get("/games/teams", params)
        return list(result) if isinstance(result, list) else []


def _sync_run_start(session: Session, endpoint: str, season: int, week: int | None) -> SourceSyncRun:
    run = SourceSyncRun(
        provider="cfbd",
        endpoint=endpoint,
        season=season,
        week=week,
        status="running",
    )
    session.add(run)
    session.flush()
    return run


def _sync_run_finish(
    session: Session,
    run: SourceSyncRun,
    *,
    status: str,
    rows: int,
    payload: object | None = None,
    error: str | None = None,
) -> None:
    run.status = status
    run.rows_received = rows
    run.finished_at = datetime.now(timezone.utc)
    run.error_text = error
    if payload is not None:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        run.response_hash = hashlib.sha256(encoded).hexdigest()
    session.add(run)


def _unique_slug(session: Session, name: str, cfbd_id: int | None) -> str:
    base = slugify(name)
    candidate = base
    counter = 2
    while True:
        existing = session.scalar(select(Team).where(Team.slug == candidate))
        if existing is None or (cfbd_id is not None and existing.cfbd_id == cfbd_id):
            return candidate
        candidate = f"{base}-{counter}"
        counter += 1


def upsert_team(
    session: Session,
    *,
    cfbd_id: int | None,
    name: str,
    season: int,
    classification: str | None,
    conference: str | None,
) -> Team:
    team = None
    if cfbd_id is not None:
        team = session.scalar(select(Team).where(Team.cfbd_id == cfbd_id))
    if team is None:
        team = session.scalar(select(Team).where(Team.name == name))
    if team is None:
        team = Team(
            cfbd_id=cfbd_id,
            name=name,
            slug=_unique_slug(session, name, cfbd_id),
        )
        session.add(team)
        session.flush()
    else:
        if team.cfbd_id is None and cfbd_id is not None:
            team.cfbd_id = cfbd_id
        if team.name != name:
            team.name = name
        session.add(team)
        session.flush()

    season_row = session.scalar(
        select(TeamSeason).where(
            TeamSeason.team_id == team.id,
            TeamSeason.season == season,
        )
    )
    if season_row is None:
        season_row = TeamSeason(team_id=team.id, season=season)
    season_row.subdivision = subdivision(classification)
    season_row.conference = conference
    season_row.active = True
    session.add(season_row)
    return team


def _game_payload_id(game: dict) -> str:
    return str(game.get("id") or game.get("gameId") or "")


def upsert_game(session: Session, payload: dict) -> Game | None:
    provider_game_id = _game_payload_id(payload)
    if not provider_game_id:
        return None

    season = int(payload.get("season") or 0)
    if not season:
        return None

    home_name = str(payload.get("homeTeam") or "").strip()
    away_name = str(payload.get("awayTeam") or "").strip()
    if not home_name or not away_name:
        return None

    home = upsert_team(
        session,
        cfbd_id=payload.get("homeId"),
        name=home_name,
        season=season,
        classification=payload.get("homeClassification"),
        conference=payload.get("homeConference"),
    )
    away = upsert_team(
        session,
        cfbd_id=payload.get("awayId"),
        name=away_name,
        season=season,
        classification=payload.get("awayClassification"),
        conference=payload.get("awayConference"),
    )

    row = session.scalar(
        select(Game).where(
            Game.provider == "cfbd",
            Game.provider_game_id == provider_game_id,
        )
    )
    if row is None:
        row = Game(provider="cfbd", provider_game_id=provider_game_id)

    row.season = season
    source_week = int(payload.get("week") or 0)
    # Ranking Week 1 is the first ranking period. If a provider identifies
    # early-season games as Week 0, fold them into ranking Week 1.
    row.week = max(1, source_week)
    row.season_type = str(payload.get("seasonType") or "regular")
    row.start_time = parse_iso_datetime(payload.get("startDate"))
    row.completed = bool(payload.get("completed"))
    row.neutral_site = bool(payload.get("neutralSite"))
    row.conference_game = bool(payload.get("conferenceGame"))
    row.home_team_id = home.id
    row.away_team_id = away.id
    row.home_subdivision = subdivision(payload.get("homeClassification"))
    row.away_subdivision = subdivision(payload.get("awayClassification"))
    row.home_points = payload.get("homePoints")
    row.away_points = payload.get("awayPoints")
    row.venue = payload.get("venue")
    row.fetched_at = datetime.now(timezone.utc)
    session.add(row)
    return row


def sync_games(
    session: Session,
    client: CFBDClient,
    season: int,
    *,
    week: int | None = None,
) -> int:
    endpoint = "/games"
    run = _sync_run_start(session, endpoint, season, week)
    session.commit()
    rows: dict[str, dict] = {}
    try:
        for classification in ("fbs", "fcs"):
            for game in client.games(
                season,
                week=week,
                classification=classification,
                season_type="regular",
            ):
                game_id = _game_payload_id(game)
                if game_id:
                    rows[game_id] = game
        for game in rows.values():
            upsert_game(session, game)
        _sync_run_finish(session, run, status="ok", rows=len(rows), payload=list(rows.values()))
        session.commit()
        return len(rows)
    except Exception as exc:
        session.rollback()
        run = session.get(SourceSyncRun, run.id)
        if run is not None:
            _sync_run_finish(session, run, status="error", rows=0, error=str(exc))
            session.commit()
        raise


def _coerce_stat_value(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def sync_game_team_stats(
    session: Session,
    client: CFBDClient,
    season: int,
    week: int,
) -> int:
    run = _sync_run_start(session, "/games/teams", season, week)
    session.commit()
    payloads: dict[str, dict] = {}
    try:
        for classification in ("fbs", "fcs"):
            for item in client.game_team_stats(season, week, classification=classification):
                game_id = str(item.get("id") or "")
                if game_id:
                    payloads[game_id] = item

        stat_count = 0
        for provider_game_id, item in payloads.items():
            game = session.scalar(
                select(Game).where(
                    Game.provider == "cfbd",
                    Game.provider_game_id == provider_game_id,
                )
            )
            if game is None:
                continue
            for team_blob in item.get("teams") or []:
                team_name = str(team_blob.get("team") or "").strip()
                if not team_name:
                    continue
                team = session.scalar(select(Team).where(Team.name == team_name))
                if team is None:
                    continue
                for stat in team_blob.get("stats") or []:
                    category = str(stat.get("category") or "").strip()
                    if not category:
                        continue
                    row = session.scalar(
                        select(GameTeamStat).where(
                            GameTeamStat.game_id == game.id,
                            GameTeamStat.team_id == team.id,
                            GameTeamStat.category == category,
                        )
                    )
                    if row is None:
                        row = GameTeamStat(
                            game_id=game.id,
                            team_id=team.id,
                            category=category,
                        )
                    row.value = _coerce_stat_value(stat.get("stat"))
                    row.fetched_at = datetime.now(timezone.utc)
                    session.add(row)
                    stat_count += 1
        _sync_run_finish(
            session,
            run,
            status="ok",
            rows=stat_count,
            payload=list(payloads.values()),
        )
        session.commit()
        return stat_count
    except Exception as exc:
        session.rollback()
        run = session.get(SourceSyncRun, run.id)
        if run is not None:
            _sync_run_finish(session, run, status="error", rows=0, error=str(exc))
            session.commit()
        raise


def division_i_game(game: Game) -> bool:
    return game.home_subdivision in DIVISION_I or game.away_subdivision in DIVISION_I
