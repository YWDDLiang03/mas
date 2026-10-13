"""Symbolic-regression scoring (core/symbolic.py, core/sr_stage.py).

The solver against a known answer, the refusals (ill-conditioned design, constant column, a
coefficient contradicting its declared direction), the deterministic three-way split, the
honesty guards on what the proposer sees, the holdout adoption decision and the fallback to the
baseline, the `expert_prior` route, and the four pre-existing gaps this slice closes.
Scripted models; no network.
"""

from __future__ import annotations

import json

import pytest

from mas.core import assessor, criteria, leaderboard, review, sr_stage, symbolic
from mas.core.journal import actor

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")


# --- fixtures without a store -------------------------------------------------------------------

def rule_item(attr_id, name, *, capability="property_estimate", parameters=None, rule_kind="preference",
              direction="higher_better", unit="unit", bases=None, sources=("database_entry",),
              question="computed_property", scheme=None):
    attribute = {"attribute_id": attr_id, "version": 1, "name": name, "definition": f"{name} of the compound",
                 "measurement_kind": "quantitative", "unit": unit, "direction": direction,
                 "acceptable_value_sources": list(sources), "aggregation": "median",
                 "evidence_request": {"capability": capability, "question_kind": question,
                                      "identifier_scheme": scheme, "parameters": parameters or {}}}
    if bases:
        attribute["acceptable_determination_bases"] = bases
    rule = {"rule_id": f"rule_{attr_id}", "version": 1, "rule_kind": rule_kind, "predicate_form": "ordering",
            "cutoff": None, "cutoff_basis": "none_evidence_insufficient"}
    return {"entry": {"rule_ref": f"rule_{attr_id}@v1", "attribute_ref": f"{attr_id}@v1", "rule_kind": rule_kind},
            "rule": rule, "attribute": attribute}


def cell_for(candidate, item, value):
    return {"assessment_id": f"asm_{candidate}_{item['entry']['rule_ref']}", "candidate_ref": candidate,
            "attribute_ref": item["entry"]["attribute_ref"], "rule_ref": item["entry"]["rule_ref"],
            "rule_kind": item["rule"]["rule_kind"],
            "verdict": "pass" if value is not None else "unknown_missing", "value": value,
            "value_kind": "derived", "conflicting_claim_refs": []}


def rules_info_for(items):
    return {item["entry"]["rule_ref"]: {"rule_kind": item["rule"]["rule_kind"],
                                        "predicate_form": item["rule"]["predicate_form"],
                                        "direction": item["attribute"]["direction"]} for item in items}


def term(form, *features, direction="higher_better", constant=None, prior=None, claims=()):
    return symbolic.Term(form=form, features=tuple(features), direction=direction, constant=constant,
                         prior_coefficient=prior, claim_refs=tuple(claims))


def rows_from(table, feature_names, target_name):
    return [({name: row[name] for name in feature_names}, row[target_name]) for row in table]


# --- the numerics -------------------------------------------------------------------------------

def test_the_solver_matches_a_known_answer_and_refuses_a_singular_system():
    assert [round(v, 10) for v in symbolic.solve([[2, 1, -1], [-3, -1, 2], [-2, 1, 2]], [8, -11, -3])] == [2.0, 3.0, -1.0]
    assert [round(v, 10) for v in symbolic.solve([[0.0, 1.0], [1.0, 0.0]], [2.0, 3.0])] == [3.0, 2.0]   # pivoting
    with pytest.raises(symbolic.FitRefused, match="singular"):
        symbolic.solve([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0])


def test_a_constant_column_and_an_ill_conditioned_design_are_refused():
    varying = [({"a": float(i), "b": float(i % 3)}, float(i)) for i in range(10)]
    constant = [({"a": 1.0, "b": float(i)}, float(i)) for i in range(10)]
    with pytest.raises(symbolic.FitRefused, match="constant_column"):
        symbolic.fit([term("identity", "a"), term("identity", "b")], constant, ridge=0.1, max_condition=1e8)
    with pytest.raises(symbolic.FitRefused, match="too_few_rows"):
        symbolic.fit([term("identity", "a")], varying[:2], ridge=0.1, max_condition=1e8)
    collinear = [({"a": float(i), "b": 2.0 * i + 1.0}, float(i)) for i in range(10)]
    with pytest.raises(symbolic.FitRefused, match="ill_conditioned"):
        symbolic.fit([term("identity", "a"), term("identity", "b")], collinear, ridge=0.1, max_condition=1e8)
    fitted = symbolic.fit([term("identity", "a"), term("identity", "b")], varying, ridge=0.0, max_condition=1e8)
    assert fitted.expression.provenance == "fitted" and fitted.diagnostics["r2_train"] > 0.99


def test_the_fit_shrinks_toward_the_declared_prior_not_toward_zero():
    rows = [({"a": float(i)}, 0.0) for i in range(12)]          # the data says nothing: y is constant
    toward_zero = symbolic.fit([term("identity", "a", prior=None)], rows, ridge=1.0, max_condition=1e8)
    toward_prior = symbolic.fit([term("identity", "a", prior=2.0)], rows, ridge=1.0, max_condition=1e8)
    assert toward_zero.expression.coefficients[0] == pytest.approx(0.0)
    assert toward_prior.expression.coefficients[0] > 0.0        # the prior survives where the data is silent


def test_a_coefficient_contradicting_its_declared_direction_is_rejected():
    falling = [({"a": float(i)}, 10.0 - float(i)) for i in range(12)]
    claimed_up = symbolic.fit([term("identity", "a", direction="higher_better")], falling, ridge=0.0, max_condition=1e8)
    (violation,) = symbolic.sign_violations(claimed_up.expression)
    assert violation["declared_direction"] == "higher_better" and violation["coefficient"] < 0
    claimed_down = symbolic.fit([term("identity", "a", direction="lower_better")], falling, ridge=0.0, max_condition=1e8)
    assert symbolic.sign_violations(claimed_down.expression) == []


