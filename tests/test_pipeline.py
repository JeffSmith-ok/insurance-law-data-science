import json

import pandas as pd

from clausemine.analyze import clause_by_doctrine, clause_by_year, clause_frequency
from clausemine.collect import collect, strip_html
from clausemine.evaluate import draw_sample, score
from clausemine.tag import tag_file, tag_text

POLLUTION = ("The insurer relies on the absolute pollution exclusion. We hold the pollution "
             "exclusion is ambiguous and, applying contra proferentem, construe it against "
             "the insurer. The insurer therefore had a duty to defend.")
COVID = ('The policy covers "direct physical loss of or damage to" property. Even if there '
         "were direct physical loss, the virus exclusion bars coverage.")


class FakeClient:
    def search(self, query, courts=None, filed_after=None):
        yield {"cluster_id": 1, "caseName": "A v. Insurer", "court_id": "cal",
               "dateFiled": "2019-05-01", "absolute_url": "/opinion/1/a/",
               "opinions": [{"id": 101}]}
        yield {"cluster_id": 2, "caseName": "B v. Insurer", "court_id": "ca9",
               "dateFiled": "2021-08-01", "absolute_url": "/opinion/2/b/",
               "opinions": [{"id": 102}]}

    def opinion_text(self, opinion_id):
        return {101: POLLUTION, 102: COVID}[opinion_id]


def test_tag_text_counts_mentions():
    row = tag_text(POLLUTION)
    assert row["clause_pollution_exclusion"] == 2
    assert row["doctrine_contra_proferentem"] == 2  # name + "against the insurer"
    assert row["doctrine_duty_to_defend"] == 1
    assert row["clause_virus_exclusion"] == 0


def test_strip_html():
    assert strip_html("<p>Duty&nbsp;to <b>defend</b></p>") == "Duty to defend"


def test_collect_is_idempotent(tmp_path):
    out = tmp_path / "raw.jsonl"
    assert collect(out, client=FakeClient()) == 2
    assert collect(out, client=FakeClient()) == 0  # already-seen IDs skipped
    records = [json.loads(line) for line in out.read_text().splitlines()]
    assert [r["opinion_id"] for r in records] == [101, 102]
    assert records[0]["url"] == "https://www.courtlistener.com/opinion/1/a/"


def test_end_to_end(tmp_path):
    raw = tmp_path / "raw.jsonl"
    collect(raw, client=FakeClient())
    df = tag_file(raw, tmp_path / "tagged.csv")

    freq = clause_frequency(df, min_mentions=2)
    assert freq["pollution_exclusion"] == 0.5
    assert freq["physical_loss"] == 0.5
    assert clause_by_year(df, 2).loc[2019, "pollution_exclusion"] == 1
    assert clause_by_doctrine(df, min_mentions=2)["pollution_exclusion"] == 1.0

    sheet = draw_sample(df, 10, tmp_path / "labels.csv")
    assert len(sheet) == 2 and (sheet["clause_pollution_exclusion"] == "").all()

    labels = pd.DataFrame({"opinion_id": [101, 102],
                           "clause_pollution_exclusion": [1, 0],
                           "clause_virus_exclusion": [0, 0]})
    result = score(df, labels).set_index("variable")
    assert result.loc["clause_pollution_exclusion", "precision"] == 1.0
    assert result.loc["clause_pollution_exclusion", "recall"] == 1.0
    # tagger flags the virus exclusion in 102 but the labeler said it wasn't at issue
    assert result.loc["clause_virus_exclusion", "precision"] == 0.0
