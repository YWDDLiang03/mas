"""Symbolic-regression scoring as a step of a run (design §5.7): the loop around `core/symbolic.py`.

The model is the source of structure here — features, forms, signed priors, prior magnitudes,
successive generations and the mechanistic account of each term — and every one of those
contributions passes a deterministic gate before it can touch a published ranking:

  build      the feature table comes from cells this run already assessed; no new tool call,
             and in `potency` mode nothing derived from the target being regressed.
  propose    the proposer sees feature names, definitions, units, directions, coverage counts,
             training-split quartiles and the previous generations' aggregate diagnostics.
             Never a per-candidate row, never the target column, never the reference outcome:
             the prompt is built from a summary object that is asserted free of candidate ids.
  gate       grammar (depth 1, offered features only, `max_terms`), hinge constants from the
             shown quartiles or a cited claim value, a blind critic running symmetric scrutiny,
             the fit's own refusals, and the declared sign of every coefficient.
  select     the mode's metric on the *select* split minus the complexity penalty.
  adopt      one comparison on the *holdout* split against the weighted-percentile baseline,
             which is recomputed on the holdout members because a percentile score is
             set-dependent. Below `min_improvement` the baseline is kept and the attempt is
             still recorded; the holdout is why more generations cannot buy adoption.
  install    the adopted expression becomes the rule set's `ordering_method` through
             `criteria.confirm_rule_set` — its approval event, and the `rule_set_version`
             review item asking an expert to confirm a fitted ranking rule, both before any
             snapshot is published.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Sequence

from . import assessor, constants, criteria, reading, review, symbolic
from .canonical import canonical_text
from .derivation import CRITIQUE_SCHEMA, _claims_block
from .ids import new_id
from .journal import EVAL_STREAM, actor as make_actor
from .models import ModelError, ModelRequest, ModelRoster, call_role
from .runtime import Core

SR_VERSION = "sr-stage-1"
SCORING = make_actor("controller", "symbolic-regression", "controller")
STEP = "symbolic_regression"

# Capabilities whose numeric cells may become features. Literature cells are left out: a
# literature value is a per-candidate reading, and a score built on it would need the reading
# to have run for every candidate, which the sweep does not promise.
FEATURE_CAPABILITIES = ("property_estimate", "record_field_lookup", "interaction_evidence_lookup",
                        "interaction_estimate")
# Names a feature may never carry: they would make the score an input to itself.
RESERVED_FEATURE_REFS = ("preference_score", "preference_coverage", "position", "rank")
MODES_BY_SETTING = {"off": (), "potency": ("potency",), "leaderboard_score": ("leaderboard_score",),
                    "both": ("potency", "leaderboard_score")}
BUFFER = 3          # expressions carried forward per generation: the experience buffer
MAX_RATIONALES = 5000   # per-candidate rationales kept in one artifact


class HonestyViolation(RuntimeError):
    """Something the proposer must not see reached its prompt. The step refuses; it never asks anyway."""


SR_SCHEMA = {
    "type": "object", "required": ["expressions"],
    "properties": {"expressions": {"type": "array", "items": {
        "type": "object", "required": ["terms", "rationale"],
        "properties": {
            "terms": {"type": "array", "items": {
                "type": "object", "required": ["form", "features", "direction", "justification"],
                "properties": {"form": {"type": "string", "enum": sorted(symbolic.FORMS)},
                               "features": {"type": "array", "items": {"type": "string"}},
                               "constant": {"type": ["number", "null"]},
                               "direction": {"type": "string", "enum": list(symbolic.TERM_DIRECTIONS)},
                               "prior_coefficient": {"type": ["number", "null"]},
                               "supporting_claim_ids": {"type": "array", "items": {"type": "string"}},
                               "justification": {"type": "string"}}}},
            "intercept_prior": {"type": "number"}, "rationale": {"type": "string"}}}}},
}

SR_PROPOSER_SYSTEM = (
    "You design the scoring expression for an evidence-driven prioritization task. You are given the features "
    "available (each already assessed for every candidate) with their definitions, units, directions, how many "
    "fitting rows carry a value, and the quartiles of each feature over those rows, plus the diagnostics of every "
    "earlier generation. You never see a per-candidate value, the target column, or any candidate's identity, and "
    "asking for them is refused. "
    "Build each expression from terms over the offered feature references, using only the forms given, applied to "
    "raw features (nothing nests). Declare for every term the direction in which its value should move the score: "
    "a fitted coefficient that contradicts the declared direction rejects the whole expression, so declare the "
    "direction you can defend pharmacologically rather than the one you think the data will show. Give a "
    "prior_coefficient wherever a magnitude can be justified: the fit shrinks toward it instead of toward zero, and "
    "where there are too few rows to fit, your priors are used directly. Cite in supporting_claim_ids the claims "
    "your justification rests on; a term whose citations exist, were admitted and had their spans verified is "
    "labelled mechanistic, otherwise associational - both are allowed in the score, only the label differs. A hinge "
    "constant must be one of the quartiles shown for that feature or a value in a claim you cite; never invent a "
    "cutoff. Prefer few, defensible terms: every term and every level of depth costs selection score. Propose two "
    "to four different expressions per generation and say in each rationale what it assumes."
)

SR_CRITIC_SYSTEM = (
    "You are a blind critic of proposed scoring expressions. You see the terms, the features they use with their "
    "definitions and units, the direction and prior magnitude declared for each term, the justification given, and "
    "the claims cited - not the proposer's overall reasoning, and no candidate data. For each expression run "
    "candidate_symmetric_scrutiny (would this expression treat every candidate alike, or does a term, a direction "
    "or a constant encode a preference for one kind of compound that the cited evidence does not support?), "
    "evidence_support (do the cited quotes support the declared direction and magnitude?), and "
    "unit_applicability_consistency (do the transformation and the unit make sense for that quantity?). Every "
    "finding must name its referent: a claim id or a term. Mark severity blocking only for a defect that should "
    "stop the expression being used to rank anything; a finding without a referent is not allowed."
)


# --- the feature table ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Feature:
    ref: str                     # the attribute reference, which is what an expression names
    name: str
    definition: str
    unit: str | None
    direction: str
    rule_ref: str
    capability: str
    determination_bases: tuple[str, ...]

    def offer(self, *, values: Sequence[float], rows: int, grid: Sequence[float]) -> dict[str, Any]:
        """What the proposer is shown about this feature: no candidate, no single value."""
        return {"ref": self.ref, "name": self.name, "definition": self.definition, "unit": self.unit,
                "direction": self.direction, "determination_bases": list(self.determination_bases),
                "rows_with_a_value": len(values), "coverage_share": round(len(values) / rows, 4) if rows else 0.0,
                "training_quartiles": symbolic.quantiles(values, grid) if len(values) >= 4 else None}


@dataclass
class Dataset:
    mode: str
    features: list[Feature]
    rows: dict[str, dict[str, float]]
    target: dict[str, float]
    target_spec: dict[str, Any]
    refused: list[dict[str, Any]] = field(default_factory=list)

    @property
    def refs(self) -> list[str]:
        return [feature.ref for feature in self.features]

    def drop(self, ref: str, *, reason: str, detail: str = "") -> None:
        feature = next((f for f in self.features if f.ref == ref), None)
        self.features = [f for f in self.features if f.ref != ref]
        for values in self.rows.values():
            values.pop(ref, None)
        self.refused.append({"ref": ref, "name": feature.name if feature else None, "reason": reason, "detail": detail})

    def split_rows(self, split: symbolic.Split, name: str) -> list[symbolic.Row]:
        """(features, target) rows of one split, in candidate order, for candidates that have a target."""
        return [(self.rows.get(ref, {}), self.target[ref]) for ref in split.members(name) if ref in self.target]

    def column(self, refs: Sequence[str], feature_ref: str) -> list[float]:
        return [self.rows[ref][feature_ref] for ref in refs if feature_ref in self.rows.get(ref, {})]


def _attr_ref(attribute: dict[str, Any]) -> str:
    return f"{attribute['attribute_id']}@v{attribute['version']}"


def _identifiers(attribute: dict[str, Any]) -> set[str]:
    # Over every route the attribute declares: a quantity read from two databases names its subject
    # in each of them, and a feature measured against the regressed target is the target whichever
    # route carried it.
    return {str(value) for route in criteria.evidence_routes(attribute)
            for value in ((route or {}).get("parameters") or {}).values()
            if isinstance(value, (str, int)) and not isinstance(value, bool)}


def potency_target_rules(rules: list[dict[str, Any]], task_context: dict[str, Any]) -> list[str]:
    """Rule refs measuring curated potency against a required scope entity: one fit per target."""
    required = {str(e.get("identifier")) for e in task_context.get("scope_entities", []) if e.get("role") == "required"}
    out = []
    for item in rules:
        attribute = item["attribute"]
        capabilities = {(r or {}).get("capability") for r in criteria.evidence_routes(attribute)}
        if ("interaction_evidence_lookup" in capabilities and _identifiers(attribute) & required
                and attribute.get("measurement_kind") == "quantitative" and not assessor.declares_predicted(attribute)):
            out.append(item["entry"]["rule_ref"])
    return sorted(out)


def build_dataset(*, mode: str, rules: list[dict[str, Any]], cells_by_candidate: dict[str, list[dict[str, Any]]],
                  task_context: dict[str, Any], target_rule_ref: str | None = None,
                  baseline_scores: dict[str, tuple[float | None, float]] | None = None) -> Dataset:
    """The feature table, from cells this run already assessed. No tool call, no new evidence."""
    if mode not in symbolic.MODES:
        raise ValueError(f"unknown symbolic-regression mode {mode!r}")
    by_rule = {item["entry"]["rule_ref"]: item for item in rules}
    candidates = sorted(cells_by_candidate)
    target: dict[str, float] = {}
    offered: list[Feature] = []
    refused: list[dict[str, Any]] = []
    if mode == "potency":
        item = by_rule[target_rule_ref]
        attribute = item["attribute"]
        target_ref, target_ids = _attr_ref(attribute), _identifiers(attribute)
        for candidate in candidates:
            for cell in cells_by_candidate[candidate]:
                if cell["rule_ref"] == target_rule_ref and cell["verdict"] in ("pass", "fail") \
                        and isinstance(cell.get("value"), (int, float)) and not isinstance(cell["value"], bool):
                    target[candidate] = float(cell["value"])
        target_spec = {"kind": "assessed_attribute", "ref": target_ref, "name": attribute["name"],
                       "definition": attribute["definition"], "unit": attribute.get("unit"),
                       "direction": attribute.get("direction"), "aggregation": attribute.get("aggregation"),
                       "note": "the regressed quantity; neither it nor anything measured against the same target "
                               "is offered as a feature"}
        for other in rules:
            candidate_attr = other["attribute"]
            routes = criteria.evidence_routes(candidate_attr)
            quantitative = candidate_attr.get("measurement_kind") == "quantitative"
            # Every route has to be a sweep-wide one: a cell pooling a literature reading into its
            # value is as unpromised for the universe as a purely literature cell is.
            if not routes or not quantitative or not all((r or {}).get("capability") in FEATURE_CAPABILITIES
                                                         for r in routes):
                continue
            ref = _attr_ref(candidate_attr)
            if ref == target_ref or (_identifiers(candidate_attr) & target_ids):
                # Measured or predicted, anything scored against the regressed target is the target.
                refused.append({"ref": ref, "name": candidate_attr["name"], "reason": "target_derived",
                                "detail": f"shares the regressed target {sorted(target_ids)}"})
                continue
            offered.append(_feature(other, candidate_attr))
    else:
        scores = baseline_scores or {}
        for candidate in candidates:
            score = scores.get(candidate, (None, 0.0))[0]
            if score is not None:
                target[candidate] = float(score)
        target_spec = {"kind": "baseline_preference_score", "ref": "preference_score",
                       "name": "weighted-preference score", "unit": "score", "direction": "higher_better",
                       "definition": "the weighted mean desirability over the confirmed preference rules, over the "
                                     "whole candidate set; the expression has to reproduce it from values alone",
                       "note": "no feature may be the score, its coverage, or a position derived from it"}
        for other in rules:
            candidate_attr = other["attribute"]
            if other["rule"]["rule_kind"] != "preference" or candidate_attr.get("measurement_kind") != "quantitative":
                continue
            ref = _attr_ref(candidate_attr)
            if ref in RESERVED_FEATURE_REFS:
                refused.append({"ref": ref, "name": candidate_attr["name"], "reason": "derived_from_the_score",
                                "detail": "a reserved name: the score may not be an input to itself"})
                continue
            offered.append(_feature(other, candidate_attr))
    kept = {feature.ref for feature in offered}
    rows = {candidate: {ref: value for ref, value in
                        assessor.feature_values(cells_by_candidate[candidate], by_rule).items() if ref in kept}
            for candidate in candidates}
    return Dataset(mode, sorted(offered, key=lambda f: f.ref), rows, target, target_spec, refused)


def _feature(item: dict[str, Any], attribute: dict[str, Any]) -> Feature:
    # In precedence order where the attribute declares one, because then the order is the meaning:
    # ["measured", "predicted"] says every value of this feature is a measurement or, where the
    # candidate has none, a prediction standing in for one. Shown to the proposer as a list, so an
    # alphabetical one would have read as "predicted, then measured" -- the opposite.
    bases = (criteria.basis_precedence(attribute)
             or attribute.get("acceptable_determination_bases") or assessor.DEFAULT_DETERMINATION_BASES)
    return Feature(ref=_attr_ref(attribute), name=attribute["name"], definition=attribute["definition"],
                   unit=attribute.get("unit"), direction=attribute.get("direction", "non_directional"),
                   rule_ref=item["entry"]["rule_ref"],
                   capability="+".join(dict.fromkeys((r or {}).get("capability") or ""
                                                     for r in criteria.evidence_routes(attribute))),
                   determination_bases=tuple(bases))


def refuse_leaking_features(dataset: Dataset, split: symbolic.Split) -> Dataset:
    """Drop any feature whose training-split ranking is the target's ranking.

    A feature in perfect rank agreement with the target over the fitting rows is the target
    under another name — a prediction of it, a re-export of it, or the score itself in
    `leaderboard_score` mode. The expression would then be an identity, and the holdout gate
    would reward it for nothing.
    """
    train = [ref for ref in split.members("train") if ref in dataset.target]
    for feature in list(dataset.features):
        values = [(dataset.rows[ref][feature.ref], dataset.target[ref]) for ref in train
                  if feature.ref in dataset.rows.get(ref, {})]
        if len(values) < 4:
            continue
        tau = symbolic.kendall_tau([v for v, _ in values], [t for _, t in values])
        if tau is not None and abs(tau) >= 1.0 - 1e-9:
            dataset.drop(feature.ref, reason="target_derived",
                         detail=f"rank agreement with the target is {tau:+.0f} over {len(values)} fitting rows")
    return dataset


# --- what the proposer sees ----------------------------------------------------------------------

def summary_for_proposer(dataset: Dataset, split: symbolic.Split, *, max_terms: int, route: str,
                         min_training_rows: int, history: list[dict[str, Any]],
                         hinge_grid: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0)) -> dict[str, Any]:
    """The whole prompt payload, built from aggregates so that nothing per-candidate can leak into it."""
    train = [ref for ref in split.members("train") if ref in dataset.target]
    counts = split.counts()
    return {
        "mode": dataset.mode, "selection_metric": symbolic.SELECTION_METRICS[dataset.mode],
        "adoption_metric": symbolic.ADOPTION_METRIC,
        "grammar": {"forms": dict(sorted(symbolic.FORMS.items())), "depth": 1, "max_terms": max_terms,
                    "forms_taking_a_constant": list(symbolic.CONSTANT_FORMS),
                    "directions": list(symbolic.TERM_DIRECTIONS),
                    "notation": "a term is {form, features: [ref, ...], direction, constant?, prior_coefficient?, "
                                "supporting_claim_ids?, justification}"},
        "target": dataset.target_spec,
        "rows": {"fitting": len(train), "comparing_generations": counts["select"],
                 "holdout": "withheld until the adoption decision", "excluded_reference_outcomes": counts["excluded"],
                 "coefficients_from": route, "min_rows_to_fit": min_training_rows},
        "features": [feature.offer(values=dataset.column(train, feature.ref), rows=len(train), grid=hinge_grid)
                     for feature in dataset.features],
        "features_refused": dataset.refused,
        "previous_generations": history,
    }


def assert_blind(summary: dict[str, Any], *, candidate_refs: Sequence[str], reference_labels: Sequence[str]) -> None:
    """Refuse to send a summary that names a candidate or the disclosed reference outcome.

    The summary is built from aggregates, so this cannot trigger on a correct build; it is here
    because the one failure that would matter — a per-candidate row or the reference compound
    reaching the proposer — must not depend on a reviewer having read `summary_for_proposer`.
    """
    text = canonical_text(summary)
    named = sorted({ref for ref in candidate_refs if ref and ref in text})
    if named:
        raise HonestyViolation(f"the proposer summary names {len(named)} candidate(s), first {named[:3]}")
    if reading.names_entity(list(reference_labels), text):
        raise HonestyViolation("the proposer summary names the disclosed reference outcome")


# --- deterministic gates on a proposal -----------------------------------------------------------

def refused_feature_requests(specs: Any, dataset: Dataset) -> list[str]:
    """Named features the build refused, so the rejection says `target_derived`, not `unknown_feature`."""
    reasons = {item["ref"]: item["reason"] for item in dataset.refused}
    out = set()
    for term in specs if isinstance(specs, list) else []:
        names = term.get("features") if isinstance(term, dict) else None
        for name in ([names] if isinstance(names, str) else names or []):
            if name in reasons:
                out.add(f"{name}: {reasons[name]}")
    return sorted(out)


def hinge_problems(terms: Sequence[symbolic.Term], *, grids: dict[str, dict[str, float] | None],
                   claims_by_id: dict[str, dict[str, Any]]) -> list[str]:
    """A hinge constant comes from the quartiles the proposer was shown, or from a value it cited."""
    problems = []
    for term in terms:
        if term.form not in symbolic.CONSTANT_FORMS:
            continue
        grid = list((grids.get(term.features[0]) or {}).values())
        cited = [claims_by_id[ref].get("value") for ref in term.claim_refs if ref in claims_by_id]
        allowed = [float(v) for v in grid + cited if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not any(abs(term.constant - value) <= 1e-9 * max(1.0, abs(value)) for value in allowed):
            problems.append(f"{term.text}: the constant is neither a shown quartile of {term.features[0]} "
                            f"nor a value in a cited claim")
    return problems


def grounding_labels(terms: Sequence[symbolic.Term],
                     claims_by_id: dict[str, dict[str, Any]]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Label each term `mechanistic` only when every claim it cites exists, was admitted and had its span verified."""
    labels, notes = {}, []
    for term in terms:
        cited = [(ref, claims_by_id.get(ref)) for ref in term.claim_refs]
        grounded = bool(cited) and all(
            claim is not None and claim.get("admission_state") == "admitted"
            and (claim.get("location") or {}).get("span_checked_against_source") for _ref, claim in cited)
        labels[term.text] = "mechanistic" if grounded else "associational"
        notes.append({"term": term.text, "grounding": labels[term.text], "claim_refs": list(term.claim_refs),
                      "unresolved_claim_refs": [ref for ref, claim in cited if claim is None],
                      "justification": term.justification})
    return labels, notes


