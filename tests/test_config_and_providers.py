"""Layered settings (core/config.py), spend accounting (core/budget.py), and the
OpenAI-compatible adapter's key-file, thinking and JSON-mode behaviour."""

from __future__ import annotations

import json

import pytest

from mas.core import config as cfg
from mas.core import models
from mas.core.budget import Budget, from_config
from mas.core.models import ModelRequest, ModelRoster, OpenAICompatibleAdapter, call_role


def resolve(**kw):
    kw.setdefault("project_file", None)
    kw.setdefault("environ", {})
    return cfg.resolve(**kw)


def test_defaults_resolve_and_every_value_has_a_layer():
    config = resolve()
    assert config["search.breadth"] == 4 and config["budget.usd_max"] == 20.0
    assert config["budget.on_exhaust"] == "warn_continue"
    assert set(config.sources) == set(cfg.SETTINGS)
    assert all(layer == "default" for layer in config.sources.values())


def test_layer_precedence_cli_beats_env_beats_profile_beats_project_beats_preset(tmp_path):
    project = tmp_path / "mas.toml"
    project.write_text("[search]\nbreadth = 5\ndepth = 3\nresults_per_query = 11\n", encoding="utf-8")
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "lab.toml").write_text("[search]\ndepth = 4\nresults_per_query = 12\n", encoding="utf-8")
    config = resolve(preset="quick", project_file=project, profile="lab", profile_dir=profiles,
                     environ={"MAS__SEARCH__RESULTS_PER_QUERY": "13", "MAS__READ__MAX_CONTENT_CHARS": "7000"},
                     overrides=cfg.parse_overrides(["read.max_content_chars=9000"]))
    assert (config["search.breadth"], config.sources["search.breadth"]) == (5, "project")
    assert (config["search.depth"], config.sources["search.depth"]) == (4, "profile")
    assert (config["search.results_per_query"], config.sources["search.results_per_query"]) == (13, "environment")
    assert (config["read.max_content_chars"], config.sources["read.max_content_chars"]) == (9000, "override")
    assert (config["read.max_papers_full_read"], config.sources["read.max_papers_full_read"]) == (10, "preset")


def test_types_ranges_and_unknown_keys_are_refused(monkeypatch):
    monkeypatch.setitem(cfg.SETTINGS, "run.flag", cfg.Setting(True, "a boolean setting for this test"))
    with pytest.raises(cfg.ConfigError, match="no setting"):
        resolve(overrides=cfg.parse_overrides(["search.bredth=3"]))
    with pytest.raises(cfg.ConfigError, match="above the maximum"):
        resolve(overrides={"search.breadth": "99"})
    with pytest.raises(cfg.ConfigError, match="not one of"):
        resolve(overrides={"budget.on_exhaust": "explode"})
    with pytest.raises(cfg.ConfigError, match="true/false"):
        resolve(overrides={"run.flag": "maybe"})
    assert resolve(overrides={"run.flag": "off"})["run.flag"] is False
    with pytest.raises(cfg.ConfigError, match="no setting"):
        resolve(environ={"MAS__SEARCH__NOPE": "1"})


def test_cross_field_checks():
    with pytest.raises(cfg.ConfigError, match="symbolic_expression"):
        resolve(overrides={"rank.method": "symbolic_expression"})
    with pytest.raises(cfg.ConfigError, match="autonomous"):
        resolve(overrides={"interaction.mode": "autonomous"})
    with pytest.raises(cfg.ConfigError, match="30%"):
        resolve(overrides={"sr.select_share": "0.4", "sr.holdout_share": "0.4"})
    assert resolve(preset="quick")["interaction.mode"] == "autonomous"   # quick clears its checkpoints


def test_hash_tracks_values_and_layer_record_explains_them():
    a, b = resolve(), resolve(overrides={"search.breadth": "6"})
    assert a.hash() != b.hash() and a.hash() == resolve().hash()
    record = b.layer_record()
    row = next(r for r in record["settings"] if r["key"] == "search.breadth")
    assert row == {"key": "search.breadth", "value": 6, "layer": "override", "unit": "queries",
                   "doc": cfg.SETTINGS["search.breadth"].doc}
    assert ("const_search_breadth", 6, "queries") in b.registered_constants()


