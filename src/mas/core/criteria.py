"""Criterion Registry (C10): Attribute and Rule records, invariants, confirmed rule sets (design §4.10)."""

from __future__ import annotations

import json
from typing import Any

from . import bound_support, review, vocab
from .canonical import canonical_text, sha256_hex
from .ids import slug
from .runtime import Core

MEASUREMENT_KINDS = ("quantitative", "ordinal", "categorical", "qualitative_determination")
DIRECTIONS = ("higher_better", "lower_better", "within_range", "target_value", "non_directional", "undetermined")
RULE_KINDS = ("hard_exclusion", "preference", "exploratory_consideration")
# Where the authority for a decision-bearing number comes from. `model_decision_boundary` is the
# line the model that produced the value defines rather than a line anybody drew here: a binary
# classifier returns the probability of its positive class, so 0.5 separates its two classes by the
# definition of the task it was trained on. It is registered as a general basis because the claim it
# makes is general -- any model that classifies states a boundary, and a screen that compares a
# candidate against it is using the model's own line. It is NOT a licence to score unexamined:
# `bound_support.AUTHORITY_BASES` holds it, so the bound needs a decision before it may score, for
# the same reason an `expert_set` one does -- no claim in the ledger states the number, and whether
# this population should be screened at the model's line is a judgement, not an arithmetic.
CUTOFF_BASES = ("measured_distribution", "regulatory_or_standard_reference", "source_stated_value",
                "expert_set", "task_constraint", "model_decision_boundary", "none_evidence_insufficient")
COMPARATORS = (">=", "<=", ">", "<", "==", "in", "not_in")
ON_STATE_POLICIES = ("unknown_no_penalty", "unknown_blocks_recommendation", "route_to_human", "exclude")
AGGREGATIONS = ("max", "min", "median", "consensus", "any_true")
# The reductions that are defined over a pooled set of numbers from unlike kinds of source, which is
# what lets one attribute read a quantity from databases and from the literature at once
# (`check_attribute`). `consensus` is deliberately absent: it asks whether the sources agree, and
# what agreement between a curated record and a read passage means is a policy nobody has set.
POOLABLE_AGGREGATIONS = ("max", "min", "median")
# Bases a value may be determined on. `predicted` is never *pooled* with the others inside one
# aggregate: a predicted value averaged in with measurements is a surrogate inside a verdict
# (design §4.11). Without a declared precedence that means a predicted quantity needs its own
# attribute and its own rule; with one (`determination_basis_precedence` below) one attribute may
# hold both bases and use exactly one of them per candidate, which is a different thing from mixing.
#
# `curated` is an expert assertion a database carries with its references — ChEMBL's
# mechanism-of-action table states that a compound engages a target, which is documented
# rather than measured, and the tool declares that basis itself (`evidence.determination_basis`).
# It is registered here so that an attribute *may* ask for it; it is deliberately absent from
# `assessor.DEFAULT_DETERMINATION_BASES`, so an attribute that does not name it sees no curated
# claim at all rather than counting an assertion as a measurement.
# `asserted` is the same shape of thing one step further out: a statement a paper makes without
# reporting the measurement behind it ("the agent was well tolerated"). It is registered for the
# same reason as `curated` -- so an attribute may ask for it -- and kept out of the defaults for the
# same reason, so nothing counts an assertion as a measurement by omission. WHY it had to be added:
# `reading.extract_claims` has always offered it in its extraction enum and the reader uses it, but
# it was absent here, so `check_attribute` refused any attribute that named it and
# `assessor.usable_claims` set every such claim aside. Measured on the manuscript task: 60 of the
# 127 claims behind registered criteria carry `asserted`, and no attribute could legally accept one
# -- the reader was writing evidence into a basis the registry had no word for. That falls hardest
# on the 26 literature-bound criteria, whose evidence is largely stated rather than tabulated.
DETERMINATION_BASES = ("measured", "derived", "predicted", "simulated", "curated", "asserted")
# The kinds of source an attribute may accept values from: the registered `evidence_kind` domain and
# nothing else. Read from the vocabulary rather than restated here, so there is one registry of what
# the system's tools can stamp on a claim and this validator cannot drift from it (see that domain's
# note for why the registry is a closed list and not the live install's contracts).
EVIDENCE_KINDS = tuple(sorted(vocab.DOMAINS["evidence_kind"]))
# The basis the cell falls back to when the one above it has nothing to say about a candidate, as an
# ordered list, highest priority first: `determination_basis_precedence: ["measured", "predicted"]`
# reads "the measurement where there is one, the prediction only where there is none".
#
# WHY it exists. The invariant above is sound about aggregates and silent about gaps, and the
# screening need it made inexpressible is the ordinary one: 74 of the 3,177 compounds of the
# manuscript universe carry any curated potency at the five required receptors, so without
# gap-filling 98% of the universe is `unknown` on the task's central quantity, and every candidate
# the board could rank is a candidate somebody has already studied. The two ways out before this
# field were both defects. One attribute accepting both bases pooled a model's output into a median
# of measurements -- the surrogate §4.11 refuses. Two attributes, one per basis, scored one quantity
# twice for every candidate that has both a measurement and a prediction: the double counting
# `core/collapse.py` exists to undo (ten promoted rules for five quantities; 34 of 3,177 compounds
# cleared the ranking floor where 99 clear it once each receptor is one quantity).
#
# WHAT IT IS NOT. It is not a licence to mix: `assessor.usable_claims` keeps the claims of the
# highest-priority basis *actually present for that candidate* and sets every other claim aside
# (`lower_precedence_basis`), so no aggregate ever spans two bases -- which is the invariant, stated
# per candidate instead of per attribute. The cell then reports the basis it actually used, so a
# gap-filled cell reads `predicted` and a measured one `measured`, and the two are told apart on
# every surface that reports provenance.
#
# WHY `predicted` may not come first: a precedence whose top entry is the model's output would use
# the prediction wherever one exists -- which is everywhere a structure exists -- and the measurement
# nowhere, so the attribute would be a predicted quantity wearing a measured one's name. The field is
# for filling gaps under a measurement, never for preferring a prediction to one. Deliberately *not*
# "predicted must be last": a prediction from a model with a declared holdout metric is not obviously
# weaker evidence than a paper's bare assertion (`asserted`), and ordering those two is the
# proposer's call, not this registry's.
PRECEDENCE_FIELD = "determination_basis_precedence"


def basis_precedence(attribute: dict[str, Any]) -> list[str] | None:
    """The declared basis precedence of an attribute, or None when it declares none.

    Reading only: the declaration is validated by `check_basis_precedence`, which `check_attribute`
    runs, so a record in the store has already been checked and a malformed one reads as absent
    here rather than crashing the assessor that is scoring a cell with it.
    """
    declared = attribute.get(PRECEDENCE_FIELD)
    if not isinstance(declared, list) or not declared:
        return None
    bases = attribute.get("acceptable_determination_bases")
    if not isinstance(bases, list) or sorted(declared) != sorted(set(bases)) or len(set(declared)) != len(declared):
        return None
    return list(declared)


def check_basis_precedence(attr: dict[str, Any]) -> list[str] | None:
    """Validate a declared `determination_basis_precedence` and return it, or None when absent.

    Four requirements, each of them the reason a weaker one would not do:
      * every entry is a registered basis -- it is the same closed list an attribute may accept;
      * `acceptable_determination_bases` is declared explicitly, because "every accepted basis"
        cannot be ordered while the accepted set is the assessor's implicit default;
      * the two lists hold the same bases, each exactly once: a basis accepted and left out of the
        precedence would have no rank, so `usable_claims` could not say whether it outranks anything,
        and a basis ranked but not accepted ranks claims that are set aside before they get here;
      * `predicted` is not first (see `PRECEDENCE_FIELD`).
    """
    declared = attr.get(PRECEDENCE_FIELD)
    if declared is None:
        return None
    if not isinstance(declared, list) or not declared:
        raise InvariantViolation("schema", f"{PRECEDENCE_FIELD} is a non-empty list of determination bases "
                                          f"when given, highest priority first")
    for basis in declared:
        _choice(PRECEDENCE_FIELD, basis, DETERMINATION_BASES)
    if len(set(declared)) != len(declared):
        raise InvariantViolation("schema", f"{PRECEDENCE_FIELD} on {attr.get('name')!r} ranks a basis twice: "
                                          f"{declared}")
    bases = attr.get("acceptable_determination_bases")
    if not isinstance(bases, list) or not bases:
        raise InvariantViolation("schema", f"{PRECEDENCE_FIELD} on {attr.get('name')!r} needs an explicit "
                                          f"acceptable_determination_bases to order")
    if sorted(set(bases)) != sorted(declared):
        raise InvariantViolation("schema", f"{PRECEDENCE_FIELD} on {attr.get('name')!r} is {declared} and the "
                                          f"attribute accepts {sorted(set(bases))}; the precedence lists every "
                                          f"accepted basis exactly once, so that every claim it keeps has a rank")
    if declared[0] == "predicted":
        raise InvariantViolation("schema", f"{PRECEDENCE_FIELD} on {attr.get('name')!r} puts predicted first, so "
                                          f"the prediction would be used wherever one exists and the measurement "
                                          f"nowhere; a precedence fills gaps under a measurement")
    return list(declared)
# Deterministic transformations an attribute may declare between the value its bound source returns
# and the quantity the attribute is about, with the parameters each one needs.
#
# WHY this exists: a proposer can define a one-sided or banded quantity correctly in prose -- "the
# excess above 500 g/mol, zero for a molecule at or below it" -- while the bound source returns the
# raw descriptor, and nothing applied the difference. The cell then carried the raw value under the
# derived quantity's name and direction, so every molecule inside the band was ranked by how small
# it was rather than tied at zero. Declaring the transformation makes it checkable and applied; the
# bounds carry a `basis` for the same reason a cutoff does, because an unsourced bound inside a
# transformation is the arbitrary cutoff the registry refuses elsewhere.
VALUE_TRANSFORMS = {"excess_above": ("bound",), "shortfall_below": ("bound",),
                    "distance_outside_band": ("low", "high")}