# --- the loop --------------------------------------------------------------------------------------

@dataclass
class ScoringContext:
    core: Core
    roster: ModelRoster
    run_id: str
    task_id: str
    by: dict[str, Any]
    knobs: dict[str, Any]
    candidate_refs: tuple[str, ...] = ()
    reference_labels: tuple[str, ...] = ()
    claim_streams: tuple[str, ...] = ()
    budget: Any = None
    ids: dict[str, Any] = field(default_factory=dict)
    request_ids: list[str] = field(default_factory=list)
    _claims: dict[str, dict[str, Any]] | None = None

    def claims_by_id(self) -> dict[str, dict[str, Any]]:
        """Claims of this run and task, loaded once and only if a term cites something."""
        if self._claims is None:
            from . import ledger
            self._claims = {claim["claim_id"]: claim
                            for claim in ledger.claims(self.core, list(self.claim_streams), admitted_only=False)}
        return self._claims

    def call(self, role: str, system: str, content: str, schema: dict[str, Any], question: str, max_tokens: int = 10000):
        response = call_role(self.core, self.roster, self.run_id, ModelRequest(
            role=role, system=system, messages=[{"role": "user", "content": content}], response_schema=schema,
            max_tokens=max_tokens, metadata={"question": question}), ids=self.ids, budget=self.budget)
        self.request_ids.append(response.request_id)
        return response

    def emit(self, kind: str, **kwargs):
        return self.core.journal.append(self.run_id, kind, actor=kwargs.pop("actor", SCORING), ids=self.ids, **kwargs)

    def put(self, kind: str, payload: dict[str, Any]) -> str:
        return self.core.artifacts.put(kind, payload)