def test_roles_must_bind_to_configured_providers(tmp_path):
    project = tmp_path / "mas.toml"
    project.write_text('[roles]\nreader = "nowhere"\n', encoding="utf-8")
    with pytest.raises(cfg.ConfigError, match="not configured"):
        resolve(project_file=project)


def test_estimate_is_offline_and_bounded():
    estimate = cfg.estimate(resolve(preset="quick"), dimensions=3, candidates=100)
    assert estimate["search_queries"] == 6 and estimate["documents_read"] <= 30
    assert estimate["candidates_assessed"] == 100 and estimate["budget_usd_max"] == 2.0


# --- budget --------------------------------------------------------------------------

def test_soft_spend_cap_warns_and_continues_hard_cap_refuses():
    soft = from_config(resolve())
    assert soft.record("usd", 15.0) == []
    assert soft.record("usd", 1.5) == ["warn"]
    assert soft.record("usd", 4.0) == ["cap"] and soft.allows("usd")
    assert soft.record("usd", 1.0) == []   # each threshold is reported once
    hard = from_config(resolve(overrides={"budget.on_exhaust": "abort"}))
    hard.record("usd", 20.0)
    assert not hard.allows("usd")
    assert Budget({"llm_turns": 0}).try_charge("llm_turns")   # 0 means no limit


# --- OpenAI-compatible adapter --------------------------------------------------------

class FakeReply:
    def __init__(self, body, status=200):
        self.body, self.status_code, self.text = body, status, json.dumps(body)

    def json(self):
        return self.body


def chat(content, *, reasoning=None, prompt=100, completion=50, finish_reason="stop"):
    message = {"content": content}
    if reasoning:
        message["reasoning_content"] = reasoning
    return FakeReply({"model": "deepseek-flash",
                      "choices": [{"message": message, "finish_reason": finish_reason}],
                      "usage": {"prompt_tokens": prompt, "completion_tokens": completion}})


def test_key_file_thinking_json_guard_and_cost(tmp_path, monkeypatch):
    key_file = tmp_path / "key"
    key_file.write_text("sk-secret-value\n", encoding="utf-8")
    sent = []

    def post(url, timeout, headers, json):   # noqa: A002 - mirrors requests.post
        sent.append({"url": url, "headers": headers, "json": json})
        return chat('{"ok": true}', reasoning="thinking text")

    monkeypatch.setattr(models.requests, "post", post)
    adapter = OpenAICompatibleAdapter("ds", "deepseek-flash", base_url="https://api.deepseek.com/",
                                      api_key_file=str(key_file), thinking=False,
                                      price_input_per_mtok=0.30, price_output_per_mtok=1.20)
    reply = adapter.complete(ModelRequest(role="reader", system="Extract.", messages=[{"role": "user", "content": "x"}],
                                          response_schema={"type": "object"}))
    body = sent[0]["json"]
    assert sent[0]["url"] == "https://api.deepseek.com/chat/completions"
    assert sent[0]["headers"]["authorization"] == "Bearer sk-secret-value"
    assert body["thinking"] == {"type": "disabled"} and body["temperature"] == 0.0
    assert body["response_format"] == {"type": "json_object"} and "json" in body["messages"][0]["content"]
    assert reply.cost_usd == pytest.approx((100 * 0.30 + 50 * 1.20) / 1e6)
    assert reply.reasoning == "thinking text"
    assert adapter.decoding(0.0) == {"thinking": False, "temperature": 0.0}


def test_thinking_on_does_not_send_an_ignored_temperature(monkeypatch):
    monkeypatch.setenv("DS_KEY", "k")
    adapter = OpenAICompatibleAdapter("ds", "deepseek-flash", base_url="https://x", api_key_env="DS_KEY",
                                      thinking=True, reasoning_effort="high")
    body = adapter.payload(ModelRequest(role="proposer", system="s", messages=[]))
    assert "temperature" not in body and body["reasoning_effort"] == "high" and "thinking" not in body
    assert adapter.decoding(0.0) == {"thinking": True, "reasoning_effort": "high"}