def check_value_transform(transform: dict[str, Any] | None, attr_name: str = "") -> None:
    if transform is None:
        return
    kind = transform.get("kind")
    if kind not in VALUE_TRANSFORMS:
        raise InvariantViolation("schema", f"value_transform kind must be one of "
                                          f"{tuple(VALUE_TRANSFORMS)}, got {kind!r}")
    for parameter in VALUE_TRANSFORMS[kind]:
        value = transform.get(parameter)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise InvariantViolation("schema", f"value_transform {kind} needs a numeric {parameter}")
    if kind == "distance_outside_band" and transform["low"] >= transform["high"]:
        raise InvariantViolation("schema", f"value_transform band low {transform['low']} is not below "
                                          f"high {transform['high']}")
    basis = transform.get("basis")
    _choice("value_transform basis", basis, tuple(b for b in CUTOFF_BASES if b != "none_evidence_insufficient"))
    if basis == "source_stated_value" and not transform.get("source_refs"):
        raise InvariantViolation("arbitrary_cutoff", f"value_transform on {attr_name!r} claims a source-stated "
                                                    f"bound without naming the claims that state it")


def apply_value_transform(value: float, transform: dict[str, Any] | None) -> float:
    """The declared quantity, from the value the source returned. Pure, total on floats."""
    if transform is None:
        return value
    kind = transform["kind"]
    if kind == "excess_above":
        return max(0.0, value - float(transform["bound"]))
    if kind == "shortfall_below":
        return max(0.0, float(transform["bound"]) - value)
    return max(0.0, float(transform["low"]) - value) + max(0.0, value - float(transform["high"]))


class InvariantViolation(ValueError):
    """A typed registry finding (design §4.10); never silently corrected."""

    def __init__(self, finding_class: str, message: str):
        super().__init__(f"{finding_class}: {message}")
        self.finding_class = finding_class


