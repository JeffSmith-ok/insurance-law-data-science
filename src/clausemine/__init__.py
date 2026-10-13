"""clausemine: text mining insurance coverage litigation."""

from pathlib import Path

__version__ = "0.1.0"

DATA = Path("data")
RAW_PATH = DATA / "raw" / "opinions.jsonl"
TAGGED_PATH = DATA / "processed" / "tagged.csv"
LABELS_PATH = DATA / "labels" / "sample.csv"
REPORTS = Path("reports")

ID_COLS = ["opinion_id", "cluster_id", "opinion_type", "case_name", "url", "court", "date_filed", "query"]
