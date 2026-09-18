from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .bootstrap import bootstrap_bundled_rankings
from .cfbd import CFBDClient
from .config import get_settings
from .db import SessionLocal, get_session, init_db
from .models import Team
from .prediction_service import rank_matchup_projection
from .ranking_service import get_snapshot, latest_snapshot
from .stats_service import (
    last_sync,
    overall_metrics,
    retrocast_metrics,
    team_metrics,
    team_retrocast_metrics,
    weekly_metrics,
    weekly_retrocast_metrics,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as session:
        bootstrap_bundled_rankings(session)
    yield


settings = get_settings()
app = FastAPI(title=settings.web_title, version="0.8.0", lifespan=lifespan)
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


def _base_context(session: Session, request: Request, *, week: int | None = None) -> dict:
    season = settings.season
    weeks = available_ranking_weeks(session, season)
    latest = latest_snapshot(session, season)
    team_count = len(all_teams(session, season))
    neutral_rank = (team_count + 1) / 2.0 if team_count else None
    selected_week = week or (latest.week if latest else (weeks[-1] if weeks else 1))
    metrics = overall_metrics(session, season)
    sync = last_sync(session)
    return {
        "request": request,
        "title": settings.web_title,
        "season": season,
        "weeks": weeks,
        "selected_week": selected_week,
        "latest_week": latest.week if latest else None,
        "team_count": team_count,
        "neutral_rank": neutral_rank,
        "metrics": metrics,
        "last_sync": sync,
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
    return {
        "status": "ok",
        "season": settings.season,
        "latest_ranking_week": snapshot.week if snapshot else None,
        "app_version": app.version,
        "model_version": settings.model_version,
        "predictor_version": settings.predictor_version,
        "cfbd_configured": CFBDClient().configured,
    }


@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    week: int | None = Query(default=None, ge=1, le=25),
    subdivision: str | None = Query(default=None),
    q: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    latest = latest_snapshot(session, settings.season)
    selected_week = week or (latest.week if latest else 1)
    snapshot = get_snapshot(session, settings.season, selected_week)
    if snapshot is None and latest is not None:
        snapshot = latest
        selected_week = latest.week
    rows = ranking_rows(
        session,
        snapshot,
        subdivision=(subdivision or "").upper() or None,
        search=q,
    ) if snapshot else []
    context = _base_context(session, request, week=selected_week)
    context.update({
        "snapshot": snapshot,
        "ranking_rows": rows,
        "subdivision_filter": (subdivision or "").upper(),
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
    context.update({"prediction_week": selected_week, "as_of_week": as_of_week, "games": games})
    return TEMPLATES.TemplateResponse(request=request, name="predictions.html", context=context)


@app.get("/stats", response_class=HTMLResponse)
def stats(
    request: Request,
    metric: str = Query(default="winner_accuracy"),
    session: Session = Depends(get_session),
):
    weekly = weekly_metrics(session, settings.season)
    retro = retrocast_metrics(session, settings.season)
    retro_weekly = weekly_retrocast_metrics(session, settings.season)
    context = _base_context(session, request)
    context.update({
        "weekly_metrics": weekly,
        "retro_metrics": retro,
        "retro_weekly_metrics": retro_weekly,
        "metric": metric,
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
    })
    return TEMPLATES.TemplateResponse(request=request, name="team.html", context=context)


@app.get("/method", response_class=HTMLResponse)
def method(request: Request, session: Session = Depends(get_session)):
    context = _base_context(session, request)
    return TEMPLATES.TemplateResponse(request=request, name="method.html", context=context)


@app.get("/tools/rank-calculator", response_class=HTMLResponse)
def rank_calculator(
    request: Request,
    rank_a: int | None = Query(default=None, ge=1, le=400),
    rank_b: int | None = Query(default=None, ge=1, le=400),
    neutral: bool = Query(default=False),
    session: Session = Depends(get_session),
):
    result = None
    if rank_a is not None and rank_b is not None:
        result = rank_matchup_projection(session, settings.season, home_rank=rank_a, away_rank=rank_b, neutral=neutral)
    context = _base_context(session, request)
    context.update({"rank_a": rank_a, "rank_b": rank_b, "neutral": neutral, "calculator_result": result})
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
    context.update({"teams": teams, "team_a": team_a, "team_b": team_b, "entry_a": entry_a, "entry_b": entry_b})
    return TEMPLATES.TemplateResponse(request=request, name="compare.html", context=context)
