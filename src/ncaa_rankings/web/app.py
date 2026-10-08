from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import hmac
from pathlib import Path
import secrets
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .bootstrap import bootstrap_bundled_rankings
from .cfbd import CFBDClient
from .config import get_settings
from .db import SessionLocal, get_session, init_db
from .manual_score_service import (
    ManualScoreError,
    admin_game_rows,
    release_manual_score,
    set_manual_score,
)
from .models import Game, Team
from .prediction_service import team_matchup_projection
from .ranking_service import get_snapshot, latest_snapshot
from .sync_schedule import LIVE_WINDOW, schedule_state, stale_after
from .stats_service import (
    last_successful_sync,
    latest_sync_attempt,
    overall_metrics,
    research_metrics,
    retrocast_summary,
    team_metrics,
    team_retrocast_metrics,
    weekly_metrics,
    weekly_research_metrics,
)
from .view_service import (
    all_teams,
    available_ranking_weeks,
    game_rows_for_week,
    ranking_rows,
    team_current_entry,
    team_ranking_history,
    team_schedule_rows,
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
ADMIN_SECURITY = HTTPBasic(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as session:
        bootstrap_bundled_rankings(session)
    yield


settings = get_settings()
app = FastAPI(title=settings.web_title, version="0.11.1", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{decimals}f}%"


def _num(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def _score(value: float | None) -> str:
    if value is None:
        return "—"
    return str(int(round(value)))


TEMPLATES.env.filters["pct"] = _pct
TEMPLATES.env.filters["num"] = _num
TEMPLATES.env.filters["score"] = _score


def _local_datetime(value: datetime | None, fmt: str = "%b %d %H:%M %Z") -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZoneInfo(settings.timezone)).strftime(fmt)


TEMPLATES.env.filters["localdt"] = _local_datetime


def _admin_csrf_token() -> str:
    return hmac.new(
        settings.admin_password.encode("utf-8"),
        b"d1-rank-manual-score-v1",
        hashlib.sha256,
    ).hexdigest()


def _require_admin(
    credentials: HTTPBasicCredentials | None = Depends(ADMIN_SECURITY),
) -> str:
    if not settings.admin_password:
        raise HTTPException(
            status_code=503,
            detail="Manual score desk is disabled until ADMIN_PASSWORD is configured.",
        )

    username_ok = (
        credentials is not None
        and secrets.compare_digest(credentials.username, settings.admin_username)
    )
    password_ok = (
        credentials is not None
        and secrets.compare_digest(credentials.password, settings.admin_password)
    )
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=401,
            detail="Admin credentials required.",
            headers={"WWW-Authenticate": 'Basic realm="D1 Rank Score Desk"'},
        )
    return credentials.username


def _verify_admin_csrf(token: str) -> None:
    expected = _admin_csrf_token()
    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid admin form token.")


def _optional_score(value: str) -> int | None:
    clean = value.strip()
    if not clean:
        return None
    try:
        return int(clean)
    except ValueError as exc:
        raise ManualScoreError("Scores must be whole numbers.") from exc


def _sync_state(session: Session) -> dict:
    attempt = latest_sync_attempt(session)
    success = last_successful_sync(session)
    now = datetime.now(timezone.utc)

    if not CFBDClient().configured:
        status = "disabled"
    elif attempt is None:
        status = "stale"
    elif attempt.status == "error":
        status = "error"
    elif attempt.status == "running":
        status = "syncing"
    elif success is None or success.finished_at is None:
        status = "stale"
    else:
        finished = success.finished_at
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        state = schedule_state(session, settings.season, now)
        status = "stale" if now - finished > stale_after(state, settings) else "ok"

    error = attempt.error_text if attempt and attempt.status == "error" else None
    if error:
        if "429" in error:
            error = "429 Too Many Requests"
        elif "401" in error:
            error = "401 Unauthorized"
        else:
            error = error.splitlines()[0][:120]

    return {
        "status": status,
        "attempt": attempt,
        "success": success,
        "error": error,
    }


def _auto_refresh_seconds(rows: list[dict]) -> int | None:
    now = datetime.now(timezone.utc)
    for row in rows:
        game = row.get("game")
        if game is None or game.completed or game.start_time is None:
            continue
        start = game.start_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if start <= now <= start + LIVE_WINDOW:
            return 300
    return None


def _base_context(session: Session, request: Request, *, week: int | None = None) -> dict:
    season = settings.season
    weeks = available_ranking_weeks(session, season)
    latest = latest_snapshot(session, season)
    team_count = len(all_teams(session, season))
    neutral_rank = (team_count + 1) / 2.0 if team_count else None
    selected_week = week or (latest.week if latest else (weeks[-1] if weeks else 1))
    metrics = overall_metrics(session, season)
    sync = _sync_state(session)
    last_schedule_week = session.scalar(
        select(func.max(Game.week)).where(
            Game.season == season,
            Game.season_type == "regular",
        )
    )
    return {
        "request": request,
        "title": settings.web_title,
        "season": season,
        "weeks": weeks,
        "selected_week": selected_week,
        "latest_week": latest.week if latest else None,
        "last_week": max(last_schedule_week or 0, latest.week if latest else 0) or 10,
        "team_count": team_count,
        "neutral_rank": neutral_rank,
        "metrics": metrics,
        "last_sync": sync["success"],
        "latest_sync_attempt": sync["attempt"],
        "sync_status": sync["status"],
        "sync_error": sync["error"],
        "cfbd_configured": CFBDClient().configured,
        "app_version": app.version,
        "model_version": settings.model_version,
        "predictor_version": settings.predictor_version,
        "now": datetime.now(timezone.utc),
    }


@app.get("/health")
def health(session: Session = Depends(get_session)) -> dict:
    session.execute(text("SELECT 1"))
    snapshot = latest_snapshot(session, settings.season)
    sync = _sync_state(session)
    return {
        "status": "ok",
        "season": settings.season,
        "latest_ranking_week": snapshot.week if snapshot else None,
        "app_version": app.version,
        "model_version": settings.model_version,
        "predictor_version": settings.predictor_version,
        "cfbd_configured": CFBDClient().configured,
        "data_sync_status": sync["status"],
        "last_sync_attempt": (
            sync["attempt"].started_at.isoformat()
            if sync["attempt"] is not None
            else None
        ),
        "last_successful_sync": (
            sync["success"].finished_at.isoformat()
            if sync["success"] is not None and sync["success"].finished_at is not None
            else None
        ),
        "last_sync_error": sync["error"],
        "live_games": schedule_state(
            session, settings.season, datetime.now(timezone.utc)
        ).live_games,
    }


@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    week: int | None = Query(default=None, ge=1, le=25),
    subdivision: str | None = Query(default=None),
    conference: str | None = Query(default=None),
    q: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    latest = latest_snapshot(session, settings.season)
    selected_week = week or (latest.week if latest else 1)
    snapshot = get_snapshot(session, settings.season, selected_week)
    if snapshot is None and latest is not None:
        snapshot = latest
        selected_week = latest.week
    subdivision_filter = (subdivision or "").upper()
    if subdivision_filter not in {"FBS", "FCS"}:
        subdivision_filter = None
    conference_filter = (conference or "").strip() or None
    all_rows = ranking_rows(session, snapshot) if snapshot else []
    conferences = sorted({
        row["conference"]
        for row in all_rows
        if row["conference"]
        and (subdivision_filter is None or row["subdivision"] == subdivision_filter)
    })
    rows = ranking_rows(
        session,
        snapshot,
        subdivision=subdivision_filter,
        conference=conference_filter,
        search=q,
    ) if snapshot else []
    context = _base_context(session, request, week=selected_week)
    context.update({
        "snapshot": snapshot,
        "ranking_rows": rows,
        "subdivision_filter": subdivision_filter or "",
        "conference_filter": conference_filter or "",
        "conferences": conferences,
        "search_query": q or "",
    })
    return TEMPLATES.TemplateResponse(request=request, name="rankings.html", context=context)


@app.get("/rankings", response_class=HTMLResponse)
def rankings_alias(request: Request):
    query = request.url.query
    target = "/" + (f"?{query}" if query else "")
    return RedirectResponse(target, status_code=307)


@app.get("/predictions", response_class=HTMLResponse)
def predictions(
    request: Request,
    week: int | None = Query(default=None, ge=1, le=25),
    as_of: int | None = Query(default=None, ge=1, le=25),
    session: Session = Depends(get_session),
):
    latest = latest_snapshot(session, settings.season)
    default_week = (latest.week + 1) if latest else 1
    selected_week = week or default_week
    as_of_week = as_of or (latest.week if latest else None)
    games = game_rows_for_week(session, settings.season, selected_week, as_of_week=as_of_week)
    context = _base_context(session, request, week=latest.week if latest else None)
    context.update({
        "prediction_week": selected_week,
        "as_of_week": as_of_week,
        "games": games,
        "auto_refresh_seconds": _auto_refresh_seconds(games),
    })
    return TEMPLATES.TemplateResponse(request=request, name="predictions.html", context=context)


STATS_METRICS = {
    "winner_accuracy": "Winner accuracy",
    "spread_mae": "Margin MAE",
    "spread_rmse": "Margin RMSE",
    "score_mae": "Score MAE",
    "total_mae": "Total MAE",
    "display_tie_rate": "Display ties",
    "brier": "Brier score",
    "upset_hit_rate": "Upset hits",
    "rank_result_correlation": "Rank–result correlation",
}


@app.get("/stats", response_class=HTMLResponse)
def stats(
    request: Request,
    metric: str = Query(default="winner_accuracy"),
    session: Session = Depends(get_session),
):
    if metric not in STATS_METRICS:
        metric = "winner_accuracy"
    weekly = weekly_metrics(session, settings.season)
    retro, retro_weekly = retrocast_summary(session, settings.season)
    shadow = research_metrics(session, settings.season)
    shadow_weekly = weekly_research_metrics(session, settings.season)
    context = _base_context(session, request)
    context.update({
        "weekly_metrics": weekly,
        "retro_metrics": retro,
        "retro_weekly_metrics": retro_weekly,
        "shadow_metrics": shadow,
        "shadow_weekly_metrics": shadow_weekly,
        "metric": metric,
        "metric_label": STATS_METRICS[metric],
    })
    return TEMPLATES.TemplateResponse(request=request, name="stats.html", context=context)


@app.get("/teams", response_class=HTMLResponse)
def team_index(request: Request, session: Session = Depends(get_session)):
    teams = all_teams(session, settings.season)
    context = _base_context(session, request)
    context.update({"teams": teams})
    return TEMPLATES.TemplateResponse(request=request, name="teams.html", context=context)


@app.get("/teams/{slug}", response_class=HTMLResponse)
def team_page(
    request: Request,
    slug: str,
    as_of: int | None = Query(default=None, ge=1, le=25),
    session: Session = Depends(get_session),
):
    team = session.scalar(select(Team).where(Team.slug == slug))
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    latest = latest_snapshot(session, settings.season)
    as_of_week = as_of or (latest.week if latest else None)
    current = team_current_entry(session, team.id, settings.season)
    schedule = team_schedule_rows(session, team, settings.season, as_of_week=as_of_week)
    history = team_ranking_history(session, team.id, settings.season)
    tmetrics = team_metrics(session, settings.season, team.id)
    tretro = team_retrocast_metrics(session, settings.season, team.id)
    context = _base_context(session, request)
    context.update({
        "team": team,
        "current_entry": current,
        "schedule": schedule,
        "history": history,
        "team_metrics": tmetrics,
        "team_retro_metrics": tretro,
        "as_of_week": as_of_week,
        "auto_refresh_seconds": _auto_refresh_seconds(schedule),
    })
    return TEMPLATES.TemplateResponse(request=request, name="team.html", context=context)


@app.get("/admin/games", response_class=HTMLResponse)
def admin_games(
    request: Request,
    week: int | None = Query(default=None, ge=1, le=25),
    q: str | None = Query(default=None),
    message: str | None = Query(default=None),
    error: str | None = Query(default=None),
    actor: str = Depends(_require_admin),
    session: Session = Depends(get_session),
):
    latest = latest_snapshot(session, settings.season)
    selected_week = week or ((latest.week + 1) if latest else 1)
    rows = admin_game_rows(
        session,
        settings.season,
        selected_week,
        search=q,
    )
    context = _base_context(session, request, week=latest.week if latest else None)
    context.update({
        "admin_actor": actor,
        "admin_week": selected_week,
        "admin_search": q or "",
        "admin_games": rows,
        "csrf_token": _admin_csrf_token(),
        "message": message,
        "error": error,
    })
    return TEMPLATES.TemplateResponse(
        request=request,
        name="admin_games.html",
        context=context,
    )


@app.post("/admin/games/{game_id}/score")
def admin_set_score(
    game_id: int,
    week: int = Form(...),
    q: str = Form(default=""),
    home_points: str = Form(default=""),
    away_points: str = Form(default=""),
    completed: str | None = Form(default=None),
    note: str = Form(default=""),
    csrf_token: str = Form(...),
    actor: str = Depends(_require_admin),
    session: Session = Depends(get_session),
):
    _verify_admin_csrf(csrf_token)
    params = {"week": week}
    if q:
        params["q"] = q

    try:
        _, created_weeks = set_manual_score(
            session,
            game_id=game_id,
            home_points=_optional_score(home_points),
            away_points=_optional_score(away_points),
            completed=completed is not None,
            note=note,
            actor=actor,
        )
        message = "Manual score saved."
        if created_weeks:
            weeks = ", ".join(str(value) for value in created_weeks)
            message += f" Created official ranking Week {weeks}."
        params["message"] = message
    except ManualScoreError as exc:
        params["error"] = str(exc)

    return RedirectResponse(
        "/admin/games?" + urlencode(params),
        status_code=303,
    )


@app.post("/admin/games/{game_id}/release")
def admin_release_score(
    game_id: int,
    week: int = Form(...),
    q: str = Form(default=""),
    note: str = Form(default=""),
    csrf_token: str = Form(...),
    actor: str = Depends(_require_admin),
    session: Session = Depends(get_session),
):
    _verify_admin_csrf(csrf_token)
    params = {"week": week}
    if q:
        params["q"] = q

    try:
        release_manual_score(
            session,
            game_id=game_id,
            note=note,
            actor=actor,
        )
        params["message"] = "Manual override released. The local score was cleared and CFBD will repopulate it on the next sync."
    except ManualScoreError as exc:
        params["error"] = str(exc)

    return RedirectResponse(
        "/admin/games?" + urlencode(params),
        status_code=303,
    )


@app.get("/method", response_class=HTMLResponse)
def method(request: Request, session: Session = Depends(get_session)):
    context = _base_context(session, request)
    return TEMPLATES.TemplateResponse(request=request, name="method.html", context=context)


@app.get("/tools/rank-calculator", response_class=HTMLResponse)
def rank_calculator(
    request: Request,
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    teams = all_teams(session, settings.season)
    home_team = session.scalar(select(Team).where(Team.slug == home)) if home else None
    away_team = session.scalar(select(Team).where(Team.slug == away)) if away else None
    result = None
    error = None
    if home and home_team is None:
        error = "Home team not found."
    elif away and away_team is None:
        error = "Away team not found."
    elif home_team is not None and away_team is not None:
        if home_team.id == away_team.id:
            error = "Choose two different teams."
        else:
            result = team_matchup_projection(
                session,
                settings.season,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
            )
            if result is None:
                error = "A hybrid projection is not available for this matchup."
    context = _base_context(session, request)
    context.update({
        "calculator_teams": teams,
        "home_slug": home or "",
        "away_slug": away or "",
        "home_team": home_team,
        "away_team": away_team,
        "calculator_result": result,
        "calculator_error": error,
    })
    return TEMPLATES.TemplateResponse(request=request, name="rank_calculator.html", context=context)


@app.get("/compare", response_class=HTMLResponse)
def compare(
    request: Request,
    a: str | None = Query(default=None),
    b: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    teams = all_teams(session, settings.season)
    team_a = session.scalar(select(Team).where(Team.slug == a)) if a else None
    team_b = session.scalar(select(Team).where(Team.slug == b)) if b else None
    entry_a = team_current_entry(session, team_a.id, settings.season) if team_a else None
    entry_b = team_current_entry(session, team_b.id, settings.season) if team_b else None
    context = _base_context(session, request)
    context.update({
        "teams": teams,
        "team_a": team_a,
        "team_b": team_b,
        "entry_a": entry_a,
        "entry_b": entry_b,
    })
    return TEMPLATES.TemplateResponse(request=request, name="compare.html", context=context)
