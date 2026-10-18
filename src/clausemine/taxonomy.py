"""Clause and doctrine patterns.

Edit this file to change what is tagged. Keys must match CODEBOOK.md: each clause key
becomes a ``clause_<key>`` column and each doctrine key a ``doctrine_<key>`` column.

Patterns are matched case-insensitively against normalized opinion text (HTML stripped,
curly quotes straightened, whitespace collapsed). A key is tagged when the total number
of matches across its patterns reaches the tagger's ``min_hits`` threshold.
"""

from __future__ import annotations

import re

Q = r"[\"']?"  # optional straight quote, since quoted policy terms are common

CLAUSES: dict[str, list[str]] = {
    "pollution_exclusion": [
        r"\b(?:absolute|total|qualified|sudden[- ]and[- ]accidental)?\s*pollution[- ]exclusion",
        r"\bpollutants?\s+exclusion",
        r"\bexclusion\s+for\s+pollut",
    ],
    "occurrence": [
        rf"\bdefinition\s+of\s+{Q}occurrence",
        rf"{Q}occurrence{Q}\s+(?:is|was|means|as\s+defined)",
        rf"\b(?:an|no|constitutes?\s+an?|was\s+an?)\s+{Q}occurrence{Q}",
        rf"\b(?:an|no)\s+{Q}accident{Q}\s+(?:within|under)\s+the\s+(?:meaning|policy)",
    ],
    "expected_intended": [
        r"\bexpected\s+(?:or|and/or)\s+intended",
        r"\bintended\s+(?:or|and/or)\s+expected",
        r"\bintentional[- ](?:acts?|injury)\s+exclusion",
    ],
    "your_work": [
        rf"{Q}your\s+work{Q}\s+exclusion",
        rf"{Q}your\s+product{Q}\s+exclusion",
        rf"\b(?:exclusion|exclusions)\s+[jkl]\(?\d?\)?\s*\(?{Q}your\s+(?:work|product)",
        r"\bsubcontractor\s+exception",
        rf"{Q}damage\s+to\s+your\s+(?:work|product){Q}",
        r"\bexclusions?\s+j\s*\(\s*[56]\s*\)",
        r"\bbusiness[- ]risk\s+exclusions?",
        r"\b(?:work[- ]product|products[- ]completed\s+operations(?:\s+hazard)?)\s+exclusion",
    ],
    "virus_exclusion": [
        r"\bvirus\s+(?:or|and)\s+bacteria\s+exclusion",
        r"\bvirus\s+exclusion",
        r"\bexclusion\s+(?:of|for)\s+loss\s+(?:due\s+to|caused\s+by)\s+(?:a\s+)?virus",
    ],
    "physical_loss": [
        rf"{Q}direct\s+physical\s+loss\s+(?:of\s+or\s+damage|or\s+damage)",
        r"\bphysical\s+loss\s+(?:of\s+)?or\s+(?:physical\s+)?damage",
        r"\bdirect\s+physical\s+loss",
    ],
    "anti_concurrent": [
        r"\banti[- ]?concurrent[- ]caus",
        r"\bregardless\s+of\s+any\s+other\s+cause\s+or\s+event\s+(?:that\s+)?contribut",
    ],
    "water_flood": [
        r"\bflood\s+exclusion",
        r"\bsurface[- ]water\s+exclusion",
        r"\bwater[- ]damage\s+exclusion",
        r"\bwater\s+exclusion",
        r"\bexclu\w*\s+(?:for\s+)?(?:flood|surface\s+water)",
    ],
    "assault_battery": [
        r"\bassault\s+(?:and|or|&)\s+battery\s+exclusion",
        r"\bassault[- ]and[- ]battery\b",
        r"\bassault\s+or\s+battery\s+(?:exclusion|endorsement)",
    ],
    "professional_services": [
        r"\bprofessional[- ]services?\s+exclusion",
        r"\bexclusion\s+for\s+professional\s+services",
        rf"{Q}professional\s+services{Q}\s+(?:exclusion|endorsement)",
    ],
    "notice": [
        r"\blate[- ]notice",
        r"\b(?:prompt|timely)\s+notice",
        r"\bnotice[- ]prejudice",
        r"\bnotice\s+(?:provision|requirement|condition)",
        r"\bas\s+soon\s+as\s+practicable",
    ],
    "cooperation": [
        r"\bcooperation\s+(?:clause|provision|condition|requirement)",
        r"\bduty\s+to\s+cooperate",
        r"\bfail(?:ed|ure)\s+to\s+cooperate",
    ],
    "other_insurance": [
        rf"{Q}other[- ]insurance{Q}\s+(?:clause|provision|condition)s?",
        r"\bexcess\s+other[- ]insurance",
        r"\bpro[- ]rata\s+(?:by\s+time\s+on\s+the\s+risk|allocation)",
        r"\bmutually\s+repugnant",
    ],
    "prior_knowledge": [
        r"\bprior[- ]knowledge\s+(?:exclusion|provision|condition)",
        r"\bknown[- ]loss\s+(?:doctrine|rule|exclusion|provision)",
        r"\bprior\s+(?:acts?|claims?)\s+exclusion",
    ],
    "liquor_liability": [
        r"\bliquor[- ]liability\s+(?:exclusion|endorsement|coverage|policy)",
        r"\bliquor\s+(?:liability\s+)?exclusion",
        rf"{Q}in\s+the\s+business\s+of\s+manufacturing,\s+distributing,\s+selling,\s+serving\s+or\s+furnishing\s+alcoholic",
        r"\bdram[- ]shop\b",
    ],
    "mold": [
        r"\b(?:mold|mould)\s+(?:or\s+fungi\s+|and\s+fungi\s+)?exclusion",
        r"\bfungi\s+(?:or|and)\s+bacteria\s+exclusion",
        r"\bfungus\s+exclusion",
        r"\bexclusion\s+(?:for|of)\s+(?:loss\s+(?:caused\s+by|due\s+to)\s+)?(?:mold|mould|fungi|fungus)",
        rf"\bfungi\s+(?:or|and|/)\s+bacteria{Q}\s+(?:exclusion|endorsement|coverage)",
        r"\b(?:mold|mould|fungi|fungus)\s+(?:endorsement|sublimit|limitation)",
        r"\bfungi,\s+(?:wet\s+or\s+dry\s+rot|mold|mould)",
        r"\bexclu(?:de[sd]?|sion)\s+(?:coverage\s+for\s+|(?:damages?|loss(?:es)?)\s+(?:caused\s+by|from)\s+)?(?:rot,\s+)?(?:mold|mould|fungi|fungus)\b",
    ],
}