def test_the_grammar_refuses_everything_outside_it():
    offered = ["a", "b"]
    assert symbolic.parse_term({"form": "hinge", "features": ["a"], "constant": 3, "direction": "lower_better"},
                               offered).text == "hinge(a, 3)"
    assert symbolic.parse_term({"form": "product", "features": ["a", "b"]}, offered).text == "a*b"
    for spec, reason in (({"form": "exp", "features": ["a"]}, "unknown_form"),
                         ({"form": "identity", "features": ["c"]}, "unknown_feature"),
                         ({"form": "product", "features": ["a"]}, "arity"),
                         ({"form": "product", "features": ["a", "a"]}, "arity"),
                         ({"form": "hinge", "features": ["a"]}, "constant"),
                         ({"form": "square", "features": ["a"], "constant": 2}, "constant"),
                         ({"form": "identity", "features": ["a"], "direction": "within_range"}, "direction"),
                         ("log(a)", "not_an_object")):
        with pytest.raises(symbolic.GrammarError, match=reason):
            symbolic.parse_term(spec, offered)
    with pytest.raises(symbolic.GrammarError, match="too_many_terms"):
        symbolic.parse_terms([{"form": "identity", "features": ["a"]}, {"form": "log1p", "features": ["b"]}],
                             offered, max_terms=1)
    with pytest.raises(symbolic.GrammarError, match="duplicate_term"):   # z(x) is x after standardisation
        symbolic.parse_terms([{"form": "identity", "features": ["a"]}, {"form": "zscore", "features": ["a"]}],
                             offered, max_terms=4)
    assert symbolic.TERM_DIRECTIONS == tuple(d for d in criteria.DIRECTIONS if d in symbolic.TERM_DIRECTIONS)


def test_evaluate_reports_a_score_with_weighted_feature_coverage():
    rows = [({"a": float(i), "b": float((i * 7) % 5)}, float(i) + 3.0 * ((i * 7) % 5)) for i in range(12)]
    fitted = symbolic.fit([term("identity", "a"), term("identity", "b")], rows, ridge=0.0, max_condition=1e8)
    expression = fitted.expression
    score, coverage = symbolic.evaluate(expression, {"a": 5.0, "b": 0.0})
    assert score == pytest.approx(5.0, abs=1e-6) and coverage == 1.0
    partial_score, partial_coverage = symbolic.evaluate(expression, {"a": 5.0})
    assert partial_score is not None and 0.0 < partial_coverage < 1.0   # a weighs what its coefficient weighs
    assert symbolic.evaluate(expression, {}) == (None, 0.0)
    assert symbolic.evaluate(expression.record(), {"a": 5.0, "b": 0.0})[0] == pytest.approx(score)


def test_the_three_way_split_is_deterministic_and_excludes_reference_outcomes():
    refs = [f"cand_ik-C{i:03d}" for i in range(200)] + ["cand_ik-REF"]
    split = symbolic.split_candidates(refs, seed=7, select_share=0.25, holdout_share=0.25, exclude=["cand_ik-REF"])
    again = symbolic.split_candidates(reversed(refs), seed=7, select_share=0.25, holdout_share=0.25,
                                      exclude=["cand_ik-REF"])
    assert split.assignment == again.assignment                      # order of the universe cannot move a candidate
    other_seed = symbolic.split_candidates(refs, seed=8, select_share=0.25, holdout_share=0.25, exclude=["cand_ik-REF"])
    assert other_seed.assignment != split.assignment
    assert split.of("cand_ik-REF") == "excluded"
    for name in ("train", "select", "holdout"):
        assert "cand_ik-REF" not in split.members(name)
    counts = split.counts()
    assert counts["excluded"] == 1 and counts["train"] + counts["select"] + counts["holdout"] == 200
    assert 0.15 < counts["holdout"] / 200 < 0.35 and 0.15 < counts["select"] / 200 < 0.35
    assert sorted(split.record()) == ["assignment_hash", "counts", "holdout_share", "rule", "seed", "select_share"]


# --- the stage: what the proposer sees ------------------------------------------------------------

POTENCY = rule_item("attr_potency", "T1 curated potency", capability="interaction_evidence_lookup",
                    parameters={"target_chembl_id": "CHEMBL_T1"}, unit="pChEMBL")
PREDICTED_POTENCY = rule_item("attr_predicted_potency", "T1 predicted affinity", capability="interaction_estimate",
                              parameters={"target_chembl_id": "CHEMBL_T1"}, unit="pChEMBL", bases=["predicted"])
DESCRIPTOR_A = rule_item("attr_a", "Descriptor A", unit="units")
DESCRIPTOR_B = rule_item("attr_b", "Descriptor B", unit="units")
TASK_CONTEXT = {"task_context_id": "task_sr", "version": 1, "objective_text": "Rank compounds for T1",
                "scope_entities": [{"entity_kind": "target", "identifier": "CHEMBL_T1", "label": "T1",
                                    "identifier_scheme": "chembl_target", "role": "required"}],
                "seed_candidates": [{"candidate_ref": "refotinib", "aliases": ["RF-7"], "is_reference_outcome": True}]}


def potency_world(n=48, *, reversed_on_holdout=False, swap_train=True):
    """`n` candidates with a curated potency target and two descriptors.

    Descriptor B agrees with the target on the fitting and comparison rows; with
    `reversed_on_holdout` it disagrees on the holdout, which is the case a loop of generations
    cannot detect for itself.
    """
    items = [POTENCY, DESCRIPTOR_A, DESCRIPTOR_B]
    refs = [f"cand_ik-C{i:03d}" for i in range(n)]
    target = {ref: 5.0 + ((i * 7) % n) / 10.0 for i, ref in enumerate(refs)}
    descriptor_a = {ref: float((i * 29) % 41) for i, ref in enumerate(refs)}   # unrelated to the target
    split = symbolic.split_candidates(refs, seed=0, select_share=0.25, holdout_share=0.25)
    descriptor_b = {ref: (-target[ref] if reversed_on_holdout and split.of(ref) == "holdout" else target[ref])
                    for ref in refs}
    if swap_train:   # a perfect rank agreement over the fitting rows is refused as the target itself
        first, second = split.members("train")[:2]
        descriptor_b[first], descriptor_b[second] = descriptor_b[second], descriptor_b[first]
    cells = {ref: [cell_for(ref, items[0], target[ref]), cell_for(ref, items[1], descriptor_a[ref]),
                   cell_for(ref, items[2], descriptor_b[ref])] for ref in refs}
    return items, cells, split


