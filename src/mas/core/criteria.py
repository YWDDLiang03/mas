"""Criterion Registry (C10): Attribute and Rule records, invariants, confirmed rule sets (design §4.10)."""

from __future__ import annotations

from typing import Any

from . import bound_support, review, vocab
from .canonical import canonical_text, sha256_hex
from .ids import slug
from .runtime import Core

MEASUREMENT_KINDS = ("quantitative", "ordinal", "categorical", "qualitative_determination")
DIRECTIONS = ("higher_better", "lower_better", "within_range", "target_value", "non_directional", "undetermined")
RULE_KINDS = ("hard_exclusion", "preference", "exploratory_consideration")
CUTOFF_BASES = ("measured_distribution", "regulatory_or_standard_reference", "source_stated_value",
                "expert_set", "task_constraint", "none_evidence_insufficient")
COMPARATORS = (">=", "<=", ">", "<", "==", "in", "not_in")
ON_STATE_POLICIES = ("unknown_no_penalty", "unknown_blocks_recommendation", "route_to_human", "exclude")
AGGREGATIONS = ("max", "min", "median", "consensus")
# Bases a value may be determined on. `predicted` is never mixed with the others inside one
# attribute: a predicted value standing in for a measurement is a surrogate inside a verdict
# (design §4.11), so a predicted quantity needs its own attribute and its own rule.
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
    route -- and `check_attribute` refuses an attribute that mixes the two kinds anyway."""
    return any(_as_route(route).get("capability") == "literature_retrieval" for route in evidence_routes(attribute))


def check_attribute(attr: dict[str, Any]) -> None:
    for field in ("name", "definition", "measurement_kind", "direction", "acceptable_value_sources"):
        if not attr.get(field):
            raise InvariantViolation("schema", f"attribute needs {field}")
    _choice("measurement_kind", attr["measurement_kind"], MEASUREMENT_KINDS)
    _choice("direction", attr["direction"], DIRECTIONS)
    _choice("aggregation", attr.get("aggregation", "consensus"), AGGREGATIONS)
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
        if "predicted" in bases and len(bases) > 1:
            # A predicted value standing in for a measurement is a surrogate inside a verdict
            # (design §4.11): a predicted quantity is its own attribute, with its own rule.
            raise InvariantViolation("schema", f"attribute {attr['name']!r} accepts predicted values alongside "
                                              f"{sorted(set(bases) - {'predicted'})}; give predicted values their own attribute")
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
    if literature and len(literature) != len(routes):
        # The two kinds take different code paths (a broker call per route against a record source;
        # a search, a read and checked extraction for literature), and pooling a claim read from a
        # paper with a claim from a database record under one aggregation needs a policy no one has set.
        raise InvariantViolation("schema", f"attribute {attr['name']!r} mixes a literature route with "
                                          f"{sorted({r['capability'] for r in routes if r['capability'] != 'literature_retrieval'})}; "
                                          f"give the literature quantity its own attribute")
    if len(literature) > 1:
        # One query per attribute is what the reading path builds (`evidence.literature_query`), so a
        # second template would never be used -- and an instruction the pipeline then undoes is worse
        # than no instruction (ADR-48).
        raise InvariantViolation("schema", f"attribute {attr['name']!r} declares {len(literature)} literature "
                                          f"routes; the reading path builds one query per attribute")


def check_rule(rule: dict[str, Any], attr: dict[str, Any]) -> None:
    _choice("rule_kind", rule.get("rule_kind"), RULE_KINDS)
    _choice("cutoff_basis", rule.get("cutoff_basis"), CUTOFF_BASES)
    for policy in ("on_missing", "on_inapplicable", "on_conflict"):
        _choice(policy, rule.get(policy, "unknown_blocks_recommendation"), ON_STATE_POLICIES)
        if rule.get(policy) == "exclude" and rule["rule_kind"] != "hard_exclusion":
            raise InvariantViolation("schema", f"{policy}: exclude is only for hard exclusions")
    cutoff = rule.get("cutoff")
    if rule.get("predicate_form", "threshold") not in ("threshold", "ordering", "range_membership", "categorical_membership",
                                                       "qualitative_judgment"):
        raise InvariantViolation("schema", f"unknown predicate_form {rule.get('predicate_form')!r}")
    if rule.get("predicate_form") == "ordering" and rule["rule_kind"] != "preference":
        raise InvariantViolation("schema", "an ordering rule ranks candidates, so it must be a preference")
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


def _versions(core: Core, task_id: str, kind: str, base_id: str) -> list[dict[str, Any]]:
    return [e.payload for e in core.journal.replay(task_id)
            if e.event_type == "criterion.version_proposed" and e.payload["kind"] == kind and e.payload["id"] == base_id]


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
    for payload in _versions(core, task_id, kind, base_id):
        if payload["version"] == int(version):
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


def confirm_rule_set(core: Core, task_id: str, *, by: dict[str, Any], ordering_method: dict[str, Any] | None = None,
                     coverage_floor: float = 1.0, constants: list[dict[str, Any]] | None = None,
                     allow_pending: bool = False, defer_capabilities: tuple[str, ...] = (),
                     defer_reason: str = "", preregistration_ref: str | None = None,
                     require_bound_support: bool = False) -> str:
    """Assemble `rules@v<n>` from the rule proposals that may enter it.

    A rule needing an expert enters only with an `hd_` approving it; a preference rule the
    trigger table lets proceed automatically enters with `confirmed_by: auto:trigger_table`.
    Proposals still awaiting a decision block the set unless `allow_pending` is given (for
    exploratory runs); they are then listed in `pending[]`, never silently dropped.

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

    A rule whose attribute a `collapse` merged away (`core/collapse.py`: several registrations of one
    quantity) does not enter at all and is listed in `collapsed_away[]`; a rule reading an attribute
    version that collapse wrote is listed in `machine_collapsed[]`. Either makes the set
    `exploratory` on the same grounds. Holding a merged-away rule out rather than demoting it is the
    point of the collapse: a demoted rule still costs a sweep pass and still counts in the hard-rule
    coverage denominator, and that denominator -- five quantities counted as ten -- is what the
    collapse exists to repair.
    """
    from . import adjudication, collapse as collapse_mod   # imported here: both read this module's records

    queue = review.items(core, [task_id])
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
    bounds_unsupported, bounds_withheld, decisions_not_carried = [], [], []
    for rule_ref in sorted(proposed.values()):
        rule = load(core, rule_ref, task_id)
        merged_away = superseded.get(rule["attribute_ref"])
        if merged_away is not None:
            collapsed_away.append({"rule_ref": rule_ref, "attribute_ref": rule["attribute_ref"],
                                   "merged_into": merged_away["surviving"]["attribute_ref_after"],
                                   "scored_by": merged_away["surviving"]["rule_ref_after"],
                                   "collapse_id": merged_away["collapse_id"]})
            continue
        adjudication_record = adjudicated.get(rule_ref)
        attr = load(core, rule["attribute_ref"], task_id)
        # WHY the *matching* route's capability is the one recorded: the deferral round-trips through
        # this field (`sr_stage` rebuilds `defer_capabilities` from it), so for an attribute with
        # several routes, recording another of its capabilities would quietly un-defer the rule on
        # the next confirmation.
        held_out = next((r["capability"] for r in evidence_routes(attr) if r["capability"] in defer_capabilities), None)
        if held_out:
            # A deferred rule carries its authority too, but it stays out of `machine_adjudicated`:
            # that list is what the set rests on, and a rule held out of this run rests on nothing.
            deferred.append({"rule_ref": rule_ref, "capability": held_out, "reason": defer_reason,
                             "authority": "machine_adjudication" if adjudication_record else None})
            continue
        # Every number this rule compares a candidate against, and what stands behind it
        # (`core/bound_support.py`, design §5.4). A bound whose support contradicts it never enters
        # the set: 90 citing a claim that states 30 is not a rule awaiting an opinion, it is a rule
        # whose own evidence says it is wrong.
        support = bound_support.validate(attr, rule, claims=_claims_for(core, task_id, attr, rule))
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
            bounds_withheld.append({"rule_ref": rule_ref, "attribute_ref": rule["attribute_ref"],
                                    "states": support["states"]})
            continue
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
        # WHY `disputed` is recorded on the entry: the trigger table admits a preference rule without an expert, and
        # it does that whether or not a critic finding about that rule is still open. Such a rule scores candidates
        # while also appearing in `pending[]`, which on its own reads as "did not enter the set". The entry says
        # which it is, so a snapshot cannot present a disputed rule as a settled one.
        entries.append({"attribute_ref": rule["attribute_ref"], "rule_ref": rule_ref, "rule_kind": rule["rule_kind"],
                        "confirmed_by": confirmed_by,
                        "authority": vocab.require("decision_authority", authority),
                        "acceptable_value_sources": attr["acceptable_value_sources"],
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
    if not entries:
        held = len(bounds_unsupported) + len(bounds_withheld)
        raise InvariantViolation("unconfirmed", "no rule version may enter the set yet"
                                 + (f"; {held} were held out over bound support" if held else ""))
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
                     if decisions_not_carried else [])
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
              "deferred": deferred, "bounds_unsupported": bounds_unsupported, "bounds_withheld": bounds_withheld,
              "decisions_not_carried": decisions_not_carried,
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
                                f"{len(collapsed_away)} collapsed away, {len(deferred)} deferred, "
                                f"{len(bounds_unsupported) + len(bounds_withheld)} held out over bound support)")
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


def registered_attributes(core: Core, task_id: str) -> list[dict[str, Any]]:
    """Latest version of every attribute proposed in a task."""
    latest: dict[str, dict[str, Any]] = {}
    for event in core.journal.replay(task_id):
        if event.event_type == "criterion.version_proposed" and event.payload["kind"] == "attribute":
            latest[event.payload["id"]] = core.artifacts.payload(event.payload["artifact_id"])
    return list(latest.values())


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
