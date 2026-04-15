from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    *,
    retries: int = 2,
    base_delay: float = 0.25,
    backoff_factor: float = 2.0,
) -> tuple[T | None, list[str]]:
    errors: list[str] = []
    for attempt in range(retries + 1):
        try:
            return fn(), errors
        except Exception as exc:  # pragma: no cover - exercised in tests
            errors.append(f"attempt={attempt + 1}: {exc}")
            if attempt < retries:
                time.sleep(base_delay * (backoff_factor**attempt))
    return None, errors
