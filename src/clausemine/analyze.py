"""Summary tables for the three research questions. Writes CSVs to reports/."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import LABELS_PATH, REPORTS, TAGGED_PATH
from .taxonomy import clause_columns, doctrine_columns


def _strip(col: str) -> str:
    return col.split("_", 1)[1]


def clause_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """RQ1: how many opinions mention each clause."""
    counts = df[clause_columns()].sum().rename(_strip)
    out = pd.DataFrame({"opinions": counts.astype(int),
                        "share": (counts / len(df)).round(4)})
    return out.sort_values("opinions", ascending=False).rename_axis("clause").reset_index()


def clause_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """RQ1 over time: opinions mentioning each clause, per filing year."""
    years = pd.to_datetime(df["date_filed"], errors="coerce").dt.year
    table = df[clause_columns()].groupby(years).sum().rename(columns=_strip)
    table.insert(0, "total_opinions", df.groupby(years).size())
    return table.rename_axis("year").reset_index()


def doctrine_by_clause(df: pd.DataFrame) -> pd.DataFrame:
    """RQ2: among opinions tagged with a clause, the share that also invoke each doctrine."""
    rows = []
    for c in clause_columns():
        sub = df[df[c] == 1]
        row = {"clause": _strip(c), "opinions": len(sub)}
        for d in doctrine_columns():
            row[_strip(d)] = round(float(sub[d].mean()), 4) if len(sub) else float("nan")
        rows.append(row)
    return pd.DataFrame(rows).sort_values("opinions", ascending=False)


def clause_by_court(df: pd.DataFrame, min_opinions: int = 5) -> pd.DataFrame:
    """RQ3: clause mention rates by court (courts with at least `min_opinions`)."""
    sizes = df.groupby("court").size()
    keep = sizes[sizes >= min_opinions].index
    sub = df[df["court"].isin(keep)]
    table = sub.groupby("court")[clause_columns()].mean().round(4).rename(columns=_strip)
    table.insert(0, "opinions", sizes[keep])
    return table.sort_values("opinions", ascending=False).reset_index()


def outcomes_by_clause(labels: pd.DataFrame) -> pd.DataFrame:
    """RQ2/RQ3 on hand labels: coverage outcome by primary clause."""
    lab = labels[labels["coverage_outcome"].fillna("").astype(str).str.strip() != ""]
    if lab.empty:
        return pd.DataFrame()
    return (pd.crosstab(lab["primary_clause"].fillna("(blank)"), lab["coverage_outcome"],
                        margins=True, margins_name="total")
            .rename_axis(index="primary_clause", columns=None).reset_index())


def run(tagged_path: Path = TAGGED_PATH, labels_path: Path = LABELS_PATH,
        out_dir: Path = REPORTS) -> dict[str, pd.DataFrame]:
    df = pd.read_csv(tagged_path)
    tables = {
        "clause_frequency": clause_frequency(df),
        "clause_by_year": clause_by_year(df),
        "doctrine_by_clause": doctrine_by_clause(df),
        "clause_by_court": clause_by_court(df),
    }
    if labels_path.exists():
        tables["outcomes_by_clause"] = outcomes_by_clause(pd.read_csv(labels_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        if not table.empty:
            table.to_csv(out_dir / f"{name}.csv", index=False)
    return tables
