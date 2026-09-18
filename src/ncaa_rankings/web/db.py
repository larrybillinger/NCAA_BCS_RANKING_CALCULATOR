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


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
