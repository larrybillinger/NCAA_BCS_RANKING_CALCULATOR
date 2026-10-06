from __future__ import annotations

from collections.abc import Callable, Hashable
from typing import TypeVar

from sqlalchemy import event
from sqlalchemy.orm import Session

T = TypeVar("T")
_MEMO_KEY = "d1rank_memo"


def session_memo(session: Session, key: Hashable, factory: Callable[[], T]) -> T:
    """Cache a derived value for the lifetime of the current transaction.

    Pages recompute the same calibration and scoring profiles for every game
    they render. Caching them on the session makes a page do that work once.
    The cache is dropped on every commit or rollback, so the worker never
    reuses a value computed before it wrote new game data.
    """
    memo = session.info.setdefault(_MEMO_KEY, {})
    if key not in memo:
        memo[key] = factory()
    return memo[key]


@event.listens_for(Session, "after_commit")
@event.listens_for(Session, "after_rollback")
def _clear_memo(session: Session) -> None:
    session.info.pop(_MEMO_KEY, None)
