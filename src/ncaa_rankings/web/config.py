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
    admin_username: str
    admin_password: str
    season: int
    sync_live_minutes: int
    sync_idle_minutes: int
    sync_full_schedule_hours: int
    sync_rate_limit_base_minutes: int
    sync_rate_limit_max_minutes: int
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
        admin_username=os.getenv("ADMIN_USERNAME", "admin").strip() or "admin",
        admin_password=os.getenv("ADMIN_PASSWORD", ""),
        season=int(os.getenv("SEASON", "2026")),
        sync_live_minutes=max(
            int(
                os.getenv("SYNC_LIVE_MINUTES")
                or os.getenv("SYNC_SATURDAY_MINUTES")
                or "60"
            ),
            15,
        ),
        sync_idle_minutes=max(
            int(
                os.getenv("SYNC_IDLE_MINUTES")
                or os.getenv("SYNC_OTHER_DAYS_MINUTES")
                or "1440"
            ),
            60,
        ),
        sync_full_schedule_hours=max(
            int(os.getenv("SYNC_FULL_SCHEDULE_HOURS", "24")), 6
        ),
        sync_rate_limit_base_minutes=max(
            int(os.getenv("SYNC_RATE_LIMIT_BASE_MINUTES", "360")), 60
        ),
        sync_rate_limit_max_minutes=max(
            int(os.getenv("SYNC_RATE_LIMIT_MAX_MINUTES", "1440")), 360
        ),
        timezone=os.getenv("TZ", "America/Chicago"),
        model_version=os.getenv("MODEL_VERSION", "division_i_weighted_v5"),
        predictor_version=os.getenv("PREDICTOR_VERSION", "hybrid_core_v1"),
        rankings_dir=Path(os.getenv("RANKINGS_DIR", "/app/rankings")),
        bootstrap_rankings=_bool_env("BOOTSTRAP_RANKINGS", True),
        web_title=os.getenv("WEB_TITLE", "D1 Rank"),
    )