def proposer_over(*names, form="identity", prior=None, claims=(), direction="higher_better"):
    """A scripted proposer that always proposes the named features, and a critic that passes everything."""
    forms = (form,) if isinstance(form, str) else form

    def script(request):
        content = request.messages[0]["content"]
        if request.role == "critic":
            views = json.loads(content.split("Expressions:\n", 1)[1].split("\n\nCited claims:")[0])
            return {"findings": [{"proposal_index": v["expression_index"], "check": "candidate_symmetric_scrutiny",
                                  "verdict": "pass", "severity": "minor", "referent": v["terms"][0]["term"],
                                  "finding": "treats candidates alike"} for v in views]}
        summary = json.loads(content)
        wanted = [f["ref"] for f in summary["features"] if f["name"] in names]
        shape = forms[len(summary["previous_generations"]) % len(forms)]
        return {"expressions": [{"terms": [{"form": shape, "features": [ref], "direction": direction,
                                            "supporting_claim_ids": list(claims),
                                            "justification": "declared for the test",
                                            **({"prior_coefficient": prior} if prior is not None else {})}
                                           for ref in wanted],
                                 "rationale": f"generation over {names} as {shape}"}]}
    return script


def proposer_naming(ref):
    """A proposer that insists on a feature reference the build refused, whatever the summary offered."""
    def script(request):
        if request.role == "critic":
            return {"findings": []}
        return {"expressions": [{"terms": [{"form": "identity", "features": [ref], "direction": "higher_better",
                                            "justification": "asks for a refused feature"}], "rationale": "x"}]}
    return script


def roster_for(script):
    from mas.core.models import ModelRoster, ScriptedAdapter
    adapters = {"p": ScriptedAdapter("p", script, model="proposer-model", provider_family="family_a"),
                "c": ScriptedAdapter("c", script, model="critic-model", provider_family="family_b")}
    return ModelRoster(adapters, {"proposer": "p", "critic": "c"}), adapters


def confirmed_task(core, members=("c000", "c001")):
    """A task whose three criteria are confirmed, so an adopted expression has a rule set to enter."""
    from mas.core import task
    spec = {"objective_text": "Rank compounds for T1", "mode": "conditional",
            "scope_entities": TASK_CONTEXT["scope_entities"], "constraints": [],
            "candidate_universe": {"kind": "enumerated_set", "members": list(members)},
            "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
            "human_review_requirements": {"recommended_requires_hd": False},
            "seed_candidates": TASK_CONTEXT["seed_candidates"]}
    task_id, _version = task.record_version(core, spec, by=OPERATOR)
    for item in (POTENCY, DESCRIPTOR_A, DESCRIPTOR_B):
        criteria.propose(core, task_id, item["attribute"], item["rule"], by=OPERATOR)
    criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    return task_id


def run_stage(core, items, cells, *, mode="potency", settings=None, run_id=None, task_id=None,
              script=None, task_context=None, identities=None, baseline=None):
    from mas.core.ids import new_id
    info = rules_info_for(items)
    baseline = baseline if baseline is not None else assessor.preference_scores(cells, info, {})
    roster, adapters = roster_for(script or proposer_over("Descriptor B"))
    record = sr_stage.fit_and_install(
        core, roster, run_id=run_id or new_id("run"), task_id=task_id or confirmed_task(core),
        task_context=task_context or TASK_CONTEXT,
        rule_set={"rule_set_ref": "rules@v1", "coverage_floor": 1.0, "pending": [], "deferred": [],
                  "entries": [i["entry"] for i in items], "ordering_method": {"kind": "weighted_preference"}},
        rules=items, cells_by_candidate=cells, rules_info=info, weights={}, baseline_scores=baseline,
        identities=identities or {}, settings={"sr.mode": mode, "rank.method": "symbolic_expression",
                                               "run.seed": 0, **(settings or {})}, by=OPERATOR)
    return record, adapters


def test_the_proposer_summary_carries_no_candidate_identifier_and_no_target_value(core):
    items, cells, split = potency_world()
    dataset = sr_stage.build_dataset(mode="potency", rules=items, cells_by_candidate=cells,
                                     task_context=TASK_CONTEXT, target_rule_ref=POTENCY["entry"]["rule_ref"])
    sr_stage.refuse_leaking_features(dataset, split)
    summary = sr_stage.summary_for_proposer(dataset, split, max_terms=4, route="fitted", min_training_rows=12,
                                            history=[])
    text = json.dumps(summary)
    assert not any(ref in text for ref in cells)                       # no candidate is named
    assert "refotinib" not in text and "RF-7" not in text
    assert set(summary["target"]) <= {"kind", "ref", "name", "definition", "unit", "direction", "aggregation", "note"}
    assert all(set(feature) == {"ref", "name", "definition", "unit", "direction", "determination_bases",
                                "rows_with_a_value", "coverage_share", "training_quartiles"}
               for feature in summary["features"])          # declarations and aggregates only, no column of values
    assert summary["rows"]["holdout"] == "withheld until the adoption decision"
    assert {f["ref"] for f in summary["features"]} == {"attr_a@v1", "attr_b@v1"}
    assert [r["reason"] for r in summary["features_refused"]] == ["target_derived"]     # the potency cell itself
    assert summary["features"][0]["training_quartiles"]["p50"] is not None
    sr_stage.assert_blind(summary, candidate_refs=list(cells), reference_labels=["refotinib", "RF-7"])
    leaked = dict(summary, features=summary["features"] + [{"ref": "x", "rows": list(cells)[:2]}])
    with pytest.raises(sr_stage.HonestyViolation, match="candidate"):
        sr_stage.assert_blind(leaked, candidate_refs=list(cells), reference_labels=["refotinib"])
    with pytest.raises(sr_stage.HonestyViolation, match="reference outcome"):
        sr_stage.assert_blind(dict(summary, note="refotinib is the compound to beat"), candidate_refs=[],
                              reference_labels=["refotinib"])


