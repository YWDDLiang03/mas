import json
import threading
import time
from pathlib import Path

import pytest

from mas.adapters.literature import jats
from mas.adapters.literature.europepmc import normalize_hit
from mas.core import ledger, reading
from mas.core.broker import Broker, ProviderResponse, ToolContract
from mas.core.models import (ExchangeAdapter, ModelError, ModelRequest, ModelRoster, ScriptedAdapter, call_role,
                             extract_json, redact, validate)
from mas.core.runtime import Core

ARTICLE = (Path(__file__).parent / "fixtures" / "article.xml").read_text()


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


# --- model layer ---------------------------------------------------------------------

def test_extract_json_tolerates_fences_and_prose():
    assert extract_json('Here you go:\n```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('prefix {"b": [1, 2]} suffix') == {"b": [1, 2]}
    with pytest.raises(ModelError):
        extract_json("no json at all")


def test_schema_validation_subset():
    schema = {"type": "object", "required": ["x"], "properties": {"x": {"type": "number"}, "y": {"enum": ["a", "b"]}}}
    assert validate({"x": 1, "y": "a"}, schema) == []
    assert validate({"x": True}, schema) == ["$.x: expected number, got bool"]
    assert "missing x" in validate({}, schema)[0]


def test_call_role_repairs_a_bad_reply_once_and_records_a_trace(core):
    replies = iter(["not json", {"answer": "ok"}])
    adapter = ScriptedAdapter("scripted", lambda request: next(replies))
    roster = ModelRoster({"scripted": adapter}, {"critic": "scripted"})
    response = call_role(core, roster, "run_x", ModelRequest(
        role="critic", system="s", messages=[{"role": "user", "content": "q"}],
        response_schema={"type": "object", "required": ["answer"]}))
    assert response.data == {"answer": "ok"}
    assert len(adapter.requests) == 2 and "did not match the schema" in adapter.requests[1].messages[-1]["content"]
    finished = [e for e in core.journal.replay("run_x") if e.event_type == "agent.finished"][0]
    trace = core.artifacts.payload(finished.payload["trace_blob"])
    assert trace["final_text"] == '{"answer": "ok"}'


def test_role_bindings_name_exact_models_and_unknown_roles_are_refused():
    adapter = ScriptedAdapter("a", lambda r: "{}", model="model-x-2026")
    roster = ModelRoster({"a": adapter}, {"reader": "a"})
    assert roster.role_bindings()[0]["model_id"] == "model-x-2026"
    with pytest.raises(ValueError):
        ModelRoster({"a": adapter}, {"oracle": "a"})


def test_roster_from_toml_supports_user_providers(tmp_path):
    config = tmp_path / "models.toml"
    config.write_text('''
[providers.subagents]
kind = "exchange"
exchange_dir = "llm_exchange"
model = "claude-opus-5-5 (subagent)"

[providers.my_api]
kind = "openai_compatible"
base_url = "https://example.invalid/v1"
api_key_env = "MY_PROVIDER_KEY"
model = "my-model"

[roles]
reader = "subagents"
critic = "my_api"
''')
    roster = ModelRoster.from_toml(config)
    bindings = {b["role"]: b for b in roster.role_bindings()}
    assert bindings["reader"]["model_id"] == "claude-opus-5-5 (subagent)"
    assert bindings["critic"]["provider_family"] == "openai_compatible"
    assert (tmp_path / "llm_exchange" / "requests").is_dir()
    with pytest.raises(ModelError) as err:   # no key in the environment: refused before any network call
        roster.adapter("critic").complete(ModelRequest(role="critic", system="s", messages=[]))
    assert err.value.error_class == "auth_missing"


def test_redact_removes_secrets():
    assert redact("key sk-123 leaked", ["sk-123"]) == "key [REDACTED] leaked"


def test_exchange_adapter_round_trip(tmp_path, monkeypatch):
    adapter = ExchangeAdapter("bridge", tmp_path / "x", poll_s=0.01, timeout_s=10)
    request = ModelRequest(role="reader", system="s", messages=[{"role": "user", "content": "q"}])
    sharing_faults = {"requests": 1, "responses": 1}
    original_read = Path.read_text

    def briefly_locked(path, *args, **kwargs):
        group = path.parent.name
        if path.stem == request.request_id and sharing_faults.get(group) and path.exists():
            sharing_faults[group] -= 1
            raise PermissionError("synthetic Windows sharing violation")
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", briefly_locked)

    def answer():
        path = tmp_path / "x" / "requests" / f"{request.request_id}.json"
        deadline = time.monotonic() + adapter.timeout_s
        while True:
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
                break
            except (FileNotFoundError, PermissionError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(adapter.poll_s)
        target = tmp_path / "x" / "responses" / f"{body['request_id']}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps({"request_id": body["request_id"], "data": {"claims": []},
                                         "model_id": "subagent-opus"}), encoding="utf-8")
        temporary.replace(target)

    thread = threading.Thread(target=answer)
    thread.start()
    response = adapter.complete(request)
    thread.join()
    assert response.data == {"claims": []} and response.provider_path == "exchange_bridge"
    assert response.model_id == "subagent-opus"
    assert sharing_faults == {"requests": 0, "responses": 0}


