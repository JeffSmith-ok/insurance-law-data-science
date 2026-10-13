import json

import pandas as pd
import pytest

from clausemine import analyze, collect, evaluate, tag
from clausemine.taxonomy import CLAUSES, DOCTRINES, tag_columns


# --- taxonomy / tagger -------------------------------------------------------

POSITIVE = {
    "clause_pollution_exclusion": "The absolute pollution exclusion bars coverage.",
    "clause_occurrence": 'Faulty workmanship is not an "occurrence" under the CGL policy.',
    "clause_expected_intended": "The expected or intended injury exclusion applies.",
    "clause_your_work": 'We turn to the "your work" exclusion and its subcontractor exception.',
    "clause_virus_exclusion": "The policy's virus exclusion forecloses the claim.",
    "clause_physical_loss": 'There was no "direct physical loss of or damage to" property.',
    "clause_anti_concurrent": "The anti-concurrent causation clause controls.",
    "clause_water_flood": "The flood exclusion and surface water exclusion apply.",
    "clause_assault_battery": "The assault and battery exclusion bars coverage.",
    "clause_professional_services": "The professional services exclusion applies.",
    "clause_notice": "Under the notice-prejudice rule, late notice alone is not enough.",
    "clause_cooperation": "The insured breached the cooperation clause.",
    "clause_other_insurance": "The other insurance clauses are mutually repugnant.",
    "clause_prior_knowledge": "The known loss doctrine bars coverage.",
    "clause_liquor_liability": "The liquor liability exclusion applies to the bar's dram shop claim.",
    "clause_mold": "The policy's mold exclusion bars coverage for the fungal growth.",
    "doctrine_ambiguity": "We hold the term is ambiguous.",
    "doctrine_contra_proferentem": "Ambiguities are construed against the insurer.",
    "doctrine_reasonable_expectations": "Under the reasonable expectations doctrine...",
    "doctrine_duty_to_defend": "The insurer had a duty to defend.",
    "doctrine_eight_corners": "Applying the eight-corners rule, we compare...",
    "doctrine_regulatory_estoppel": "Plaintiffs invoke regulatory estoppel.",
}


def test_every_key_has_a_positive_example():
    assert set(POSITIVE) == set(tag_columns())


@pytest.mark.parametrize("col,text", sorted(POSITIVE.items()))
def test_positive_examples_fire(col, text):
    assert tag.tag_text(text)[col] == 1


def test_unrelated_text_is_all_zero():
    row = tag.tag_text("The defendant was convicted of burglary and appealed his sentence.")
    assert sum(row.values()) == 0


def test_normalize_strips_html_and_curly_quotes():
    raw = "<p>The \u201cyour work\u201d&nbsp;exclusion</p>"
    assert tag.normalize(raw) == 'The "your work" exclusion'
    assert tag.tag_text(raw)["clause_your_work"] == 1


def test_min_hits_threshold():
    text = "The pollution exclusion is mentioned once."
    assert tag.tag_text(text, min_hits=1)["clause_pollution_exclusion"] == 1
    assert tag.tag_text(text, min_hits=2)["clause_pollution_exclusion"] == 0


def test_density_cutoff_drops_boilerplate_in_long_opinions():
    # One passing mention of the duty to defend buried in ~20,000 characters of other text
    # is boilerplate (0.5 hits per 10k chars < 1.0 cutoff); a dense discussion is not.
    filler = "The court reviewed the record and the parties' briefs. " * 360
    passing = filler + "The insurer had a duty to defend."
    assert tag.tag_text(passing)["doctrine_duty_to_defend"] == 0
    assert tag.tag_text(passing, use_density=False)["doctrine_duty_to_defend"] == 1
    dense = filler + "The duty to defend is broad. " * 5
    assert tag.tag_text(dense)["doctrine_duty_to_defend"] == 1


@pytest.mark.parametrize("text", [
    'The "damage to your work" exclusion bars the claim.',
    "Exclusions j(5) and j(6) unambiguously exclude coverage.",
    "The business risk exclusions apply to faulty workmanship.",
    "The products-completed operations hazard exclusion negates coverage.",
])
def test_your_work_variants(text):
    assert tag.tag_text(text)["clause_your_work"] == 1


def test_taxonomy_keys_match_codebook():
    assert len(CLAUSES) == 16 and len(DOCTRINES) == 6


# --- collect -----------------------------------------------------------------

