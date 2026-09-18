from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cfbd_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    abbreviation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    seasons: Mapped[list["TeamSeason"]] = relationship(back_populates="team")


class TeamSeason(Base):
    __tablename__ = "team_seasons"
    __table_args__ = (
        UniqueConstraint("team_id", "season", name="uq_team_season"),
        Index("ix_team_season_pool", "season", "subdivision", "active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    season: Mapped[int] = mapped_column(Integer, index=True)
    subdivision: Mapped[str] = mapped_column(String(20), default="OTHER")
    conference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    team: Mapped[Team] = relationship(back_populates="seasons")


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("provider", "provider_game_id", name="uq_game_provider_id"),
        Index("ix_games_season_week", "season", "week"),
        Index("ix_games_start_time", "start_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(40), default="cfbd")
    provider_game_id: Mapped[str] = mapped_column(String(64))
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int] = mapped_column(Integer, index=True)
    season_type: Mapped[str] = mapped_column(String(30), default="regular")
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    neutral_site: Mapped[bool] = mapped_column(Boolean, default=False)
    conference_game: Mapped[bool] = mapped_column(Boolean, default=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_subdivision: Mapped[str] = mapped_column(String(20), default="OTHER")
    away_subdivision: Mapped[str] = mapped_column(String(20), default="OTHER")
    home_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])


class GameTeamStat(Base):
    __tablename__ = "game_team_stats"
    __table_args__ = (
        UniqueConstraint("game_id", "team_id", "category", name="uq_game_team_stat"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(120))
    value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RankingSnapshot(Base):
    __tablename__ = "ranking_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "season", "week", "model_version", "official", name="uq_ranking_snapshot"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int] = mapped_column(Integer, index=True)
    model_version: Mapped[str] = mapped_column(String(80))
    official: Mapped[bool] = mapped_column(Boolean, default=True)
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    entries: Mapped[list["RankingEntry"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class RankingEntry(Base):
    __tablename__ = "ranking_entries"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "team_id", name="uq_ranking_entry"),
        Index("ix_ranking_entry_rank", "snapshot_id", "rank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("ranking_snapshots.id", ondelete="CASCADE")
    )
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    raw_score: Mapped[float] = mapped_column(Float, default=0.0)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    opponent_strength: Mapped[float] = mapped_column(Float, default=0.0)
    movement: Mapped[int | None] = mapped_column(Integer, nullable=True)

    snapshot: Mapped[RankingSnapshot] = relationship(back_populates="entries")
    team: Mapped[Team] = relationship()


class RankingGameAudit(Base):
    __tablename__ = "ranking_game_audits"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "game_id", "team_id", name="uq_ranking_game_audit"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("ranking_snapshots.id"))
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    opponent_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    opponent_rank_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    opponent_points: Mapped[float] = mapped_column(Float, default=0.0)
    win_points: Mapped[float] = mapped_column(Float, default=0.0)
    margin_points: Mapped[float] = mapped_column(Float, default=0.0)
    site_points: Mapped[float] = mapped_column(Float, default=0.0)
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    game_total: Mapped[float] = mapped_column(Float, default=0.0)


class PredictionSnapshot(Base):
    __tablename__ = "prediction_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "ranking_snapshot_id",
            "predictor_version",
            name="uq_prediction_snapshot",
        ),
        Index("ix_prediction_game", "game_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    ranking_snapshot_id: Mapped[int] = mapped_column(ForeignKey("ranking_snapshots.id"))
    predictor_version: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    locks_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    official: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    home_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projected_home_points: Mapped[float] = mapped_column(Float)
    projected_away_points: Mapped[float] = mapped_column(Float)
    projected_margin: Mapped[float] = mapped_column(Float)
    home_win_probability: Mapped[float] = mapped_column(Float)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    model_detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    game: Mapped[Game] = relationship()
    ranking_snapshot: Mapped[RankingSnapshot] = relationship()


class SourceSyncRun(Base):
    __tablename__ = "source_sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(40), default="cfbd")
    endpoint: Mapped[str] = mapped_column(String(180))
    season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="running")
    rows_received: Mapped[int] = mapped_column(Integer, default=0)
    response_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
