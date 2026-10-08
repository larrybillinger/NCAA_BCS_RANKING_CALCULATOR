from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Team, TeamSeason

DIVISION_I = {"FBS", "FCS"}

# CFBD occasionally changes the display name for a school while keeping the
# provider ID stable. Bundled/historical rows may predate that provider ID, so
# these aliases let the first provider-backed sync attach the durable ID to the
# existing school instead of creating a second active team.
PROVIDER_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "Pennsylvania": ("Penn",),
}
_ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in PROVIDER_NAME_ALIASES.items()
    for alias in aliases
}


def identity_names(name: str) -> tuple[str, ...]:
    """Return the provider name plus known historical aliases for one school."""
    canonical = _ALIAS_TO_CANONICAL.get(name, name)
    aliases = PROVIDER_NAME_ALIASES.get(canonical, ())
    ordered = [name]
    if canonical not in ordered:
        ordered.append(canonical)
    for alias in aliases:
        if alias not in ordered:
            ordered.append(alias)
    return tuple(ordered)


def find_provider_team(session: Session, *, cfbd_id: int | None, name: str) -> Team | None:
    """Resolve a provider team by durable ID, exact name, then a known alias."""
    if cfbd_id is not None:
        team = session.scalar(select(Team).where(Team.cfbd_id == cfbd_id))
        if team is not None:
            return team

    team = session.scalar(select(Team).where(Team.name == name))
    if team is not None:
        return team

    for candidate_name in identity_names(name):
        if candidate_name == name:
            continue
        candidate = session.scalar(select(Team).where(Team.name == candidate_name))
        if candidate is None:
            continue
        if cfbd_id is None or candidate.cfbd_id in {None, cfbd_id}:
            return candidate
    return None


def reconcile_active_roster(
    session: Session,
    *,
    season: int,
    seen_team_ids: set[int],
) -> int:
    """Deactivate D-I season rows absent from a successful full provider roster."""
    deactivated = 0
    rows = session.scalars(
        select(TeamSeason).where(
            TeamSeason.season == season,
            TeamSeason.active.is_(True),
            TeamSeason.subdivision.in_(tuple(DIVISION_I)),
        )
    )
    for row in rows:
        if row.team_id in seen_team_ids:
            continue
        row.active = False
        session.add(row)
        deactivated += 1
    return deactivated
