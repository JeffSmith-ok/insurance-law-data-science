"""Compare the regex tagger with the hand-labeled sample (see CODEBOOK.md)."""

from pathlib import Path

import pandas as pd

LABEL_FIELDS = ["coverage_outcome", "primary_clause", "notes"]


def draw_sample(tagged: pd.DataFrame, n: int, out_path: Path, seed: int = 0) -> pd.DataFrame:
    """Write a labeling sheet: tagger columns blanked so labeling is blind to them."""
    sample = tagged.sample(n=min(n, len(tagged)), random_state=seed)
    sheet = sample[["opinion_id", "case_name", "court", "date_filed", "url"]].copy()
    for col in tagged.columns:
        if col.startswith(("clause_", "doctrine_")):
            sheet[col] = ""
    for col in LABEL_FIELDS:
        sheet[col] = ""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(out_path, index=False)
    return sheet


def score(tagged: pd.DataFrame, labels: pd.DataFrame, min_mentions: int = 1) -> pd.DataFrame:
    """Precision/recall per variable, treating >= min_mentions as a positive prediction."""
    labels = labels.dropna(subset=[c for c in labels.columns
                                   if c.startswith(("clause_", "doctrine_"))], how="all")
    merged = labels.merge(tagged, on="opinion_id", suffixes=("_true", "_pred"))
    rows = []
    for col in labels.columns:
        if not col.startswith(("clause_", "doctrine_")) or f"{col}_pred" not in merged:
            continue
        truth = merged[f"{col}_true"].fillna(0).astype(int) == 1
        pred = merged[f"{col}_pred"] >= min_mentions
        tp, fp, fn = (truth & pred).sum(), (~truth & pred).sum(), (truth & ~pred).sum()
        rows.append({
            "variable": col,
            "support": int(truth.sum()),
            "precision": tp / (tp + fp) if tp + fp else float("nan"),
            "recall": tp / (tp + fn) if tp + fn else float("nan"),
        })
    return pd.DataFrame(rows)
