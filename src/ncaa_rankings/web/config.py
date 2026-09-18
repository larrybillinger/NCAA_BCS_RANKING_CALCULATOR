from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    cfbd_api_key: str
    cfbd_base_url: str
    season: int
    sync_minutes: int
    timezone: str
    model_version: str
    predictor_version: str
    rankings_dir: Path
    bootstrap_rankings: bool
    web_title: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "sqlite+pysqlite:////tmp/ncaa-rankings.db",
        ),
        cfbd_api_key=os.getenv("CFBD_API_KEY", "").strip(),
        cfbd_base_url=os.getenv(
            "CFBD_BASE_URL", "https://api.collegefootballdata.com"
        ).rstrip("/"),
        season=int(os.getenv("SEASON", "2026")),
        sync_minutes=max(int(os.getenv("SYNC_MINUTES", "15")), 5),
        timezone=os.getenv("TZ", "America/Chicago"),
        model_version=os.getenv("MODEL_VERSION", "division_i_weighted_v5"),
        predictor_version=os.getenv("PREDICTOR_VERSION", "rank_gap_v3"),
        rankings_dir=Path(os.getenv("RANKINGS_DIR", "/app/rankings")),
        bootstrap_rankings=_bool_env("BOOTSTRAP_RANKINGS", True),
        web_title=os.getenv("WEB_TITLE", "D1 Rank"),
    )
