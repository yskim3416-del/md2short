"""외부 API 재시도: 429/5xx/timeout/transport error 3회, 0.5/1.0/2.0s backoff."""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx

BACKOFF_S = (0.5, 1.0, 2.0)
DEFAULT_TIMEOUT = httpx.Timeout(120.0, connect=15.0)


class ApiError(RuntimeError):
    """재시도 후에도 실패한 외부 API 호출."""

    def __init__(self, message: str, status_code: int | None = None, body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def _retryable(status: int) -> bool:
    return status == 429 or status >= 500


def post_with_retry(
    client: httpx.Client,
    url: str,
    *,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs: Any,
) -> httpx.Response:
    """POST 후 2xx 응답을 돌려준다. 재시도 불가 4xx는 즉시 ApiError."""
    last: str = ""
    for attempt in range(len(BACKOFF_S) + 1):
        try:
            resp = client.post(url, **kwargs)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last = f"{type(exc).__name__}: {exc}"
        else:
            if resp.is_success:
                return resp
            if not _retryable(resp.status_code):
                raise ApiError(
                    f"POST {url} failed: HTTP {resp.status_code}: {resp.text[:500]}",
                    resp.status_code,
                    resp.text,
                )
            last = f"HTTP {resp.status_code}: {resp.text[:300]}"
        if attempt < len(BACKOFF_S):
            sleep(BACKOFF_S[attempt])
    raise ApiError(f"POST {url} failed after {len(BACKOFF_S)} retries: {last}")