# --- JATS reading --------------------------------------------------------------------

def test_jats_parse_produces_located_passages_without_references():
    doc = jats.parse(ARTICLE)
    ids = [p["passage_id"] for p in doc["passages"]]
    assert ids[:3] == ["title", "abstract.p1", "abstract.p2"]
    assert "sec2.1.p1" in ids and "table1" in ids
    assert not any("Should not be read" in p["text"] for p in doc["passages"])
    table = next(p for p in doc["passages"] if p["passage_id"] == "table1")
    assert "Exampletinib | 12.5" in table["text"]
    assert doc["identifiers"]["pmcid"] == "PMC0000001"
    assert doc["license"].startswith("https://creativecommons.org")


def test_abstract_passages_split_on_headings():
    passages = jats.abstract_passages("<h4>Background</h4>Kinase X matters a great deal here.<h4>Results</h4>Drug Y was active.",
                                      "Title")
    assert [p["section_path"] for p in passages[1:]] == [["Abstract", "Background"], ["Abstract", "Results"]]


def test_normalize_hit_marks_preprints_reviews_and_open_access():
    hit = normalize_hit({"id": "1", "source": "PPR", "title": "<i>T</i>", "isOpenAccess": "Y",
                         "pubTypeList": {"pubType": ["Preprint", "Review"]}, "doi": "10.1/x"})
    assert hit["is_preprint"] and hit["is_review"] and hit["is_open_access"] and hit["title"] == "T"


# --- quote checks --------------------------------------------------------------------

def test_quote_matching_normalizes_typography_but_needs_real_text():
    passage = "Exampletinib reduced kinase X activity with an IC50 of 12·5 nM – in cell-free assays."
    assert reading.quote_found("reduced kinase X activity with an IC50 of 12.5 nM - in cell-free", passage)
    assert not reading.quote_found("reduced kinase Y activity", passage)
    assert not reading.quote_found("IC50", passage)  # too short to be a quote
    assert reading.value_in_quote(12.5, "an IC50 of 12.5 nM")
    assert not reading.value_in_quote(125, "an IC50 of 12.5 nM")
    assert reading.names_entity(["Exampletinib"], "exampletinib was given")
    assert not reading.names_entity(["tinib"], "exampletinib was given")


# --- the reading pipeline ------------------------------------------------------------

class FakeReader:
    contract = ToolContract(tool_id="tool_fake_reader", capability="document_reading", capability_kind="document_reading",
                            question_kinds=("read",), contract_version="1", implementation_version="fake",
                            purpose_statement="read", evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, question_kind, inputs):
        doc = dict(jats.parse(ARTICLE), access_state="full_text_available", reading_depth="full_text",
                   source_hit={"is_preprint": False, "title": "t"})
        return ProviderResponse(values=[{"name": "document", "value": doc, "value_kind": "curated"}])


class FakeSearch:
    contract = ToolContract(tool_id="tool_fake_search", capability="literature_retrieval", capability_kind="source_retrieval",
                            question_kinds=("search",), contract_version="1", implementation_version="fake",
                            purpose_statement="search", evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, question_kind, inputs):
        hits = {"q1": [{"doi": "10.0000/test.1", "pmcid": "PMC0000001", "title": "Exampletinib study",
                        "identifiers": [{"scheme": "doi", "value": "10.0000/test.1"}]}],
                "q2": [{"doi": "10.0000/TEST.1", "title": "Exampletinib study"},
                       {"pmid": "99", "title": "Other", "identifiers": [{"scheme": "pmid", "value": "99"}]}]}[inputs["query"]]
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits])


def test_search_deduplicates_and_records_coverage(core):
    broker = Broker(core)
    broker.register(FakeSearch())
    hits, coverage_id = reading.search(core, broker, "run_x", ["q1", "q2"], cutoff_date="2026-10-13")
    assert len(hits) == 2 and hits[0]["found_by"] == ["q1", "q2"]
    coverage = core.artifacts.payload(coverage_id)
    assert coverage["unique_hits"] == 2 and coverage["date_range"]["to"] == "2026-10-13"


