# Codebook

One row per **opinion**. Hand-label a random sample in `data/labels/sample.csv` and use it
to measure tagger accuracy. Where possible, a second labeler independently codes 20% of rows
so inter-rater agreement (Cohen's kappa) can be reported.

## Identifiers (auto-filled)

| Field | Description |
|---|---|
| `opinion_id` | CourtListener opinion ID |
| `case_name` | Case caption |
| `court` | CourtListener court ID (e.g. `ca9`, `cal`, `nyappdiv`) |
| `date_filed` | YYYY-MM-DD |

## Clause variables (0/1 each, `clause_<key>`)

Code **1 only if the court interprets or applies the clause to decide an issue**. A passing
mention, a recital of the policy, or discussion in a quoted case = 0.

| Key | Clause | Notes |
|---|---|---|
| `pollution_exclusion` | Pollution exclusion (absolute or qualified) | Includes "total pollution exclusion" |
| `occurrence` | Definition of "occurrence" / "accident" | Insuring agreement, usually CGL |
| `expected_intended` | Expected or intended injury exclusion | |
| `your_work` | "Your work" / "your product" exclusions | Construction defect cases |
| `virus_exclusion` | Virus / bacteria exclusion | |
| `physical_loss` | "Direct physical loss or damage" | Many COVID-19 business-interruption cases |
| `anti_concurrent` | Anti-concurrent causation clause | |
| `water_flood` | Flood / surface water / water damage exclusions | |
| `assault_battery` | Assault and battery exclusion | |
| `professional_services` | Professional services exclusion | |
| `notice` | Notice / prompt-notice condition | Includes late-notice prejudice rule |
| `cooperation` | Cooperation clause | |
| `other_insurance` | Other-insurance clause | Allocation among insurers |
| `prior_knowledge` | Prior knowledge / known loss | Claims-made policies |
| `liquor_liability` | Liquor liability exclusion / dram shop | Bars, restaurants, event hosts |
| `mold` | Mold / fungi exclusion | Property and CGL; often paired with water damage |

## Doctrine variables (0/1 each, `doctrine_<key>`)

| Key | Code 1 when the court... |
|---|---|
| `ambiguity` | finds (or expressly rejects) that policy language is ambiguous |
| `contra_proferentem` | construes ambiguity against the insurer / drafter |
| `reasonable_expectations` | applies the reasonable-expectations doctrine |
| `duty_to_defend` | decides whether the insurer owed a duty to defend |
| `eight_corners` | applies the eight-corners / four-corners rule |
| `regulatory_estoppel` | considers regulatory estoppel (e.g. ISO filing representations) |

## Outcome variables (hand-labeled only)

| Field | Values |
|---|---|
| `coverage_outcome` | `policyholder`, `insurer`, `mixed`, `none` (no coverage ruling, e.g. procedural) |
| `primary_clause` | The single clause key most central to the decision, or blank |
| `notes` | Free text |

## Labeling rules

1. Read the syllabus/headnotes, the issue statement and the disposition, then search
   within the opinion for each clause.
2. When in doubt about "at issue" versus "mentioned", code 0 and write a note.
3. `coverage_outcome` is about the **coverage question**, not the procedural disposition.
   Reversing a summary judgment for the insurer is `policyholder` only if the court finds
   coverage (or a duty to defend). A remand for fact-finding is `none`.

## Tagger validation

The tagger is checked against a hand-labeled sample (`clausemine sample` →
`data/labels/sample.csv` → `clausemine evaluate`). First validation round: 150 opinions
labeled by an attorney (JMS) under the decision rule above, October 2026.

**Finding.** With a single-mention rule, recall was near 1.0 for every key, but precision
was low for keys whose language courts recite as boilerplate. Examples: occurrence 0.25,
contra proferentem 0.21, ambiguity 0.57, duty to defend 0.66. Opinions that actually
decide an issue discuss it far more densely than opinions that only mention it.

**Change.** `taxonomy.MIN_DENSITY` adds a per-key cutoff in hits per 10,000 characters.
Normalizing by length keeps long opinions from clearing the bar on boilerplate alone.
Cutoffs were chosen as round values in the range that maximized F1 on each half of the
sample. The sample was split by `cluster_id` parity, and the cutoff chosen on one half
was scored on the other. "Your work" patterns were also widened to cover "damage to your
work/product", exclusions j(5)/j(6), business-risk exclusions, and products-completed
operations exclusions. `clausemine tag --no-density` restores the old rule.

| key | precision before → after | recall before → after |
|---|---|---|
| occurrence | 0.25 → 0.58 | 1.00 → 0.88 |
| expected/intended | 0.40 → 0.80 | 1.00 → 1.00 |
| your work | 1.00 → 0.86 | 0.65 → 0.95 |
| notice | 0.64 → 0.83 | 1.00 → 0.95 |
| ambiguity | 0.57 → 0.74 | 1.00 → 0.94 |
| duty to defend | 0.66 → 0.85 | 0.96 → 0.89 |

**Known limits.** Contra proferentem (precision 0.21) and reasonable expectations (0.33)
are not reliably tagged. Courts recite both rules in nearly every coverage opinion, and
whether a court *applied* one turns on reasoning that keyword patterns cannot see.
Findings on those two doctrines should come from hand labels, not tagger output.

Virus exclusion, water/flood, mold, and other-insurance have fewer than five positive
cases in this sample, so their scores are not yet meaningful.

The cutoffs were fitted to this sample, so the scores above are optimistic. The next
labeled sample should be drawn from newly collected opinions and used as a true test set.

## Case exclusions

Keyword searches return some cases that are not insurance coverage disputes. Examples: a
criminal assault prosecution, a tenant's mold-injury suit, a contract with a company named
"... Mold, Inc.", or a notice of claim against a city. These are listed with a reason in
`data/labels/excluded_cases.csv` and dropped from findings (`clausemine findings`).

Screening rule for a new search: keep every case with an insurer in the caption. Review the
rest. A case with no insurer in the caption and coverage language ("duty to defend",
"coverage", "exclusion applies") below 1.2 hits per 10,000 characters is excluded. Cases
above that line are kept: in October 2026 they were all coverage disputes, including
Louisiana direct-action suits that name the insurer alongside the insured. Borderline
cases are read by hand.
