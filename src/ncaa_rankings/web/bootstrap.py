from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import RankingEntry, RankingSnapshot, Team, TeamSeason
from .ranking_service import get_snapshot
from .utils import slugify


def _unique_slug(session: Session, name: str) -> str:
    base = slugify(name)
    candidate = base
    counter = 2
    while session.scalar(select(Team).where(Team.slug == candidate)) is not None:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _team(session: Session, name: str) -> Team:
    team = session.scalar(select(Team).where(Team.name == name))
    if team is None:
        team = Team(name=name, slug=_unique_slug(session, name))
        session.add(team)
        session.flush()
    return team


def _record(value: str) -> tuple[int, int]:
    try:
        wins, losses = value.split("-", 1)
        return int(wins), int(losses)
    except (ValueError, AttributeError):
        return 0, 0


def import_ranking_csv(
    session: Session,
    path: Path,
    *,
    season: int,
    week: int,
    model_version: str,
) -> RankingSnapshot:
    existing = get_snapshot(session, season, week)
    if existing is not None:
        return existing

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"Bundled ranking file is empty: {path}")

    previous = get_snapshot(session, season, week - 1) if week > 1 else None
    previous_ranks: dict[int, int] = {}
    if previous is not None:
        for entry in session.scalars(
            select(RankingEntry).where(RankingEntry.snapshot_id == previous.id)
        ):
            previous_ranks[entry.team_id] = entry.rank

    snapshot = RankingSnapshot(
        season=season,
        week=week,
        model_version=model_version,
        official=True,
        source_note=f"Bundled official ranking imported from {path.name}.",
    )
    session.add(snapshot)
    session.flush()

    for row in rows:
        name = (row.get("Team") or "").strip()
        if not name:
            continue
        team = _team(session, name)
        subdivision = (row.get("Subdivision") or "OTHER").upper()
        season_row = session.scalar(
            select(TeamSeason).where(
                TeamSeason.team_id == team.id,
                TeamSeason.season == season,
            )
        )
        if season_row is None:
            season_row = TeamSeason(team_id=team.id, season=season)
        season_row.subdivision = subdivision
        season_row.active = subdivision in {"FBS", "FCS"}
        session.add(season_row)

        wins, losses = _record(row.get("Record") or "0-0")
        rank = int(float(row.get("Rank") or 0))
        previous_rank = previous_ranks.get(team.id)
        session.add(
            RankingEntry(
                snapshot_id=snapshot.id,
                team_id=team.id,
                rank=rank,
                score=float(row.get("Score") or 0.0),
                wins=wins,
                losses=losses,
                opponent_strength=float(row.get("Opponent Strength") or 0.0),
                movement=(previous_rank - rank) if previous_rank is not None else None,
            )
        )

    session.commit()
    return snapshot


def bootstrap_bundled_rankings(session: Session) -> list[int]:
    settings = get_settings()
    if not settings.bootstrap_rankings:
        return []
    created: list[int] = []
    season_dir = settings.rankings_dir / str(settings.season)
    for week in range(1, 21):
        path = season_dir / f"week_{week:02d}.csv"
        if not path.exists():
            continue
        if get_snapshot(session, settings.season, week) is None:
            import_ranking_csv(
                session,
                path,
                season=settings.season,
                week=week,
                model_version=settings.model_version,
            )
            created.append(week)
    return created