def _critique(ctx: ScoringContext, proposals: list[dict[str, Any]], dataset: Dataset,
              generation: int) -> dict[int, list[dict[str, Any]]]:
    """One blind critic pass over the generation's surviving expressions."""
    units = {feature.ref: {"name": feature.name, "definition": feature.definition, "unit": feature.unit,
                           "direction": feature.direction} for feature in dataset.features}
    views = [{"expression_index": index, "terms": [
        {"term": term.text, "form": term.form, "features": [units.get(name, {"name": name}) | {"ref": name}
                                                            for name in term.features],
         "declared_direction": term.direction, "constant": term.constant,
         "prior_coefficient": term.prior_coefficient, "justification": term.justification,
         "supporting_claim_ids": list(term.claim_refs)} for term in item["terms"]]}
        for index, item in enumerate(proposals)]
    claims = ctx.claims_by_id()
    cited = sorted({ref for item in proposals for term in item["terms"] for ref in term.claim_refs if ref in claims})
    response = ctx.call("critic", SR_CRITIC_SYSTEM,
                        f"Scoring mode: {dataset.mode}\nTarget quantity: "
                        f"{json.dumps(dataset.target_spec, ensure_ascii=False)}\n\nExpressions:\n"
                        f"{json.dumps(views, ensure_ascii=False, indent=1)}\n\nCited claims:\n"
                        f"{_claims_block([claims[ref] for ref in cited])}", CRITIQUE_SCHEMA,
                        f"critique scoring expressions (generation {generation})", max_tokens=8000)
    out: dict[int, list[dict[str, Any]]] = {index: [] for index in range(len(proposals))}
    for finding in response.data["findings"]:
        if finding.get("referent") and finding["proposal_index"] in out:   # a finding without a referent is not a finding
            out[finding["proposal_index"]].append(finding)
    return out