def test_a_feature_derived_from_the_target_is_refused_deterministically(core):
    items, cells, split = potency_world()
    with_prediction = items + [PREDICTED_POTENCY]
    for ref, rows in cells.items():
        rows.append(cell_for(ref, PREDICTED_POTENCY, 1.0))
    dataset = sr_stage.build_dataset(mode="potency", rules=with_prediction, cells_by_candidate=cells,
                                     task_context=TASK_CONTEXT, target_rule_ref=POTENCY["entry"]["rule_ref"])
    refused = {item["ref"]: item for item in dataset.refused}
    assert set(refused) == {"attr_potency@v1", "attr_predicted_potency@v1"}   # a prediction of the target is the target
    assert all(item["reason"] == "target_derived" for item in refused.values())
    assert "attr_predicted_potency@v1" not in dataset.refs
    # a feature in perfect rank agreement with the target over the fitting rows goes the same way
    honest, perfect, _ = potency_world(swap_train=False)
    dataset = sr_stage.build_dataset(mode="potency", rules=honest, cells_by_candidate=perfect,
                                     task_context=TASK_CONTEXT, target_rule_ref=POTENCY["entry"]["rule_ref"])
    sr_stage.refuse_leaking_features(dataset, split)
    assert "attr_b@v1" not in dataset.refs
    assert [r["detail"] for r in dataset.refused if r["ref"] == "attr_b@v1"][0].startswith("rank agreement")
    record, _ = run_stage(core, honest, perfect, script=proposer_naming("attr_b@v1"))
    attempt = record["attempts"][0]
    assert [r["reason"] for r in attempt["rejected"]] == ["target_derived_feature", "target_derived_feature"]
    assert attempt["stopped"] == "diminishing_information_gain" and "selected" not in attempt
    assert core.artifacts.payload(attempt["rejected"][0]["artifact_id"])["reason"] == "target_derived_feature"


# --- the stage: generations, the holdout gate, and the fallback -------------------------------------

def test_generations_cannot_overfit_their_way_to_adoption(core):
    """A feature that agrees with the target on the fitting and comparison rows but not on the
    holdout: the loop cannot see that, and the one holdout look is what refuses it."""
    items, cells, _split = potency_world(reversed_on_holdout=True)
    record, adapters = run_stage(core, items, cells,
                                 script=proposer_over("Descriptor B", form=("identity", "log1p", "square", "inverse")))
    (attempt,) = record["attempts"]
    assert attempt["route"] == "fitted" and len(attempt["generations"]) == 4
    selection = attempt["selected"]["selection"]
    assert (selection["metric"], selection["n"], selection["n_rows"]) == ("validation_r2", 11, 11)
    assert selection["value"] > 0.98                           # all but perfect on the rows it was allowed to see
    assert attempt["selected"]["record"]["canonical_text"] == "attr_b@v1"      # ties go to the simplest text
    adoption = attempt["adoption"]
    assert adoption["expression"] == pytest.approx(-1.0) and adoption["baseline"] > adoption["expression"]
    assert adoption["margin"] < 0 and adoption["reason"] == "did_not_beat_the_baseline_on_the_holdout"
    assert record["adopted"] is False and record["installed_rule_set_ref"] is None
    # the fourth generation's 1/(1+x) falls with the feature although it declared higher_better
    rejected = [r["reason"] for r in attempt["rejected"]]
    assert rejected == ["sign_contradicts_declared_direction"]
    events = [e for e in core.journal.replay(record["run_id"])]
    assert [e.event_type for e in events].count("exchange.proposed") == 4
    assert [e.event_type for e in events].count("decision.recorded") == 1     # the holdout is consulted once
    assert next(e for e in events if e.event_type == "decision.recorded").payload["decision"] == \
        "keep_the_weighted_preference_baseline"
    assert sum(1 for g in attempt["generations"] for _ in g["expressions"]) == 3


def test_the_baseline_is_kept_when_the_expression_does_not_win_by_enough(core):
    from mas.core import constants
    from mas.core.ids import new_id
    items, cells, _split = potency_world()
    run_id = new_id("run")
    constants.register(core, "const_sr_min_improvement", 0.9, unit="fraction", scope="core_policy",
                       cutoff_basis="expert_set", set_by=OPERATOR, stream_id=run_id)
    record, _ = run_stage(core, items, cells, run_id=run_id)
    (attempt,) = record["attempts"]
    adoption = attempt["adoption"]
    assert adoption["min_improvement"] == 0.9
    assert 0.0 < adoption["margin"] < 0.9                      # it does win, just not by the registered margin
    assert record["adopted"] is False and adoption["reason"] == "did_not_beat_the_baseline_on_the_holdout"
    assert sr_stage.record_of(core, run_id)["attempts"][0]["selected"]["record"]["provenance"] == "fitted"
    again, _ = run_stage(core, items, cells, run_id=run_id)
    assert again["artifact_id"] == record["artifact_id"]        # a resumed run refits nothing and registers nothing twice


def test_coefficients_come_from_the_cited_prior_when_rows_are_scarce(core):
    items, cells, _split = potency_world(n=16)
    record, _ = run_stage(core, items, cells, script=proposer_over("Descriptor B", prior=0.5))
    (attempt,) = record["attempts"]
    assert attempt["route"] == "expert_prior" and attempt["rows"]["fitting"] == 7
    selected = attempt["selected"]
    assert selected["record"]["provenance"] == "expert_prior" and selected["record"]["coefficients"][0] > 0
    assert selected["diagnostics"]["declared_priors"] == [0.5] and selected["diagnostics"]["condition_estimate"] is None
    assert attempt["adoption"]["adopted"] in (True, False)     # the holdout gate applies to a prior too
    without_prior, _ = run_stage(core, items, cells, script=proposer_over("Descriptor B"))
    assert [r["reason"] for r in without_prior["attempts"][0]["rejected"]][0] == "fit_refused:no_declared_prior"


def test_a_blocking_critic_finding_with_a_referent_rejects_the_expression(core):
    items, cells, _split = potency_world()

    def script(request):
        if request.role == "critic":
            views = json.loads(request.messages[0]["content"].split("Expressions:\n", 1)[1].split("\n\nCited claims:")[0])
            return {"findings": [{"proposal_index": 0, "check": "candidate_symmetric_scrutiny", "verdict": "fail",
                                  "severity": "blocking", "referent": views[0]["terms"][0]["term"],
                                  "finding": "the term favours one chemotype the citations do not support"},
                                 {"proposal_index": 0, "check": "evidence_support", "verdict": "fail",
                                  "severity": "blocking", "referent": "",
                                  "finding": "no referent, so not a finding"}]}
        return proposer_over("Descriptor B")(request)

    record, _ = run_stage(core, items, cells, script=script)
    (attempt,) = record["attempts"]
    assert [r["reason"] for r in attempt["rejected"]] == ["critic_blocking", "critic_blocking"]   # two generations
    assert "favours one chemotype" in attempt["rejected"][0]["detail"]
    assert "no referent" not in attempt["rejected"][0]["detail"]
    assert "selected" not in attempt and record["adopted"] is False


