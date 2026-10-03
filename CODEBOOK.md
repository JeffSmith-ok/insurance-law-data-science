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