DOCTRINES: dict[str, list[str]] = {
    "ambiguity": [
        r"\b(?:is|are|was|were|not|un)\s*ambiguous",
        r"\bunambiguous(?:ly)?\b",
        r"\bsusceptible\s+(?:of|to)\s+(?:more\s+than\s+one|two)\s+reasonable",
        r"\bambiguity\b",
    ],
    "contra_proferentem": [
        r"\bcontra\s+proferentem",
        r"\bconstrued?\s+(?:strictly\s+)?against\s+the\s+(?:insurer|drafter|insurance\s+company)",
        r"\bresolved?\s+(?:in\s+favor\s+of\s+the\s+insured|against\s+the\s+insurer)",
        r"\bconstrued?\s+(?:liberally\s+)?in\s+favor\s+of\s+(?:the\s+)?(?:insured|coverage)",
    ],
    "reasonable_expectations": [
        r"\breasonable[- ]expectations?\s+(?:doctrine|of\s+the\s+insured|test)",
        r"\bobjectively\s+reasonable\s+expectations",
        r"\breasonable\s+expectations\s+of\s+(?:an?\s+|the\s+)?(?:insured|policyholder)",
    ],
    "duty_to_defend": [
        r"\bduty\s+to\s+defend",
        r"\bobligation\s+to\s+defend",
        r"\bdefense\s+obligation",
    ],
    "eight_corners": [
        r"\beight[- ]corners?",
        r"\bfour[- ]corners?\s+(?:rule|test|of\s+the\s+complaint)",
        r"\ballegations\s+of\s+the\s+complaint\s+(?:and|with)\s+the\s+(?:terms\s+of\s+the\s+)?policy",
    ],
    "regulatory_estoppel": [
        r"\bregulatory\s+estoppel",
        r"\binsurance\s+services\s+office\b.{0,200}\b(?:represent|filing|regulators?)",
        r"\b(?:ISO|drafters?)\b.{0,120}\brepresent\w*\s+to\s+(?:state\s+)?(?:insurance\s+)?regulators",
    ],
}

# Minimum hits per 10,000 characters for a key to be tagged. Courts recite boilerplate
# ("ambiguities are construed against the insurer", "the duty to defend is broader than
# the duty to indemnify") in opinions that never decide the issue; opinions that do decide
# it discuss the language far more densely. Normalizing by length keeps long opinions from
# clearing the bar on boilerplate alone. Cutoffs were chosen on the 150-opinion hand-labeled
# sample and checked on held-out halves (see CODEBOOK.md, "Tagger validation").
# Keys not listed use only the min_hits threshold.
MIN_DENSITY: dict[str, float] = {
    "pollution_exclusion": 1.0,
    "occurrence": 2.0,
    "expected_intended": 1.0,
    "physical_loss": 2.0,
    "notice": 1.0,
    "ambiguity": 1.5,
    "duty_to_defend": 1.0,
}

_FLAGS = re.IGNORECASE | re.DOTALL


def _compile(table: dict[str, list[str]]) -> dict[str, list[re.Pattern[str]]]:
    return {key: [re.compile(p, _FLAGS) for p in pats] for key, pats in table.items()}


CLAUSE_PATTERNS = _compile(CLAUSES)
DOCTRINE_PATTERNS = _compile(DOCTRINES)


def clause_columns() -> list[str]:
    return [f"clause_{k}" for k in CLAUSES]


def doctrine_columns() -> list[str]:
    return [f"doctrine_{k}" for k in DOCTRINES]


def tag_columns() -> list[str]:
    return clause_columns() + doctrine_columns()
