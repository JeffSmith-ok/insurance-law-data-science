"""Website findings: one JSON file with every number shown on smithcapital.dev.

Three blocks:
  * ``tagged``    clause and doctrine rates by dispute type, from the tagger, over every collected case
  * ``labeled``   doctrine and outcome rates by dispute type, from the hand-labeled sample
  * ``accuracy``  tagger precision/recall against the hand labels (density rule vs. single mention)

Counting unit is the case (CourtListener cluster): a case with several opinions counts once,
and a variable is 1 for the case if it is 1 for any of its opinions. Cases listed in
``data/labels/excluded_cases.csv`` (search hits that are not insurance coverage disputes) are dropped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import DATA, LABELS_PATH, RAW_PATH, REPORTS, TAGGED_PATH
from .evaluate import _clean_labels, binary_metrics
from .tag import read_jsonl, tag_text
from .taxonomy import tag_columns

EXCLUDED_PATH = DATA / "labels" / "excluded_cases.csv"
FINDINGS_PATH = REPORTS / "findings.json"

# Dispute type, assigned from the CourtListener search that found the case.
GROUPS = [
    ("pol", "Pollution exclusion", "pollution exclusion"),
    ("con", "Construction defect", "your work"),
    ("late", "Late notice", "late notice"),
    ("prop", "Property / COVID", "direct physical loss"),
]

TAGGED_ROWS = {
    "clauses": [
        ("clause_occurrence", "“Occurrence” definition"),
        ("clause_your_work", "“Your work” exclusion"),
        ("clause_notice", "Notice condition"),
        ("clause_physical_loss", "Direct physical loss or damage"),
        ("clause_virus_exclusion", "Virus exclusion"),
    ],
}
LABELED_ROWS = [
    ("doctrine_ambiguity", "Court decided whether language is ambiguous"),
    ("doctrine_contra_proferentem", "Construed against the insurer"),
    ("doctrine_reasonable_expectations", "Reasonable expectations applied"),
    ("doctrine_duty_to_defend", "Duty to defend decided"),
]
OUTCOMES = ["insurer", "policyholder", "mixed", "none"]
ACCURACY_KEYS = [
    ("clause_pollution_exclusion", "Pollution exclusion"),
    ("clause_your_work", "“Your work” exclusion"),
    ("clause_notice", "Notice condition"),
    ("clause_physical_loss", "Direct physical loss"),
    ("clause_occurrence", "“Occurrence”"),
    ("doctrine_duty_to_defend", "Duty to defend"),
    ("doctrine_ambiguity", "Ambiguity"),
    ("doctrine_contra_proferentem", "Construed against insurer"),
]


def assign_group(query: str) -> str | None:
    q = str(query).lower()
    for key, _, needle in GROUPS:
        if needle in q:
            return key
    return None


def _excluded(path: Path) -> set[int]:
    if not path.exists():
        return set()
    return set(pd.read_csv(path)["cluster_id"].astype(int))


def to_cases(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Collapse opinions to cases: max over each case's opinions; group from its first opinion."""
    df = df.assign(group=df["query"].map(assign_group))
    agg = {c: "max" for c in cols}
    agg["group"] = "first"
    return df.groupby("cluster_id").agg(agg).reset_index()


def _rates(cases: pd.DataFrame, rows: list[tuple[str, str]]) -> list[dict]:
    out = []
    for col, label in rows:
        row = {"label": label, "var": col}
        for key, _, _ in GROUPS:
            sub = cases[cases["group"] == key]
            k = int(sub[col].sum())
            row[key] = [k, round(100 * k / len(sub), 1) if len(sub) else 0.0]
        out.append(row)
    return out


def _groups(cases: pd.DataFrame) -> list[dict]:
    return [{"key": k, "name": name, "n": int((cases["group"] == k).sum())} for k, name, _ in GROUPS]


def tagged_block(tagged: pd.DataFrame, excluded: set[int]) -> dict:
    df = tagged[~tagged["cluster_id"].isin(excluded)]
    cases = to_cases(df, tag_columns())
    cases = cases[cases["group"].notna()]
    return {"opinions": int(len(df)), "cases": int(len(cases)), "groups": _groups(cases),
            "clauses": _rates(cases, TAGGED_ROWS["clauses"])}


def labeled_block(labels: pd.DataFrame, excluded: set[int]) -> dict:
    lab = _clean_labels(labels)
    lab = lab[~lab["cluster_id"].isin(excluded)]
    cases = to_cases(lab, [c for c, _ in LABELED_ROWS])
    # Outcome is the same on every opinion of a case (codebook rule); take the first non-blank.
    outcome = (lab[lab["coverage_outcome"] != ""].groupby("cluster_id")["coverage_outcome"].first())
    cases["coverage_outcome"] = cases["cluster_id"].map(outcome).fillna("none")
    cases = cases[cases["group"].notna()]
    outcomes = []
    for key, _, _ in GROUPS:
        sub = cases[cases["group"] == key]
        counts = sub["coverage_outcome"].value_counts()
        outcomes.append({"group": key, **{o: int(counts.get(o, 0)) for o in OUTCOMES}})
    labelers = sorted(set(lab["labeler"].dropna().astype(str))) if "labeler" in lab else []
    return {"opinions": int(len(lab)), "cases": int(len(cases)), "labelers": labelers,
            "groups": _groups(cases), "doctrines": _rates(cases, LABELED_ROWS), "outcomes": outcomes}


def accuracy_block(tagged: pd.DataFrame, labels: pd.DataFrame, raw_path: Path) -> dict:
    """Precision/recall of the current tagger, and of the single-mention rule if raw text is present."""
    lab = _clean_labels(labels)
    current = lab.merge(tagged, on="opinion_id", suffixes=("_gold", "_pred"))
    single = None
    if raw_path.exists():
        want = set(lab["opinion_id"])
        rows = [{"opinion_id": r["opinion_id"], **tag_text(r.get("text") or "", use_density=False)}
                for r in read_jsonl(raw_path) if r.get("opinion_id") in want]
        single = lab.merge(pd.DataFrame(rows), on="opinion_id", suffixes=("_gold", "_pred"))
    out = []
    for col, label in ACCURACY_KEYS:
        m = binary_metrics(current[f"{col}_pred"], current[f"{col}_gold"])
        row = {"label": label, "var": col, "support": int(m["support"]),
               "precision": round(float(m["precision"]), 2), "recall": round(float(m["recall"]), 2)}
        if single is not None:
            s = binary_metrics(single[f"{col}_pred"], single[f"{col}_gold"])
            row["precision_single"] = round(float(s["precision"]), 2)
            row["recall_single"] = round(float(s["recall"]), 2)
        out.append(row)
    return {"opinions": int(len(current)), "rows": out}


def run(tagged_path: Path = TAGGED_PATH, labels_path: Path = LABELS_PATH, raw_path: Path = RAW_PATH,
        excluded_path: Path = EXCLUDED_PATH, out_path: Path = FINDINGS_PATH) -> dict:
    tagged = pd.read_csv(tagged_path)
    excluded = _excluded(excluded_path)
    result = {"tagged": tagged_block(tagged, excluded), "excluded_cases": len(excluded)}
    if labels_path.exists():
        labels = pd.read_csv(labels_path)
        result["labeled"] = labeled_block(labels, excluded)
        result["accuracy"] = accuracy_block(tagged, labels, raw_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