def test_empty_reply_is_retried_and_errors_never_contain_the_key(tmp_path, monkeypatch):
    replies = iter([chat(""), chat('{"a": 1}')])
    monkeypatch.setattr(models.requests, "post", lambda *a, **k: next(replies))
    monkeypatch.setenv("DS_KEY", "sk-very-secret")
    adapter = OpenAICompatibleAdapter("ds", "m", base_url="https://x", api_key_env="DS_KEY")
    reply = adapter.complete(ModelRequest(role="reader", system="s", messages=[]))
    assert reply.text == '{"a": 1}' and reply.usage["input_tokens"] == 200

    monkeypatch.setattr(models.requests, "post",
                        lambda *a, **k: FakeReply({"error": "bad key sk-very-secret"}, status=401))
    with pytest.raises(models.ModelError) as error:
        adapter.complete(ModelRequest(role="reader", system="s", messages=[]))
    assert error.value.error_class == "auth_rejected" and "sk-very-secret" not in str(error.value)


def test_a_reply_cut_off_at_the_token_limit_is_asked_again_with_room(monkeypatch):
    """Measured on deepseek-flash: with thinking on, reasoning can consume the whole allowance
    and the content comes back empty with finish_reason "length". Re-sending the same request
    repeats that, so the adapter raises the limit instead."""
    sent, replies = [], iter([chat("", finish_reason="length"), chat('{"a": 1}')])

    def post(url, timeout, headers, json):   # noqa: A002 - mirrors requests.post
        sent.append(json["max_tokens"])
        return next(replies)

    monkeypatch.setattr(models.requests, "post", post)
    monkeypatch.setenv("DS_KEY", "k")
    adapter = OpenAICompatibleAdapter("ds", "m", base_url="https://x", api_key_env="DS_KEY", thinking=True)
    reply = adapter.complete(ModelRequest(role="proposer", system="s", messages=[], max_tokens=1000,
                                          response_schema={"type": "object"}))
    assert sent == [1000, 2000] and reply.text == '{"a": 1}' and reply.truncated is False


def test_a_reply_that_stays_truncated_says_so_and_stops_at_the_ceiling(monkeypatch):
    sent = []

    def post(url, timeout, headers, json):   # noqa: A002 - mirrors requests.post
        sent.append(json["max_tokens"])
        return chat('{"a": ', finish_reason="length")

    monkeypatch.setattr(models.requests, "post", post)
    monkeypatch.setenv("DS_KEY", "k")
    adapter = OpenAICompatibleAdapter("ds", "m", base_url="https://x", api_key_env="DS_KEY",
                                      max_token_ceiling=2500)
    reply = adapter.complete(ModelRequest(role="proposer", system="s", messages=[], max_tokens=1000,
                                          response_schema={"type": "object"}))
    assert sent == [1000, 2000, 2500] and reply.truncated is True


def test_a_truncated_reply_is_repaired_with_more_room_and_recorded(core, monkeypatch):
    sent, replies = [], iter([chat("", finish_reason="length"), chat("", finish_reason="length"),
                              chat("", finish_reason="length"), chat('{"v": 7}')])

    def post(url, timeout, headers, json):   # noqa: A002 - mirrors requests.post
        sent.append(json["max_tokens"])
        return next(replies)

    monkeypatch.setattr(models.requests, "post", post)
    monkeypatch.setenv("DS_KEY", "k")
    roster = ModelRoster.from_tables(
        {"ds": {"kind": "openai_compatible", "base_url": "https://x", "api_key_env": "DS_KEY", "model": "m"}},
        {"proposer": "ds"}, ".")
    response = call_role(core, roster, "run_x",
                         ModelRequest(role="proposer", system="s", messages=[], max_tokens=1000,
                                      response_schema={"type": "object", "required": ["v"]}))
    assert response.data == {"v": 7}
    assert sent[0] == 1000 and max(sent) > 1000   # the repair asked for room, not the same request again
    finished = [e for e in core.journal.replay("run_x") if e.event_type == "agent.finished"][-1]
    assert finished.payload["schema_ok"] is True and "reply_truncated" in finished.payload


def test_missing_key_source_is_reported_without_a_value(tmp_path):
    adapter = OpenAICompatibleAdapter("ds", "m", base_url="https://x", api_key_env="MAS_TEST_UNSET_KEY",
                                      api_key_file=str(tmp_path / "absent"))
    with pytest.raises(models.ModelError) as error:
        adapter.complete(ModelRequest(role="reader", system="s", messages=[]))
    assert error.value.error_class == "auth_missing"