def _choice(name: str, value: Any, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        raise InvariantViolation("schema", f"{name} must be one of {allowed}, got {value!r}")


# Parameters that say how hard to look for a quantity rather than which quantity is meant. A target
# id names the measurement; a query template, its relevance terms and a result limit are retrieval
# knobs, and two attributes whose templates differ can still be about one quantity.
RETRIEVAL_PARAMETERS = ("query_template", "relevance_terms", "search_limit")


def evidence_routes(attribute: dict[str, Any]) -> list[dict[str, Any]]:
    """Every evidence route an attribute declares, whether it declared one (`evidence_request`)
    or several (`evidence_requests`).

    WHY an attribute may declare several: measured on the manuscript registry, 14 October 2026, the
    ten promoted rules covered five quantities. For each required receptor two attributes carried the
    same measurement -- same unit, direction, aggregation, acceptable sources and `target_chembl_id`,
    differing only in the `question_kind` that names which database answers. Each receptor was
    therefore scored twice and the coverage denominator counted five quantities that do not exist:
    34 of 3,177 compounds cleared the 0.5 ranking coverage floor where 96 clear it once the five are
    one quantity each. One quantity read from two databases is one attribute with two routes.
    """
    declared = attribute.get("evidence_requests")
    if declared:
        return list(declared)
    request = attribute.get("evidence_request")
    return [request] if request else []


def _as_route(request: Any) -> dict[str, Any]:
    """One route, for reading. Anything that is not a route record reads as an empty one, so that a
    model reply holding a malformed route is refused by `check_attribute` rather than crashing the
    stage that is reading it (a provider's bad reply is a finding, never a crash)."""
    return request if isinstance(request, dict) else {}


def route_key(request: dict[str, Any]) -> str:
    """Canonical identity of one route: the question asked and the parameters it is asked with.

    `identifier_scheme` is left out on purpose: it follows from the capability and question kind
    (that is how a catalog entry is bound), so two routes differing only in it ask one source one
    question and are the same route.
    """
    route = _as_route(request)
    return canonical_text({k: route.get(k) for k in ("capability", "question_kind", "parameters")})


def subject_parameters(request: dict[str, Any]) -> dict[str, Any]:
    """The parameters identifying what a route is about, without the retrieval knobs."""
    return {k: v for k, v in (_as_route(request).get("parameters") or {}).items() if k not in RETRIEVAL_PARAMETERS}


def is_literature_bound(attribute: dict[str, Any]) -> bool:
    """True when any route reads literature: that route needs the search-and-read path, so the
    attribute takes it. One route is enough because the path is a property of the cell, not of a
    route -- an attribute may now carry a literature route *beside* database routes
    (`check_attribute`), and such a cell is gathered on both paths (`evidence.gather`)."""
    return any(_as_route(route).get("capability") == "literature_retrieval" for route in evidence_routes(attribute))


def literature_route(attribute: dict[str, Any]) -> dict[str, Any] | None:
    """The attribute's one literature route, or None when it has none.

    The reading path builds one query per attribute and `check_attribute` admits at most one such
    route, so "the" is exact. Read by name rather than positionally: on an attribute that also
    declares database routes, `evidence_routes(...)[0]` is a database route with no query template,
    which produced a bare-name query and searched for the compound rather than for the quantity.
    """
    return next((route for route in evidence_routes(attribute)
                 if _as_route(route).get("capability") == "literature_retrieval"), None)


def is_task_mandated(attribute: dict[str, Any]) -> bool:
    """True for an attribute an adapter template built out of one field of the task context.

    The two halves together, because neither alone says it: `proposed_by.role` says a template
    wrote it rather than a proposer, and `derived_from.field` names the task-context field it was
    built from. That link is what `adjudication.restated_constraint` rests its one approving route
    on -- "a link an adapter template wrote when it built the criterion *from* the constraint, which
    no proposer can forge" -- so the same pair identifies the criteria the task itself mandates
    wherever that population is needed (`criteria_export._origin`'s `task_mandated_template`,
    `assessor.calibration_guard`'s reference set).
    """
    return ((attribute.get("proposed_by") or {}).get("role") == "adapter_template"
            and bool((attribute.get("derived_from") or {}).get("field")))


def is_required_scope(attribute: dict[str, Any], context: dict[str, Any]) -> bool:
    required = {str(e["identifier"]) for e in context.get("scope_entities", []) if e.get("role") == "required"}
    subjects = {str(value) for route in evidence_routes(attribute) for value in subject_parameters(route).values()}
    return is_task_mandated(attribute) and bool(required & subjects)


def required_scope_rule_refs(context: dict[str, Any], rules: list[dict[str, Any]]) -> list[str]:
    refs, bound = [], set()
    required = {str(e["identifier"]) for e in context.get("scope_entities", []) if e.get("role") == "required"}
    for item in rules:
        attr = item["attribute"]
        if is_required_scope(attr, context):
            refs.append(item["entry"]["rule_ref"])
            bound.update(str(value) for route in evidence_routes(attr) for value in subject_parameters(route).values())
    return sorted(set(refs) | {f"unbound_required_scope:{identifier}" for identifier in required - bound})


def quantity_identity(attribute: dict[str, Any]) -> str:
    """Explicit shared property/conditions, unit and mathematics; provenance is not another quantity.

    Without an explicit ID, retain the route identity. Callers must not group different assay
    conditions or methods posing different scientific questions under one ID. Separate estimates
    remain separate evidence records; this identity only supports direct-first score selection.
    """
    if not attribute.get("quantity_id"):
        return evidence_key(attribute)
    transform = attribute.get("value_transform")
    if transform and transform.get("kind") in VALUE_TRANSFORMS:
        transform = {key: transform.get(key) for key in ("kind", *VALUE_TRANSFORMS[transform["kind"]])}
    return sha256_hex({"quantity": attribute["quantity_id"], "unit": attribute.get("unit"), "transform": transform})


def check_attribute(attr: dict[str, Any]) -> None:
    for field in ("name", "definition", "measurement_kind", "direction", "acceptable_value_sources"):
        if not attr.get(field):
            raise InvariantViolation("schema", f"attribute needs {field}")
    _choice("measurement_kind", attr["measurement_kind"], MEASUREMENT_KINDS)
    _choice("direction", attr["direction"], DIRECTIONS)
    # Every accepted source kind is one some tool of this system can actually stamp on a claim
    # (`vocab.DOMAINS["evidence_kind"]`). WHY it is checked and not merely required to be present:
    # an attribute naming a kind nothing produces has every claim it reads set aside
    # (`assessor.usable_claims`, `evidence_kind_not_accepted`) and its cell reads `unknown_missing`,
    # so the mistake looks exactly like absent evidence -- it survived in the registry for as long
    # as it did because nothing distinguished the two. The refusal is deliberately NOT measured
    # against the tools registered in this install: an install without the ADMET predictor produces
    # no `model_prediction`, and an attribute asking for one is unanswerable *here* rather than
    # wrong, which is a run-time gap (`evidence.producible_evidence_kinds`) and not a schema defect.
    sources = attr["acceptable_value_sources"]
    if not isinstance(sources, list):
        raise InvariantViolation("schema", "acceptable_value_sources is a non-empty list of evidence kinds")
    for kind in sources:
        if kind not in EVIDENCE_KINDS:
            raise InvariantViolation("schema", f"acceptable_value_sources on {attr.get('name')!r} names "
                                               f"{kind!r}, which no tool of this system produces; the kinds a "
                                               f"claim can carry are {EVIDENCE_KINDS}, and an attribute accepting "
                                               f"anything else has every claim it reads set aside and its cell "
                                               f"reads as absent evidence")
    _choice("aggregation", attr.get("aggregation", "consensus"), AGGREGATIONS)
    if "aggregation_scope" in attr:
        if attr["aggregation_scope"] != "pooled_observations":
            raise InvariantViolation("schema", "aggregation_scope supports only 'pooled_observations': "
                                     "the declared aggregation over raw observations, without per-target grouping")
        if attr.get("aggregation") not in POOLABLE_AGGREGATIONS:
            raise InvariantViolation("schema", "pooled_observations requires an explicit min, max or median aggregation")
    if attr.get("aggregation") == "any_true":
        semantics = attr.get("existence_semantics") or {}
        if attr.get("measurement_kind") != "categorical" or attr.get("unit") is not None or \
                semantics.get("kind") != "documented_existence_v1" or not semantics.get("property") or not semantics.get("value"):
            raise InvariantViolation("schema", "any_true requires a categorical unitless documented-existence attribute with an explicit property/value")
    check_value_transform(attr.get("value_transform"), attr.get("name", ""))
    if attr.get("value_transform") and attr["measurement_kind"] != "quantitative":
        raise InvariantViolation("schema", f"value_transform on {attr['name']!r} needs a quantitative attribute")
    if attr["measurement_kind"] == "quantitative" and not attr.get("unit"):
        raise InvariantViolation("units", f"quantitative attribute {attr['name']!r} has no unit")
    bases = attr.get("acceptable_determination_bases")
    if bases is not None:
        if not isinstance(bases, list) or not bases:
            raise InvariantViolation("schema", "acceptable_determination_bases is a non-empty list when given")
        for basis in bases:
            _choice("acceptable_determination_bases", basis, DETERMINATION_BASES)
    precedence = check_basis_precedence(attr)
    if bases is not None and "predicted" in bases and len(bases) > 1 and precedence is None:
        # A predicted value pooled with measurements is a surrogate inside a verdict (design §4.11):
        # without a declared precedence a predicted quantity is its own attribute, with its own rule.
        # With one, exactly one basis is used per candidate and nothing is pooled.
        raise InvariantViolation("schema", f"attribute {attr['name']!r} accepts predicted values alongside "
                                          f"{sorted(set(bases) - {'predicted'})}; give predicted values their own "
                                          f"attribute, or declare {PRECEDENCE_FIELD} (e.g. "
                                          f"{['measured', 'predicted']}) so that one basis is used per candidate "
                                          f"and the two are never pooled")
    routes = evidence_routes(attr)
    if not routes:
        raise InvariantViolation("schema", "attribute needs evidence_request")
    if attr.get("evidence_requests") and attr.get("evidence_request") and \
            route_key(attr["evidence_request"]) not in {route_key(r) for r in routes}:
        raise InvariantViolation("schema", f"attribute {attr['name']!r} declares evidence_requests and a separate "
                                          f"evidence_request that is not among them; nothing would ever ask it")
    seen: set[str] = set()
    for request in routes:
        if not isinstance(request, dict) or not request.get("capability") or not request.get("question_kind"):
            raise InvariantViolation("schema", "evidence_request needs capability and question_kind")
        if route_key(request) in seen:
            raise InvariantViolation("schema", f"attribute {attr['name']!r} declares the same evidence route twice; "
                                              f"the second asks nothing new and its values would be aggregated twice")
        seen.add(route_key(request))
    literature = [r for r in routes if r["capability"] == "literature_retrieval"]
    if literature and len(literature) != len(routes) and \
            (attr["measurement_kind"] != "quantitative" or not attr.get("unit")
             or attr.get("aggregation") not in POOLABLE_AGGREGATIONS):
        # WHY mixing is permitted at all now, and only here. The two kinds take different code paths
        # -- a broker call per route against a record source; a search, a read and checked extraction
        # for literature -- which `evidence.gather` now runs both of for one cell, taking the union
        # exactly as it already did for two databases. What was genuinely missing was a policy for
        # pooling a passage with a record, and for one shape of quantity that policy is now set: a
        # quantitative attribute with a declared unit reduced by a numeric aggregation is one number
        # on one scale, every contributing claim is checked against that unit (`assessor.usable_claims`,
        # which converts where an exact documented conversion exists and sets the claim aside
        # otherwise), and `median` over the pooled set is the same reduction the attribute already
        # declared for its two curations. The need is measured: 74 of the 3,177 candidates of the
        # manuscript universe carry any curated potency at the five required receptors, and a
        # published selectivity table is where the rest of that quantity is reported.
        #
        # Everything else is still refused, because nothing about it is defined. `consensus` asks
        # whether sources agree, and agreement between a curated record and a read passage is a
        # question nobody has answered; a categorical or unitless attribute has no scale to check a
        # passage against, so the oral-route gate and its literature companion stay two criteria
        # (`adapters/drug/registration.objective_templates`).
        raise InvariantViolation("schema", f"attribute {attr['name']!r} mixes a literature route with "
                                          f"{sorted({r['capability'] for r in routes if r['capability'] != 'literature_retrieval'})} "
                                          f"and is {attr['measurement_kind']} / unit {attr.get('unit')!r} / aggregation "
                                          f"{attr.get('aggregation', 'consensus')!r}; a literature route may be pooled with "
                                          f"database routes only on a quantitative attribute with a unit reduced by one of "
                                          f"{POOLABLE_AGGREGATIONS}, where every claim is checked against one scale -- "
                                          f"otherwise give the literature quantity its own attribute")
    if len(literature) > 1:
        # One query per attribute is what the reading path builds (`evidence.literature_query`), so a
        # second template would never be used -- and an instruction the pipeline then undoes is worse
        # than no instruction (ADR-48).
        raise InvariantViolation("schema", f"attribute {attr['name']!r} declares {len(literature)} literature "
                                          f"routes; the reading path builds one query per attribute")


def check_rule(rule: dict[str, Any], attr: dict[str, Any]) -> None:
    if attr.get("aggregation") == "any_true":
        cutoff = rule.get("cutoff") or {}
        if rule.get("predicate_form") != "categorical_membership" or cutoff.get("comparator") != "==" \
                or cutoff.get("value") is not True or cutoff.get("unit") is not None \
                or any(rule.get(key) == "exclude" for key in ("on_missing", "on_conflict", "on_inapplicable")):
            raise InvariantViolation("schema", "documented-existence rules test Boolean true; absence/conflict cannot be turned into exclusion")
    _choice("rule_kind", rule.get("rule_kind"), RULE_KINDS)
    _choice("cutoff_basis", rule.get("cutoff_basis"), CUTOFF_BASES)
    for policy in ("on_missing", "on_inapplicable", "on_conflict"):
        _choice(policy, rule.get(policy, "unknown_blocks_recommendation"), ON_STATE_POLICIES)
        if rule.get(policy) == "exclude" and rule["rule_kind"] != "hard_exclusion":
            raise InvariantViolation("schema", f"{policy}: exclude is only for hard exclusions")
    cutoff = rule.get("cutoff")
    if rule.get("predicate_form", "threshold") not in ("threshold", "ordering", "range_membership", "categorical_membership",
                                                       "qualitative_judgment", "recorded_observation"):
        raise InvariantViolation("schema", f"unknown predicate_form {rule.get('predicate_form')!r}")
    if rule.get("predicate_form") == "ordering" and rule["rule_kind"] != "preference":
        raise InvariantViolation("schema", "an ordering rule ranks candidates, so it must be a preference")
    if rule.get("predicate_form") == "recorded_observation" and (
            rule["rule_kind"] != "exploratory_consideration" or cutoff is not None
            or rule["cutoff_basis"] != "none_evidence_insufficient"):
        raise InvariantViolation("schema", "recorded_observation records availability without comparison or ranking; "
                                 "it requires exploratory_consideration, null cutoff and none_evidence_insufficient")
    if rule["cutoff_basis"] == "none_evidence_insufficient":
        if cutoff:
            raise InvariantViolation("arbitrary_cutoff", "none_evidence_insufficient with a cutoff value")
        return
    if not cutoff:
        raise InvariantViolation("schema", "rule needs a cutoff or cutoff_basis none_evidence_insufficient")
    _choice("comparator", cutoff.get("comparator"), COMPARATORS)
    if rule.get("predicate_form") == "categorical_membership" or attr["measurement_kind"] == "categorical":
        if cutoff["comparator"] not in ("in", "not_in", "=="):
            raise InvariantViolation("schema", "a categorical rule uses in, not_in, or ==")
        values = cutoff.get("value") if isinstance(cutoff.get("value"), list) else [cutoff.get("value")]
        if not values or not all(isinstance(v, (str, bool)) for v in values):
            raise InvariantViolation("schema", "a categorical cutoff lists categories (strings or booleans)")
        return
    if cutoff["comparator"] in ("in", "not_in"):
        raise InvariantViolation("schema", "in and not_in are for categorical rules")
    if not isinstance(cutoff.get("value"), (int, float)) or isinstance(cutoff.get("value"), bool):
        raise InvariantViolation("schema", "cutoff value must be a number")
    if attr["measurement_kind"] == "quantitative" and cutoff.get("unit") != attr.get("unit"):
        raise InvariantViolation("units", f"cutoff unit {cutoff.get('unit')!r} differs from attribute unit {attr.get('unit')!r}")


def preference_execution_problems(attribute: dict[str, Any], rule: dict[str, Any]) -> list[str]:
    """Mechanical scoring readiness, independent of scientific approval. Pure; hard rules unchanged."""
    if rule.get("rule_kind") != "preference":
        return []
    # Several databases for one target still measure one subject. The current
    # catalog identifies distinct target subjects by target_chembl_id, not route
    # count; retrieval queries and descriptor properties are not extra targets.
    targets = sorted({subject_parameters(route)["target_chembl_id"] for route in evidence_routes(attribute)
                      if isinstance(subject_parameters(route).get("target_chembl_id"), str)
                      and subject_parameters(route)["target_chembl_id"]})
    if attribute.get("measurement_kind") in ("quantitative", "ordinal") and len(targets) > 1:
        if (attribute.get("aggregation_scope") != "pooled_observations"
                or attribute.get("aggregation") not in POOLABLE_AGGREGATIONS):
            return [f"numeric preference combines {len(targets)} distinct target subjects ({', '.join(targets)}); "
                    f"the assessor only applies {attribute.get('aggregation', 'consensus')!r} to pooled raw "
                    "observations and does not compute per-target summaries, min/max of per-target summaries, "
                    "spread, ratios or member completeness. A grouped reduction has no executable contract; "
                    "only an explicitly intended raw pool may declare aggregation_scope='pooled_observations' "
                    "with min, max or median. Keep the independent target criteria or defer this composite."]
    predicate = rule.get("predicate_form", "threshold")
    cutoff = rule.get("cutoff")
    transform = attribute.get("value_transform") or {}
    if (attribute.get("measurement_kind") in ("quantitative", "ordinal") and not transform
            and attribute.get("direction") in ("within_range", "target_value") and isinstance(cutoff, dict)):
        # A source interpretation supplies provenance, not an executable second bound.
        # Exact point equality and an explicitly declared finite set keep their literal
        # semantics; a one-sided scalar test never becomes a band or nearest-target score.
        value = cutoff.get("value")
        exact_target = (attribute.get("direction") == "target_value" and predicate != "ordering"
                        and cutoff.get("comparator") == "==" and isinstance(value, (int, float))
                        and not isinstance(value, bool))
        explicit_set = (predicate == "categorical_membership" and cutoff.get("comparator") in ("in", "not_in")
                        and isinstance(value, list))
        if not exact_target and not explicit_set:
            return [f"numeric preference declares {attribute.get('direction')!r} on raw values, but its "
                    "comparison does not implement an interval or distance to a target. Declare an executable "
                    "value_transform with supported bounds and a distance-space comparison/order, or declare "
                    "an explicitly one-sided monotonic criterion. bound_support cannot supply omitted bounds "
                    "or an undeclared target-distance calculation"]
    if transform.get("kind") == "distance_outside_band" and isinstance(cutoff, dict):
        value, comparator = cutoff.get("value"), cutoff.get("comparator")
        numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        raw_endpoint = numeric and value != 0 and value in (transform.get("low"), transform.get("high"))
        if raw_endpoint and attribute.get("direction") == "within_range":
            return ["distance_outside_band scores a nonnegative distance, not the raw measurement; "
                    f"cutoff {comparator} {value} reuses a raw band endpoint with within_range semantics. "
                    "Declare the preference on the distance scale (for example lower_better ordering), "
                    "rather than applying a raw band boundary after the transform"]
        if numeric and value > 0 and attribute.get("direction") == "lower_better" and comparator in (">", ">="):
            return ["distance_outside_band with lower_better cannot reward distances above a positive cutoff; "
                    "the comparison points away from the preferred band. Use an explicitly supported "
                    "distance-space comparison or ordering without inventing a cutoff"]
    if cutoff is None:
        if predicate != "ordering":
            return [f"preference has no executable predicate: {predicate!r} needs a declared comparison "
                    "cutoff; no cutoff or pass value is inferred"]
        if attribute.get("direction") not in ("higher_better", "lower_better"):
            return ["preference ordering requires higher_better or lower_better; "
                    f"{attribute.get('direction')!r} defines no executable order"]
        # Preserve the assessor's existing numeric categorical/ordinal encodings. Their type
        # label or lack of a physical unit alone does not make an explicit order unexecutable.
        return []
    if not isinstance(cutoff, dict) or not cutoff:
        return ["preference has no executable comparison: cutoff must be a non-empty comparison record"]
    try:
        check_rule(rule, attribute)
    except InvariantViolation as error:
        return [f"preference comparison is not executable: {error}"]
    return []


def preference_execution_findings(core: Core, task_id: str, *,
                                 rule_set: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Read-only findings for active proposals, or the exact entries of a selected frozen set."""
    entries = (rule_set["entries"] if rule_set is not None else
               [{"rule_ref": f"{rule['rule_id']}@v{rule['version']}", "attribute_ref": rule["attribute_ref"]}
                for rule in registered_rule_records(core, task_id)])
    findings = []
    for entry in entries:
        rule = load(core, entry["rule_ref"], task_id)
        attribute = load(core, entry["attribute_ref"], task_id)
        problems = preference_execution_problems(attribute, rule)
        if problems:
            findings.append({"rule_ref": entry["rule_ref"], "attribute_ref": entry["attribute_ref"],
                             "scope": "rule", "reason_kind": "non_executable_preference",
                             "reason": "; ".join(problems), "problems": problems})
    return findings


def unresolved_review_findings(core: Core, task_id: str, *,
                               rule_set: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Read-only queue/receipt reasons. An unresolved attempt is work done, never approval."""
    entries = rule_set["entries"] if rule_set is not None else registry_inventory(core, task_id)["active"]
    selected = {entry["rule_ref"]: entry for entry in entries}
    pending = {item["item_id"]: item for item in review.items(core, [task_id]).values()
               if item["subject"].get("kind") == "rule_version" and item["state"] in ("open", "in_review")
               and item["subject"].get("id") in selected}
    by_item: dict[str, list[dict[str, Any]]] = {key: [] for key in pending}
    if pending:
        for (body,) in core.store.db.execute(
                "SELECT body FROM events WHERE stream_id=? AND event_type='decision.recorded' "
                "AND json_extract(body,'$.payload.record_kind')='review_attempt' ORDER BY seq", (task_id,)):
            payload = json.loads(body)["payload"]
            item = pending.get(payload.get("item_id"))
            if item is None:
                continue
            receipt = core.artifacts.payload(payload["artifact_id"])
            entry = selected[item["subject"]["id"]]
            if receipt.get("rule_ref") != entry["rule_ref"] or receipt.get("attribute_ref") != entry["attribute_ref"]:
                continue
            by_item[item["item_id"]].append({"attempt_ref": payload["artifact_id"],
                **{key: receipt.get(key) for key in ("outcome", "reason_text", "reason_origin", "source_kind",
                    "model_verdict", "model_reasoning", "source_agent_records", "recorded_at")}})
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in pending.values():
        grouped.setdefault(item["subject"]["id"], []).append({"item_ref": item["item_id"], "state": item["state"],
            "subject": item["subject"], "queue_reason": item.get("why_expert_required"),
            "attempts": by_item[item["item_id"]]})
    findings = []
    for ref, rows in grouped.items():
        reasons = [f"{row['item_ref']}: " + ((row["attempts"][-1].get("reason_text") if row["attempts"] else None)
                   or row.get("queue_reason") or "review remains unresolved") for row in rows]
        findings.append({"rule_ref": ref, "attribute_ref": selected[ref]["attribute_ref"], "scope": "rule",
            "reason_kind": "unresolved_review", "reason": "withheld from scoring while review is unresolved: "
                           + "; ".join(reasons), "review_item_refs": [row["item_ref"] for row in rows], "reviews": rows})
    return findings


def _versions(core: Core, task_id: str, kind: str, base_id: str, *,
              version: int | None = None) -> list[dict[str, Any]]:
    query = ("SELECT json_extract(body,'$.payload') FROM events WHERE stream_id=? AND seq>=1 "
             "AND event_type='criterion.version_proposed' AND json_extract(body,'$.payload.kind')=? "
             "AND json_extract(body,'$.payload.id')=?")
    parameters: list[Any] = [task_id, kind, base_id]
    if version is not None:
        query += " AND json_extract(body,'$.payload.version')=?"
        parameters.append(version)
    return [json.loads(row[0]) for row in core.store.db.execute(query + " ORDER BY seq", parameters)]


def propose(core: Core, task_id: str, attribute: dict[str, Any], rule: dict[str, Any], *,
            by: dict[str, Any], derivation_configuration: str = "reference_disclosed",
            dispute: dict[str, Any] | None = None,
            support: dict[str, Any] | None = None) -> tuple[str, str]:
    """Propose one attribute version and one rule version, and raise their confirmation item.

    Proposals enter as `proposed`; templates and people never pre-approve them.
    Returns (attribute_ref@v, rule_ref@v).
    """
    vocab.require("derivation_configuration", derivation_configuration)
    check_attribute(attribute)
    check_rule(rule, attribute)
    attr_id = attribute.get("attribute_id") or f"attr_{slug(attribute['name'])}"
    rule_id = rule.get("rule_id") or f"rule_{slug(attribute['name'])}"
    attr_version = len(_versions(core, task_id, "attribute", attr_id)) + 1
    rule_version = len(_versions(core, task_id, "rule", rule_id)) + 1
    attr_ref, rule_ref = f"{attr_id}@v{attr_version}", f"{rule_id}@v{rule_version}"
    attr_record = dict(attribute, attribute_id=attr_id, version=attr_version, status="proposed",
                       derivation_configuration=derivation_configuration, proposed_by=by)
    attr_record.setdefault("aggregation", "consensus")
    rule_record = dict(rule, rule_id=rule_id, version=rule_version, attribute_ref=attr_ref, status="proposed",
                       proposed_by=by)
    for policy in ("on_missing", "on_inapplicable", "on_conflict"):
        rule_record.setdefault(policy, "unknown_blocks_recommendation")
    rule_record.setdefault("predicate_form", "threshold")
    rule_record.setdefault("applies_to_result_kind", "all_pass_set")
    for kind, base_id, version, record in (("attribute", attr_id, attr_version, attr_record),
                                           ("rule", rule_id, rule_version, rule_record)):
        artifact_id = core.artifacts.put(kind, record)
        core.journal.append(task_id, "criterion.version_proposed", actor=by, ids={"task_id": task_id},
                            payload={"kind": kind, "id": base_id, "version": version, "artifact_id": artifact_id},
                            artifact_links=[{"kind": kind, "id": artifact_id, "version": version}],
                            summary=f"proposed {base_id}@v{version}")
    if dispute is not None:
        review.request(core, task_id, subject={"kind": "rule_version", "id": rule_ref, "version": rule_version,
                                               "attribute_ref": attr_ref},
                       why_expert_required="proposer and critic still disagree after one revision",
                       requested_by=by, inspection_bundle=dispute)
    else:
        # `support` is the bound-support report for this very attribute and rule when the caller has
        # the claims to compute it (`core/bound_support.py`); without it the authority table still
        # reads the rule, the attribute and the bounds inside the transform, which is what F3 was about.
        owed = authority_requirements(rule_record, attr_record, support=support)
        if owed:
            review.request(core, task_id, subject={"kind": "rule_version", "id": rule_ref, "version": rule_version,
                                                   "attribute_ref": attr_ref},
                           why_expert_required="; ".join(r["detail"] for r in owed), requested_by=by)
    return attr_ref, rule_ref


def record_version(core: Core, task_id: str, kind: str, ref: str, record: dict[str, Any], *,
                   by: dict[str, Any], summary: str, extra: dict[str, Any] | None = None) -> str:
    """Record one new version of an attribute or a rule, outside `propose`, and return its ref.

    WHY outside `propose`: `propose` writes an attribute and a rule together and then consults the
    trigger table about the rule, so sending one edited record through it would propose the other a
    second time and raise a fresh confirmation item on a criterion nobody changed. The caller checks
    the record (`check_attribute`, `check_rule`) and decides whether an item is owed.

    `core/adjudication.py` keeps its own two private copies of this for the versions a machine
    adjudication writes; they do the same thing and should fold into this one.
    """
    base_id = ref.split("@v")[0]
    version = len(_versions(core, task_id, kind, base_id)) + 1
    full = dict(record, **{f"{kind}_id": base_id}, version=version, status="proposed", supersedes=ref,
                **(extra or {}))
    artifact_id = core.artifacts.put(kind, full)
    core.journal.append(task_id, "criterion.version_proposed", actor=by, ids={"task_id": task_id},
                        payload={"kind": kind, "id": base_id, "version": version, "artifact_id": artifact_id,
                                 **(extra or {})},
                        artifact_links=[{"kind": kind, "id": artifact_id, "version": version}], summary=summary)
    return f"{base_id}@v{version}"


def revise_for_workbench(core: Core, task_id: str, rule_ref: str, changes: dict[str, Any], *,
                         reason: str, by: dict[str, Any]) -> dict[str, Any]:
    """Append changes={attribute:{...},rule:{...}} and a fresh review; preserve old frozen records."""
    from .derivation import ATTRIBUTE_FIELDS, RULE_FIELDS
    if not isinstance(reason, str) or not reason.strip():
        raise InvariantViolation("schema", "a workbench revision must state its reason")
    if not isinstance(changes, dict) or set(changes) - {"attribute", "rule"}:
        raise InvariantViolation("schema", "changes must contain attribute/rule field dictionaries")
    ac, rc = changes.get("attribute") or {}, changes.get("rule") or {}
    if not isinstance(ac, dict) or not isinstance(rc, dict) or set(ac) - set(ATTRIBUTE_FIELDS) - {"quantity_id"} \
            or set(rc) - set(RULE_FIELDS) - {"applies_to_result_kind"}:
        raise InvariantViolation("schema", "workbench changes contain non-authorable fields")
    old_rule = load(core, rule_ref, task_id)
    current = next((r for r in registered_rule_records(core, task_id) if r["rule_id"] == old_rule["rule_id"]), None)
    if current is None or current["version"] != old_rule["version"]:
        raise InvariantViolation("schema", "revise the current active rule version, not a historical or retired rule")
    old_attr = load(core, old_rule["attribute_ref"], task_id)
    attr, rule = dict(old_attr, **ac), dict(old_rule, **rc)
    if attr == old_attr and rule == old_rule:
        return {"changed": False, "attribute_ref": old_rule["attribute_ref"], "rule_ref": rule_ref, "requires_new_freeze": False}
    if any(old_attr.get(k) != attr.get(k) for k in ac if k != "rationale") or rc:
        if "bound_support" not in ac:
            attr.pop("bound_support", None)
        if "bound_support" not in rc:
            rule.pop("bound_support", None)
    for record in (attr, rule):
        for key in ("adjudicated_by", "adjudication_id", "approval_kind", "confirmed_by", "confirmed_by_a_person"):
            record.pop(key, None)
        record["proposed_by"] = by
    check_attribute(attr)
    check_rule(rule, attr)
    extra = {"workbench_revision": {"source_rule_ref": rule_ref, "source_attribute_ref": old_rule["attribute_ref"],
                                    "changes": changes, "reason": reason}}
    attr_ref = record_version(core, task_id, "attribute", old_rule["attribute_ref"], attr, by=by,
                              summary=f"workbench revision: {reason}", extra=extra)
    rule["attribute_ref"] = attr_ref
    new_ref = record_version(core, task_id, "rule", rule_ref, rule, by=by,
                             summary=f"workbench revision: {reason}", extra=extra)
    item = review.request(core, task_id, subject={"kind": "rule_version", "id": new_ref,
                          "version": int(new_ref.rsplit("@v", 1)[1]), "attribute_ref": attr_ref},
                          why_expert_required="a workbench revision requires fresh evidence/applicability review; " + reason,
                          requested_by=by, inspection_bundle=extra)
    return {"changed": True, "attribute_ref": attr_ref, "rule_ref": new_ref, "review_item_id": item,
            "requires_new_freeze": True, "previous_authority_carried": False}


def authority_requirements(rule: dict[str, Any], attribute: dict[str, Any], *,
                           support: dict[str, Any] | None = None,
                           weighting: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Every reason this criterion needs a decision before it may score, from the whole object.

    Trigger table (design §12.1), computed from the rule, the attribute, the bounds inside its
    `value_transform` and the weighting policy that will rank with it -- not from the rule alone.

    WHY the whole object: `needs_expert` read `rule["rule_kind"]` and `rule["cutoff_basis"]` and
    nothing else, while `check_value_transform` accepts `basis: expert_set` for a bound that is read
    on every cell the rule scores. Measured on this checkout, 14 October 2026: an ordering preference
    whose transform bound carried `basis: expert_set` was registered with zero review items and
    entered a confirmed set with `confirmed_by: auto:trigger_table` -- the authority requirement
    disappeared because the number had moved out of the one field the table was reading. Moving a
    number from a cutoff into a transform must not change what it needs (§6 F3).
    """
    out: list[dict[str, str]] = []
    if rule.get("rule_kind") == "hard_exclusion":
        out.append({"reason": "hard_exclusion",
                    "detail": "a hard exclusion deletes candidates from the result"})
    if rule.get("cutoff_basis") in bound_support.AUTHORITY_BASES:
        out.append({"reason": f"cutoff_basis_{rule['cutoff_basis']}",
                    "detail": f"the cutoff claims cutoff_basis {rule['cutoff_basis']}"})
    transform = (attribute or {}).get("value_transform") or {}
    if transform.get("basis") in bound_support.AUTHORITY_BASES:
        out.append({"reason": f"transform_basis_{transform['basis']}",
                    "detail": f"the {transform.get('kind')} bound inside value_transform claims basis "
                              f"{transform['basis']}, which is the same claim a cutoff of that basis makes"})
    for bound in (support or {}).get("bounds", []):
        if bound["state"] in bound_support.REVIEW_STATES:
            out.append({"reason": "bound_interpretation_added",
                        "detail": f"{bound['parameter_path']} reads {bound['value']} as a decision line that its "
                                  f"source does not state as one"})
        elif bound["state"] in bound_support.BLOCKING_STATES:
            out.append({"reason": "bound_unsupported",
                        "detail": f"{bound['parameter_path']} reads {bound['value']} and its support does not "
                                  f"establish that number"})
    weights = (weighting or {}).get("weight_vector") or {}
    rule_ref = f"{rule.get('rule_id')}@v{rule.get('version')}"
    for key in (rule_ref, rule.get("rule_id"), attribute.get("attribute_ref") if attribute else None):
        if key and key in weights and not (weighting or {}).get("weight_provenance"):
            # A weight is a decision about how much this criterion counts, and §5.4 asks for the
            # provenance of weights and weight groups like any other registered parameter.
            out.append({"reason": "weight_without_provenance",
                        "detail": f"the ordering method weights {key} at {weights[key]} and names no provenance "
                                  f"for that weight"})
            break
    return out


def needs_expert(rule: dict[str, Any], attribute: dict[str, Any], *, support: dict[str, Any] | None = None,
                 weighting: dict[str, Any] | None = None) -> bool:
    """Whether this criterion needs an `hd_` before it may score (`authority_requirements`).

    The attribute is required rather than optional: a caller that cannot supply it cannot see the
    bounds inside the transform, and an authority check that silently reads half the object is the
    defect this signature exists to close (§6 F3).
    """
    return bool(authority_requirements(rule, attribute, support=support, weighting=weighting))


def load(core: Core, ref: str, task_id: str) -> dict[str, Any]:
    """The record of an attribute or rule version proposed in a task."""
    base_id, version = ref.rsplit("@v", 1)
    kind = "attribute" if base_id.startswith("attr_") else "rule"
    try:
        wanted = int(version)
    except ValueError:
        # Historically an absent base raises KeyError even if its version is not
        # numeric; conversion was evaluated only after finding a proposed base.
        if _versions(core, task_id, kind, base_id):
            raise
        raise KeyError(ref) from None
    for payload in _versions(core, task_id, kind, base_id, version=wanted):
        if payload["version"] == wanted:
            return core.artifacts.payload(payload["artifact_id"])
    raise KeyError(ref)


def chosen_after_results(ordering_method: dict[str, Any] | None) -> bool:
    """True for an ordering method derived from the results it will then rank (design §5.7).

    A symbolic expression is fitted on assessed cells, so the ranking rule was chosen after
    seeing the data: unless it was preregistered, the rule set is exploratory however many of
    its rules are confirmed. Without this, a fitted ordering method would inherit the
    `prespecified` label of the rules it was fitted on top of.
    """
    return (ordering_method or {}).get("kind") == "symbolic_expression"


# --- deferral: which capabilities a run holds out, and what that costs a rule ---------------------
#
# A confirmation may hold capabilities out of its run (`--defer-capability literature_retrieval`:
# sweep the universe on the database routes, read the literature over a shortlist afterwards). The
# unit of that deferral is the *route*, not the rule, because an attribute may read one quantity from
# several routes of unlike kinds (`check_attribute`): the mandated receptor potency is read from
# ChEMBL, from IUPHAR/BPS and from a published selectivity table. Holding the whole rule out because
# one of its three routes needs the held-out capability left the two curations unasked and scored the
# task's own quantity nowhere -- and the mandated-coverage floor, the calibration guard's reference
# population and every count taken from those cells are computed from exactly those cells.
DEFERRAL_SCOPES = ("rule", "route")


def deferral_scope(row: dict[str, Any]) -> str:
    """Whether a `deferred[]` row holds a whole rule out of the set or only some of its routes.

    A row written before route-level deferral existed carries no scope and held the whole rule out,
    so that is the default: a reader of an older rule set is told what that set actually did.
    """
    return row.get("scope") or "rule"


def deferred_capabilities(rule_set: dict[str, Any]) -> tuple[str, ...]:
    """The capabilities a confirmed set held out of its run, for a re-confirmation to hold out again.

    Read from the set's own `deferred_capabilities` where it has one, and rebuilt from the
    `deferred[]` rows otherwise, which is all an older record carries.

    WHY the field as well as the rows: a route-level row is recorded on a rule that *entered* the
    set, so if every rule naming a held-out capability were held out for some other reason (an
    unsupported bound, no decision yet) the rows would be empty and a re-confirmation -- which is
    what `sr_stage._install` does when it installs a fitted ordering method -- would silently
    un-defer the capability and ask for reading the run had decided not to buy.
    """
    declared = rule_set.get("deferred_capabilities")
    if declared:
        return tuple(sorted(set(declared)))
    return tuple(sorted({capability for row in (rule_set.get("deferred") or [])
                         for capability in (row.get("capabilities") or [row.get("capability")]) if capability}))


def deferral_reason(rule_set: dict[str, Any]) -> str:
    """The reason a confirmed set gave for its deferral, from the record or from its first row."""
    rows = rule_set.get("deferred") or []
    return rule_set.get("defer_reason") or (rows[0].get("reason") if rows else "") or ""


def entry_deferred_capabilities(entry: dict[str, Any]) -> tuple[str, ...]:
    """The capabilities held out of this run for one *scoring* rule (`confirm_rule_set`).

    What the controller passes to `evidence.gather` so the run skips those routes and asks the
    others: the rule scores, on the evidence its entry says it scores on.
    """
    return tuple(sorted({route["capability"] for route in (entry.get("deferred_routes") or [])}))


def route_summary(request: Any) -> dict[str, Any]:
    """One route as a rule-set entry records it: the source asked and the question asked of it."""
    route = _as_route(request)
    return {"capability": route.get("capability"), "question_kind": route.get("question_kind")}


def confirm_rule_set(core: Core, task_id: str, *, by: dict[str, Any], ordering_method: dict[str, Any] | None = None,
                     coverage_floor: float = 1.0, constants: list[dict[str, Any]] | None = None,
                     allow_pending: bool = False, defer_capabilities: tuple[str, ...] = (),
                     defer_reason: str = "", preregistration_ref: str | None = None,
                     require_bound_support: bool = False, withhold_unresolved_reviews: bool = False) -> str:
    """Assemble `rules@v<n>` from the rule proposals that may enter it.

    A rule needing an expert enters only with an `hd_` approving it; a preference rule the
    trigger table lets proceed automatically enters with `confirmed_by: auto:trigger_table`.
    Proposals still awaiting a decision block the set unless `allow_pending` is given (for
    exploratory runs); they are then listed in `pending[]`, never silently dropped.

    `withhold_unresolved_reviews` also holds still-open preferences out of scoring instead of
    admitting them through the trigger table. False preserves legacy confirmation behavior.
    This does not resolve a queue item: pending hard constraints remain blocking downstream.

    A rule whose item was resolved by a `machine_adjudication` instead enters with that `adj_` as
    its `confirmed_by`, is listed in `machine_adjudicated[]`, and carries `authority:
    machine_adjudication` on its entry. One such rule makes the whole set `exploratory` with a
    reason naming the count, for the same reason a fitted ordering method does: the label is what a
    reader has to go on, and a set no person has confirmed must not read as a settled one.

    A rule a number enters the board on must have that number supported: every cutoff and every
    bound inside a `value_transform` is validated against the claims the criterion cites
    (`core/bound_support.py`, design §5.4). A rule whose bound its own cited claims contradict is
    held out and listed in `bounds_unsupported[]`; with `require_bound_support` a rule whose bounds
    are not established as source-stated thresholds is held out too and listed in
    `bounds_withheld[]`. Each entry carries the state of each of its bounds, so a reader can see
    which numbers a source states and which the criterion interprets.

    A bound a machine adjudication granted on a declared interpretation (`adjudication` route 6)
    scores as a cutoff and is listed in `bounds_granted[]` with the `adj_` that granted it, with a
    separate line for any rule still *excluding* candidates on such a bound. Its state is
    `interpretation_granted`, never `sourced_threshold`, and it makes the set `exploratory` on its
    own grounds as well as through `machine_adjudicated[]`.

    `defer_capabilities` holds capabilities out of this run, per *route* and not per rule
    (DEFERRAL_SCOPES). A rule every one of whose routes names a held-out capability has nothing to
    read and stays out of the set, listed in `deferred[]` with `scope: rule`. A rule that keeps at
    least one route enters and scores on those routes, with the held-out ones recorded on its entry
    (`deferred_routes`, beside the `scoring_routes` the values actually come from) and a
    `scope: route` row in `deferred[]` naming both.

    A rule whose attribute a `collapse` merged away (`core/collapse.py`: several registrations of one
    quantity) does not enter at all and is listed in `collapsed_away[]`; a rule reading an attribute
    version that collapse wrote is listed in `machine_collapsed[]`. Either makes the set
    `exploratory` on the same grounds. Holding a merged-away rule out rather than demoting it is the
    point of the collapse: a demoted rule still costs a sweep pass and still counts in the hard-rule
    coverage denominator, and that denominator -- five quantities counted as ten -- is what the
    collapse exists to repair.
    """
    from . import adjudication, collapse as collapse_mod   # imported here: both read this module's records

    registry = registry_inventory(core, task_id)
    active_refs = {entry["rule_ref"] for entry in registry["active"]}
    queue = {key: item for key, item in review.items(core, [task_id]).items()
             if item["subject"].get("kind") != "rule_version" or item["subject"].get("id") in active_refs}
    adjudicated = adjudication.by_rule_version(core, task_id)
    superseded = collapse_mod.superseded_attributes(core, task_id)
    collapsed_surviving = collapse_mod.surviving_rules(core, task_id)
    decided = {i["subject"]["id"]: i for i in queue.values()
               if i["subject"]["kind"] == "rule_version" and i["state"] == "decided"}
    open_refs = sorted(i["subject"]["id"] for i in queue.values()
                       if i["subject"]["kind"] == "rule_version" and i["state"] in ("open", "in_review"))
    if open_refs and not allow_pending:
        raise InvariantViolation("unconfirmed", f"{len(open_refs)} rule proposals await an expert decision")
    proposed = {}
    for event in core.journal.replay(task_id):
        if event.event_type == "criterion.version_proposed" and event.payload["kind"] == "rule":
            proposed[event.payload["id"]] = f"{event.payload['id']}@v{event.payload['version']}"   # latest version wins
    entries, deferred, machine_adjudicated, collapsed_away = [], [], [], []
    unresolved = {row["rule_ref"]: row for row in unresolved_review_findings(core, task_id)} \
        if withhold_unresolved_reviews else {}
    execution_findings = {row["rule_ref"]: row for row in preference_execution_findings(core, task_id)}
    bounds_unsupported, bounds_withheld, decisions_not_carried, bounds_granted = [], [], [], []
    for rule_ref in sorted(proposed.values()):
        rule = load(core, rule_ref, task_id)
        merged_away = superseded.get(rule["attribute_ref"])
        if merged_away is not None:
            collapsed_away.append({"rule_ref": rule_ref, "attribute_ref": rule["attribute_ref"],
                                   "merged_into": merged_away["surviving"]["attribute_ref_after"],
                                   "scored_by": merged_away["surviving"]["rule_ref_after"],
                                   "collapse_id": merged_away["collapse_id"]})
            continue
        if rule_ref not in active_refs:
            continue
        adjudication_record = adjudicated.get(rule_ref)
        attr = load(core, rule["attribute_ref"], task_id)
        if rule_ref in unresolved:
            deferred.append(unresolved[rule_ref])
            continue
        if rule_ref in execution_findings:
            # Keep the proposal active and auditable, but never put a non-executable
            # preference into scoring or its coverage denominator. Approval cannot invent
            # an absent comparison. This is a rule deferral, not a capability deferral.
            deferred.append(execution_findings[rule_ref])
            continue
        # Which of this attribute's routes this run holds out, and whether that leaves the rule
        # anything to score on (see DEFERRAL_SCOPES above).
        #
        # WHY the *matching* routes are the ones recorded: the deferral round-trips through this
        # record (`sr_stage` re-confirms with `deferred_capabilities` read back off it), so recording
        # another of the attribute's capabilities would quietly un-defer the route next time.
        routes = evidence_routes(attr)
        held_capabilities = [route_summary(r)["capability"] for r in routes
                             if route_summary(r)["capability"] in defer_capabilities]
        deferred_routes = [route_summary(r) for r in routes
                           if route_summary(r)["capability"] in defer_capabilities]
        scoring_routes = [route_summary(r) for r in routes
                          if route_summary(r)["capability"] not in defer_capabilities]
        if held_capabilities and not scoring_routes:
            # Every route needs a capability this run is not running, so the rule has nothing left to
            # read and does not enter the set at all: the rule-level deferral, unchanged.
            # A deferred rule carries its authority too, but it stays out of `machine_adjudicated`:
            # that list is what the set rests on, and a rule held out of this run rests on nothing.
            deferred.append({"rule_ref": rule_ref, "scope": "rule", "capability": held_capabilities[0],
                             "capabilities": sorted(set(held_capabilities)), "routes": deferred_routes,
                             "scores_on": [], "reason": defer_reason,
                             "authority": "machine_adjudication" if adjudication_record else None})
            continue
        # Every number this rule compares a candidate against, and what stands behind it
        # (`core/bound_support.py`, design §5.4). A bound whose support contradicts it never enters
        # the set: 90 citing a claim that states 30 is not a rule awaiting an opinion, it is a rule
        # whose own evidence says it is wrong.
        #
        # `grants` comes from the `adj_` record that resolved this rule's queue item and from nowhere
        # else (`adjudication.granted_bounds`, empty for every other route and for a refusal): an
        # interpreted bound may act as a cutoff only where an authority said so, and a rule that
        # could say so about itself would need no authority at all.
        granted = adjudication.granted_bounds(adjudication_record)
        support = bound_support.validate(attr, rule, claims=_claims_for(core, task_id, attr, rule),
                                         grants=granted)
        if support["unsupported_paths"]:
            bounds_unsupported.append({"rule_ref": rule_ref, "attribute_ref": rule["attribute_ref"],
                                       "paths": support["unsupported_paths"],
                                       "findings": bound_support.messages(support)})
            continue
        if require_bound_support and support["states"] and \
                any(state != "sourced_threshold" for state in support["states"].values()):
            # The strict gate a freeze or a published sourced set asks for (§6 F2: missing or
            # invalid support stays visible and non-scoring). Off by default, because an already
            # promoted criterion carries no support record at all and §9.2 asks that absent
            # metadata be marked unknown rather than be given a passing status *or* a failing one.
            # An `interpretation_granted` bound is withheld here too, and that is the gate working:
            # it asks for thresholds the sources themselves state, and a granted bound is one an
            # agent read into a passage that reports a measurement. The grant is still recorded and
            # still named in `bounds_granted[]`; what this gate refuses is calling it sourced.
            bounds_withheld.append({"rule_ref": rule_ref, "attribute_ref": rule["attribute_ref"],
                                    "states": support["states"], "fallback": None})
            # WHY a preference may fall back to ranking instead of leaving the set: withholding the
            # *cutoff* and withholding the *measurement* are different acts, and only the first is
            # what the support contract establishes. Measured on the clean derivation of 14 October
            # 2026: all 33 cutoff-bearing proposals declared a support record, and the proposer
            # declared 29 of them `reports_measurement` and 4 `provides_heuristic` -- none
            # `states_decision_threshold`, because the literature reports measurements and rules of
            # thumb and does not state screening cutoffs. So the strict gate withholds every derived
            # threshold, and dropping the criteria with them would discard sourced measurements the
            # task does care about. Ranking candidates by a measured value in the attribute's
            # declared direction asserts no cutoff, which is precisely what is unsupported here.
            # A hard exclusion gets no such fallback: an exclusion with no defensible cutoff has
            # nothing left to do, and demoting it would quietly turn a requirement into a nudge.
            # Only a withheld *cutoff* can fall back. A withheld transform bound is not removed by
            # dropping the predicate: the transform still computes the cell from that number, so the
            # unsupported value would go on scoring under a different predicate form. Dropping the
            # transform instead would change which quantity the attribute is about, which is not a
            # repair this may make on its own.
            unsourced = [path for path, state in support["states"].items() if state != "sourced_threshold"]
            if rule["rule_kind"] != "preference" or not attr.get("direction") \
                    or attr.get("direction") == "non_directional" \
                    or not all(path.startswith("rule.cutoff") for path in unsourced):
                continue
            rule = dict(rule, predicate_form="ordering", cutoff=None,
                        cutoff_basis="none_evidence_insufficient")
            bounds_withheld[-1]["fallback"] = "ranked_without_the_withheld_cutoff"
            # Re-validated against the rule as it will now score: the authority a bound owed is owed
            # by the bound, and this rule no longer carries one. Reusing the earlier report would
            # keep demanding a decision about a cutoff that has just been removed.
            support = bound_support.validate(attr, rule, claims=_claims_for(core, task_id, attr, rule))
        item = decided.get(rule_ref)
        if item is not None and item["subject"].get("attribute_ref") not in (None, rule["attribute_ref"]):
            # A decision is a decision about one version of one decision-bearing object. The rule
            # version named in the subject may now read another attribute version -- a collapse or a
            # machine adjudication writes one -- and approving the earlier pair said nothing about
            # the parameters of the later one (§6 F3: approving one version does not approve
            # materially changed parameters in another).
            decisions_not_carried.append({"rule_ref": rule_ref, "decision_id": item["decision_id"],
                                          "decided_attribute_ref": item["subject"].get("attribute_ref"),
                                          "attribute_ref_now": rule["attribute_ref"]})
            item = None
        if item is not None:
            if item["decision"] not in ("approve", "approve_with_edits"):
                continue
            confirmed_by, authority = item["decision_id"], "human_scientific_approval"
        elif adjudication_record is not None:
            confirmed_by, authority = adjudication_record["adjudication_id"], "machine_adjudication"
            machine_adjudicated.append(rule_ref)
        elif not needs_expert(rule, attr, support=support, weighting=ordering_method):
            confirmed_by, authority = "auto:trigger_table", "trigger_table"
        else:
            continue
        if support["granted_paths"]:
            # A rule that scores on a bound an agent granted, named here as well as in
            # `machine_adjudicated[]`, because the two say different things: that list says no person
            # confirmed the rule, this one says which *number* is acting as a decision bound on an
            # agent's reading of a passage that states no cutoff -- and, where the rule is still a
            # hard exclusion, that candidates are being removed on it.
            bounds_granted.append({"rule_ref": rule_ref, "attribute_ref": rule["attribute_ref"],
                                   "paths": support["granted_paths"], "rule_kind": rule["rule_kind"],
                                   "adjudication_id": adjudication_record["adjudication_id"],
                                   "excludes_candidates": rule["rule_kind"] == "hard_exclusion"})
        # WHY `disputed` is recorded on the entry: the trigger table admits a preference rule without an expert, and
        # it does that whether or not a critic finding about that rule is still open. Such a rule scores candidates
        # while also appearing in `pending[]`, which on its own reads as "did not enter the set". The entry says
        # which it is, so a snapshot cannot present a disputed rule as a settled one.
        entries.append({"attribute_ref": rule["attribute_ref"], "rule_ref": rule_ref, "rule_kind": rule["rule_kind"],
                        "confirmed_by": confirmed_by,
                        "authority": vocab.require("decision_authority", authority),
                        "acceptable_value_sources": attr["acceptable_value_sources"],
                        # Which sources this run asked for this rule's values and which it held out,
                        # so a reader of a cell can tell a value read from the curated databases
                        # alone from one that also used a literature reading. Recorded on every
                        # entry, including the ordinary one where nothing is held out, because an
                        # absent list would read as unknown rather than as "nothing was held out".
                        "scoring_routes": scoring_routes, "deferred_routes": deferred_routes,
                        "on_states": [rule["on_missing"], rule["on_inapplicable"], rule["on_conflict"]],
                        "cutoff_basis": rule["cutoff_basis"], "disputed": rule_ref in set(open_refs),
                        # One state per number this rule compares a candidate against, so a reader of
                        # the set can see which of its bounds a source states and which it interprets.
                        "bound_support": {"states": support["states"],
                                          "needing_a_decision": support["review_paths"],
                                          "claims_resolved": support["claims_resolved"],
                                          # How each number is traced, and which of them is one end of a
                                          # range its source states rather than a line that source draws.
                                          "traces": {b["parameter_path"]: b["trace_kind"] for b in support["bounds"]},
                                          "range_endpoints": sorted(b["parameter_path"] for b in support["bounds"]
                                                                    if b["range_endpoint"])}})
        if deferred_routes:
            # The rule entered and scores; a row still appears here, marked `route`, because this is
            # the list every other surface reads the deferral off -- `sr_stage` for the capabilities
            # a re-confirmation must hold out again, `criteria_export` for what each criterion did
            # this run. `scores_on` says what it was asked instead, so the row cannot be read as
            # "this rule scored nothing".
            deferred.append({"rule_ref": rule_ref, "scope": "route", "capability": deferred_routes[0]["capability"],
                             "capabilities": sorted({r["capability"] for r in deferred_routes}),
                             "routes": deferred_routes,
                             "scores_on": [r["capability"] for r in scoring_routes], "reason": defer_reason,
                             "authority": "machine_adjudication" if adjudication_record else None})
    if not entries:
        held = len(bounds_unsupported) + len(bounds_withheld)
        raise InvariantViolation("unconfirmed", "no rule version may enter the set yet"
                                 + (f"; {held} were held out over bound support" if held else "")
                                 + ("; non-executable preferences: " + "; ".join(
                                     f"{row['rule_ref']}: {row['reason']}" for row in execution_findings.values())
                                    if execution_findings else "")
                                 + ("; unresolved reviews withheld: " + "; ".join(
                                     f"{row['rule_ref']}: {row['reason']}" for row in unresolved.values())
                                    if unresolved else ""))
    existing = [e for e in core.journal.replay(task_id) if e.event_type == "criterion.version_approved"]
    version = len(existing) + 1
    admission_predicate = {"entries": [{k: e[k] for k in ("acceptable_value_sources", "on_states", "cutoff_basis")} for e in entries],
                           "coverage_floor": coverage_floor, "constants": constants or []}
    # WHY a registration reference has to resolve: `prespecified` is the label that says this rule set was
    # fixed before it saw results, and it was emitted purely because nothing else had gone wrong --
    # `preregistration_ref` was an unvalidated parameter a caller could leave null or fill with any string,
    # and a synthetic confirmation produced `acceptance_label: prespecified` with `preregistration_ref: null`.
    # A claim about when a decision was taken cannot rest on a field nobody checks, so an unresolvable
    # reference is now a reason the set is exploratory, and an absent one keeps the label it already had.
    registration_missing = []
    if preregistration_ref is not None:
        try:
            core.artifacts.payload(preregistration_ref)
        except KeyError:
            registration_missing = [f"the registration {preregistration_ref} this set names does not resolve, "
                                    f"so nothing establishes that it was fixed before seeing results"]
            preregistration_ref = None
    fitted_ordering = chosen_after_results(ordering_method) and not preregistration_ref
    scoring_disputed = sorted(e["rule_ref"] for e in entries if e["disputed"])
    machine_adjudicated = sorted(machine_adjudicated)
    excluding_on_a_granted_bound = sorted(e["rule_ref"] for e in bounds_granted if e["excludes_candidates"])
    machine_collapsed = sorted(e["rule_ref"] for e in entries if e["rule_ref"] in collapsed_surviving)
    # Two separate facts, each stated only when it is true: a rule may read a collapsed attribute
    # after the collapse was withdrawn (the version stays; the registry is append-only), and a pure
    # duplicate may be merged away without any version being written for the survivor.
    collapse_reasons = ([f"{len(machine_collapsed)} rules read an attribute version the software wrote when it "
                         f"collapsed several registrations of one quantity; no person confirmed that: "
                         f"{', '.join(machine_collapsed)}"] if machine_collapsed else []) + \
                       ([f"{len(collapsed_away)} rules are held out of this set because the software merged their "
                         f"attributes away: {', '.join(e['rule_ref'] for e in collapsed_away)}"]
                        if collapsed_away else [])
    bound_reasons = ([f"{len(bounds_unsupported)} rules are held out of this set because a number they compare "
                      f"candidates against is not supported by the claims they cite: "
                      f"{', '.join(e['rule_ref'] for e in bounds_unsupported)}"] if bounds_unsupported else []) + \
                    ([f"{len(bounds_withheld)} rules are held out because support records establishing their "
                      f"bounds as source-stated thresholds are missing or incomplete: "
                      f"{', '.join(e['rule_ref'] for e in bounds_withheld)}"] if bounds_withheld else []) + \
                    ([f"{len(decisions_not_carried)} rules read an attribute version the decision on them did not "
                      f"cover: {', '.join(e['rule_ref'] for e in decisions_not_carried)}"]
                     if decisions_not_carried else []) + \
                    ([f"{len(bounds_granted)} rules score on a bound an agent granted on a declared "
                      f"interpretation rather than on a threshold their source states: "
                      f"{', '.join(sorted(e['rule_ref'] for e in bounds_granted))}"] if bounds_granted else []) + \
                    ([f"{len(excluding_on_a_granted_bound)} of them remove candidates on such a bound: "
                      f"{', '.join(excluding_on_a_granted_bound)}"] if excluding_on_a_granted_bound else [])
    acceptance_reasons = ([f"{len(open_refs)} rule proposals await an expert decision"] if open_refs else []) + \
                         ([f"{len(scoring_disputed)} of them score candidates while disputed: "
                           f"{', '.join(scoring_disputed)}"] if scoring_disputed else []) + \
                         ([f"{len(machine_adjudicated)} rules were adjudicated by an agent; no person has "
                           f"confirmed them: {', '.join(machine_adjudicated)}"] if machine_adjudicated else []) + \
                         collapse_reasons + bound_reasons + registration_missing + \
                         (["the ordering method was fitted on the results it ranks"] if fitted_ordering else [])
    record = {"rule_set_ref": f"rules@v{version}", "task_id": task_id, "entries": entries,
              "ordering_method": ordering_method or {"kind": "weighted_preference", "weight_vector": {}, "tie_break": "candidate_id"},
              "coverage_floor": coverage_floor,
              "evidence_admission_predicate_hash": sha256_hex(admission_predicate),
              "confirmed_by": [e["confirmed_by"] for e in entries], "pending": open_refs,
              "pending_but_scoring": scoring_disputed, "machine_adjudicated": machine_adjudicated,
              "machine_collapsed": machine_collapsed, "collapsed_away": collapsed_away,
              "deferred": deferred, "retired": registry["retired"],
              "withhold_unresolved_reviews": withhold_unresolved_reviews,
              # The run policy itself, beside the rows it produced: what a re-confirmation has to
              # hold out again (`deferred_capabilities`), which the rows alone cannot always say.
              "deferred_capabilities": sorted(set(defer_capabilities)), "defer_reason": defer_reason or None,
              "bounds_unsupported": bounds_unsupported, "bounds_withheld": bounds_withheld,
              "bounds_granted": bounds_granted, "decisions_not_carried": decisions_not_carried,
              "acceptance_label": vocab.require("acceptance_label", "exploratory" if acceptance_reasons else "prespecified"),
              "acceptance_reasons": acceptance_reasons, "preregistration_ref": preregistration_ref}
    artifact_id = core.artifacts.put("rule_set", record)
    core.journal.append(task_id, "criterion.version_approved", actor=by, ids={"task_id": task_id},
                        payload={"rule_set_ref": record["rule_set_ref"], "artifact_id": artifact_id,
                                 "hash": record["evidence_admission_predicate_hash"], "pending": open_refs},
                        artifact_links=[{"kind": "rule_set", "id": artifact_id, "version": version}],
                        summary=f"confirmed {record['rule_set_ref']} ({len(entries)} rules, {len(open_refs)} pending "
                                f"of which {len(scoring_disputed)} score anyway, {len(machine_adjudicated)} adjudicated "
                                f"by an agent, {len(machine_collapsed)} reading a collapsed attribute, "
                                f"{len(collapsed_away)} collapsed away, "
                                f"{sum(1 for d in deferred if deferral_scope(d) == 'rule')} deferred whole, "
                                f"{sum(1 for d in deferred if deferral_scope(d) == 'route')} scoring with a route "
                                f"held out, "
                                f"{len(bounds_unsupported) + len(bounds_withheld)} held out over bound support, "
                                f"{len(bounds_granted)} scoring on a bound an agent granted)")
    return record["rule_set_ref"]


def _claims_for(core: Core, task_id: str, attribute: dict[str, Any], rule: dict[str, Any]
                ) -> list[dict[str, Any]] | None:
    """The admitted claims a criterion cites, read only when it holds a number to check.

    WHY the guard: confirming a rule set is a fold over the journal, and most rules of the live task
    carry no cutoff at all (ordering preferences). Resolving citations for them would read the run
    streams once per rule for nothing.
    """
    if not bound_support.bounds(attribute, rule):
        return []
    return bound_support.resolve_claims(core, task_id, attribute.get("supporting_claim_refs") or [])


def rule_set(core: Core, task_id: str, ref: str | None = None) -> dict[str, Any]:
    approvals = [e for e in core.journal.replay(task_id) if e.event_type == "criterion.version_approved"]
    if not approvals:
        raise KeyError(f"{task_id} has no confirmed rule set")
    chosen = approvals[-1] if ref is None else next(e for e in approvals if e.payload["rule_set_ref"] == ref)
    return core.artifacts.payload(chosen.payload["artifact_id"])


def registered_rule_records(core: Core, task_id: str, *, include_retired: bool = False) -> list[dict[str, Any]]:
    """Latest proposed rules; retirement is an explicit append-only registry transition."""
    latest = {}
    retired = {}
    for event in core.journal.replay(task_id):
        if event.event_type == "criterion.version_proposed" and event.payload["kind"] == "rule":
            latest[event.payload["id"]] = core.artifacts.payload(event.payload["artifact_id"])
        elif event.event_type == "criterion.change_recorded" and event.payload.get("registry"):
            retired[event.payload["rule_ref"]] = event.payload["registry_state"] == "retired"
    from . import collapse
    superseded = {} if include_retired else collapse.superseded_attributes(core, task_id)
    return [record for record in latest.values() if include_retired or
            (not retired.get(f"{record['rule_id']}@v{record['version']}", False)
             and record["attribute_ref"] not in superseded)]


def retire_rule(core: Core, task_id: str, rule_ref: str, *, by: dict[str, Any], reason: str,
                superseded_by: str | None = None, reduction_run_id: str | None = None,
                source_pool_ref: str | None = None) -> None:
    """Retire one exact rule version without erasing its proposal, review or frozen snapshots."""
    if not reason.strip():
        raise ValueError("a registry retirement needs a scientific reason")
    rule = load(core, rule_ref, task_id)
    if superseded_by:
        load(core, superseded_by, task_id)
    if rule_ref not in {f"{r['rule_id']}@v{r['version']}" for r in registered_rule_records(core, task_id)}:
        return
    core.journal.append(task_id, "criterion.change_recorded", actor=by, ids={"task_id": task_id},
                        payload={"registry": True, "registry_state": "retired", "operation": "remove",
                                 "rule_ref": rule_ref, "attribute_ref": rule["attribute_ref"],
                                 "superseded_by_rule_ref": superseded_by, "reason_text": reason,
                                 "reduction_run_id": reduction_run_id, "source_pool_ref": source_pool_ref},
                        summary=f"retired {rule_ref}: {reason[:160]}")


def registry_inventory(core: Core, task_id: str) -> dict[str, Any]:
    """Active includes unconfirmed/disputed/deferred rules; scoring is counted separately."""
    all_rules = registered_rule_records(core, task_id, include_retired=True)
    active = {f"{r['rule_id']}@v{r['version']}": r for r in registered_rule_records(core, task_id)}
    queue = review.items(core, [task_id])
    pending = {item["subject"].get("id") for item in queue.values()
               if item["state"] in ("open", "in_review")}
    try:
        scoring = {entry["rule_ref"] for entry in rule_set(core, task_id)["entries"]}
    except KeyError:
        scoring = set()
    rows = [{"rule_ref": ref, "attribute_ref": record["attribute_ref"],
             "pending_review": ref in pending, "scoring_in_latest_frozen_set": ref in scoring}
            for ref, record in active.items()]
    retired = [{"rule_ref": f"{r['rule_id']}@v{r['version']}", "attribute_ref": r["attribute_ref"]}
               for r in all_rules if f"{r['rule_id']}@v{r['version']}" not in active]
    return {"active": rows, "retired": retired, "active_registered_count": len(rows),
            "pending_review_count": sum(row["pending_review"] for row in rows),
            "scoring_in_latest_frozen_set_count": len(scoring & active.keys()),
            "historical_registered_count": len(all_rules), "retired_latest_count": len(retired)}


def registered_attributes(core: Core, task_id: str, *, include_retired: bool = False) -> list[dict[str, Any]]:
    """Latest attributes, keeping explicitly retired quantities available for historical exports."""
    latest: dict[str, dict[str, Any]] = {}
    for event in core.journal.replay(task_id):
        if event.event_type == "criterion.version_proposed" and event.payload["kind"] == "attribute":
            latest[event.payload["id"]] = core.artifacts.payload(event.payload["artifact_id"])
    if include_retired:
        return list(latest.values())
    all_bases = {rule["attribute_ref"].split("@v")[0]
                 for rule in registered_rule_records(core, task_id, include_retired=True)}
    active_bases = {rule["attribute_ref"].split("@v")[0] for rule in registered_rule_records(core, task_id)}
    return [record for base, record in latest.items() if base not in all_bases or base in active_bases]


def evidence_key(attribute: dict[str, Any]) -> str:
    """Two attributes asking the same tools the same questions are duplicates (registry invariant).

    Keyed on the whole set of routes rather than on one of them, so that two attributes reading one
    quantity from the same two databases are duplicates, while the one-database and the two-database
    form of a quantity are not: the second asks something the first never asks, and the merge that
    produces it has to be able to enter a registry the first one is already in.
    """
    if is_literature_bound(attribute):
        return sha256_hex({"name": (attribute.get("name") or "").strip().lower(), "unit": attribute.get("unit")})
    return sha256_hex(sorted(route_key(r) for r in evidence_routes(attribute)))
