from __future__ import annotations

from collections.abc import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_options(url: str) -> dict:
    options: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return options


settings = get_settings()
engine = create_engine(settings.database_url, **_engine_options(settings.database_url))
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_fractional_opponent_rank()
    _migrate_site_points()
    _migrate_average_ranking_fields()
    _migrate_manual_score_fields()
    _migrate_context_fields()


def _migrate_fractional_opponent_rank() -> None:
    """Upgrade existing PostgreSQL installs for averaged tied scoring ranks."""
    if engine.dialect.name != "postgresql":
        return

    columns = {
        column["name"]: str(column["type"]).upper()
        for column in inspect(engine).get_columns("ranking_game_audits")
    }
    opponent_rank_type = columns.get("opponent_rank_used", "")
    if opponent_rank_type in {"INTEGER", "INT", "INT4"}:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE ranking_game_audits "
                    "ALTER COLUMN opponent_rank_used TYPE DOUBLE PRECISION "
                    "USING opponent_rank_used::double precision"
                )
            )


def _migrate_site_points() -> None:
    """Add production site-adjustment audit storage on existing installs."""
    if engine.dialect.name != "postgresql":
        return

    columns = {
        column["name"]
        for column in inspect(engine).get_columns("ranking_game_audits")
    }
    if "site_points" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE ranking_game_audits "
                    "ADD COLUMN site_points DOUBLE PRECISION NOT NULL DEFAULT 0"
                )
            )


def _migrate_average_ranking_fields() -> None:
    """Add fields used to rank by average frozen game score."""
    if engine.dialect.name != "postgresql":
        return

    columns = {
        column["name"]
        for column in inspect(engine).get_columns("ranking_entries")
    }
    with engine.begin() as connection:
        if "raw_score" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE ranking_entries "
                    "ADD COLUMN raw_score DOUBLE PRECISION NOT NULL DEFAULT 0"
                )
            )
        if "games_played" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE ranking_entries "
                    "ADD COLUMN games_played INTEGER NOT NULL DEFAULT 0"
                )
            )


def _migrate_manual_score_fields() -> None:
    """Add manual score override metadata to existing PostgreSQL game tables."""
    if engine.dialect.name != "postgresql":
        return

    columns = {
        column["name"]
        for column in inspect(engine).get_columns("games")
    }
    with engine.begin() as connection:
        if "manual_score_override" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE games "
                    "ADD COLUMN manual_score_override BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_games_manual_score_override "
                    "ON games (manual_score_override)"
                )
            )
        if "manual_score_updated_at" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE games "
                    "ADD COLUMN manual_score_updated_at TIMESTAMP WITH TIME ZONE"
                )
            )
        if "manual_score_note" not in columns:
            connection.execute(
                text("ALTER TABLE games ADD COLUMN manual_score_note TEXT")
            )
        if "manual_score_actor" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE games "
                    "ADD COLUMN manual_score_actor VARCHAR(120)"
                )
            )


def _migrate_context_fields() -> None:
    """Add static team/venue context columns to existing PostgreSQL installs."""
    if engine.dialect.name != "postgresql":
        return

    game_columns = {
        column["name"]
        for column in inspect(engine).get_columns("games")
    }
    team_season_columns = {
        column["name"]
        for column in inspect(engine).get_columns("team_seasons")
    }

    with engine.begin() as connection:
        if "venue_id" not in game_columns:
            connection.execute(
                text("ALTER TABLE games ADD COLUMN venue_id INTEGER")
            )
        if "home_venue_id" not in team_season_columns:
            connection.execute(
                text("ALTER TABLE team_seasons ADD COLUMN home_venue_id INTEGER")
            )
        if "home_venue" not in team_season_columns:
            connection.execute(
                text("ALTER TABLE team_seasons ADD COLUMN home_venue VARCHAR(200)")
            )
        if "home_timezone" not in team_season_columns:
            connection.execute(
                text("ALTER TABLE team_seasons ADD COLUMN home_timezone VARCHAR(80)")
            )
        if "home_elevation_ft" not in team_season_columns:
            connection.execute(
                text(
                    "ALTER TABLE team_seasons "
                    "ADD COLUMN home_elevation_ft DOUBLE PRECISION"
                )
            )
        if "home_context_source" not in team_season_columns:
            connection.execute(
                text(
                    "ALTER TABLE team_seasons "
                    "ADD COLUMN home_context_source VARCHAR(120)"
                )
            )
        if "home_context_updated_at" not in team_season_columns:
            connection.execute(
                text(
                    "ALTER TABLE team_seasons "
                    "ADD COLUMN home_context_updated_at TIMESTAMP WITH TIME ZONE"
                )
            )


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
