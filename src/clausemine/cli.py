"""Command-line entry point: clausemine <collect|tag|sample|evaluate|analyze>."""

import argparse
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/opinions.jsonl")
TAGGED = Path("data/processed/tagged.csv")
LABELS = Path("data/labels/sample.csv")
REPORTS = Path("reports")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="clausemine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("collect", help="download opinions from CourtListener")
    p.add_argument("--query")
    p.add_argument("--max", type=int, default=200)
    p.add_argument("--courts", help="space-separated CourtListener court IDs")
    p.add_argument("--filed-after", help="YYYY-MM-DD")

    sub.add_parser("tag", help="tag clauses and doctrines")
    p = sub.add_parser("sample", help="draw a hand-labeling sample")
    p.add_argument("--n", type=int, default=150)
    sub.add_parser("evaluate", help="score the tagger against hand labels")
    p = sub.add_parser("analyze", help="write summary tables to reports/")
    p.add_argument("--min-mentions", type=int, default=2)

    args = parser.parse_args(argv)

    if args.cmd == "collect":
        from .collect import DEFAULT_QUERY, collect
        n = collect(RAW, query=args.query or DEFAULT_QUERY, max_opinions=args.max,
                    courts=args.courts, filed_after=args.filed_after)
        print(f"wrote {n} new opinions to {RAW}")
    elif args.cmd == "tag":
        from .tag import tag_file
        df = tag_file(RAW, TAGGED)
        print(f"tagged {len(df)} opinions -> {TAGGED}")
    elif args.cmd == "sample":
        from .evaluate import draw_sample
        sheet = draw_sample(pd.read_csv(TAGGED), args.n, LABELS)
        print(f"wrote {len(sheet)}-row labeling sheet to {LABELS}")
    elif args.cmd == "evaluate":
        from .evaluate import score
        print(score(pd.read_csv(TAGGED), pd.read_csv(LABELS)).to_string(index=False))
    elif args.cmd == "analyze":
        from .analyze import clause_frequency, write_reports
        df = pd.read_csv(TAGGED)
        write_reports(df, REPORTS, args.min_mentions)
        print(clause_frequency(df, args.min_mentions).to_string())
        print(f"\nreports written to {REPORTS}/")


if __name__ == "__main__":
    main()
