"""CourtListener API client: search for opinions, then fetch each opinion's text.

Docs: https://www.courtlistener.com/help/api/rest/
Writes one JSON object per opinion to data/raw/opinions.jsonl. Re-running appends only
opinions not already in the file, so an interrupted pull can be resumed.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterator

import requests

from . import RAW_PATH

BASE = "https://www.courtlistener.com/api/rest/v4"
# Preference order for opinion text; the first non-empty field wins.
TEXT_FIELDS = ["html_with_citations", "html_lawbox", "html_columbia", "xml_harvard",
               "html", "plain_text"]


class CourtListener:
    """Small CourtListener client that stays under the API's rate limits.

    CourtListener caps how many requests an account may make per hour. When it answers
    429 Too Many Requests it says how long to wait (Retry-After, often tens of minutes).
    This client prints that wait and the time it will resume, sleeps through it, and
    carries on, so a long pull never sits silently.
    """

    def __init__(self, token: str | None = None, delay: float = 2.5,
                 session: requests.Session | None = None, max_retries: int = 4,
                 max_rate_limit_waits: int = 6, sleep=time.sleep):
        token = token or os.environ.get("COURTLISTENER_TOKEN")
        if not token:
            raise RuntimeError("Set COURTLISTENER_TOKEN (free token: "
                               "https://www.courtlistener.com/help/api/rest/)")
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"Token {token}",
                                     "User-Agent": "clausemine/0.1 (research)"})
        self.delay = delay
        self.max_retries = max_retries
        self.max_rate_limit_waits = max_rate_limit_waits
        self._sleep = sleep

    def _wait(self, seconds: float, reason: str) -> None:
        """Sleep, telling the user why, for how long, and when work resumes."""
        seconds = max(1.0, seconds)
        resume = datetime.now() + timedelta(seconds=seconds)
        print(f"  {reason}: waiting {_fmt(seconds)}, resuming about "
              f"{resume.strftime('%I:%M %p').lstrip('0')} (Ctrl+C is safe; rerun to resume)",
              file=sys.stderr, flush=True)
        remaining = seconds
        while remaining > 0:
            step = min(remaining, 300.0)
            self._sleep(step)
            remaining -= step
            if remaining > 0:
                print(f"  ...still waiting, {_fmt(remaining)} left", file=sys.stderr, flush=True)

    def _get(self, url: str, params: dict | None = None) -> dict:
        errors = 0
        rate_waits = 0
        while True:
            try:
                resp = self.session.get(url, params=params, timeout=60)
            except (requests.ConnectionError, requests.Timeout) as exc:
                errors += 1
                if errors > self.max_retries:
                    raise
                self._wait(2 ** errors * 5, f"Network problem ({type(exc).__name__})")
                continue

            if resp.status_code == 429:
                rate_waits += 1
                if rate_waits > self.max_rate_limit_waits:
                    resp.raise_for_status()
                wait = _retry_after(resp.headers.get("Retry-After"), default=60.0)
                self._wait(wait + 5, "CourtListener rate limit reached")
                continue

            if resp.status_code >= 500:
                errors += 1
                if errors > self.max_retries:
                    resp.raise_for_status()
                wait = _retry_after(resp.headers.get("Retry-After"), default=2 ** errors * 5)
                self._wait(wait, f"CourtListener server error {resp.status_code}")
                continue

            resp.raise_for_status()
            self._sleep(self.delay)
            return resp.json()

    def search(self, query: str, max_results: int = 200, **filters) -> Iterator[dict]:
        """Yield one dict per *opinion* (a search hit is a cluster that may hold several)."""
        params = {"q": query, "type": "o", "order_by": "score desc", **filters}
        url: str | None = f"{BASE}/search/"
        n = 0
        while url and n < max_results:
            data = self._get(url, params=params)
            params = None  # the `next` URL already carries the query string
            for hit in data.get("results", []):
                for op in hit.get("opinions") or []:
                    if n >= max_results:
                        return
                    yield {
                        "opinion_id": op.get("id"),
                        "cluster_id": hit.get("cluster_id"),
                        "case_name": hit.get("caseName"),
                        "court": hit.get("court_id"),
                        "date_filed": hit.get("dateFiled"),
                        "opinion_type": op.get("type"),
                        "url": f"https://www.courtlistener.com{hit.get('absolute_url', '')}",
                    }
                    n += 1
            url = data.get("next")

    def opinion_text(self, opinion_id: int) -> str:
        data = self._get(f"{BASE}/opinions/{opinion_id}/",
                         params={"fields": ",".join(TEXT_FIELDS)})
        return extract_text(data)


def _retry_after(value: str | None, default: float) -> float:
    """Seconds to wait from a Retry-After header (a number of seconds or an HTTP date)."""
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
        return max(0.0, (when - datetime.now(when.tzinfo)).total_seconds())
    except (TypeError, ValueError):
        return default


def _fmt(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 90:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 90:
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min"


def extract_text(opinion: dict) -> str:
    for field in TEXT_FIELDS:
        value = opinion.get(field)
        if value and value.strip():
            return value
    return ""


def existing_ids(path: Path) -> set:
    if not path.exists():
        return set()
    ids = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ids.add(json.loads(line).get("opinion_id"))
    return ids


def run(query: str, max_results: int = 200, out_path: Path = RAW_PATH,
        client: CourtListener | None = None, delay: float = 2.5, max_scan: int = 2000,
        **filters) -> int:
    """Download up to ``max_results`` *new* opinions for ``query``.

    Opinions already in ``out_path`` are skipped and do not count toward ``max_results``, so
    a search that overlaps an earlier one keeps paging until it finds new cases. ``max_scan``
    caps how many search hits are examined in total (paging is cheap: one request per 20 hits;
    each new opinion costs one more request for its text).
    """
    client = client or CourtListener(delay=delay)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen = existing_ids(out_path)
    written = skipped = 0
    with open(out_path, "a", encoding="utf-8") as f:
        for meta in client.search(query, max_results=max_scan, **filters):
            if meta["opinion_id"] in seen:
                skipped += 1
                continue
            meta["query"] = query
            meta["text"] = client.opinion_text(meta["opinion_id"])
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            f.flush()
            seen.add(meta["opinion_id"])
            written += 1
            print(f"[{written}] {meta['court']} {meta['date_filed']} {meta['case_name']}")
            if written >= max_results:
                break  # stop before paging further
    if skipped:
        print(f"  ({skipped} hits were already collected and skipped)")
    return written
