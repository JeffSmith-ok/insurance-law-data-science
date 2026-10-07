"""Apply the taxonomy to opinion text."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from . import ID_COLS, RAW_PATH, TAGGED_PATH
from .taxonomy import CLAUSE_PATTERNS, DOCTRINE_PATTERNS

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_QUOTES = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
                         "\u2010": "-", "\u2011": "-", "\u2013": "-", "\u2014": "-"})


def normalize(text: str) -> str:
    """Strip HTML, unescape entities, straighten quotes/dashes, collapse whitespace."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text).translate(_QUOTES)
    return _WS_RE.sub(" ", text).strip()


def count_hits(text: str, patterns: dict[str, list[re.Pattern[str]]]) -> dict[str, int]:
    return {key: sum(len(p.findall(text)) for p in pats) for key, pats in patterns.items()}


def tag_text(text: str, min_hits: int = 1) -> dict[str, int]:
    """Return {"clause_<key>": 0/1, ..., "doctrine_<key>": 0/1} for one opinion."""
    text = normalize(text)
    row: dict[str, int] = {}
    for prefix, patterns in (("clause", CLAUSE_PATTERNS), ("doctrine", DOCTRINE_PATTERNS)):
        for key, n in count_hits(text, patterns).items():
            row[f"{prefix}_{key}"] = int(n >= min_hits)
    return row


def read_jsonl(path: Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def tag_records(records: Iterable[dict], min_hits: int = 1) -> pd.DataFrame:
    rows = []
    for rec in records:
        row = {c: rec.get(c) for c in ID_COLS}
        text = rec.get("text") or ""
        row["n_chars"] = len(text)
        row.update(tag_text(text, min_hits=min_hits))
        rows.append(row)
    return pd.DataFrame(rows)


def run(raw_path: Path = RAW_PATH, out_path: Path = TAGGED_PATH, min_hits: int = 1) -> pd.DataFrame:
    df = tag_records(read_jsonl(raw_path), min_hits=min_hits)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df