def test_extracted_claims_are_admitted_only_with_verified_quotes(core):
    broker = Broker(core)
    broker.register(FakeReader())
    document = reading.read(core, broker, "run_x", {"pmcid": "PMC0000001", "title": "Exampletinib study",
                                                     "identifiers": [{"scheme": "doi", "value": "10.0000/test.1"}]})
    assert document["source_id"] == "src_doi_10.0000/test.1" and document["reading_depth"] == "full_text"
    script_claims = {"claims": [
        {"passage_id": "abstract.p2", "quoted_span": "Exampletinib reduced kinase X activity with an IC50 of 12.5 nM",
         "statement": "IC50 12.5 nM against kinase X", "determination_basis": "measured", "polarity": "supports",
         "value": 12.5, "unit": "nM"},
        {"passage_id": "abstract.p2", "quoted_span": "Exampletinib reduced kinase X activity with an IC50 of 2.5 nM",
         "statement": "invented quote", "determination_basis": "measured", "polarity": "supports", "value": 2.5, "unit": "nM"},
        {"passage_id": "sec2.1.p1", "quoted_span": "The oral bioavailability of exampletinib in rats was 45%",
         "statement": "F = 45% in rats", "determination_basis": "measured", "polarity": "supports", "value": 54, "unit": "%"},
        {"passage_id": "sec2.1.p2", "quoted_span": "Comparatortinib showed no activity against kinase X",
         "statement": "other compound inactive", "determination_basis": "measured", "polarity": "conflicts"},
        {"passage_id": "sec9.p9", "quoted_span": "anything at all here", "statement": "bad passage",
         "determination_basis": "asserted", "polarity": "inconclusive"},
    ]}
    roster = ModelRoster({"s": ScriptedAdapter("s", lambda r: script_claims)}, {"reader": "s"})
    question = {"purpose": "candidate_attribute", "objective_text": "inhibit kinase X",
                "attribute": {"name": "Potency", "definition": "IC50 against kinase X", "unit": "nM", "ref": "attr_potency@v1"},
                "candidate": {"candidate_id": "cand_ik-EX", "labels": ["Exampletinib", "EX-1"]}}
    claims = reading.extract_claims(core, roster, "run_x", document, question)
    states = [(c["admission_state"], c["admission_reasons"]) for c in claims]
    assert states[0] == ("admitted", ["quote_verified", "value_in_quote", "candidate_named_in_quote"])
    assert states[1][0] == "quarantined" and "quote_not_found_in_passage" in states[1][1]
    assert states[2][0] == "quarantined" and "value_not_in_quote" in states[2][1]
    assert states[3][0] == "quarantined" and "candidate_not_named_in_source" in states[3][1]
    assert states[4][0] == "quarantined" and "passage_not_found" in states[4][1]
    admitted = ledger.claims(core, ["run_x"], candidate_ref="cand_ik-EX")
    assert len(admitted) == 1 and admitted[0]["location"]["span_checked_against_source"] is True


def test_summaries_drop_points_without_valid_citations(core):
    document = {"source_id": "src_doi_x", "document_artifact_id": "art_x", "title": "t", "reading_depth": "full_text",
                "passages": jats.parse(ARTICLE)["passages"]}
    reply = {"study_kind": "preclinical", "relevance": "high",
             "limitations": ["synthetic"],
             "key_points": [{"point": "IC50 12.5 nM", "passage_ids": ["abstract.p2"]},
                            {"point": "made up", "passage_ids": ["sec99.p1"]}]}
    roster = ModelRoster({"s": ScriptedAdapter("s", lambda r: reply)}, {"summarizer": "s"})
    summary = reading.summarize(core, roster, "run_x", document, focus="potency")
    assert [p["point"] for p in summary["key_points"]] == ["IC50 12.5 nM"]
    assert summary["uncited_points_dropped"] == 1 and summary["is_evidence"] is False


def test_case_source_matching_catches_identifiers_and_near_identical_titles():
    sources = [{"identifiers": [{"scheme": "doi", "value": "10.1/MS"}],
                "title": "Evidence Guided Candidate Evaluation Improves Selection Across Diverse Research Tasks"}]
    assert reading.is_case_source({"doi": "10.1/ms", "title": "anything"}, sources)
    assert reading.is_case_source({"title": "Evidence guided candidate evaluation improves selection across diverse research tasks."},
                                  sources)
    assert not reading.is_case_source({"title": "General evidence quality: a review"}, sources)