class FakeResp:
    def __init__(self, payload, status=200):
        self.payload, self.status_code, self.headers = payload, status, {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        if "/search/" in url:
            page2 = "page2" in url
            hits = [{"cluster_id": 2 if page2 else 1, "caseName": "B v. Ins" if page2 else "A v. Ins",
                     "court_id": "cal", "dateFiled": "2021-05-01", "absolute_url": "/x/",
                     "opinions": [{"id": 20 if page2 else 10, "type": "lead"}]}]
            return FakeResp({"results": hits,
                             "next": None if page2 else "https://cl/api/search/?page2"})
        return FakeResp({"plain_text": "", "html_with_citations": "<p>pollution exclusion</p>"})


def test_collect_paginates_and_resumes(tmp_path):
    out = tmp_path / "op.jsonl"
    client = collect.CourtListener(token="t", delay=0, session=FakeSession())
    assert collect.run("q", max_results=10, out_path=out, client=client) == 2
    recs = [json.loads(l) for l in out.read_text().splitlines()]
    assert [r["opinion_id"] for r in recs] == [10, 20]
    assert "pollution exclusion" in recs[0]["text"]
    assert client.session.headers["Authorization"] == "Token t"
    # Second run writes nothing new.
    assert collect.run("q", max_results=10, out_path=out, client=client) == 0


def test_collect_respects_max(tmp_path):
    client = collect.CourtListener(token="t", delay=0, session=FakeSession())
    assert collect.run("q", max_results=1, out_path=tmp_path / "o.jsonl", client=client) == 1


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("COURTLISTENER_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        collect.CourtListener()


# --- evaluate ----------------------------------------------------------------

def test_binary_metrics():
    m = evaluate.binary_metrics(pd.Series([1, 1, 0, 0]), pd.Series([1, 0, 1, 0]))
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (1, 1, 1, 1)
    assert m["precision"] == m["recall"] == m["f1"] == 0.5
    assert m["kappa"] == 0


def test_kappa_perfect_and_chance():
    assert evaluate.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1
    assert evaluate.cohen_kappa(["a", "b", "a", "b"], ["a", "a", "b", "b"]) == 0


def _tagged(tmp_path):
    raw = tmp_path / "raw.jsonl"
    recs = [
        {"opinion_id": 1, "case_name": "A", "court": "cal", "date_filed": "2020-01-01",
         "text": "The pollution exclusion is ambiguous; construed against the insurer."},
        {"opinion_id": 2, "case_name": "B", "court": "cal", "date_filed": "2021-01-01",
         "text": "The virus exclusion bars coverage for direct physical loss."},
        {"opinion_id": 3, "case_name": "C", "court": "ny", "date_filed": "2021-06-01",
         "text": "Late notice; the insurer had no duty to defend."},
    ]
    raw.write_text("\n".join(json.dumps(r) for r in recs))
    out = tmp_path / "tagged.csv"
    tag.run(raw, out)
    return out


def test_sample_is_blind_and_protected(tmp_path):
    tagged = _tagged(tmp_path)
    labels = tmp_path / "sample.csv"
    df = evaluate.draw_sample(tagged, labels, n=2)
    assert len(df) == 2 and (df["clause_pollution_exclusion"] == "").all()
    with pytest.raises(FileExistsError):
        evaluate.draw_sample(tagged, labels, n=2)


def test_evaluate_end_to_end(tmp_path):
    tagged = _tagged(tmp_path)
    labels = tmp_path / "sample.csv"
    evaluate.draw_sample(tagged, labels, n=3)
    lab = pd.read_csv(labels)
    lab["clause_pollution_exclusion"] = [1, 0, 0]
    lab["clause_virus_exclusion"] = [0, 0, 0]  # tagger will have 1 false positive
    lab["coverage_outcome"] = ["policyholder", "insurer", "none"]
    lab.to_csv(labels, index=False)
    rep = evaluate.evaluate(tagged, labels, out_path=None).set_index("variable")
    assert rep.loc["clause_pollution_exclusion", "precision"] == 1
    assert rep.loc["clause_virus_exclusion", "fp"] == 1
    assert "clause_notice" not in rep.index  # unlabeled columns are skipped


def test_bad_outcome_value_rejected(tmp_path):
    tagged = _tagged(tmp_path)
    labels = tmp_path / "sample.csv"
    evaluate.draw_sample(tagged, labels, n=3)
    lab = pd.read_csv(labels)
    lab["coverage_outcome"] = ["won", "", ""]
    lab.to_csv(labels, index=False)
    with pytest.raises(ValueError):
        evaluate.evaluate(tagged, labels, out_path=None)


# --- analyze -----------------------------------------------------------------

def test_analyze_tables(tmp_path):
    tagged = _tagged(tmp_path)
    tables = analyze.run(tagged, tmp_path / "none.csv", tmp_path / "reports")
    freq = tables["clause_frequency"].set_index("clause")
    assert freq.loc["pollution_exclusion", "opinions"] == 1
    by_year = tables["clause_by_year"].set_index("year")
    assert by_year.loc[2021, "total_opinions"] == 2
    dbc = tables["doctrine_by_clause"].set_index("clause")
    assert dbc.loc["pollution_exclusion", "contra_proferentem"] == 1
    assert (tmp_path / "reports" / "clause_frequency.csv").exists()


class _FakeResp:
    def __init__(self, status, payload=None, headers=None):
        self.status_code = status
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code}")


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.calls = 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return self.responses.pop(0)


def test_rate_limit_waits_retry_after_then_succeeds(capsys):
    from clausemine.collect import CourtListener
    slept = []
    session = _FakeSession([_FakeResp(429, headers={"Retry-After": "2409"}),
                            _FakeResp(200, {"ok": True})])
    client = CourtListener(token="t", session=session, delay=0, sleep=slept.append)
    assert client._get("https://example.test") == {"ok": True}
    assert session.calls == 2
    assert sum(slept) >= 2409          # honoured the full Retry-After (plus margin)
    err = capsys.readouterr().err
    assert "rate limit" in err and "resuming about" in err


def test_rate_limit_gives_up_after_max_waits():
    import pytest as _pytest
    import requests
    from clausemine.collect import CourtListener
    session = _FakeSession([_FakeResp(429, headers={"Retry-After": "1"})] * 3)
    client = CourtListener(token="t", session=session, delay=0, sleep=lambda s: None,
                           max_rate_limit_waits=2)
    with _pytest.raises(requests.HTTPError):
        client._get("https://example.test")


def test_retry_after_parsing():
    from clausemine.collect import _retry_after
    assert _retry_after("120", default=5) == 120
    assert _retry_after(None, default=5) == 5
    assert _retry_after("garbage", default=7) == 7
