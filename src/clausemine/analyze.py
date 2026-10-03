"""Summary tables over tagged opinions."""

from pathlib import Path

import pandas as pd


def _flags(df: pd.DataFrame, prefix: str, min_mentions: int) -> pd.DataFrame:
    cols = [c for c in df.columns if c.startswith(prefix)]
    return (df[cols] >= min_mentions).rename(columns=lambda c: c.removeprefix(prefix))


def clause_frequency(df: pd.DataFrame, min_mentions: int = 2) -> pd.Series:
    """Share of opinions mentioning each clause at least min_mentions times."""
    return _flags(df, "clause_", min_mentions).mean().sort_values(ascending=False)


def clause_by_year(df: pd.DataFrame, min_mentions: int = 2) -> pd.DataFrame:
    year = pd.to_datetime(df["date_filed"], errors="coerce").dt.year.rename("year")
    return _flags(df, "clause_", min_mentions).groupby(year).sum().astype(int)


def clause_by_doctrine(df: pd.DataFrame, doctrine: str = "contra_proferentem",
                       min_mentions: int = 2) -> pd.Series:
    """Among opinions discussing each clause, share that also invoke the doctrine."""
    clauses = _flags(df, "clause_", min_mentions)
    doc = df[f"doctrine_{doctrine}"] >= 1
    return pd.Series({c: doc[clauses[c]].mean() if clauses[c].any() else float("nan")
                      for c in clauses.columns}).sort_values(ascending=False)


def write_reports(df: pd.DataFrame, out_dir: Path, min_mentions: int = 2) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    clause_frequency(df, min_mentions).to_csv(out_dir / "clause_frequency.csv", header=["share"])
    clause_by_year(df, min_mentions).to_csv(out_dir / "clause_by_year.csv")
    clause_by_doctrine(df, min_mentions=min_mentions).to_csv(
        out_dir / "clause_contra_proferentem.csv", header=["share"])
