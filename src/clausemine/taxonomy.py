"""Regex patterns for policy clauses and interpretive doctrines.

Keys match the variable names in CODEBOOK.md. Patterns are matched case-insensitively
against opinion text. They detect *mentions*; use the hand-labeled sample to check how
well a mention predicts that a clause was actually at issue.
"""

import re

CLAUSES: dict[str, list[str]] = {
    "pollution_exclusion": [r"pollution exclusion", r"pollutants? exclusion"],
    "occurrence": [r'definition of [“"]?occurrence', r'[“"]occurrence[”"] (?:is defined|means)',
                   r"constitutes? an [“\"]?occurrence"],
    "expected_intended": [r"expected or intended"],
    "your_work": [r'[“"]?your work[”"]? exclusion', r'[“"]?your product[”"]? exclusion'],
    "virus_exclusion": [r"virus exclusion", r"exclusion of loss due to virus"],
    "physical_loss": [r"direct physical loss"],
    "anti_concurrent": [r"anti-?concurrent caus"],
    "water_flood": [r"flood exclusion", r"surface water", r"water (?:damage )?exclusion"],
    "assault_battery": [r"assault (?:and|&|or) battery exclusion"],
    "professional_services": [r"professional services exclusion"],
    "notice": [r"late notice", r"(?:prompt|timely) notice", r"notice[- ]prejudice"],
    "cooperation": [r"cooperation clause", r"duty to cooperate"],
    "other_insurance": [r"other[- ]insurance clause", r"other[- ]insurance provision"],
    "prior_knowledge": [r"prior knowledge", r"known loss"],
}

DOCTRINES: dict[str, list[str]] = {
    "ambiguity": [r"\bambiguous\b", r"\bambiguity\b"],
    "contra_proferentem": [r"contra proferentem", r"constru(?:e|ed|ing)(?: \w+)? (?:strictly )?against the (?:insurer|drafter)",
                           r"resolved in favor of the insured"],
    "reasonable_expectations": [r"reasonable expectations"],
    "duty_to_defend": [r"duty to defend"],
    "eight_corners": [r"(?:eight|four)[- ]corners"],
    "regulatory_estoppel": [r"regulatory estoppel"],
}


def compile_patterns(groups: dict[str, list[str]]) -> dict[str, re.Pattern]:
    return {key: re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE)
            for key, pats in groups.items()}


CLAUSE_PATTERNS = compile_patterns(CLAUSES)
DOCTRINE_PATTERNS = compile_patterns(DOCTRINES)
