"""Draw a blind labeling sample and compare the tagger with hand labels."""

from __future__ import annotations

import re

from pathlib import Path

import pandas as pd

from . import DATA, ID_COLS, LABELS_PATH, REPORTS, TAGGED_PATH
from .taxonomy import tag_columns

OUTCOME_COLS = ["coverage_outcome", "primary_clause", "notes", "labeler"]
OUTCOMES = {"policyholder", "insurer", "mixed", "none"}


def _name_key(name: str) -> str:
    """Case-name key for spotting duplicate clusters: lowercase letters only, first 40."""
    return re.sub(r"[^a-z]", "", str(name).lower())[:40]


def draw_sample(tagged_path: Path = TAGGED_PATH, out_path: Path = LABELS_PATH,
                n: int = 150, seed: int = 42, force: bool = False,
                skip: list[Path] | None = None, one_per_case: bool = False,
                excluded_path: Path | None = None) -> pd.DataFrame:
    """Write a blank labeling sheet. Tagger predictions are NOT included, so labeling is blind.

    ``skip``: earlier labeling sheets; every case (cluster) in them is left out, so a second
    sample tests the tagger only on cases it was never checked or tuned against.
    ``one_per_case``: draw at most one opinion per case (the lead or combined opinion when
    there is one), so labels are not spent on duplicate copies of the same decision.
    ``excluded_path``: the non-coverage case list (default data/labels/excluded_cases.csv).
    """
    if out_path.exists() and not force:
        raise FileExistsError(f"{out_path} exists; pass force=True (--force) to overwrite "
                              "hand labels.")
    tagged = pd.read_csv(tagged_path)
    drop: set[int] = set()
    skip_names: set[str] = set()
    for path in skip or []:
        earlier = pd.read_csv(path)
        drop |= set(earlier["cluster_id"].dropna().astype(int))
        if "case_name" in earlier:
            skip_names |= set(earlier["case_name"].dropna().map(_name_key))
    if skip_names:  # CourtListener sometimes files one decision under two cluster IDs
        drop |= set(tagged.loc[tagged["case_name"].fillna("").map(_name_key).isin(skip_names), "cluster_id"])
    excluded_path = excluded_path or (DATA / "labels" / "excluded_cases.csv")
    if excluded_path.exists():
        drop |= set(pd.read_csv(excluded_path)["cluster_id"].astype(int))
    pool = tagged[~tagged["cluster_id"].isin(drop)]
    if one_per_case:
        rank = pool["opinion_type"].map({"combined-opinion": 0, "lead-opinion": 1}).fillna(2)
        pool = (pool.assign(_rank=rank).sort_values(["cluster_id", "_rank", "opinion_id"])
                .drop_duplicates("cluster_id").drop(columns="_rank"))
    sample = pool.sample(n=min(n, len(pool)), random_state=seed)[ID_COLS].copy()
    for col in tag_columns() + OUTCOME_COLS:
        sample[col] = ""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sample.sort_values("opinion_id").to_csv(out_path, index=False)
    return sample


def binary_metrics(pred: pd.Series, gold: pd.Series) -> dict:
    pred, gold = pred.astype(int), gold.astype(int)
    tp = int(((pred == 1) & (gold == 1)).sum())
    fp = int(((pred == 1) & (gold == 0)).sum())
    fn = int(((pred == 0) & (gold == 1)).sum())
    tn = int(((pred == 0) & (gold == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if tp and (precision + recall) else float("nan"))
    return {"n": tp + fp + fn + tn, "support": tp + fn, "tp": tp, "fp": fp, "fn": fn,
            "tn": tn, "precision": precision, "recall": recall, "f1": f1,
            "kappa": cohen_kappa(pred, gold)}


def cohen_kappa(a: pd.Series, b: pd.Series) -> float:
    a, b = pd.Series(a).astype(str).reset_index(drop=True), pd.Series(b).astype(str).reset_index(drop=True)
    n = len(a)
    if n == 0:
        return float("nan")
    p_o = float((a == b).mean())
    cats = set(a) | set(b)
    p_e = sum(float((a == c).mean()) * float((b == c).mean()) for c in cats)
    if p_e == 1:
        return 1.0 if p_o == 1 else float("nan")
    return (p_o - p_e) / (1 - p_e)


def _clean_labels(labels: pd.DataFrame) -> pd.DataFrame:
    labels = labels.copy()
    for col in tag_columns():
        if col in labels:
            labels[col] = pd.to_numeric(labels[col], errors="coerce")
            bad = labels[col].notna() & ~labels[col].isin([0, 1])
            if bad.any():
                raise ValueError(f"{col}: values must be 0 or 1 (rows {list(labels.index[bad])})")
    if "coverage_outcome" in labels:
        out = labels["coverage_outcome"].fillna("").astype(str).str.strip().str.lower()
        bad = (out != "") & ~out.isin(OUTCOMES)
        if bad.any():
            raise ValueError(f"coverage_outcome must be one of {sorted(OUTCOMES)}: "
                             f"{sorted(set(out[bad]))}")
        labels["coverage_outcome"] = out
    return labels


def evaluate(tagged_path: Path = TAGGED_PATH, labels_path: Path = LABELS_PATH,
             out_path: Path | None = REPORTS / "evaluation.csv") -> pd.DataFrame:
    tagged = pd.read_csv(tagged_path)
    labels = _clean_labels(pd.read_csv(labels_path))
    merged = labels.merge(tagged, on="opinion_id", suffixes=("_gold", "_pred"))
    rows = []
    for col in tag_columns():
        sub = merged[[f"{col}_gold", f"{col}_pred"]].dropna()
        if sub.empty:
            continue
        rows.append({"variable": col, **binary_metrics(sub[f"{col}_pred"], sub[f"{col}_gold"])})
    report = pd.DataFrame(rows)
    if out_path is not None and not report.empty:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(out_path, index=False)
    return report


def agreement(labels_a: Path, labels_b: Path,
              out_path: Path | None = REPORTS / "agreement.csv") -> pd.DataFrame:
    """Inter-rater agreement (Cohen's kappa) between two labelers on overlapping opinions."""
    a = _clean_labels(pd.read_csv(labels_a))
    b = _clean_labels(pd.read_csv(labels_b))
    merged = a.merge(b, on="opinion_id", suffixes=("_a", "_b"))
    rows = []
    for col in tag_columns() + ["coverage_outcome", "primary_clause"]:
        if f"{col}_a" not in merged:
            continue
        sub = merged[[f"{col}_a", f"{col}_b"]].replace("", pd.NA).dropna()
        if sub.empty:
            continue
        rows.append({"variable": col, "n": len(sub),
                     "pct_agree": float((sub[f"{col}_a"].astype(str) == sub[f"{col}_b"].astype(str)).mean()),
                     "kappa": cohen_kappa(sub[f"{col}_a"], sub[f"{col}_b"])})
    report = pd.DataFrame(rows)
    if out_path is not None and not report.empty:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(out_path, index=False)
    return report
