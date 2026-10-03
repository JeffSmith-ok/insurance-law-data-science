"""Collect insurance coverage opinions from the CourtListener REST API (v4).

Docs: https://www.courtlistener.com/help/api/rest/
"""

import html
import json
import os
import re
import time
from pathlib import Path
from typing import Iterator

import requests

BASE_URL = "https://www.courtlistener.com/api/rest/v4"
DEFAULT_QUERY = '(insurer OR insurance) AND (exclusion OR "duty to defend") AND coverage'


class CourtListener:
    def __init__(self, token: str | None = None, delay: float = 1.0):
        token = token or os.environ.get("COURTLISTENER_TOKEN")
        if not token:
            raise RuntimeError("Set COURTLISTENER_TOKEN (free at courtlistener.com).")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Token {token}"
        self.delay = delay

    def _get(self, url: str, params: dict | None = None) -> dict:
        resp = self.session.get(url, params=params, timeout=60)
        resp.raise_for_status()
        time.sleep(self.delay)  # stay well inside rate limits
        return resp.json()

    def search(self, query: str, courts: str | None = None,
               filed_after: str | None = None) -> Iterator[dict]:
        """Yield opinion search results, following pagination."""
        params = {"q": query, "type": "o", "order_by": "dateFiled desc"}
        if courts:
            params["court"] = courts
        if filed_after:
            params["filed_after"] = filed_after
        url: str | None = f"{BASE_URL}/search/"
        while url:
            page = self._get(url, params)
            yield from page.get("results", [])
            url, params = page.get("next"), None  # "next" already carries the query

    def opinion_text(self, opinion_id: int) -> str:
        op = self._get(f"{BASE_URL}/opinions/{opinion_id}/")
        if op.get("plain_text"):
            return op["plain_text"]
        for field in ("html_with_citations", "html", "html_lawbox", "xml_harvard"):
            if op.get(field):
                return strip_html(op[field])
        return ""


def strip_html(markup: str) -> str:
    text = re.sub(r"<[^>]+>", " ", markup)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def collect(out_path: Path, query: str = DEFAULT_QUERY, max_opinions: int = 200,
            courts: str | None = None, filed_after: str | None = None,
            client: CourtListener | None = None) -> int:
    """Write up to max_opinions records to a JSONL file, skipping IDs already present."""
    client = client or CourtListener()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if out_path.exists():
        with out_path.open() as f:
            seen = {json.loads(line)["opinion_id"] for line in f if line.strip()}

    written = 0
    with out_path.open("a") as f:
        for hit in client.search(query, courts=courts, filed_after=filed_after):
            for op in hit.get("opinions", []):
                if written >= max_opinions:
                    return written
                if op["id"] in seen:
                    continue
                record = {
                    "opinion_id": op["id"],
                    "cluster_id": hit.get("cluster_id"),
                    "case_name": hit.get("caseName"),
                    "court": hit.get("court_id"),
                    "date_filed": hit.get("dateFiled"),
                    "citation": hit.get("citation"),
                    "url": "https://www.courtlistener.com" + hit.get("absolute_url", ""),
                    "text": client.opinion_text(op["id"]),
                }
                f.write(json.dumps(record) + "\n")
                seen.add(op["id"])
                written += 1
    return written