def _reject(ctx: ScoringContext, *, mode: str, generation: int, index: int, spec: Any, reason: str,
            detail: str, findings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Record one rejected expression as its own artifact: what was proposed, and why it is not used."""
    record = {"mode": mode, "generation": generation, "proposal_index": index, "reason": reason, "detail": detail,
              "proposal": spec, "critic_findings": findings or [], "sr_version": SR_VERSION}
    record["artifact_id"] = ctx.put("scoring_expression_rejected", record)
    return record


def _generation_note(generation: int, results: list[dict[str, Any]], rejected: list[dict[str, Any]],
                     best: dict[str, Any] | None) -> dict[str, Any]:
    """The aggregate record of one generation; this, and only this, is what the next generation sees."""
    kept = sorted((r for r in results if r["selection_score"] is not None),
                  key=lambda r: (-r["selection_score"], r["n_terms"], r["canonical_text"]))[:BUFFER]
    return {"generation": generation,
            "expressions": [{"text": r["text"], "canonical_text": r["canonical_text"], "n_terms": r["n_terms"],
                             "route": r["diagnostics"]["route"], "metric": r["selection"],
                             "selection_score": round(r["selection_score"], 6),
                             "condition_estimate": r["diagnostics"]["condition_estimate"],
                             "residual_quantiles": r["diagnostics"]["residual_quantiles"],
                             "term_stability": r["diagnostics"]["term_stability"],
                             "grounding": [note["grounding"] for note in r["grounding"]]} for r in kept],
            "rejected": [{"reason": r["reason"], "detail": r["detail"]} for r in rejected],
            "best_so_far": None if best is None else {"text": best["text"],
                                                      "selection_score": round(best["selection_score"], 6)}}


def _attempt(ctx: ScoringContext, *, mode: str, dataset: Dataset, split: symbolic.Split,
             target_rule_ref: str | None) -> dict[str, Any]:
    """`generations` rounds of propose → gate → fit → select for one mode and one target."""
    knobs = ctx.knobs
    train = dataset.split_rows(split, "train")
    select = dataset.split_rows(split, "select")
    # The route is decided on the usable training rows, before any terms exist; a fit that still
    # cannot run on the terms actually proposed refuses with its own reason, recorded per expression.
    route = "fitted" if len(train) >= knobs["min_training_rows"] else "expert_prior"
    history: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    stopped = "generations_finished"
    if not dataset.features:
        return {"mode": mode, "target_rule_ref": target_rule_ref, "route": route, "generations": history,
                "rejected": rejected, "best": None, "stopped": "no_features_offered",
                "split": split.record(), "features_refused": dataset.refused}
    for generation in range(1, knobs["generations"] + 1):
        summary = summary_for_proposer(dataset, split, max_terms=knobs["max_terms"], route=route,
                                       min_training_rows=knobs["min_training_rows"], history=history,
                                       hinge_grid=knobs["hinge_grid"])
        try:
            assert_blind(summary, candidate_refs=ctx.candidate_refs, reference_labels=ctx.reference_labels)
        except HonestyViolation as violation:
            # Nothing is sent: the attempt ends here, loudly, and the baseline keeps the ranking.
            ctx.emit("run.annotated", payload={"annotation": "honesty_violation", "step": STEP, "mode": mode,
                                               "generation": generation, "detail": str(violation)},
                     summary=f"{STEP} refused to prompt the proposer: {violation}")
            stopped = f"honesty_violation:{violation}"
            break
        grids = {item["ref"]: item["training_quartiles"] for item in summary["features"]}
        try:
            response = ctx.call("proposer", SR_PROPOSER_SYSTEM, json.dumps(summary, ensure_ascii=False, indent=1),
                                SR_SCHEMA, f"propose scoring expressions (generation {generation})")
        except ModelError as error:
            stopped = f"model_error:{error.error_class}"   # a refused or unparsable call ends the loop, not the run
            break
        ctx.emit("exchange.proposed", payload={"step": STEP, "mode": mode, "generation": generation,
                                               "n_expressions": len(response.data["expressions"]),
                                               "request_id": response.request_id},
                 summary=f"{mode}: generation {generation} proposed {len(response.data['expressions'])} expression(s)")
        proposals, round_rejected = [], []
        for index, spec in enumerate(response.data["expressions"]):
            blocked = refused_feature_requests(spec.get("terms"), dataset)
            if blocked:
                round_rejected.append(_reject(ctx, mode=mode, generation=generation, index=index, spec=spec,
                                              reason="target_derived_feature", detail="; ".join(blocked)))
                continue
            try:
                terms = symbolic.parse_terms(spec.get("terms"), dataset.refs, max_terms=knobs["max_terms"])
            except symbolic.GrammarError as error:
                round_rejected.append(_reject(ctx, mode=mode, generation=generation, index=index, spec=spec,
                                              reason=f"grammar:{error.reason}", detail=str(error)))
                continue
            problems = hinge_problems(terms, grids=grids, claims_by_id=ctx.claims_by_id() if any(
                term.form in symbolic.CONSTANT_FORMS for term in terms) else {})
            if problems:
                round_rejected.append(_reject(ctx, mode=mode, generation=generation, index=index, spec=spec,
                                              reason="unsourced_constant", detail="; ".join(problems)))
                continue
            proposals.append({"index": index, "spec": spec, "terms": terms})
        findings: dict[int, list[dict[str, Any]]] = {}
        if proposals:
            try:
                findings = _critique(ctx, proposals, dataset, generation)
            except ModelError as error:
                stopped = f"model_error:{error.error_class}"
                findings = {}
            ctx.emit("exchange.critiqued", payload={"step": STEP, "mode": mode, "generation": generation,
                                                    "n_findings": sum(len(f) for f in findings.values())})
        results = []
        for position, item in enumerate(proposals):
            mine = findings.get(position, [])
            blocking = [f for f in mine if f["verdict"] == "fail" and f.get("severity") == "blocking"]
            if blocking:
                round_rejected.append(_reject(ctx, mode=mode, generation=generation, index=item["index"],
                                              spec=item["spec"], reason="critic_blocking",
                                              detail="; ".join(f["finding"] for f in blocking)[:500], findings=mine))
                continue
            try:
                fitted = (symbolic.fit(item["terms"], train, ridge=knobs["ridge"], max_condition=knobs["max_condition"],
                                       stability=True) if route == "fitted"
                          else symbolic.expert_prior_expression(
                              item["terms"], train, intercept_prior=float(item["spec"].get("intercept_prior") or 0.0)))
            except symbolic.FitRefused as error:
                round_rejected.append(_reject(ctx, mode=mode, generation=generation, index=item["index"],
                                              spec=item["spec"], reason=f"fit_refused:{error.reason}", detail=str(error),
                                              findings=mine))
                continue
            violations = symbolic.sign_violations(fitted.expression)
            if violations:
                round_rejected.append(_reject(ctx, mode=mode, generation=generation, index=item["index"],
                                              spec=item["spec"], reason="sign_contradicts_declared_direction",
                                              detail=json.dumps(violations, ensure_ascii=False), findings=mine))
                continue
            labels, grounding = grounding_labels(item["terms"], ctx.claims_by_id() if any(
                term.claim_refs for term in item["terms"]) else {})
            expression = symbolic.with_grounding(fitted.expression, labels)
            metric = symbolic.metric_on_rows(expression, select, mode=mode)
            score = symbolic.selection_score(metric["value"], expression, complexity_penalty=knobs["complexity_penalty"])
            record = expression.record()
            result = {"mode": mode, "generation": generation, "expression": expression, "record": record,
                      "diagnostics": fitted.diagnostics, "selection": metric, "selection_score": score,
                      "n_terms": len(expression.terms), "canonical_text": expression.canonical_text,
                      "text": expression.text, "grounding": grounding, "critic_findings": mine,
                      "rationale_text": str(item["spec"].get("rationale") or "")[:1000]}
            result["artifact_id"] = ctx.put("scoring_expression", {
                k: result[k] for k in ("mode", "generation", "record", "diagnostics", "selection", "selection_score",
                                       "grounding", "critic_findings", "rationale_text")})
            results.append(result)
            if symbolic.better(result, best):
                best = result
        rejected += round_rejected
        history.append(_generation_note(generation, results, round_rejected, best))
        ctx.emit("exchange.closed", payload={"step": STEP, "mode": mode, "generation": generation,
                                             "kept": len(results), "rejected": len(round_rejected),
                                             "best": None if best is None else best["canonical_text"]},
                 summary=f"{mode}: generation {generation} kept {len(results)}, rejected {len(round_rejected)}")
        if stopped.startswith("model_error"):
            break
        if len(history) >= 2 and history[-1]["expressions"] == history[-2]["expressions"]:
            stopped = "diminishing_information_gain"   # the same expressions twice: more calls buy nothing
            break
    return {"mode": mode, "target_rule_ref": target_rule_ref, "route": route, "generations": history,
            "rejected": rejected, "best": best, "stopped": stopped, "split": split.record(),
            "features_offered": dataset.refs, "features_refused": dataset.refused,
            "rows": {"fitting": len(train), "comparing": len(select)}}


# --- adoption --------------------------------------------------------------------------------------

def adoption_check(*, dataset: Dataset, split: symbolic.Split, expression: Any, rules_info: dict[str, dict[str, Any]],
                   weights: dict[str, float], cells_by_candidate: dict[str, list[dict[str, Any]]],
                   min_improvement: float) -> dict[str, Any]:
    """The one look at the holdout: does the expression order it better than the baseline does?

    Both scorers are compared on rank agreement with the holdout target, because a fitted
    expression and a weighted-percentile score live on different scales and only their order is
    comparable. The baseline is recomputed over the holdout members alone: a percentile score
    depends on the set it is computed in, so that is what it would actually produce here.
    """
    members = [ref for ref in split.members("holdout") if ref in dataset.target]
    cells = {ref: cells_by_candidate.get(ref, []) for ref in members}
    baseline = assessor.preference_scores(cells, rules_info, weights)
    expression_scores = assessor.expression_scores(cells, rules_info, expression)
    paired = [ref for ref in members if baseline.get(ref, (None, 0.0))[0] is not None
              and expression_scores.get(ref, (None, 0.0))[0] is not None]
    target = [dataset.target[ref] for ref in paired]
    baseline_tau = symbolic.kendall_tau([baseline[ref][0] for ref in paired], target)
    expression_tau = symbolic.kendall_tau([expression_scores[ref][0] for ref in paired], target)
    margin = None if baseline_tau is None or expression_tau is None else expression_tau - baseline_tau
    adopted = margin is not None and margin >= min_improvement
    return {"metric": symbolic.ADOPTION_METRIC, "holdout_n": len(members), "compared_n": len(paired),
            "baseline": baseline_tau, "expression": expression_tau, "margin": margin,
            "min_improvement": min_improvement, "adopted": adopted,
            "reason": ("adopted" if adopted else "holdout_too_small" if len(paired) < 2 else
                       "did_not_beat_the_baseline_on_the_holdout"),
            "baseline_scorer": "weighted_preference recomputed over the holdout members",
            "mean_coverage": (round(sum(expression_scores[ref][1] for ref in members) / len(members), 4)
                              if members else None)}


def rationale(expression: Any, values: dict[str, Any], *, candidate_ref: str) -> dict[str, Any]:
    """One candidate's score explained: terms by absolute contribution, with the claims behind each."""
    expr = symbolic.as_expression(expression)
    score, coverage = symbolic.evaluate(expr, values)
    items = sorted(symbolic.term_contributions(expr, values), key=lambda item: -abs(item["contribution"] or 0.0))
    total = sum(abs(item["contribution"]) for item in items if item["contribution"] is not None)
    return {
        "candidate_ref": candidate_ref, "score": score, "coverage": coverage, "intercept": expr.intercept,
        "terms": [{"term": item["term"], "features": item["features"], "feature_values": item["feature_values"],
                   "value": item["value"], "coefficient": item["coefficient"], "contribution": item["contribution"],
                   "share": (round(abs(item["contribution"]) / total, 4) if total else None),
                   "direction": item["direction"], "grounding": item["grounding"], "claim_refs": item["claim_refs"]}
                  for item in items if not item["missing"]],
        "terms_missing": [{"term": item["term"], "features": item["features"],
                           "missing_features": [name for name in item["features"]
                                                if not isinstance(values.get(name), (int, float))
                                                or isinstance(values.get(name), bool)]}
                          for item in items if item["missing"]],
    }


def rationales(expression: Any, dataset: Dataset) -> dict[str, dict[str, Any]]:
    return {ref: rationale(expression, dataset.rows.get(ref, {}), candidate_ref=ref)
            for ref in sorted(dataset.rows)[:MAX_RATIONALES]}


# --- the step ----------------------------------------------------------------------------------------

def enabled(settings: dict[str, Any] | None) -> bool:
    return bool(MODES_BY_SETTING.get((settings or {}).get("sr.mode", "off"), ()))


def _knobs(core: Core, run_id: str) -> dict[str, Any]:
    """Every number this step uses, from the registered constants of this run."""
    scope = (EVAL_STREAM, run_id)
    names = {"generations": "const_sr_generations", "max_terms": "const_sr_max_terms",
             "min_improvement": "const_sr_min_improvement", "min_training_rows": "const_sr_min_training_rows",
             "select_share": "const_sr_select_share", "holdout_share": "const_sr_holdout_share",
             "ridge": "const_sr_ridge", "complexity_penalty": "const_sr_complexity_penalty",
             "max_condition": "const_sr_max_condition"}
    out = {key: constants.value(core, const_id, scope) for key, const_id in names.items()}
    out["hinge_grid"] = [float(point) for point in constants.value(core, "const_sr_hinge_grid", scope)]
    names["hinge_grid"] = "const_sr_hinge_grid"
    for key in ("generations", "max_terms", "min_training_rows"):
        out[key] = int(out[key])
    for key in ("min_improvement", "select_share", "holdout_share", "ridge", "complexity_penalty", "max_condition"):
        out[key] = float(out[key])
    out["constants"] = names
    return out


def reference_outcomes(task_context: dict[str, Any], identities: dict[str, dict[str, Any]]) -> tuple[set[str], list[str]]:
    """(candidate ids to exclude from every split, labels the proposer may never see)."""
    seeds = [s for s in task_context.get("seed_candidates", []) if s.get("is_reference_outcome")]
    labels = [label for seed in seeds for label in [seed["candidate_ref"], *(seed.get("aliases") or [])] if label]
    excluded = set()
    for candidate_id, record in identities.items():
        if record.get("input_label") in {seed["candidate_ref"] for seed in seeds}:
            excluded.add(candidate_id)
            labels += [l for l in (record.get("preferred_label"), record.get("input_label")) if l]
    excluded |= {seed["candidate_ref"] for seed in seeds} & set(identities)
    return excluded, sorted({label for label in labels})


def fit_and_install(core: Core, roster: ModelRoster | None, *, run_id: str, task_id: str, task_context: dict[str, Any],
                    rule_set: dict[str, Any], rules: list[dict[str, Any]], cells_by_candidate: dict[str, list[dict]],
                    rules_info: dict[str, dict[str, Any]], weights: dict[str, float],
                    baseline_scores: dict[str, tuple[float | None, float]], identities: dict[str, dict[str, Any]],
                    settings: dict[str, Any], by: dict[str, Any], budget: Any = None,
                    ids: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fit, gate, compare on the holdout, and install the winner as the ordering method.

    Returns the record of the attempt whether or not it was adopted; `installed_rule_set_ref` is
    set only when an expression won on the holdout and the settings ask for it to do the ranking.
    """
    modes = MODES_BY_SETTING.get(settings.get("sr.mode", "off"), ())
    # `adopted` means an expression is now the ordering method. An attempt can win its holdout
    # comparison and still not be installed, when the settings leave the ranking to the baseline.
    record: dict[str, Any] = {"sr_version": SR_VERSION, "run_id": run_id, "task_id": task_id,
                              "mode_setting": settings.get("sr.mode", "off"),
                              "rank_method": settings.get("rank.method", "weighted_preference"),
                              "attempts": [], "adopted": False, "installed_rule_set_ref": None,
                              "ordering_method": None, "rationale_artifact_id": None}
    if not modes:
        return record
    recorded = record_of(core, run_id)
    if recorded is not None:
        return recorded   # a resumed run keeps the expression it already fitted, and registers nothing twice
    missing = [role for role in ("proposer", "critic") if role not in (roster.roles if roster else {})]
    if missing:
        record["not_attempted"] = f"no model bound to {missing}"
        core.journal.append(run_id, "run.annotated", actor=SCORING, ids=dict(ids or {}),
                            payload={"annotation": "step_skipped", "step": STEP, "reason": record["not_attempted"]},
                            summary=f"{STEP} skipped: {record['not_attempted']}")
        return record
    ids = dict(ids or {}, step_id=f"step_{run_id}_{STEP}")
    knobs = _knobs(core, run_id)
    excluded, reference_labels = reference_outcomes(task_context, identities)
    ctx = ScoringContext(core=core, roster=roster, run_id=run_id, task_id=task_id, by=by, knobs=knobs,
                         candidate_refs=tuple(sorted(cells_by_candidate)), reference_labels=tuple(reference_labels),
                         claim_streams=(run_id, task_id), budget=budget, ids=ids)
    seed = int(settings.get("run.seed", 0) or 0)
    core.journal.append(run_id, "step.started", actor=SCORING, ids=ids,
                        payload={"step": STEP, "modes": list(modes), "knobs": {k: v for k, v in knobs.items()
                                                                               if k != "constants"}},
                        question="can a fitted expression order the candidates better than the weighted percentile?")
    for mode in modes:
        targets = potency_target_rules(rules, task_context) if mode == "potency" else [None]
        if not targets:
            record["attempts"].append({"mode": mode, "stopped": "no_required_target_potency_rule", "best": None})
            continue
        for target_rule_ref in targets:
            dataset = build_dataset(mode=mode, rules=rules, cells_by_candidate=cells_by_candidate,
                                    task_context=task_context, target_rule_ref=target_rule_ref,
                                    baseline_scores=baseline_scores)
            split = symbolic.split_candidates(sorted(cells_by_candidate), seed=seed,
                                              select_share=knobs["select_share"], holdout_share=knobs["holdout_share"],
                                              exclude=excluded)
            refuse_leaking_features(dataset, split)
            attempt = _attempt(ctx, mode=mode, dataset=dataset, split=split, target_rule_ref=target_rule_ref)
            best = attempt.pop("best")
            if best is not None:
                attempt["selected"] = {k: best[k] for k in ("generation", "record", "diagnostics", "selection",
                                                            "selection_score", "grounding", "rationale_text",
                                                            "artifact_id")}
                attempt["adoption"] = adoption_check(
                    dataset=dataset, split=split, expression=best["expression"], rules_info=rules_info,
                    weights=weights, cells_by_candidate=cells_by_candidate, min_improvement=knobs["min_improvement"])
                attempt["_expression"], attempt["_dataset"] = best["expression"], dataset
            record["attempts"].append(attempt)
    winner = _winner(record["attempts"])
    if winner is not None and record["rank_method"] == "symbolic_expression":
        record.update(_install(ctx, task_context=task_context, rule_set=rule_set, attempt=winner))
    elif winner is not None:
        record["not_installed"] = "rank.method is weighted_preference: the expression is recorded, not used"
    for attempt in record["attempts"]:
        attempt.pop("_expression", None)
        attempt.pop("_dataset", None)
    decision = ("adopt_symbolic_expression" if record["adopted"] else
                "keep_the_weighted_preference_baseline")
    core.journal.append(run_id, "decision.recorded", actor=SCORING, ids=ids,
                        payload={"step": STEP, "decision": decision,
                                 "comparisons": [a.get("adoption") for a in record["attempts"] if a.get("adoption")],
                                 "installed_rule_set_ref": record["installed_rule_set_ref"]},
                        summary=f"{STEP}: {decision}")
    record["artifact_id"] = core.artifacts.put("symbolic_regression", record)
    core.journal.append(run_id, "step.completed", actor=SCORING, ids=ids, state_to="completed",
                        payload={"step": STEP, "adopted": record["adopted"],
                                 "artifact_id": record["artifact_id"],
                                 "rule_set_ref": record["installed_rule_set_ref"]},
                        artifact_links=[{"kind": "symbolic_regression", "id": record["artifact_id"]}],
                        summary=f"{STEP}: {'adopted' if record['adopted'] else 'baseline kept'}")
    return record


def _winner(attempts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The attempt eligible to rank: adopted on its holdout, then the largest margin, fewest terms, canonical text."""
    eligible = [a for a in attempts if (a.get("adoption") or {}).get("adopted")]
    if not eligible:
        return None
    return sorted(eligible, key=lambda a: (-a["adoption"]["margin"], len(a["selected"]["record"]["terms"]),
                                           a["selected"]["record"]["canonical_text"]))[0]


def _install(ctx: ScoringContext, *, task_context: dict[str, Any], rule_set: dict[str, Any],
             attempt: dict[str, Any]) -> dict[str, Any]:
    """Register the expression, make it the rule set's ordering method, and ask an expert to confirm it."""
    expression = attempt["_expression"]
    record = attempt["selected"]["record"]
    expression_ref = new_id("expr")
    artifact_id = ctx.put("scoring_expression", {
        "expression_ref": expression_ref, "mode": attempt["mode"], "target_rule_ref": attempt["target_rule_ref"],
        "expression": record, "diagnostics": attempt["selected"]["diagnostics"],
        "selection": attempt["selected"]["selection"], "adoption": attempt["adoption"], "split": attempt["split"],
        "grounding": attempt["selected"]["grounding"], "rationale_text": attempt["selected"]["rationale_text"],
        "features_refused": attempt["features_refused"], "sr_version": SR_VERSION})
    ordering_method = {
        "kind": "symbolic_expression", "expression_ref": expression_ref, "artifact_id": artifact_id,
        "expression_text": record["text"],
        "coefficients": [{"term": term["text"], "coefficient": coefficient, "direction": term["direction"],
                          "grounding": term["grounding"]}
                         for term, coefficient in zip(record["terms"], record["coefficients"])],
        "feature_refs": record["feature_refs"], "split": attempt["split"],
        "metrics": {"selection": attempt["selected"]["selection"], "adoption": attempt["adoption"]},
        "fitter_version": record["fitter_version"], "provenance": record["provenance"],
        "tie_break": "candidate_id", "mode": attempt["mode"], "expression": record,
    }
    # The deferral this run was confirmed with, held out again by the set this installs. Read
    # through `criteria.deferred_capabilities`, which prefers the set's own record of the policy to
    # the rows it produced: a route-level deferral is recorded on the rules that *entered*, so
    # rebuilding the policy from the rows alone can lose a capability and ask, in the set that now
    # decides the ranking, for reading this run deliberately did not buy.
    rule_set_ref = criteria.confirm_rule_set(
        ctx.core, ctx.task_id, by=ctx.by, ordering_method=ordering_method,
        coverage_floor=rule_set.get("coverage_floor", 1.0), allow_pending=bool(rule_set.get("pending")),
        defer_capabilities=criteria.deferred_capabilities(rule_set),
        defer_reason=criteria.deferral_reason(rule_set))
    review.request(ctx.core, ctx.task_id,
                   subject={"kind": "rule_set_version", "id": rule_set_ref, "ordering_method": "symbolic_expression"},
                   why_expert_required="a scoring expression fitted on this run's own results now decides the "
                                       "ranking; an expert confirms the ordering method before it is relied on",
                   requested_by=ctx.by,
                   inspection_bundle={"expression_ref": expression_ref, "artifact_id": artifact_id,
                                      "expression_text": record["text"], "adoption": attempt["adoption"],
                                      "provenance": record["provenance"]})
    rationale_artifact = ctx.put("scoring_rationale", {
        "expression_ref": expression_ref, "run_id": ctx.run_id, "mode": attempt["mode"],
        "rationales": rationales(expression, attempt["_dataset"])})
    return {"adopted": True, "installed_rule_set_ref": rule_set_ref, "ordering_method": ordering_method,
            "expression_ref": expression_ref, "expression_artifact_id": artifact_id,
            "rationale_artifact_id": rationale_artifact}


def rationale_of(core: Core, run_id: str, candidate_ref: str) -> dict[str, Any] | None:
    """One candidate's scoring rationale from the run's recorded symbolic-regression step, if there is one."""
    for event in reversed(core.journal.replay(run_id)):
        if event.event_type == "step.completed" and event.payload.get("step") == STEP:
            record = core.artifacts.payload(event.payload["artifact_id"])
            if not record.get("rationale_artifact_id"):
                return None
            payload = core.artifacts.payload(record["rationale_artifact_id"])
            return payload["rationales"].get(candidate_ref)
    return None


def record_of(core: Core, run_id: str) -> dict[str, Any] | None:
    """This run's recorded symbolic-regression step, adopted or not, with the artifact it was stored as."""
    for event in reversed(core.journal.replay(run_id)):
        if event.event_type == "step.completed" and event.payload.get("step") == STEP:
            return dict(core.artifacts.payload(event.payload["artifact_id"]),
                        artifact_id=event.payload["artifact_id"])
    return None
