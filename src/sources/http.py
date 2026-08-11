"""Shared HTTP client for source fetchers.

Sources are polled at most once a day by the scheduled workflow, but a
hung connection or an unbounded retry loop on a transient failure could
still tie up a run indefinitely or hammer an upstream service that only
tolerates us as a courtesy (EFFIS's WFS endpoint is undocumented, FIRMS
enforces a MAP_KEY transaction limit). This session applies one consistent
policy everywhere: an identifying User-Agent, a bounded timeout, and a
small number of backed-off retries limited to responses that are actually
likely to be transient (429/5xx), rather than each source rolling its own.
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "Mozilla/5.0 (compatible; GreekFireWatch/1.0; +https://github.com/pgeorgantopoulos/greek-fire-watch)"
DEFAULT_TIMEOUT = 30


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


session = _build_session()


def get(url: str, **kwargs: object) -> requests.Response:
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    return session.get(url, **kwargs)
