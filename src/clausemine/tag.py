"""Tag opinions with the clauses and doctrines they mention."""

import json
from pathlib import Path

import pandas as pd

from .taxonomy import CLAUSE_PATTERNS, DOCTRINE_PATTERNS

META_COLS = ["opinion_id", "case_name", "court", "date_filed", "url"]


def tag_text(text: str) -> dict[str, int]:
    """Return mention counts for every clause and doctrine key."""
    row = {f"clause_{k}": len(p.findall(text)) for k, p in CLAUSE_PATTERNS.items()}
    row |= {f"doctrine_{k}": len(p.findall(text)) for k, p in DOCTRINE_PATTERNS.items()}
    return row


def tag_file(in_path: Path, out_path: Path) -> pd.DataFrame:
    rows = []
    with in_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            text = rec.get("text") or ""
            rows.append({c: rec.get(c) for c in META_COLS}
                        | {"n_words": len(text.split())} | tag_text(text))
    df = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df