def test_a_hinge_constant_must_come_from_a_quartile_or_a_cited_claim(core):
    items, cells, _split = potency_world()

    def invented(request):
        if request.role == "critic":
            return {"findings": []}
        summary = json.loads(request.messages[0]["content"])
        ref = next(f["ref"] for f in summary["features"] if f["name"] == "Descriptor B")
        return {"expressions": [{"terms": [{"form": "hinge", "features": [ref], "constant": 6.66,
                                            "direction": "higher_better", "justification": "invented"}],
                                 "rationale": "an unsourced knee"},
                                {"terms": [{"form": "hinge", "features": [ref],
                                            "constant": next(f["training_quartiles"]["p50"] for f in summary["features"]
                                                             if f["ref"] == ref),
                                            "direction": "higher_better", "justification": "the median shown"}],
                                 "rationale": "a knee at the shown median"}]}

    record, _ = run_stage(core, items, cells, script=invented)
    (attempt,) = record["attempts"]
    assert [r["reason"] for r in attempt["rejected"]] == ["unsourced_constant", "unsourced_constant"]
    assert attempt["selected"]["record"]["terms"][0]["form"] == "hinge"      # the knee at the shown median stands


def test_a_terms_citations_decide_whether_it_is_called_mechanistic(core):
    from mas.core import ledger
    from mas.core.ids import new_id
    items, cells, _split = potency_world()
    task_id = confirmed_task(core)
    verified = ledger.record_claim(core, task_id, {
        "location": {"location_kind": "paragraph", "locator_value": "sec1.p1", "quoted_span": "lipophilicity drives "
                     "cellular potency in this series", "span_checked_against_source": True},
        "normalized_statement": "lipophilicity drives potency", "determination_basis": "measured", "value": 1.0,
        "unit": "units", "source_ref": "src_x", "reading_depth": "full_text"},
        by=OPERATOR, admission_state="admitted", admission_reasons=["quote_verified"])
    quarantined = ledger.record_claim(core, task_id, {
        "location": {"location_kind": "paragraph", "locator_value": "sec1.p2", "quoted_span": "no such span",
                     "span_checked_against_source": False},
        "normalized_statement": "unverified", "determination_basis": "measured", "source_ref": "src_x",
        "reading_depth": "full_text"},
        by=OPERATOR, admission_state="quarantined", admission_reasons=["quote_not_found_in_passage"])
    grounded, _ = run_stage(core, items, cells, task_id=task_id, run_id=new_id("run"),
                            script=proposer_over("Descriptor B", claims=[verified]))
    assert grounded["attempts"][0]["selected"]["grounding"][0]["grounding"] == "mechanistic"
    record, _ = run_stage(core, items, cells, task_id=task_id, run_id=new_id("run"),
                          script=proposer_over("Descriptor B", claims=[quarantined, "claim_that_does_not_exist"]))
    note = record["attempts"][0]["selected"]["grounding"][0]
    assert note["grounding"] == "associational" and note["unresolved_claim_refs"] == ["claim_that_does_not_exist"]


def test_expression_scores_match_the_preference_scores_contract():
    items = [DESCRIPTOR_A, DESCRIPTOR_B]
    info = rules_info_for(items)
    cells = {f"cand_ik-C{i:03d}": [cell_for(f"cand_ik-C{i:03d}", items[0], float(i)),
                                   cell_for(f"cand_ik-C{i:03d}", items[1], float((i * 7) % 5))] for i in range(12)}
    cells["cand_ik-EMPTY"] = [cell_for("cand_ik-EMPTY", items[0], None), cell_for("cand_ik-EMPTY", items[1], None)]
    rows = [({"attr_a@v1": float(i), "attr_b@v1": float((i * 7) % 5)}, float(i)) for i in range(12)]
    expression = symbolic.fit([term("identity", "attr_a@v1")], rows, ridge=0.0, max_condition=1e8).expression
    baseline = assessor.preference_scores(cells, info, {})
    scored = assessor.expression_scores(cells, info, expression)
    assert set(scored) == set(baseline) == set(cells)
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in scored.values())
    assert all(pair[0] is None or isinstance(pair[0], float) for pair in scored.values())
    assert all(0.0 <= pair[1] <= 1.0 for pair in scored.values())
    assert scored["cand_ik-EMPTY"] == (None, 0.0) and baseline["cand_ik-EMPTY"] == (None, 0.0)
    assert scored["cand_ik-C005"][0] == pytest.approx(5.0, abs=1e-6) and scored["cand_ik-C005"][1] == 1.0
    # a cell of a rule that is no longer in the confirmed set is missing evidence, not a usable value
    assert assessor.expression_scores(cells, {}, expression)["cand_ik-C005"] == (None, 0.0)
    assert assessor.expression_scores(cells, info, expression.record()) == scored


# --- the four gaps this slice closes ----------------------------------------------------------------

def test_a_fitted_ordering_method_forces_the_exploratory_label(core):
    task_id = confirmed_task(core)
    assert criteria.rule_set(core, task_id)["acceptance_label"] == "prespecified"
    fitted_method = {"kind": "symbolic_expression", "expression_text": "0.5*attr_b@v1 + 6.0",
                     "provenance": "fitted", "tie_break": "candidate_id"}
    fitted = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR,
                                                                        ordering_method=fitted_method))
    assert fitted["acceptance_label"] == "exploratory"
    assert fitted["acceptance_reasons"] == ["the ordering method was fitted on the results it ranks"]
    assert criteria.chosen_after_results(fitted_method) and not criteria.chosen_after_results({"kind": "weighted_preference"})
    preregistered = criteria.rule_set(core, task_id, criteria.confirm_rule_set(
        core, task_id, by=OPERATOR, ordering_method=fitted_method, preregistration_ref="proto_sr_1"))
    assert preregistered["acceptance_label"] == "prespecified"      # declared before the results, so not exploratory
    assert preregistered["preregistration_ref"] == "proto_sr_1"


