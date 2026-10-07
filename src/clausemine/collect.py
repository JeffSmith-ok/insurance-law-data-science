"""CourtListener API client: search for opinions, then fetch each opinion's text.

Docs: https://www.courtlistener.com/help/api/rest/
Writes one JSON object per opinion to data/raw/opinions.jsonl. Re-running appends only
opinions not already in the file, so an interrupted pull can be resumed.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Iterator

import requests

from . import RAW_PATH

BASE = "https://www.courtlistener.com/api/rest/v4"
# Preference order for opinion text; the first non-empty field wins.
TEXT_FIELDS = ["html_with_citations", "html_lawbox", "html_columbia", "xml_harvard",
               "html", "plain_text"]


class CourtListener:
    def __init__(self, token: str | None = None, delay: float = 0.75,
                 session: requests.Session | None = None, max_retries: int = 4):
        token = token or os.environ.get("COURTLISTENER_TOKEN")
        if not token:
            raise RuntimeError("Set COURTLISTENER_TOKEN (free token: "
                               "https://www.courtlistener.com/help/api/rest/)")
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"Token {token}",
                                     "User-Agent": "clausemine/0.1 (research)"})
        self.delay = delay
        self.max_retries = max_retries

    def _get(self, url: str, params: dict | None = None) -> dict:
        for attempt in range(self.max_retries + 1):
            resp = self.session.get(url, params=params, timeout=60)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == self.max_retries:
                    resp.raise_for_status()
                wait = float(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                time.sleep(wait)
                continue
            resp.raise_for_status()
            time.sleep(self.delay)
            return resp.json()
        raise RuntimeError("unreachable")

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
        client: CourtListener | None = None, **filters) -> int:
    client = client or CourtListener()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen = existing_ids(out_path)
    written = 0
    with open(out_path, "a", encoding="utf-8") as f:
        for meta in client.search(query, max_results=max_results, **filters):
            if meta["opinion_id"] in seen:
                continue
            meta["query"] = query
            meta["text"] = client.opinion_text(meta["opinion_id"])
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            f.flush()
            seen.add(meta["opinion_id"])
            written += 1
            print(f"[{written}] {meta['court']} {meta['date_filed']} {meta['case_name']}")
    return written
