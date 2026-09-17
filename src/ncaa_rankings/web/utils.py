from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "team"


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def subdivision(value: str | None) -> str:
    if not value:
        return "OTHER"
    cleaned = value.strip().upper()
    if cleaned == "FBS":
        return "FBS"
    if cleaned == "FCS":
        return "FCS"
    if cleaned in {"II", "DII", "DIVISION II"}:
        return "II"
    if cleaned in {"III", "DIII", "DIVISION III", "II/III"}:
        return "III"
    return cleaned or "OTHER"