def test_the_comparability_key_includes_the_member_set(core):
    context = {"task_context_id": "task_members", "version": 1, "objective_text": "Rank compounds",
               "mode": "conditional", "evaluation_scope": {"comparison_basis": "both"},
               "scope_entities": [], "constraints": [],
               "candidate_universe": {"kind": "enumerated_set", "members": ["a", "b", "c"]}}
    first = leaderboard.leaderboard_record(core, context, members=["a", "b", "c"])
    assert leaderboard.leaderboard_record(core, context, members=["c", "b", "a"]) == first   # a set, not a list
    assert leaderboard.leaderboard_record(core, context) == first                            # from the universe
    smaller = leaderboard.leaderboard_record(core, context, members=["a", "b"])
    assert smaller != first        # a percentile score depends on the set, so these are not comparable
    opened = [e.payload for e in core.journal.replay("task_members") if e.event_type == "leaderboard.current_set"]
    assert [r["leaderboard_id"] for r in opened] == [first, smaller]
    assert opened[-1]["supersedes"] == first
    assert leaderboard.member_set_hash(context) == leaderboard.member_set_hash(context, ["c", "a", "b"])


def _snapshot(*, states, scores, cells, floor=0.75, entries=(("rule_attr_a@v1", "preference"),)):
    context = {"task_context_id": "task_abs", "version": 1, "objective_text": "o", "mode": "conditional",
               "evaluation_scope": {"comparison_basis": "both"}}
    rule_set = {"rule_set_ref": "rules@v1", "ordering_method": {"kind": "weighted_preference"},
                "entries": [{"rule_ref": ref, "rule_kind": kind} for ref, kind in entries]}
    roll_ups = {ref: {"state": state, "state_reason": f"{state}: for the test", "hard_rule_coverage": None,
                      "blocking_unknowns": []} for ref, state in states.items()}
    return leaderboard.build_snapshot(task_context=context, leaderboard_id="lbd_abs_1", run_id="run_abs",
                                      round_id="r", rule_set=rule_set, evidence_snapshot_id=None, roll_ups=roll_ups,
                                      cells=cells, scores=scores, identities={}, parent=None, sweep_completeness=1.0,
                                      budget={}, ranking_coverage_floor=floor)


def test_a_snapshot_with_nothing_rankable_records_no_recommendation():
    thin = {ref: [cell_for(ref, DESCRIPTOR_A, 1.0)] for ref in ("a", "b")}
    snapshot = _snapshot(states={"a": "provisional", "b": "provisional"}, scores={"a": (0.9, 0.3), "b": (0.4, 0.2)},
                         cells=thin)
    assert snapshot["result_kind"] == "no_recommendation" and snapshot["no_recommendation"] is True
    assert snapshot["abstention_reason"] == "insufficient_coverage"
    assert snapshot["reporting_tuple"]["unranked_for_coverage"] == 2
    assert all(entry["position"] is None for entry in snapshot["candidate_entries"])
    excluded = _snapshot(states={"a": "rejected", "b": "rejected"}, scores={}, cells=thin)
    assert excluded["abstention_reason"] == "all_candidates_excluded"
    conflicted = {ref: [dict(cell_for(ref, DESCRIPTOR_A, 1.0), verdict="unknown_conflicted", value=None),
                        cell_for(ref, DESCRIPTOR_B, 2.0)] for ref in ("a", "b")}
    assert _snapshot(states={"a": "provisional", "b": "provisional"}, scores={}, cells=conflicted,
                     )["abstention_reason"] == "unresolved_conflicts"
    nothing = {ref: [dict(cell_for(ref, DESCRIPTOR_A, None), verdict="unknown_missing")] for ref in ("a", "b")}
    assert _snapshot(states={"a": "provisional", "b": "provisional"}, scores={}, cells=nothing,
                     )["abstention_reason"] == "evidence_unavailable"
    ranked = _snapshot(states={"a": "provisional", "b": "provisional"}, scores={"a": (0.9, 1.0), "b": (0.4, 1.0)},
                       cells=thin)
    assert ranked["result_kind"] == "ranked_under_score" and ranked["abstention_reason"] is None


def test_predicted_values_need_their_own_attribute_with_its_own_rule():
    measured = POTENCY["attribute"]
    predicted = PREDICTED_POTENCY["attribute"]
    claim = {"claim_id": "claim_1", "admission_state": "admitted", "evidence_kind": "database_entry",
             "determination_basis": "predicted", "value": 7.2, "unit": "pChEMBL",
             "location": {"location_kind": "record_field", "locator_value": "x", "span_checked_against_source": True}}
    usable, set_aside = assessor.usable_claims([claim], dict(measured, acceptable_value_sources=["database_entry"]))
    assert not usable and set_aside[0]["set_aside_reason"] == "determination_basis_not_accepted"
    usable, set_aside = assessor.usable_claims([claim], predicted)
    assert [c["claim_id"] for c in usable] == ["claim_1"] and not set_aside
    assert assessor.declares_predicted(predicted) and not assessor.declares_predicted(measured)
    with pytest.raises(criteria.InvariantViolation, match="their own attribute"):
        criteria.check_attribute(dict(predicted, acceptable_determination_bases=["measured", "predicted"]))
    with pytest.raises(criteria.InvariantViolation, match="acceptable_determination_bases"):
        criteria.check_attribute(dict(predicted, acceptable_determination_bases=["guessed"]))
    criteria.check_attribute(predicted)
    assessment, reason = assessor.assess_cell(candidate={"candidate_id": "cand_ik-C000"}, attribute=predicted,
                                              rule=PREDICTED_POTENCY["rule"], rule_set_ref="rules@v1", claims=[claim],
                                              resolved=True)
    assert (assessment["verdict"], assessment["value"]) == ("pass", 7.2)
    assert assessment["value_kind"] == "predicted" and assessment["determination_basis"] == "predicted"
    assert "7.2 pChEMBL" in reason["reason_text"]


# --- end to end: fitted, adopted, installed, and reported ---------------------------------------------

from mas.core.broker import Broker, ProviderResponse, ToolContract   # noqa: E402  (fixtures only)

