# Insurance Law Data Science: Coverage Clause Text Mining

Which insurance policy clauses get litigated most, and how do courts interpret them?

This project collects court opinions on insurance coverage disputes, tags each one with
the policy clauses and interpretive doctrines it discusses, and analyzes trends by clause,
jurisdiction and year.

> Research project, not legal advice.

## Research questions

1. **Frequency:** Which clauses (e.g. pollution exclusion, "occurrence" definition, virus
   exclusion) appear most often in coverage litigation, and how has that changed over time?
2. **Interpretation:** How often do courts invoke ambiguity / *contra proferentem* for each
   clause, and does that track outcomes?
3. **Jurisdiction:** Do states differ in how they read the same standard (ISO) clause?

## Pipeline

```
collect  ->  data/raw/opinions.jsonl        CourtListener search + opinion text
tag      ->  data/processed/tagged.csv      rule-based clause & doctrine tagging
label    ->  data/labels/sample.csv         hand-labeled sample (see CODEBOOK.md)
evaluate ->  precision/recall of tagger vs. hand labels
analyze  ->  reports/                       counts, trends, cross-tabs
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Free API token: https://www.courtlistener.com/help/api/rest/
export COURTLISTENER_TOKEN=...

clausemine collect --query '"pollution exclusion" AND insurer' --max 200
clausemine tag
clausemine sample --n 150          # draw a sample to hand-label
clausemine sample --n 50 --out data/labels/sample2.csv --skip data/labels/sample.csv --one-per-case  # fresh test sample
clausemine evaluate                # after filling in data/labels/sample.csv
clausemine analyze
clausemine findings                # reports/findings.json: the numbers shown on smithcapital.dev
pytest
```

## Layout

| Path | Purpose |
|---|---|
| `src/clausemine/collect.py` | CourtListener API client (search + opinion text) |
| `src/clausemine/taxonomy.py` | Clause and doctrine patterns: **edit this to change what is tagged** |
| `src/clausemine/tag.py` | Applies the taxonomy to opinion text |
| `src/clausemine/evaluate.py` | Compares the tagger with hand labels |
| `src/clausemine/analyze.py` | Summary tables |
| `CODEBOOK.md` | Variable definitions and labeling rules |
| `data/` | Raw and processed data (git-ignored except labels) |

## Limitations

- Published opinions are not a random sample of coverage disputes. Most claims settle and
  many trial-court rulings go unpublished, so frequencies describe *litigated, reported*
  disputes only.
- Regex tagging finds clauses that are *mentioned*. A hand-labeled sample is needed to
  separate mentions from clauses that were actually *at issue*.
- Check CourtListener's terms of use and rate limits before large pulls.
