from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .config import get_settings
from .db import SessionLocal, init_db
from .models import (
    Game,
    GameTeamStat,
    RankingEntry,
    RankingSnapshot,
    Team,
    TeamSeason,
)
from .team_identity import PROVIDER_NAME_ALIASES


@dataclass(slots=True)
class RepairResult:
    canonical_name: str
    legacy_name: str
    repaired: bool
    preserved_weeks: list[int] | None = None
    games_repointed: int = 0
    stats_repointed: int = 0
    stats_deduplicated: int = 0


def _team(session: Session, name: str) -> Team | None:
    return session.scalar(select(Team).where(Team.name == name))


def _affected_weeks(
    session: Session,
    *,
    season: int,
    model_version: str,
    team_id: int,
) -> list[int]:
    return list(
        session.scalars(
            select(RankingSnapshot.week)
            .join(RankingEntry, RankingEntry.snapshot_id == RankingSnapshot.id)
            .where(
                RankingSnapshot.season == season,
                RankingSnapshot.model_version == model_version,
                RankingSnapshot.official.is_(True),
                RankingEntry.team_id == team_id,
            )
            .order_by(RankingSnapshot.week)
        )
    )


def _frozen_games_played(
    session: Session,
    *,
    season: int,
    model_version: str,
    team_id: int,
) -> int:
    """Most games the team has in any frozen active-model snapshot."""
    return int(
        session.scalar(
            select(func.max(RankingEntry.games_played))
            .join(RankingSnapshot, RankingSnapshot.id == RankingEntry.snapshot_id)
            .where(
                RankingSnapshot.season == season,
                RankingSnapshot.model_version == model_version,
                RankingSnapshot.official.is_(True),
                RankingEntry.team_id == team_id,
            )
        )
        or 0
    )


def _repoint_games(session: Session, source_id: int, target_id: int) -> int:
    home = session.execute(
        update(Game).where(Game.home_team_id == source_id).values(home_team_id=target_id)
    ).rowcount or 0
    away = session.execute(
        update(Game).where(Game.away_team_id == source_id).values(away_team_id=target_id)
    ).rowcount or 0
    return int(home + away)


def _repoint_stats(session: Session, source_id: int, target_id: int) -> tuple[int, int]:
    repointed = 0
    deduplicated = 0
    source_rows = list(
        session.scalars(select(GameTeamStat).where(GameTeamStat.team_id == source_id))
    )
    for row in source_rows:
        existing = session.scalar(
            select(GameTeamStat).where(
                GameTeamStat.game_id == row.game_id,
                GameTeamStat.team_id == target_id,
                GameTeamStat.category == row.category,
            )
        )
        if existing is not None:
            session.delete(row)
            deduplicated += 1
            continue
        row.team_id = target_id
        session.add(row)
        repointed += 1
    return repointed, deduplicated


def _merge_current_season(
    session: Session,
    *,
    season: int,
    source: Team,
    target: Team,
) -> None:
    source_row = session.scalar(
        select(TeamSeason).where(
            TeamSeason.team_id == source.id,
            TeamSeason.season == season,
        )
    )
    target_row = session.scalar(
        select(TeamSeason).where(
            TeamSeason.team_id == target.id,
            TeamSeason.season == season,
        )
    )

    if target_row is None and source_row is not None:
        target_row = TeamSeason(
            team_id=target.id,
            season=season,
            subdivision=source_row.subdivision,
            conference=source_row.conference,
            active=True,
            home_venue_id=source_row.home_venue_id,
            home_venue=source_row.home_venue,
            home_timezone=source_row.home_timezone,
            home_elevation_ft=source_row.home_elevation_ft,
            home_context_source=source_row.home_context_source,
            home_context_updated_at=source_row.home_context_updated_at,
        )
        session.add(target_row)
    elif target_row is not None:
        target_row.active = True
        session.add(target_row)

    if source_row is not None:
        source_row.active = False
        session.add(source_row)


def repair_known_team_identities(
    session: Session,
    *,
    season: int,
    model_version: str,
) -> list[RepairResult]:
    """Merge known provider-name duplicates going forward.

    Frozen official snapshots, and the predictions locked against them, are
    left exactly as published: old games are not recursively revalued and
    official predictions are never rewritten. The legacy row leaves the active
    pool, so every ranking calculated after the repair uses the corrected pool.

    This is only safe when the legacy row carries no frozen game results; if it
    does, moving its games forward would silently drop those results, so the
    repair refuses and leaves everything unchanged.
    """
    results: list[RepairResult] = []

    for canonical_name, aliases in PROVIDER_NAME_ALIASES.items():
        canonical = _team(session, canonical_name)
        if canonical is None:
            continue

        for legacy_name in aliases:
            legacy = _team(session, legacy_name)
            if legacy is None or legacy.id == canonical.id:
                continue
            if canonical.cfbd_id is None:
                raise RuntimeError(
                    f"Refusing to merge {legacy_name!r} into {canonical_name!r}: "
                    "the canonical row has no CFBD ID."
                )
            if legacy.cfbd_id not in {None, canonical.cfbd_id}:
                raise RuntimeError(
                    f"Refusing to merge {legacy_name!r} into {canonical_name!r}: "
                    "the rows have different CFBD IDs."
                )
            if _frozen_games_played(
                session,
                season=season,
                model_version=model_version,
                team_id=legacy.id,
            ):
                raise RuntimeError(
                    f"Refusing to merge {legacy_name!r} into {canonical_name!r}: "
                    "the legacy row has game results in frozen official rankings. "
                    "A forward repair would drop them; this needs an explicit "
                    "rebuild decision."
                )

            legacy_season = session.scalar(
                select(TeamSeason).where(
                    TeamSeason.team_id == legacy.id,
                    TeamSeason.season == season,
                )
            )
            was_active = bool(legacy_season and legacy_season.active)
            preserved_weeks = _affected_weeks(
                session,
                season=season,
                model_version=model_version,
                team_id=legacy.id,
            )

            games_repointed = _repoint_games(session, legacy.id, canonical.id)
            stats_repointed, stats_deduplicated = _repoint_stats(
                session,
                legacy.id,
                canonical.id,
            )
            _merge_current_season(
                session,
                season=season,
                source=legacy,
                target=canonical,
            )
            session.commit()

            results.append(
                RepairResult(
                    canonical_name=canonical_name,
                    legacy_name=legacy_name,
                    repaired=bool(
                        was_active or games_repointed or stats_repointed or stats_deduplicated
                    ),
                    preserved_weeks=preserved_weeks,
                    games_repointed=games_repointed,
                    stats_repointed=stats_repointed,
                    stats_deduplicated=stats_deduplicated,
                )
            )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge known duplicate CFBD team identities going forward."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Required safety flag. The command otherwise makes no changes.",
    )
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("No changes made. Re-run with --apply after taking a database backup.")

    settings = get_settings()
    init_db()
    with SessionLocal() as session:
        results = repair_known_team_identities(
            session,
            season=settings.season,
            model_version=settings.model_version,
        )
    print(json.dumps([asdict(result) for result in results], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