ADAPTER = {"adapter_id": "sr_test_adapter", "adapter_version": "1", "primary_scheme": "ik"}
UNITS = {"MolecularWeight": "g/mol", "XLogP": "log units"}
WORLD = {}
for _index in range(40):
    _weight = 250.0 + (_index * 37) % 290
    _logp = 1.0 + ((_index * 13) % 50) / 10.0
    WORLD[f"C{_index:03d}"] = {"MolecularWeight": _weight, "XLogP": _logp,
                               "potency": round(2.0 + 0.004 * _weight + 0.3 * _logp, 4)}
WORLD["REFOTINIB"] = {"MolecularWeight": 410.0, "XLogP": 3.0, "potency": round(2.0 + 0.004 * 410.0 + 0.9, 4)}

E2E = [rule_item("attr_t1_potency", "T1 curated potency", capability="interaction_evidence_lookup",
                 question="pchembl_values", scheme="ik", parameters={"target_chembl_id": "CHEMBL_T1"},
                 unit="pChEMBL", sources=("curated_measurement",)),
       rule_item("attr_molecular_weight", "Molecular weight", scheme="ik", parameters={"property": "MolecularWeight"},
                 unit="g/mol", direction="lower_better"),
       rule_item("attr_calculated_logp", "Calculated logP", scheme="ik", parameters={"property": "XLogP"},
                 unit="log units", direction="lower_better")]


def contract(tool_id, capability, kind, question, evidence, ceiling, *, required=(), identity=("identifier",)):
    return ToolContract(tool_id=tool_id, capability=capability, capability_kind=kind, question_kinds=(question,),
                        contract_version="1", implementation_version="fake-1", purpose_statement="test",
                        evidence_kind_produced=evidence, claim_strength_ceiling=ceiling,
                        required_inputs=required, identity_inputs=identity)


class Identities:
    contract = contract("tool_sr_identity", "identity_resolution", "entity_resolution", "resolve_name",
                        "database_entry", "curated", required=("name",), identity=())

    def invoke(self, question_kind, inputs):
        name = inputs["name"].upper()
        return ProviderResponse(values=[{"name": "identity", "value": {
            "preferred_label": name, "identifiers": [{"scheme": "ik", "value": name}],
            "link_basis": "exact_identifier_match"}, "value_kind": "curated"}], data_version="fake")


class Potency:
    contract = contract("tool_sr_potency", "interaction_evidence_lookup", "relationship_evidence_lookup",
                        "pchembl_values", "curated_measurement", "measured")

    def invoke(self, question_kind, inputs):
        row = WORLD[inputs["identifier"]]
        return ProviderResponse(values=[{"name": "pchembl_value", "value": row["potency"], "unit": "pChEMBL",
                                         "value_kind": "measured",
                                         "source_record_ref": f"chembl:{inputs['identifier']}"}],
                                data_version="fake", upstream_refs=[f"chembl:{inputs['identifier']}"])


class Descriptors:
    contract = contract("tool_sr_descriptors", "property_estimate", "attribute_estimate", "computed_property",
                        "database_entry", "curated")

    def invoke(self, question_kind, inputs):
        field = inputs["property"]
        return ProviderResponse(values=[{"name": field, "value": WORLD[inputs["identifier"]][field],
                                         "unit": UNITS[field], "value_kind": "derived",
                                         "source_record_ref": f"pubchem:{inputs['identifier']}"}],
                                data_version="fake", upstream_refs=[f"pubchem:{inputs['identifier']}"])


def e2e_task(core):
    from mas.core import task
    spec = {"objective_text": "Prioritize compounds for target T1", "mode": "conditional",
            "scope_entities": TASK_CONTEXT["scope_entities"], "constraints": [],
            "candidate_universe": {"kind": "enumerated_set", "members": [f"c{i:03d}" for i in range(40)]},
            "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
            "human_review_requirements": {"recommended_requires_hd": False},
            "seed_candidates": [{"candidate_ref": "refotinib", "aliases": ["RF-7"], "is_reference_outcome": True}]}
    task_id, _version = task.record_version(core, spec, by=OPERATOR)
    for item in E2E:
        criteria.propose(core, task_id, item["attribute"], item["rule"], by=OPERATOR)
    criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    return task_id


