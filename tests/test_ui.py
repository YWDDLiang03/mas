"""The browser workbench (ui/server.py, ui/views.py) and the read-only store open it needs.

Every endpoint is driven through `Workbench.handle`, so the pages are checked by their values and
not by eye: the known ranks and scores of the end-to-end run, the claim quote behind a verdict,
the per-term rationale of a fitted score, and the pool's lineage. The rest are the properties the
surface rests on: markup in a claim quote never reaches a page raw, a non-loopback host is
refused before it is bound, every method but GET and HEAD is 405, legacy views cannot write, and a
read-only core opens a root another host holds. One test serves a real request over a socket.
No network.
"""

from __future__ import annotations

import json
import re
import socket
import sqlite3
import threading
import time
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener, urlopen
from urllib.error import HTTPError

import pytest

from mas.core import config as config_mod, criteria, ledger, mechanism, pool as pool_mod
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core
from mas.core.store import StoreError
from mas.ui import views
from mas.ui.server import Workbench, address, make_server, non_loopback_reason, serve
from mas.ui.operations import OperationError, OperationManager
from tests.test_run_end_to_end import OPERATOR, make_controller, setup_task
from tests.test_symbolic import _e2e_store

READER = actor("agent", "reader-1", "reader")
QUOTE = "Alpha had an oral bioavailability of 40%"
MARKUP_QUOTE = "Alpha inhibited T1 with an IC50 < 10 nM <script>alert(1)</script>"
HALF_LIFE = {"name": "Terminal half-life", "definition": "Terminal half-life after a single oral dose",
             "measurement_kind": "quantitative", "unit": "h", "direction": "higher_better",
             "acceptable_value_sources": ["peer_reviewed"], "aggregation": "median",
             "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                                  "parameters": {"query_template": '({names}) AND "half-life"'}}}
HALF_LIFE_RULE = {"rule_kind": "hard_exclusion", "cutoff": {"comparator": ">=", "value": 6, "unit": "h"},
                  "cutoff_basis": "expert_set"}
POOL_ITEM = {"attribute": {"name": "Half-life", "unit": "h"}, "rule": {"rule_kind": "preference"},
             "supporting_claim_ids": [], "dimension": "pk"}
POOL_RESTATED = {"attribute": {"name": "Terminal half-life", "unit": "h"}, "rule": {"rule_kind": "preference"},
                 "supporting_claim_ids": [], "dimension": "pk"}


def _summarizer(text: str) -> ModelRoster:
    """A summarizer that writes one sentence citing every claim it was offered."""
    def script(request):
        offered = re.findall(r'"claim_id": "(claim_[0-9A-Z]{26})"', request.messages[0]["content"])
        return {"sentences": [{"text": text, "claim_ids": offered}]}
    return ModelRoster({"s": ScriptedAdapter("s", script, model="scripted-summarizer")}, {"summarizer": "s"})


def _markup_claim(core: Core, run_id: str) -> str:
    return ledger.record_claim(core, run_id, {
        "source_ref": "src_doi_10.0-Alpha", "candidate_ref": "cand_ik-ALPHA", "attribute_ref": "attr_potency@v1",
        "location": {"location_kind": "paragraph", "locator_value": "sec2.p1", "section_path": ["Results"],
                     "quoted_span": MARKUP_QUOTE, "span_checked_against_source": True},
        "claim_text": MARKUP_QUOTE, "claim_text_marker": "paraphrase", "normalized_statement": MARKUP_QUOTE,
        "claim_type": "literature_extracted", "evidence_kind": "peer_reviewed", "determination_basis": "measured",
        "value": 10, "unit": "nM", "polarity": "supports", "scope_match": "direct", "reading_depth": "full_text"},
        by=READER, admission_state="admitted", admission_reasons=["quote_verified", "candidate_named_in_quote"])


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """A complete store on disk: the end-to-end run, a mechanism note, a criteria pool, an open review item."""
    root = tmp_path_factory.mktemp("workbench") / "store"
    with Core.open(root) as core:
        task_id = setup_task(core)
        run_id = make_controller(core).start(task_id, by=OPERATOR, sweep_seed=7)
        _markup_claim(core, run_id)
        mechanism.explain(core, _summarizer("Alpha had an oral bioavailability of 40% after a single dose."),
                          run_id=run_id, task_id=task_id, candidate_ref="cand_ik-ALPHA", labels=["Alpha"])
        writer = pool_mod.Pool(core, task_id, by=OPERATOR, run_id=run_id).at("distill", 1)
        writer.add(POOL_ITEM, reason_text="half-life supports once-daily dosing")
        writer.add(POOL_RESTATED, reason_text="the same question from a second paper")
        writer.merge(list(writer.fold().values()), POOL_ITEM, reason_text="two names for one question")
        criteria.propose(core, task_id, HALF_LIFE, HALF_LIFE_RULE, by=OPERATOR)
    return root, task_id, run_id


@pytest.fixture(scope="module")
def bench(built):
    root, _task_id, _run_id = built
    return Workbench(root)


@pytest.fixture(scope="module")
def fitted(tmp_path_factory):
    """The symbolic-regression end-to-end store: a snapshot ordered by a fitted expression."""
    root = tmp_path_factory.mktemp("fitted") / "store"
    task_id = _e2e_store(root)
    return Workbench(root), task_id


def payload(bench: Workbench, target: str) -> dict:
    response = bench.handle("GET", "/api" + ("" if target == "/" else target))
    assert response.status == 200, response.body
    assert response.content_type.startswith("application/json")
    return json.loads(response.body)


def page(bench: Workbench, target: str) -> str:
    response = bench.handle("GET", target)
    assert response.status == 200, response.body
    assert response.content_type.startswith("text/html")
    return response.body.decode("utf-8")


# --- the pages ---------------------------------------------------------------------------------

def test_the_first_page_lists_the_tasks_the_runs_and_their_chain(bench, built):
    _root, task_id, run_id = built
    data = payload(bench, "/")
    (task,) = data["tasks"]
    assert (task["task_id"], task["version"], task["mode"]) == (task_id, 1, "conditional")
    assert task["universe_size"] == 4 and task["snapshots"] == 1 and task["blocking_unknowns"] == 0
    assert task["leaderboard"] == f"/leaderboard?task={task_id}"
    (run,) = data["runs"]
    assert (run["run_id"], run["state"], run["state_label"]) == (run_id, "completed", "completed")
    assert run["termination_reason_label"] == "planned rounds finished" and run["rules@v"] == "rules@v1"
    (chain,) = data["chains"]
    assert chain["rounds"] == 1 and chain["runs"][0]["continuation_kind_label"] == "first run"
    assert task_id in page(bench, "/")


def test_the_leaderboard_page_carries_the_known_ranks_scores_and_registered_labels(bench, built):
    _root, task_id, _run_id = built
    data = payload(bench, f"/leaderboard?task={task_id}")
    rows = {row["candidate_ref"]: row for row in data["rows"]}
    assert (rows["cand_ik-ALPHA"]["position"], rows["cand_ik-ALPHA"]["score"]) == (1, 1.0)
    assert rows["cand_ik-BETA"]["position"] == 2 and rows["cand_ik-ALPHA"]["state_label"] == "recommended"
    assert rows["cand_ik-GAMMA"]["state_label"] == "rejected" and rows["cand_ik-GAMMA"]["position"] is None
    assert rows["cand_name-delta"]["state_label"] == "unassessed"
    assert rows["cand_ik-ALPHA"]["review_status"] == "no human review yet"
    assert (data["rankable_set_size"], data["members_compared"], data["admitted_n"]) == (2, 4, 2)
    assert data["result_kind_label"] == "both" and data["acceptance_label_shown"] == "prespecified"
    assert data["coverage_fraction"] == 0.75 and data["sweep_completeness"] == 1.0
    assert data["precision_among_admitted"] is None and data["rows_not_shown"] == 0
    assert data["snapshots"][0]["snapshot_id"] == data["snapshot_id"]
    # the floor over the task's own criteria, beside the ranking coverage floor: this task registers
    # no adapter-template criterion, so it mandates nothing and the floor applies to nobody -- which
    # the page reports as a number and an empty list rather than by omitting it
    assert data["mandated_coverage_floor"] == 1.0 and data["mandated_criteria"] == []
    assert data["ineligible_for_mandated_coverage"] == 0
    assert rows["cand_ik-ALPHA"]["clears_mandated_criteria"] is None
    assert rows["cand_ik-ALPHA"]["mandated_blocked_by"] == []
    shown = page(bench, f"/leaderboard?task={task_id}")
    assert "cand_ik-ALPHA" in shown and "recommended" in shown and "no human review yet" in shown


def test_the_candidate_page_shows_the_verdicts_the_claim_quotes_and_the_mechanism_note(bench, built):
    _root, task_id, run_id = built
    data = payload(bench, f"/candidate?task={task_id}&id=cand_ik-ALPHA")
    assert (data["position"], data["score"], data["state_label"]) == (1, 1.0, "recommended")
    assert data["run_id"] == run_id and data["hard_rule_coverage"] == 1.0
    verdicts = {cell["attribute_ref"]: cell for cell in data["per_criterion"]}
    assert verdicts["attr_molecular-weight@v1"]["verdict_label"] == "pass"
    assert verdicts["attr_molecular-weight@v1"]["value"] == 300.0
    assert verdicts["attr_oral-bioavailability@v1"]["evidence"], "a passing cell names the claims it used"
    quotes = {claim["claim_id"]: claim for claim in data["claims"]}
    quoted = [claim for claim in quotes.values() if claim["quote"] == QUOTE]
    assert len(quoted) == 1 and quoted[0]["source_ref"] and quoted[0]["locator"] == "sec1.p1"
    assert quoted[0]["location_kind"] == "paragraph" and quoted[0]["span_checked_against_source"] is True
    note = data["mechanism_of_action"]
    assert note["explanation_status"] == "evidence_linked" and note["is_evidence"] is False
    assert note["sentences"][0]["text"].startswith("Alpha had an oral bioavailability")
    assert QUOTE in [claim["quote"] for claim in note["sentences"][0]["claims"]]
    assert "no fitted expression" in data["score_rationale"]["note"]
    shown = page(bench, f"/candidate?task={task_id}&id=cand_ik-ALPHA")
    assert QUOTE in shown and "sec1.p1" in shown and "evidence_linked" in shown


def test_a_candidate_without_a_note_reads_unexplained_rather_than_empty(bench, built):
    _root, task_id, _run_id = built
    note = payload(bench, f"/candidate?task={task_id}&id=cand_ik-BETA")["mechanism_of_action"]
    assert note["explanation_status"] == "unexplained" and note["sentences"] == []
    assert "mas candidate explain" in note["unexplained_reason"]
    assert "unexplained" in page(bench, f"/candidate?task={task_id}&id=cand_ik-BETA")


def test_a_claim_quote_carrying_markup_never_reaches_the_page_raw(bench, built):
    _root, task_id, _run_id = built
    data = payload(bench, f"/candidate?task={task_id}&id=cand_ik-ALPHA")
    assert MARKUP_QUOTE in [claim["quote"] for claim in data["claims"]]
    shown = page(bench, f"/candidate?task={task_id}&id=cand_ik-ALPHA")
    assert MARKUP_QUOTE not in shown and "<script>" not in shown
    assert "IC50 &lt; 10 nM &lt;script&gt;alert(1)&lt;/script&gt;" in shown


def test_the_candidate_page_explains_every_term_of_a_fitted_score(fitted):
    bench, task_id = fitted
    board = payload(bench, f"/leaderboard?task={task_id}")
    assert board["ordering_method"]["kind"] == "symbolic_expression" and board["ordering_method"]["expression_text"]
    assert board["acceptance_label_shown"] == "exploratory (chosen after results)"
    assert "fitted on the results it ranks" in " ".join(board["acceptance_reasons"])
    data = payload(bench, f"/candidate?task={task_id}&id=cand_ik-C000")
    rationale = data["score_rationale"]
    assert rationale["ordering_method"] == "symbolic_expression" and rationale["terms_missing"] == []
    assert rationale["score"] == pytest.approx(data["score"])
    assert sum(term["share"] for term in rationale["terms"]) == pytest.approx(1.0)
    for term in rationale["terms"]:
        assert term["features"] and isinstance(term["value"], float) and isinstance(term["coefficient"], float)
        assert term["grounding"] and term["direction"]
    shown = page(bench, f"/candidate?task={task_id}&id=cand_ik-C000")
    assert "attr_molecular_weight@v1" in shown and "coefficient" in shown


def test_the_run_page_is_the_progress_projection_with_the_budget_apart(bench, built):
    _root, _task_id, run_id = built
    data = payload(bench, f"/run?run={run_id}")
    scopes = {row["scope"]: row for row in data["progress"]}
    assert scopes["stage:assess"]["completed"] == scopes["stage:assess"]["planned"] == 8
    assert scopes["stage:assess"]["percent"] == 100 and scopes["stage:assess"]["denominator_kind"] == "enumerated_fixed"
    assert all("percent" not in row for row in data["progress"] if row["denominator_kind"] != "enumerated_fixed")
    assert data["state_label"] == "completed" and data["snapshot_id"].startswith("lb_")
    assert {row["verdict"]: row["count"] for row in data["verdicts"]}["pass"] == 4
    assert data["budget"]["used"]["tool_calls"] > 0 and data["binding"]["sweep_seed"] == 7
    assert f"/leaderboard?task=" in page(bench, f"/run?run={run_id}")


def test_the_review_page_shows_the_queue_and_says_where_a_decision_is_made(bench, built):
    data = payload(bench, "/review")
    assert data["decisions_are_made"] == views.TERMINAL_DECISION
    assert data["pending_n"] == 1 and data["blocking_n"] == 1
    (pending,) = data["pending"]
    assert pending["subject_id"] == "rule_terminal-half-life@v1" and pending["subject_kind"] == "rule version"
    assert pending["decided_where"] == views.TERMINAL_DECISION
    assert pending["decide_with"].startswith(f"mas review decide {pending['item_id']} --decision")
    assert [row["decision"] for row in data["decided"]] == ["approve", "approve"]
    assert all(row["decision_id"].startswith("hd_") for row in data["decided"])
    shown = page(bench, "/review")
    assert "the decision is made on the terminal, not here" in shown and "mas review decide" in shown


def test_the_pool_page_shows_state_version_and_lineage(bench, built):
    _root, task_id, _run_id = built
    data = payload(bench, f"/pool?task={task_id}")
    assert data["items_n"] == 3 and data["active"] == 1 and len(data["pool_hash"]) == 64
    assert {row["state"]: row["items"] for row in data["counts"]} == {"candidate": 1, "merged_away": 2}
    child = next(item for item in data["items"] if item["state"] == "candidate")
    merged = [item for item in data["items"] if item["state"] == "merged_away"]
    assert sorted(child["parents"]) == sorted(f"{item['criterion_id']}@v{item['version']}" for item in merged)
    assert all(child["criterion_id"] in " ".join(item["children"]) for item in merged)
    assert merged[0]["state_label"] == "merged into another" and merged[0]["last_change"]["operation"] == "merge"
    assert child["version"] == 1 and child["name"] == "Half-life" and child["unit"] == "h"
    assert "merged into another" in page(bench, f"/pool?task={task_id}")


def test_the_settings_page_carries_the_layer_of_every_value_and_redacts_the_keys(built, tmp_path):
    root, _task_id, _run_id = built
    key_file = tmp_path / "secret-folder" / "deepseek-key"
    key_file.parent.mkdir()
    key_file.write_text("sk-must-never-be-read", encoding="utf-8")
    project = tmp_path / "mas.toml"
    project.write_text(f'[search]\nbreadth = 7\n\n[providers.deepseek]\nkind = "openai_compatible"\n'
                       f'base_url = "https://api.deepseek.com"\nmodel = "deepseek-flash"\n'
                       f'api_key_env = "DEEPSEEK_API_KEY"\napi_key_file = "{key_file.as_posix()}"\napi_key = "sk-inline"\n\n'
                       f'[roles]\nreader = "deepseek"\n', encoding="utf-8")
    settings = config_mod.resolve(project_file=project, environ={})
    bench = Workbench(root, settings=settings)
    data = payload(bench, "/settings")
    body = json.dumps(data) + page(bench, "/settings")
    assert str(key_file) not in body and "sk-must-never-be-read" not in body and "sk-inline" not in body
    (provider,) = data["providers"]
    assert provider["api_key_file"] == "read at call time from a key file named deepseek-key"
    assert provider["api_key_env"] == "read at call time from the environment variable DEEPSEEK_API_KEY"
    assert provider["api_key"] == "redacted" and provider["model"] == "deepseek-flash"
    layers = {row["key"]: row for row in data["settings"]}
    assert (layers["search.breadth"]["value"], layers["search.breadth"]["layer"]) == (7, "project")
    assert layers["rank.top_n"]["layer"] == "default" and layers["search.breadth"]["doc"]
    assert data["config_hash"] == settings.hash() and data["roles"] == {"reader": "deepseek"}


def test_the_settings_page_names_the_model_answering_for_each_role(built):
    """The roster usually lives in a models file rather than a configuration table, so without the
    bindings the page showed neither provider nor role for a real set-up - and which model answered
    for which role is the first thing an operator looks for."""
    root, _task_id, _run_id = built
    bindings = [{"role": "reader", "adapter_id": "deepseek_exact", "provider_family": "deepseek",
                 "model_id": "deepseek-flash", "model_version": "deepseek-flash",
                 "decoding_parameters": {"thinking": False, "temperature": 0.0}},
                {"role": "proposer", "adapter_id": "subagents", "provider_family": "anthropic",
                 "model_id": "claude-opus-5 (subagent)", "model_version": "claude-opus-5 (subagent)",
                 "decoding_parameters": {}}]
    bench = Workbench(root, role_bindings=bindings)
    data = payload(bench, "/settings")
    rendered = page(bench, "/settings")
    assert [row["role"] for row in data["role_bindings"]] == ["reader", "proposer"]
    assert data["role_bindings"][0]["model_id"] == "deepseek-flash"
    assert "deepseek-flash" in rendered and "claude-opus-5 (subagent)" in rendered
    assert payload(Workbench(root), "/settings")["role_bindings"] == []


def test_every_page_is_served_as_html_and_as_the_same_json(bench, built):
    _root, task_id, run_id = built
    targets = ["/", f"/leaderboard?task={task_id}", f"/candidate?task={task_id}&id=cand_ik-ALPHA",
               f"/run?run={run_id}", "/review", f"/pool?task={task_id}", "/settings"]
    for target in targets:
        data, shown = payload(bench, target), page(bench, target)
        assert set(("page", "surface", "freshness", "as_of")) <= set(data)
        assert shown.startswith("<!doctype html>") and shown.endswith("</html>")
        assert '<main id="main-content">' in shown and "<h1>" in shown and "this page as JSON" in shown
        assert views.READ_ONLY in data["surface"] and "static:" in data["freshness"]


# --- what the surface refuses -------------------------------------------------------------------

def test_no_page_answers_a_post_put_delete_or_patch(bench, built):
    _root, task_id, _run_id = built
    for target in ("/", "/review", "/settings", f"/leaderboard?task={task_id}", "/api/review"):
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            response = bench.handle(method, target)
            assert response.status == 405
            assert b"read-only" in response.body and b"mas review decide" in response.body


def test_an_unknown_task_candidate_run_or_page_is_404(bench, built):
    _root, task_id, _run_id = built
    for target, expected in ((f"/leaderboard?task=task_nope", b"no task task_nope"),
                             (f"/pool?task=task_nope", b"no task task_nope"),
                             (f"/candidate?task={task_id}&id=nothinglikethis", b"is not in snapshot"),
                             ("/run?run=run_nope", b"no run run_nope"),
                             ("/elsewhere", b"no page at")):
        for prefix in ("", "/api"):
            response = bench.handle("GET", prefix + target)
            assert response.status == 404 and expected in response.body
    assert bench.handle("GET", "/leaderboard").status == 200
    assert b"?task=" in bench.handle("GET", "/candidate").body
    assert bench.handle("GET", "/leaderboard?task=x&top=none").status == 400


def test_the_workbench_binds_a_loopback_address_only(built):
    root, _task_id, _run_id = built
    for host in ("0.0.0.0", "192.168.1.5", "::"):
        with pytest.raises(ValueError, match="loopback"):
            make_server(root, port=0, host=host)
    assert non_loopback_reason("127.0.0.1") is None and non_loopback_reason("::1") is None
    assert non_loopback_reason("localhost") is None
    server = make_server(root, port=0)
    try:
        assert address(server).startswith("http://127.0.0.1:") and server.server_port > 0
    finally:
        server.server_close()


def test_ui_views_and_operations_cannot_write_directly_to_a_store():
    # Legacy rendering/operations keep their original read-only boundary.
    # New projections write a separate cache; research briefs write a guarded annotation store.
    modules = [Path("src/mas/ui") / name for name in ("views.py", "server.py", "operations.py",
               "read_api.py", "read_model.py", "evidence_read.py", "read_summaries.py")]
    for path in modules:
        source = path.read_text(encoding="utf-8")
        for forbidden in ("journal.append", "artifacts.put"):
            assert forbidden not in source, f"{path.name} mentions {forbidden}"
        if path.name != "operations.py":
            for forbidden in ("read_text(", "read_bytes(", ".environ", "getenv"):
                assert forbidden not in source, f"{path.name} mentions {forbidden}"
        for call in re.findall(r"Core\.open\(([^)]*)\)", source):
            assert "read_only=True" in call, f"{path.name} opens a store without read_only=True: {call}"
        assert "def do_POST" not in source or "_answer" in source


def test_projection_reads_write_only_the_separate_cache(built, tmp_path):
    from mas.ui.read_api import ReadAPI
    from mas.ui.read_model import ReadModel

    root, task_id, _ = built
    model = ReadModel(root, cache_path=tmp_path / "projection.sqlite")
    with model._source() as source:
        before = list(source.iterdump())
        with pytest.raises(sqlite3.OperationalError, match="readonly|read-only"):
            source.execute("CREATE TABLE forbidden_scientific_write(value TEXT)")
    assert model.sync()["ready"]
    response = ReadAPI(model).get(task_id, "candidates", {"status": "all"})
    assert response["total"] == 4
    with model._cache() as cache:
        assert cache.execute("SELECT COUNT(*) FROM candidate_rows").fetchone()[0] == 4
    with model._source() as source:
        assert list(source.iterdump()) == before
    assert model.cache_path != model.source_path
    with pytest.raises(ValueError, match="separate"):
        ReadModel(root, cache_path=root / "store.db")


def test_a_read_only_core_opens_a_root_another_host_holds_and_refuses_every_write(tmp_path):
    root = tmp_path / "store"
    with Core.open(root) as host:
        host.journal.append("task_x", "task.version_recorded", actor=OPERATOR, payload={"version": 1})
        with pytest.raises(StoreError) as locked:
            Core.open(root)
        assert locked.value.code == "store_locked"
        with Core.open(root, read_only=True) as reader:
            assert reader.read_only is True and reader.store.read_only is True
            assert [event.event_type for event in reader.journal.replay("task_x")] == ["task.version_recorded"]
            assert reader.journal.streams("task_") == ["task_x"] and reader.journal.last_seq("task_x") == 1
            with pytest.raises(StoreError) as refused:
                reader.journal.append("task_x", "task.version_recorded", actor=OPERATOR, payload={"version": 2})
            assert refused.value.code == "read_only"
            with pytest.raises(StoreError) as refused_artifact:
                reader.artifacts.put("task_context", {"objective_text": "x"})
            assert refused_artifact.value.code == "read_only"
        assert host.journal.last_seq("task_x") == 1
    with pytest.raises(StoreError) as missing:
        Core.open(tmp_path / "nowhere", read_only=True)
    assert missing.value.code == "store_root_missing"


# --- served over a socket -----------------------------------------------------------------------

def test_a_browser_on_loopback_walks_the_built_store(built):
    root, task_id, run_id = built
    server = make_server(root, port=0)
    fetched: dict[str, tuple[int, bytes]] = {}
    host = threading.Thread(target=server.serve_forever, daemon=True)
    host.start()
    try:
        base = address(server).rstrip("/")
        for target in ("/", f"/leaderboard?task={task_id}", f"/candidate?task={task_id}&id=cand_ik-ALPHA",
                       f"/run?run={run_id}", "/review", f"/pool?task={task_id}", "/settings",
                       f"/api/leaderboard?task={task_id}"):
            with urlopen(base + target, timeout=20) as answer:
                fetched[target] = (answer.status, answer.read())
    finally:
        server.shutdown()
        host.join(timeout=20)
        server.server_close()
    assert len(fetched) == 8 and {status for status, _body in fetched.values()} == {200}
    assert b"<!doctype html>" in fetched["/"][1] and b"cand_ik-ALPHA" in fetched[f"/leaderboard?task={task_id}"][1]
    served = json.loads(fetched[f"/api/leaderboard?task={task_id}"][1])
    assert served["rows"][0]["candidate_ref"] == "cand_ik-ALPHA" and served["rows"][0]["position"] == 1
    assert QUOTE.encode() in fetched[f"/candidate?task={task_id}&id=cand_ik-ALPHA"][1]


def test_the_terminal_prints_a_loopback_url_and_says_the_surface_is_read_only(built, monkeypatch, capsys):
    root, _task_id, _run_id = built
    from mas.cli import main as cli
    from mas.ui import server as ui_server
    served: list[str] = []
    monkeypatch.setattr(ui_server, "serve", lambda server: served.append(address(server)) or server.server_close())
    assert cli.main(["--store", str(root), "ui", "serve", "--port", "0"]) == 0
    printed = capsys.readouterr().out
    assert served and served[0].startswith("http://127.0.0.1:")
    assert f"workbench at {served[0]}" in printed and "read-only" in printed
    assert "mas review decide" in printed and "mas run start" in printed


def test_serving_closes_the_socket_when_it_is_interrupted(built):
    root, _task_id, _run_id = built
    server = make_server(root, port=0)
    monkey = server.serve_forever

    def interrupt() -> None:
        raise KeyboardInterrupt

    server.serve_forever = interrupt
    serve(server)
    assert server.socket.fileno() == -1 and monkey is not None


def test_ipv6_loopback_uses_an_ipv6_socket_and_a_usable_url(built):
    if not socket.has_ipv6:
        pytest.skip("IPv6 is unavailable on this host")
    root, _task_id, _run_id = built
    try:
        server = make_server(root, port=0, host="::1")
    except OSError as error:
        pytest.skip(f"IPv6 loopback cannot be bound on this host: {error}")
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        base = address(server)
        assert base.startswith("http://[::1]:")
        with build_opener(ProxyHandler({})).open(base + "api", timeout=10) as response:
            assert response.status == 200 and json.load(response)["tasks_n"] == 1
    finally:
        server.shutdown()
        worker.join(timeout=10)
        server.server_close()


def test_opt_in_operations_require_token_same_origin_and_allowlisted_action(built):
    root, task_id, _run_id = built
    manager = OperationManager(root)
    server = make_server(root, port=0, operations=manager)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = address(server).rstrip("/")
    try:
        with urlopen(base + "/operations", timeout=10) as response:
            assert manager.token.encode() in response.read()
        for token, origin in (("bad-token", base), (manager.token, "http://untrusted.example")):
            request = Request(base + "/api/operations", data=b'{}', method="POST",
                              headers={"Content-Type": "application/json", "Origin": origin,
                                       "X-MAS-Operation-Token": token})
            with pytest.raises(HTTPError) as refused:
                urlopen(request, timeout=10)
            assert refused.value.code == 403
        request = Request(base + "/api/operations", data=json.dumps({"action": "expert_decide", "task_id": task_id}).encode(),
                          method="POST", headers={"Content-Type": "application/json", "Origin": base,
                                                   "X-MAS-Operation-Token": manager.token})
        with pytest.raises(HTTPError) as refused:
            urlopen(request, timeout=10)
        assert refused.value.code == 400
        assert manager.snapshot()["jobs"] == []
        with pytest.raises(OperationError, match="frozen"):
            manager.start({"action": "run_start", "task_id": task_id})
        with pytest.raises(OperationError, match="did not start"):
            manager.cancel("job_somebody_else_started")
    finally:
        server.shutdown()
        worker.join(timeout=10)
        server.server_close()
        manager.close()


def test_an_operation_runs_the_cli_and_preserves_its_real_failure_and_logs(built, tmp_path):
    root, task_id, _run_id = built
    # Explicitly disable adjudication: this real CLI subprocess must refuse before any model call.
    config = tmp_path / "mas.toml"
    config.write_text('[interaction]\nmode = "checkpoint"\nautonomous_adjudication = false\n', encoding="utf-8")
    manager = OperationManager(root, cli_options=["--config", str(config), "--set", "budget.usd_max=0"],
                               config_hash="test-config")
    try:
        job = manager.start({"action": "adjudicate_item", "task_id": task_id,
                             "item": "rule_terminal-half-life@v1"})
        deadline = time.monotonic() + 15
        while manager.snapshot()["jobs"][0]["exit_code"] is None and time.monotonic() < deadline:
            time.sleep(.05)
        result = manager.snapshot()["jobs"][0]
        assert result["pid"] == job["pid"] and result["status"] == "failed" and result["exit_code"] != 0
        assert "interaction.autonomous_adjudication is off" in result["log_tail"]
        assert result["initiator"] == {"kind": "agent", "id": "codex", "surface": "browser"}
        assert Path(result["log_path"]).is_file()
        recorded = json.loads(Path(result["log_path"]).with_name("job.json").read_text(encoding="utf-8"))
        assert recorded["config_hash"] == "test-config" and recorded["pid"] == result["pid"]
    finally:
        manager.close()


def test_settings_edits_are_validated_saved_and_reloaded_without_secret_fields(built):
    root, task_id, _run_id = built
    manager = OperationManager(root)
    with pytest.raises((OperationError, config_mod.ConfigError)):
        manager.save_settings({"providers.mine.api_key": "not-allowed"})
    with pytest.raises(config_mod.ConfigError):
        manager.save_settings({"assess.workers": 0})
    saved = manager.save_settings({"search.volume": "mid", "textbook.volume": "mid", "assess.workers": 2})
    manager.select_task(task_id)
    restored = OperationManager(root)
    assert saved["preset"] == "standard" and restored.settings["assess.workers"] == 2
    assert restored.current_task == task_id and restored.settings["search.volume"] == "mid"
    assert "api_key" not in manager.state_path.read_text(encoding="utf-8")


def test_leaderboard_pagination_and_csv_keep_the_snapshot_and_all_candidates(bench, built):
    import csv
    import io
    _root, task_id, _run_id = built
    first = payload(bench, f"/leaderboard?task={task_id}&top=2&page=1")
    second = payload(bench, f"/leaderboard?task={task_id}&snapshot={first['snapshot_id']}&top=2&page=2")
    assert first["pagination"]["pages"] == 2 and second["pagination"]["first_row"] == 3
    assert not ({row["candidate_ref"] for row in first["rows"]} & {row["candidate_ref"] for row in second["rows"]})
    assert all(first["snapshot_id"] in row["candidate"] for row in first["rows"])
    exported = bench.handle("GET", f"/export/leaderboard.csv?task={task_id}&snapshot={first['snapshot_id']}")
    rows = list(csv.DictReader(io.StringIO(exported.body.decode("utf-8-sig"))))
    assert exported.status == 200 and len(rows) == first["members_compared"] == 4
    assert {row["snapshot_id"] for row in rows} == {first["snapshot_id"]}


def test_navigation_uses_server_task_and_ui_language_does_not_translate_research(built):
    from html.parser import HTMLParser
    from mas.ui import i18n
    from mas.ui.server import _page
    root, task_id, _run_id = built
    manager = OperationManager(root)
    manager.select_task(task_id)
    bench = Workbench(root, operations=manager)

    class Navigation(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links = []

        def handle_starttag(self, tag, attrs):
            fields = dict(attrs)
            if tag == "a" and "nav-link" in fields.get("class", ""):
                self.links.append(fields["href"])

    english = bench.handle("GET", "/settings")
    parser = Navigation()
    parser.feed(english.body.decode("utf-8"))
    assert b'<html lang="en">' in english.body
    assert len(parser.links) == 6 and all(f"task={task_id}" in target for target in parser.links)
    assert all("/#tasks" not in target and bench.handle("GET", target).status == 200 for target in parser.links)
    chinese = bench.handle("GET", "/settings?lang=zh")
    assert "mas_ui_language=zh" in chinese.headers["Set-Cookie"]
    assert b'<html lang="zh-CN">' in bench.handle("GET", "/settings", headers={"Cookie": "mas_ui_language=zh"}).body

    data = bench.view("/candidate", {"task": [task_id], "id": ["cand_ik-ALPHA"]})
    data["label"] = "研究任务 is a literal research label"
    for language in ("en", "zh"):
        token = i18n.LANGUAGE.set(language)
        try:
            shown = _page("/candidate", data).body.decode("utf-8")
            assert data["label"] in shown and QUOTE in shown
        finally:
            i18n.LANGUAGE.reset(token)


def test_empty_navigation_and_unknown_model_cost_have_useful_nonzero_assumptions(tmp_path):
    from mas.ui import presentation
    root = tmp_path / "empty-workspace"
    Core.open(root).close()
    bench = Workbench(root)
    for target in ("/leaderboard", "/pool", "/candidate", "/run"):
        response = bench.handle("GET", target)
        assert response.status == 200 and b"/operations" in response.body
    assert presentation.cost_value(None, "unknown") == "Unknown"
    assert "Known subtotal" in presentation.cost_value(.02, "partial")


def test_progress_keeps_unknown_costs_and_partial_usage_distinct(core):
    from mas.ui.views import _derivation_activity
    run_id = "run_accounting_fixture"
    core.journal.append(run_id, "agent.finished", actor=READER,
                        payload={"request_id": "unknown-request", "role": "reader", "usage": {},
                                 "usage_status": "unknown", "cost_usd": None, "cost_status": "unknown"})
    detail, budget = _derivation_activity(core, run_id, {}, "running")
    assert budget["used"]["usd"] is None and budget["cost_status"] == "unknown"
    assert detail["model_usage_by_role"][0]["estimated_cost_usd"] is None
    core.journal.append(run_id, "agent.finished", actor=READER,
                        payload={"request_id": "partial-request", "role": "reader", "usage": {"input_tokens": 10},
                                 "usage_status": "partial", "cost_usd": .02, "cost_status": "partial"})
    detail, budget = _derivation_activity(core, run_id, {}, "running")
    assert budget["used"]["usd"] == .02 and budget["cost_status"] == "partial"
    assert budget["used"]["output_tokens"] is None and budget["usage_status"] == "partial"
    legacy = "run_legacy_usage_fixture"
    core.journal.append(legacy, "agent.finished", actor=READER,
                        payload={"request_id": "legacy-request", "role": "reader", "usage": {"input_tokens": 7}, "cost_usd": .01})
    detail, budget = _derivation_activity(core, legacy, {}, "completed")
    assert budget["usage_status"] == "recorded" and detail["model_usage_by_role"][0]["usage_status"] == "recorded"


def test_existing_task_run_blocks_duplicate_actions_from_another_server(core):
    from mas.core import task as task_mod
    spec = {"objective_text": "Cross-server guard fixture", "mode": "exploratory", "evaluation_scope": "metadata only",
            "seed_candidates": [{"candidate_ref": "fixture_candidate"}]}
    task_id, _ = task_mod.record_version(core, spec, by=OPERATOR)
    other_task, _ = task_mod.record_version(core, spec, by=OPERATOR)
    core.journal.append("run_other_server_fixture", "run.created", actor=OPERATOR, state_to="running",
                        payload={"task_id": task_id})
    manager = OperationManager(core.store.root)
    for action in ("run_start", "reduce_registered", "freeze_profile", "supplement_attach"):
        with pytest.raises(OperationError) as refused:
            manager.start({"action": action, "task_id": task_id})
        assert refused.value.run_id == "run_other_server_fixture"
    assert manager._processes == {} and manager._jobs == {}
    assert other_task not in manager.active_runs(core)
    assert manager.select_task(task_id)["current_task"] == task_id


def test_task_review_keeps_earlier_criterion_versions_in_history_and_api_complete(core):
    from mas.core import review, task as task_mod
    task_id, _ = task_mod.record_version(core, {
        "objective_text": "Current criterion review fixture", "mode": "exploratory",
        "evaluation_scope": "metadata only", "seed_candidates": [{"candidate_ref": "fixture_candidate"}]}, by=OPERATOR)
    old_attr, old_rule = criteria.propose(core, task_id, HALF_LIFE, HALF_LIFE_RULE, by=OPERATOR)
    new_attr, new_rule = criteria.propose(core, task_id, HALF_LIFE, HALF_LIFE_RULE, by=OPERATOR)
    for ref in (old_attr, new_attr):
        review.request(core, task_id, subject={"kind": "attribute_version", "id": ref},
                       why_expert_required="Attribute check", requested_by=OPERATOR)
    review.request(core, task_id, subject={"kind": "candidate_state", "id": "fixture_candidate"},
                   why_expert_required="Candidate check", requested_by=OPERATOR)
    bench = Workbench(core.store.root)
    target = f"/api/review?task={task_id}&routes=0"
    original = json.loads(bench.handle("GET", target).body)
    current = json.loads(bench.handle("GET", target + "&current_versions=1").body)
    assert original["pending_n"] == 5 and original["historical"] == []
    assert current["pending_n"] == current["blocking_n"] == 3
    assert {row["subject_id"] for row in current["pending"]} == {new_rule, new_attr, "fixture_candidate"}
    assert {row["subject_id"] for row in current["historical"]} == {old_rule, old_attr}
    assert all(row["state"] == "open" for row in current["historical"])
    shown = bench.handle("GET", f"/review?task={task_id}").body.decode("utf-8")
    assert "Earlier criterion requests" in shown and "current_versions=1" in shown
    criteria.retire_rule(core, task_id, new_rule, by=OPERATOR, reason="Retired fixture criterion")
    retired = json.loads(bench.handle("GET", target + "&current_versions=1").body)
    assert retired["pending_n"] == 1 and retired["historical_pending_n"] == 4
    assert json.loads(bench.handle("GET", target).body)["pending_n"] == 5
