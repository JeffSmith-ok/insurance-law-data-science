"""Command-line interface: clausemine {collect,tag,sample,evaluate,agreement,analyze}."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import LABELS_PATH, RAW_PATH, REPORTS, TAGGED_PATH


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="clausemine", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="search CourtListener and download opinion text")
    c.add_argument("--query", required=True, help="CourtListener search query")
    c.add_argument("--max", type=int, default=200, help="max opinions to fetch")
    c.add_argument("--court", help="space-separated court IDs, e.g. 'cal ca9'")
    c.add_argument("--filed-after", help="YYYY-MM-DD")
    c.add_argument("--filed-before", help="YYYY-MM-DD")
    c.add_argument("--out", type=Path, default=RAW_PATH)
    c.add_argument("--delay", type=float, default=2.5,
                   help="seconds between API requests (default 2.5; keeps under the rate limit)")

    t = sub.add_parser("tag", help="apply the taxonomy to downloaded opinions")
    t.add_argument("--min-hits", type=int, default=1,
                   help="matches required to tag a key (raise to cut passing mentions)")
    t.add_argument("--no-density", action="store_true",
                   help="ignore the per-10,000-character cutoffs in taxonomy.MIN_DENSITY")
    t.add_argument("--raw", type=Path, default=RAW_PATH)
    t.add_argument("--out", type=Path, default=TAGGED_PATH)

    s = sub.add_parser("sample", help="write a blank, blind labeling sheet")
    s.add_argument("--n", type=int, default=150)
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--out", type=Path, default=LABELS_PATH)
    s.add_argument("--force", action="store_true", help="overwrite an existing sheet")

    e = sub.add_parser("evaluate", help="tagger precision/recall vs. hand labels")
    e.add_argument("--labels", type=Path, default=LABELS_PATH)

    a = sub.add_parser("agreement", help="Cohen's kappa between two labelers")
    a.add_argument("labels_a", type=Path)
    a.add_argument("labels_b", type=Path)

    sub.add_parser("analyze", help="write summary tables to reports/")

    args = p.parse_args(argv)
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 30)

    if args.cmd == "collect":
        from .collect import run
        query = args.query
        if args.filed_after or args.filed_before:
            lo, hi = args.filed_after or "*", args.filed_before or "*"
            query = f"({query}) AND dateFiled:[{lo} TO {hi}]"
        filters = {"court": args.court} if args.court else {}
        n = run(query, max_results=args.max, out_path=args.out, delay=args.delay, **filters)
        print(f"Wrote {n} new opinions to {args.out}")
    elif args.cmd == "tag":
        from .tag import run
        df = run(args.raw, args.out, min_hits=args.min_hits, use_density=not args.no_density)
        print(f"Tagged {len(df)} opinions -> {args.out}")
    elif args.cmd == "sample":
        from .evaluate import draw_sample
        df = draw_sample(TAGGED_PATH, args.out, n=args.n, seed=args.seed, force=args.force)
        print(f"Wrote {len(df)} rows to {args.out}. Label blind, per CODEBOOK.md.")
    elif args.cmd == "evaluate":
        from .evaluate import evaluate
        report = evaluate(TAGGED_PATH, args.labels)
        print(report.round(3).to_string(index=False) if not report.empty
              else "No labeled rows found yet.")
    elif args.cmd == "agreement":
        from .evaluate import agreement
        print(agreement(args.labels_a, args.labels_b).round(3).to_string(index=False))
    elif args.cmd == "analyze":
        from .analyze import run
        for name, table in run().items():
            print(f"\n== {name} ==")
            print(table.head(20).to_string(index=False))
        print(f"\nCSV tables written to {REPORTS}/")


if __name__ == "__main__":
    main()