def test_an_adopted_expression_is_installed_before_the_snapshot_and_scores_the_board(core):
    from mas.core import config as config_mod
    from mas.core.controller import RunController
    task_id = e2e_task(core)
    broker = Broker(core, sleep=lambda seconds: None)
    for provider in (Identities(), Potency(), Descriptors()):
        broker.register(provider)
    roster, adapters = roster_for(proposer_over("Molecular weight", "Calculated logP"))
    settings = config_mod.resolve(project_file=None, environ={}, overrides={
        "sr.mode": "potency", "rank.method": "symbolic_expression", "run.seed": 0})
    controller = RunController(core, broker, roster, adapter=ADAPTER)
    run_id = controller.start(task_id, by=OPERATOR, settings=settings)
    assert controller.current_state(run_id) == "completed"

    record = sr_stage.record_of(core, run_id)
    assert record["adopted"] is True and record["installed_rule_set_ref"] == "rules@v2"
    (attempt,) = record["attempts"]
    assert attempt["route"] == "fitted" and attempt["split"]["counts"]["excluded"] == 1
    assert attempt["adoption"]["expression"] > attempt["adoption"]["baseline"]
    assert attempt["adoption"]["margin"] >= attempt["adoption"]["min_improvement"]

    snapshot = leaderboard.snapshots(core, task_id)[-1]
    ordering = snapshot["ordering_method"]
    assert snapshot["rules@v"] == "rules@v2" and ordering["kind"] == "symbolic_expression"
    assert ordering["provenance"] == "fitted" and ordering["tie_break"] == "candidate_id"
    assert ordering["feature_refs"] == ["attr_calculated_logp@v1", "attr_molecular_weight@v1"]
    assert ordering["expression_ref"].startswith("expr_") and ordering["fitter_version"] == symbolic.FITTER_VERSION
    installed = criteria.rule_set(core, task_id, "rules@v2")
    assert installed["acceptance_label"] == "exploratory"       # a ranking rule fitted on the results it ranks
    approvals = [e for e in core.journal.replay(task_id) if e.event_type == "criterion.version_approved"]
    assert approvals[-1].payload["rule_set_ref"] == "rules@v2"  # registered before the snapshot that reports it
    items = [i for i in review.items(core, [task_id]).values() if i["subject"]["kind"] == "rule_set_version"]
    assert len(items) == 1 and items[0]["state"] == "open" and items[0]["subject"]["id"] == "rules@v2"

    entries = {e["candidate_ref"]: e for e in snapshot["candidate_entries"]}
    assert entries["cand_ik-C000"]["preference_score"] == pytest.approx(WORLD["C000"]["potency"], abs=0.3)
    assert entries["cand_ik-C000"]["preference_coverage"] == 1.0
    ranked = sorted((e for e in entries.values() if e["position"]), key=lambda e: e["position"])
    assert ranked[0]["position"] == 1 and len(ranked) == 41
    measured = [WORLD[e["candidate_ref"].split("-", 1)[1]]["potency"] for e in ranked]
    # the board now orders by predicted potency; the shrinkage toward the prior keeps it just short of exact
    assert symbolic.kendall_tau([-e["position"] for e in ranked], measured) > 0.99
    assert entries["cand_ik-REFOTINIB"]["position"] is not None      # excluded from the fit, still ranked

    explained = sr_stage.rationale_of(core, run_id, "cand_ik-C000")
    assert [t["term"] for t in explained["terms"]] == sorted(
        [t["term"] for t in explained["terms"]], key=lambda text: -abs(
            next(abs(i["contribution"]) for i in explained["terms"] if i["term"] == text)))
    assert sum(t["share"] for t in explained["terms"]) == pytest.approx(1.0)
    assert explained["terms_missing"] == [] and explained["score"] == pytest.approx(
        entries["cand_ik-C000"]["preference_score"])

    prompts = [r.messages[0]["content"] for r in adapters["p"].requests]
    assert prompts and not any("cand_ik" in text or "REFOTINIB" in text or "refotinib" in text for text in prompts)
    kinds = [e.event_type for e in core.journal.replay(run_id)]
    assert kinds.index("decision.recorded") < kinds.index("leaderboard.snapshot_published")


def _e2e_store(root):
    """The end-to-end run above, in a store on disk, for the terminal client to read."""
    from mas.core import config as config_mod
    from mas.core.controller import RunController
    from mas.core.runtime import Core
    with Core.open(root) as core:
        task_id = e2e_task(core)
        broker = Broker(core, sleep=lambda seconds: None)
        for provider in (Identities(), Potency(), Descriptors()):
            broker.register(provider)
        roster, _adapters = roster_for(proposer_over("Molecular weight", "Calculated logP"))
        settings = config_mod.resolve(project_file=None, environ={}, overrides={
            "sr.mode": "potency", "rank.method": "symbolic_expression", "run.seed": 0})
        RunController(core, broker, roster, adapter=ADAPTER).start(task_id, by=OPERATOR, settings=settings)
    return task_id


def test_the_terminal_client_shows_the_expression_and_a_candidate_rationale(tmp_path, capsys):
    from mas.cli import main as cli
    root = tmp_path / "store"
    task_id = _e2e_store(root)
    assert cli.main(["--store", str(root), "score", "show", task_id]) == 0
    shown = capsys.readouterr().out
    assert "ordering method: symbolic_expression" in shown and "holdout kendall_tau" in shown
    assert "exploratory" in shown and "the ordering method was fitted on the results it ranks" in shown
    assert "attr_molecular_weight@v1" in shown and "refused feature T1 curated potency: target_derived" in shown
    assert "validation_r2" in shown and "splits {" in shown
    assert cli.main(["--store", str(root), "candidate", "show", task_id, "c000"]) == 0
    explained = capsys.readouterr().out
    assert "terms by contribution" in explained and "attr_calculated_logp@v1" in explained
    assert cli.main(["--store", str(root), "board", "show", task_id]) == 0
    assert "score = " in capsys.readouterr().out


def test_score_mode_regresses_the_baseline_score_from_the_preference_values(core):
    """`leaderboard_score` mode: the target is the baseline score over the whole set, and the
    comparison is against the baseline *recomputed on the holdout*, which a percentile score makes
    a different ranking."""
    items = [DESCRIPTOR_A, DESCRIPTOR_B, rule_item("attr_c", "Descriptor C", unit="units")]
    refs = [f"cand_ik-C{i:03d}" for i in range(48)]
    cells = {ref: [cell_for(ref, items[0], float((i * 29) % 41)), cell_for(ref, items[1], float((i * 7) % 48)),
                   cell_for(ref, items[2], float((i * 11) % 37))] for i, ref in enumerate(refs)}
    record, _ = run_stage(core, items, cells, mode="leaderboard_score",
                          script=proposer_over("Descriptor A", "Descriptor B", "Descriptor C"))
    (attempt,) = record["attempts"]
    assert attempt["mode"] == "leaderboard_score" and attempt["target_rule_ref"] is None
    assert attempt["route"] == "fitted" and attempt["selected"]["selection"]["metric"] == "kendall_tau"
    assert attempt["features_offered"] == ["attr_a@v1", "attr_b@v1", "attr_c@v1"]
    adoption = attempt["adoption"]
    assert adoption["metric"] == "kendall_tau" and adoption["baseline"] < 1.0   # set-dependent inside the holdout
    assert adoption["baseline_scorer"].startswith("weighted_preference recomputed")
    assert record["adopted"] == (adoption["margin"] >= adoption["min_improvement"])


def test_both_modes_run_and_only_one_expression_can_be_installed(core):
    items, cells, _split = potency_world()
    record, _ = run_stage(core, items, cells, mode="both", script=proposer_over("Descriptor B"))
    assert [attempt["mode"] for attempt in record["attempts"]] == ["potency", "leaderboard_score"]
    adopted = [a for a in record["attempts"] if (a.get("adoption") or {}).get("adopted")]
    assert record["installed_rule_set_ref"] if adopted else record["installed_rule_set_ref"] is None
    installed = [e.payload["rule_set_ref"] for e in core.journal.replay(record["task_id"])
                 if e.event_type == "criterion.version_approved"]
    assert len(installed) == 2 if adopted else len(installed) == 1     # one ordering method, one rule set version