def test_call_role_records_spend_and_reports_thresholds_once(core, monkeypatch):
    monkeypatch.setattr(models.requests, "post", lambda *a, **k: chat('{"v": 1}', prompt=1_000_000, completion=0))
    monkeypatch.setenv("DS_KEY", "k")
    roster = ModelRoster.from_tables(
        {"ds": {"kind": "openai_compatible", "base_url": "https://x", "api_key_env": "DS_KEY", "model": "m",
                "price_input_per_mtok": 0.9}}, {"reader": "ds"}, ".")
    budget = Budget({"usd": 2.0}, soft_kinds=("usd",), warn_at=0.8)
    for _ in range(3):
        call_role(core, roster, "run_test", ModelRequest(role="reader", system="s", messages=[],
                                                          response_schema={"type": "object"}), budget=budget)
    notes = [e.payload for e in core.journal.replay("run_test")
             if e.event_type == "run.annotated" and e.payload.get('annotation') == 'budget_threshold']
    assert [n["level"] for n in notes] == ["warn", "cap"] and notes[-1]["continues"] is True
    finished = [e.payload for e in core.journal.replay("run_test") if e.event_type == "agent.finished"]
    assert finished[0]["cost_usd"] == pytest.approx(0.9)


def test_the_configured_stage_order_is_the_one_the_library_defaults_to():
    """Two sources of truth for the pool's stage order, and they drifted.

    `derivation_run.DEFAULT_STAGES` was corrected so that `merge` runs after `refine` -- otherwise
    merge only sees the items `filter` happened not to flag. But the CLI passes
    `stage_names=tuple(settings["criteria.stages"])`, so the settings list overrides the library
    default, and that list still had `merge` third. The regression test for the fix called
    `derive_iterative` directly without `stage_names`, so it passed while every real run through the
    CLI kept the broken order: measured on the clean derivation of 14 October 2026, `filter` sent 49
    of 59 items to `needs_refine` and `merge` then reported `{groups: 0, merged: 0}`.
    """
    from mas.core import config as config_mod
    from mas.core.derivation_run import DEFAULT_STAGES

    configured = config_mod.resolve()["criteria.stages"]
    assert tuple(configured) == DEFAULT_STAGES, (
        "the stage order a run actually uses comes from settings, so it must match the library "
        "default rather than quietly diverging from it")
    assert configured.index("merge") > configured.index("refine"), (
        "merge must run after refine or it sees a pool whose repairable items are still unrepaired")


def test_the_literature_volume_bands_raise_patience_and_not_only_the_ceiling():
    """Measured on 14 October 2026: `--preset deep` allows 200 documents per dimension and enumerate
    made 19 reader calls. The ceiling was never the constraint -- a dimension stops when newly
    relevant records fall below `search.saturation_stop` and when `saturation_k` consecutive
    documents add nothing. A band that raised only the cap would change nothing, which is why these
    move saturation too."""
    from mas.core import config as config_mod
    from mas.core import derivation

    seen = []
    for band in ("low", "mid", "high", "xhigh"):
        v = config_mod.resolve(overrides={"search.volume": band, "textbook.volume": band})
        r = derivation.research_params(v)
        seen.append((r["max_documents"], r["saturation_stop"], r["saturation_k"],
                     r["max_records_screened"], r["books_per_dimension"]))

    docs = [s[0] for s in seen]
    assert docs == sorted(docs) and docs[0] < docs[-1], "more volume must allow more documents"
    stops = [s[1] for s in seen]
    assert stops == sorted(stops, reverse=True), "more volume must mean a lower saturation floor"
    ks = [s[2] for s in seen]
    assert ks == sorted(ks) and ks[0] < ks[-1], "more volume must mean more patience before stopping"
    books = [s[4] for s in seen]
    assert books == sorted(books) and books[0] < books[-1], "more volume must allow more books"

    # an explicitly raised ceiling is not silently lowered by a volume word
    v = config_mod.resolve(overrides={"search.volume": "low", "read.max_papers_full_read": 500})
    assert derivation.research_params(v)["max_documents"] == 500
