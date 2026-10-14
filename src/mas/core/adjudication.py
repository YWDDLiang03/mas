"""Machine adjudication (C18, beside the Human Review Queue): resolving a queue item with no person.

A `machine_adjudication` (`adj_`) resolves one review queue item so a run can proceed when no expert
is available. It is not an expert decision and never becomes one. It carries `approval_kind:
agent_verdict`, never `human_scientific_approval`; it folds the queue item into its own state
(`machine_adjudicated`), not `decided`; and every rule it touches carries `authority:
machine_adjudication` into the rule set, its acceptance label and the board. `review.decide` is
untouched by this module: an `hd_` is still created only by a person confirming at a terminal.

Five routes: the first four chosen by *why* the item needed an expert (`criteria.needs_expert`), the
fifth by what the subject attribute's own definition states, for an item that needed no expert at all:

  task_constraint_restated       the cutoff restates a constraint the task context itself states,
                                 so the authority is the user's own task text and no judgement is
                                 added. Deterministic, no model call. Approves.
  no_authority_available         `cutoff_basis: expert_set` says in so many words that the number
                                 came from an expert's judgement. There is no expert, so there is
                                 no authority: the rule is demoted to an exploratory consideration
                                 and stops scoring. Never approves.
  irreversible_without_authority a hard exclusion deletes candidates from the result, which an
                                 agent must not do on its own authority. Demoting it to a
                                 preference keeps what it measured and removes the irreversibility.
  dispute_adjudicated            proposer and critic still disagree after a revision. The
                                 `adjudicator` role decides, blind to the proposer's rationale and
                                 on a third model family where the roster has one.
  definition_restated            the attribute's definition states a derived quantity -- an excess
                                 above a bound, a distance outside a band -- that the attribute
                                 never declared as a `value_transform`, so every cell carries the
                                 raw value its source returns under the derived quantity's name and
                                 direction. The authority is the definition already promoted into
                                 the store and the claims it cites, exactly as route 1's authority
                                 is the user's own task text: the route adds no judgement and only
                                 writes structurally what that text already states. It refuses a
                                 definition it can read two *different* quantities out of, and reads
                                 several readings as one only where they reconcile exactly: the
                                 manuscript's lipophilicity definition states a 2 to 4 band and then
                                 spells out each side for the reader ("the shortfall below 2 ... and
                                 the excess above 4"), which parses as three readings of the one
                                 band. Two one-sided bounds with no band of their own stay refused --
                                 no text says they are the two ends of one band. Deterministic, no
                                 model call. Changes no rule kind and no cutoff.

WHY a demotion is a new rule version rather than a field on the entry: the assessor reads
`rule["rule_kind"]` from the rule record it loads (`assessor.assess_cell`, `roll_up`), so a demotion
recorded only on the rule-set entry would leave a hard exclusion still excluding candidates while
every surface said it had been demoted.

WHY route 5 writes two versions: the sweep loads the attribute the *rule* names (`controller` reads
`entries[].attribute_ref`, which `confirm_rule_set` copies from `rule["attribute_ref"]`), so a new
attribute version nothing points at would leave every cell reading the raw value while the registry
said the quantity had been declared. The rule version it writes changes that one field and nothing
else: same kind, same predicate form, same cutoff, same basis.
"""

from __future__ import annotations

import json
import re
from typing import Any

from . import bound_support, criteria, ledger, review, vocab
from .clock import utc_now
from .ids import new_id
from .journal import actor as make_actor
from .models import ModelError, ModelRequest, ModelRoster, call_role
from .runtime import Core
from . import task as task_mod

# One line per route, numbered as the module docstring numbers them: what the route does to the
# criterion. (`route_of` tries them in another order, most conservative outcome first.)
ROUTE_EFFECT = {
    "task_constraint_restated": "approve the rule unchanged, citing the task-context field it restates",
    "no_authority_available": "demote the rule to an exploratory consideration, so it stops scoring",
    "irreversible_without_authority": "demote the hard exclusion to a preference, so no candidate is removed",
    "dispute_adjudicated": "put the dispute to the adjudicator, blind to the proposer's rationale",
    "definition_restated": "declare the transformation the attribute's own definition states, so the cell "
                           "carries the quantity it names",
}
ROUTES = tuple(ROUTE_EFFECT)
VERDICTS = ("uphold_proposal", "uphold_objection", "revise", "cannot_resolve")
# The rule kind each resolution leaves behind; `approve` and `declare_value_transform` leave the
# kind the proposal had, the second because it changes the attribute and not the rule.
RESOLUTIONS = {"approve": None, "demote_to_preference": "preference",
               "demote_to_exploratory_consideration": "exploratory_consideration",
               "declare_value_transform": None}

# The deterministic routes add no judgement of their own, so their actor is the software, not an agent.
MACHINE = make_actor("system", "machine-adjudication", "adjudicator")

ADJUDICATOR_SYSTEM = (
    "You adjudicate an open disagreement between a proposer and a blind critic about one screening "
    "criterion. You see the criterion and the critic's findings, not the proposer's reasoning, and you "
    "work only from the criterion's own text and the claims it cites. Answer with one verdict: "
    "uphold_proposal (the findings do not stand against the cited claims), uphold_objection (a finding "
    "stands and the criterion should not score as proposed), revise (the dispute is settled by a "
    "specific change to the rule, which you give in full), or cannot_resolve (the evidence before you "
    "does not settle it). Cite the claim ids your reasoning rests on; cite no claim that is not listed. "
    "A revision may only weaken a rule, never strengthen it: you may not make a rule a hard_exclusion, "
    "and you may not introduce a cutoff value no cited claim states. Never name a specific candidate "
    "compound."
)

ADJUDICATION_SCHEMA = {
    "type": "object", "required": ["verdict", "reasoning", "cited_claim_ids"],
    "properties": {"verdict": {"type": "string", "enum": list(VERDICTS)},
                   "reasoning": {"type": "string"},
                   "cited_claim_ids": {"type": "array", "items": {"type": "string"}},
                   "revised_rule": {"type": "object"}},
}

_WORDS = re.compile(r"[a-z0-9.]+")
_STOP = {"the", "of", "a", "an", "in", "to", "and", "or", "for", "with", "by", "at", "on", "as", "is",
         "be", "must", "should", "only", "any", "all", "its", "it", "that", "this", "are", "was"}


class AdjudicationError(RuntimeError):
    """An item that cannot be adjudicated at all: not a rule version, or no adjudicator to call."""


def _words(text: str) -> set[str]:
    return {w.strip(".") for w in _WORDS.findall((text or "").lower())} - _STOP - {""}


# WHY these two come from `bound_support`: "the number this text states" and "the cited claim that
# states this bound" are one definition in the codebase now, so an audit, a machine adjudication and
# a proposal validator cannot disagree about what a bound traces to (§9: one shared support helper).
_numbers = bound_support.numbers
_claims_stating = bound_support.claims_stating


# --- route 1: does the task text itself state this cutoff? --------------------------------------

def restated_constraint(rule: dict[str, Any], attribute: dict[str, Any],
                        context: dict[str, Any]) -> dict[str, Any] | None:
    """The task constraint this rule restates, or None when the task text does not state it.

    A rule rests on the task's own authority only when it was built *from* a constraint by an
    adapter template, which records `derived_from {task_context, field}` naming the field -- checked
    against the constraints the task context actually holds (`constraints[] {text, kind, hardness,
    provenance}`). Nothing a proposer writes can establish this, which is the point.

    A hard exclusion must restate a *hard* constraint, and a numeric cutoff must also appear in the
    constraint's text. A number the task never states is a judgement about where to draw a line,
    which is exactly what this route may not supply.
    """
    constraints = context.get("constraints") or []
    if not constraints:
        return None
    cutoff = rule.get("cutoff") or {}
    value = cutoff.get("value")
    wanted_number = (_numbers(str(value)) if isinstance(value, (int, float)) and not isinstance(value, bool)
                     else set())
    task_ref = f"{context['task_context_id']}@v{context['version']}"
    derived = (attribute.get("derived_from") or {}).get("field")

    def supported(index: int, constraint: dict[str, Any], match: str) -> dict[str, Any] | None:
        # A soft constraint cannot authorise deleting candidates: a hard exclusion restates a hard one.
        if rule["rule_kind"] == "hard_exclusion" and constraint.get("hardness") != "hard":
            return None
        if wanted_number and not (wanted_number <= _numbers(constraint.get("text", ""))):
            return None
        return {"task_context_ref": task_ref, "field": f"constraints[{index}]", "match": match,
                "constraint_text": constraint.get("text"), "hardness": constraint.get("hardness"),
                "provenance": constraint.get("provenance")}

    for index, constraint in enumerate(constraints):
        if derived and derived == f"constraints[{index}]":
            found = supported(index, constraint, "derived_from_task_field")
            if found:
                return found
    # WHY there is no wording path here: matching a constraint's words against the attribute's own
    # name and definition would let a proposal authorise itself by quoting the task back at the
    # reader -- and this is the only route that approves rather than demotes. `derived_from.field`
    # is a link an adapter template wrote when it built the criterion *from* the constraint, which
    # no proposer can forge. A criterion that genuinely restates the task but carries no such link
    # is demoted instead of approved: the conservative failure, which is the right one here.
    return None


# --- route 5: does the attribute's definition itself state a derived quantity? ------------------

# One form per registered transform (`criteria.VALUE_TRANSFORMS`), each capturing the bound(s) that
# kind needs. Every form demands the noun that *names* a derived quantity -- "excess", "shortfall",
# "distance ... outside" -- and not merely a direction word, because "molecular weight above 500
# g/mol" names a threshold while "the excess above 500 g/mol" names a quantity, and only the second
# says the source's raw value is not what the attribute is about.
#
# One reading, or none: `[^.;]` keeps a match inside one sentence, and `[^.;,\d]` makes a one-sided
# bound the first number after the direction word *in the same clause*, so "the excess above the
# stated upper bound, with a tolerance of 10 g/mol" states no bound this can read rather than reading
# the tolerance as the bound. A band is recognised by its structure ("<low> to <high>") instead,
# which is why it may look past a comma.
_QUANTITY_FORMS = (
    ("distance_outside_band", ("low", "high"),
     re.compile(r"(?:distance|deviation|departure|amount|extent)[^.;]{0,80}?outside[^.;]{0,40}?"
                r"(-?\d+(?:\.\d+)?)\s*(?:to|and)\s+(-?\d+(?:\.\d+)?)")),
    ("excess_above", ("bound",),
     re.compile(r"(?:excess|exceedance|overshoot)[^.;]{0,40}?(?:above|over|beyond|exceeding|of)"
                r"[^.;,\d]{0,30}(-?\d+(?:\.\d+)?)")),
    ("shortfall_below", ("bound",),
     re.compile(r"(?:shortfall|deficit|shortage)[^.;]{0,40}?(?:below|under|beneath|short of|of)"
                r"[^.;,\d]{0,30}(-?\d+(?:\.\d+)?)")),
)
# A band is written "2-4" as often as "2 to 4", and `_NUMBER` reads the hyphen form as 2 and -4.
_RANGE_DASH = re.compile(r"(?<=\d)\s*[‐-―−-]\s*(?=\d)")


def _as_number(text: str) -> float | int:
    return float(text) if "." in text else int(text)


def _one_quantity_decomposed(found: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The single band that every one of these readings is a reading of, or None.

    WHY several readings are not always several quantities: the lipophilicity attribute of the
    manuscript task states its band once and then decomposes it for the reader -- "outside the band
    of approximately 2 to 4 ...: zero inside the band, the shortfall below 2 for a more polar
    molecule, and the excess above 4 for a more lipophilic one" -- which the forms read as three
    readings whose bounds are the same two numbers: the band's `low` IS the shortfall's bound and
    its `high` IS the excess's. That is one quantity written out twice, not the case the refusal is
    for, which is readings that disagree about what every cell would then carry.

    Exactly, and only inward: a one-sided bound that is not the band's own end on that side stays
    refused, because which number the writer meant is then precisely what is unclear, and so do two
    one-sided readings with no band -- a band assembled out of them would be this module's
    invention rather than the definition's statement.
    """
    bands = [reading for reading in found if reading["kind"] == "distance_outside_band"]
    if len(bands) != 1:
        return None
    band = bands[0]
    side_of = {"shortfall_below": band["low"], "excess_above": band["high"]}
    for reading in found:
        if reading is not band and reading.get("bound") != side_of.get(reading["kind"]):
            return None
    return band


def stated_quantity(definition: str) -> dict[str, Any] | None:
    """The transform kind and bound(s) an attribute's definition states, or None.

    Conservative on purpose, in both directions. Only the three kinds `criteria.VALUE_TRANSFORMS`
    registers are recognised, and only where the definition states the bounds numerically: a bound
    inside a transformation is read on every cell the rule scores, so a wrong one silently changes
    what the board measures. Anything that does not resolve to exactly one quantity -- no bound, a
    bound this cannot map to a registered kind, two readings that disagree about the quantity or
    about a bound of it -- returns None, which leaves the item on the queue for a person instead of
    guessing. Several readings are one quantity only where they reconcile exactly, which is a band
    the definition also spells out one side at a time (`_one_quantity_decomposed`).
    """
    text = _RANGE_DASH.sub(" to ", (definition or "").lower())
    found: list[dict[str, Any]] = []
    for kind, parameters, pattern in _QUANTITY_FORMS:
        for match in pattern.finditer(text):
            reading = {"kind": kind, **dict(zip(parameters, (_as_number(g) for g in match.groups())))}
            if reading not in found:
                found.append(reading)
    reading = found[0] if len(found) == 1 else _one_quantity_decomposed(found)
    if reading is None:
        return None
    # A band whose stated low is not below its stated high is a definition this cannot read, not one
    # to repair by swapping the bounds: which end the writer meant is exactly what is unclear.
    if reading["kind"] == "distance_outside_band" and reading["low"] >= reading["high"]:
        return None
    return reading


def _quantity_in_words(transform: dict[str, Any]) -> str:
    if transform["kind"] == "distance_outside_band":
        return f"the distance outside the band {transform['low']} to {transform['high']}"
    bound = transform["bound"]
    return f"the excess above {bound}" if transform["kind"] == "excess_above" else f"the shortfall below {bound}"


def _restatable(attribute: dict[str, Any]) -> dict[str, Any] | None:
    """The reading of this attribute's definition there would be something to trace, or None.

    An attribute that already declares a transformation has nothing to restate, and one that is not
    quantitative may not carry a transformation at all (`check_attribute`).
    """
    if attribute.get("value_transform") or attribute.get("measurement_kind") != "quantitative":
        return None
    return stated_quantity(attribute.get("definition", ""))


def restated_definition(attribute: dict[str, Any], claims: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The transformation this attribute's own definition already describes, or None.

    Returns None rather than a partial reading whenever the definition does not state a transform
    this module can map to a registered kind, or when a bound it states is not traceable to a claim
    the attribute already cites. An untraceable bound inside a transformation is the arbitrary cutoff
    the rule registry refuses elsewhere, and `check_value_transform` says so in the same words.
    """
    reading = _restatable(attribute)
    if reading is None:
        return None
    traces, refs = {}, []
    for parameter in criteria.VALUE_TRANSFORMS[reading["kind"]]:
        stating = _claims_stating(reading[parameter], attribute.get("unit"), claims)
        if not stating:
            return None
        traces[parameter] = stating
        refs.extend(trace["claim_id"] for trace in stating)
    return {"field": "definition", "match": "definition_states_a_derived_quantity",
            "definition_text": attribute.get("definition"), "quantity_text": _quantity_in_words(reading),
            "bound_traces": traces, "claim_ids": sorted(set(refs)),
            # `source_stated_value` and nothing else: the bound is traceable to a cited claim or this
            # route does not fire, so the basis the transform carries is the one the trace supports.
            "value_transform": dict(reading, basis="source_stated_value", source_refs=sorted(set(refs)))}


def _cited_claims(core: Core, task_id: str, attribute: dict[str, Any], item: dict[str, Any]) -> list[dict[str, Any]]:
    """The admitted claims an attribute cites, wherever the run that enumerated them recorded them.

    A promoted criterion's claims were enumerated in a derivation run's own stream, and an item
    raised outside a dispute names no run, so the run streams are read when the bundle does not name
    one. Nothing is read at all unless the definition states a bound there would be something to
    trace, which is what keeps `route_preview` cheap for the four routes that cite no claim.
    """
    cited = set(attribute.get("supporting_claim_refs") or [])
    if not cited or _restatable(attribute) is None:
        return []
    bundle = item.get("inspection_bundle") or {}
    streams = [task_id] + ([bundle["derivation_run"]] if bundle.get("derivation_run")
                           else core.journal.streams("run_"))
    return [c for c in ledger.claims(core, streams) if c["claim_id"] in cited]


# --- route selection ----------------------------------------------------------------------------

def _is_dispute(item: dict[str, Any]) -> bool:
    return bool((item.get("inspection_bundle") or {}).get("open_critic_findings"))


def route_of(rule: dict[str, Any], attribute: dict[str, Any], context: dict[str, Any],
             item: dict[str, Any], claims: list[dict[str, Any]] | None = None) -> tuple[str, dict[str, Any] | None]:
    """The route that resolves this item, and what it cites (routes 1 and 5 cite something).

    Order matters where a rule qualifies for more than one route, and it runs from the most
    conservative outcome to the least: an `expert_set` hard exclusion is demoted to a
    non-scoring exploratory consideration rather than to a scoring preference, because the
    authority its cutoff claims (an expert's judgement) is the one thing missing.

    Route 5 is tried last of the five and only ahead of the `no_authority_available` fallback. It is
    the one route that leaves a rule scoring without an expert having said anything, so where a rule
    also claims an authority it does not have -- an `expert_set` cutoff, a task constraint the task
    text does not state, a hard exclusion -- the route that answers that claim wins and route 5 never
    sees the item. What is left for it is the case it is for: a rule nothing is wrong with, whose
    attribute measures something other than what it says it measures.
    """
    if _is_dispute(item):
        return "dispute_adjudicated", None
    if rule["cutoff_basis"] == "task_constraint":
        restated = restated_constraint(rule, attribute, context)
        if restated is not None:
            return "task_constraint_restated", restated
        # The task text does not state it, so the claimed authority is not there. A hard exclusion
        # still has an irreversible effect to remove (route 3); anything else has only a cutoff
        # nothing supports, which is route 2's case under another name.
        return ("irreversible_without_authority" if rule["rule_kind"] == "hard_exclusion"
                else "no_authority_available"), None
    if rule["cutoff_basis"] == "expert_set":
        return "no_authority_available", None
    if rule["rule_kind"] == "hard_exclusion":
        return "irreversible_without_authority", None
    restated = restated_definition(attribute, claims or [])
    if restated is not None:
        return "definition_restated", restated
    return "no_authority_available", None


def route_preview(core: Core, item: dict[str, Any]) -> dict[str, Any]:
    """Which route would resolve this item, without writing anything. Never raises."""
    unknown = {"route": None, "route_label": None, "would": None,
               "why_not": "only an open rule-version item is resolvable without a person"}
    if item["subject"]["kind"] != "rule_version" or item["state"] not in ("open", "in_review"):
        return unknown
    try:
        task_id = item["stream_id"]
        context = task_mod.get(core, task_id)
        rule = criteria.load(core, item["subject"]["id"], task_id)
        attribute = criteria.load(core, rule["attribute_ref"], task_id)
        claims = _cited_claims(core, task_id, attribute, item)
    except (KeyError, StopIteration):
        return dict(unknown, why_not="the rule or the task context this item names is not in this store root")
    route, _restated = route_of(rule, attribute, context, item, claims)
    return {"route": route, "route_label": vocab.label("adjudication_route", route), "would": ROUTE_EFFECT[route],
            "why_not": None}


# --- demotion -------------------------------------------------------------------------------------

def _demoted(rule: dict[str, Any], rule_kind: str) -> dict[str, Any]:
    """The same rule at a weaker kind, with the fields `check_rule` ties to the old kind brought along.

    Two of them would otherwise fail the registry's own invariants: `exclude` is a state policy only a
    hard exclusion may hold, and an `ordering` predicate is how a rule moves candidates up and down a
    board, so it is valid only on a preference.
    """
    out = dict(rule, rule_kind=rule_kind)
    if rule_kind != "hard_exclusion":
        for policy in ("on_missing", "on_inapplicable", "on_conflict"):
            if out.get(policy) == "exclude":
                out[policy] = "unknown_blocks_recommendation"
    if rule_kind != "preference" and out.get("predicate_form") == "ordering":
        out["predicate_form"] = "qualitative_judgment"
    return out


def _record_rule_version(core: Core, task_id: str, rule_ref: str, rule: dict[str, Any], *,
                         by: dict[str, Any], adjudication_id: str, summary: str) -> str:
    """Record a new version of a rule, outside `criteria.propose` so no new review item is raised.

    `criteria.propose` raises a confirmation item for anything the trigger table gates, and an
    `expert_set` cutoff is still `expert_set` after a demotion -- re-proposing through it would put
    the item straight back on the queue this adjudication just took it off.
    """
    base_id = rule_ref.split("@v")[0]
    attribute = criteria.load(core, rule["attribute_ref"], task_id)
    criteria.check_rule(rule, attribute)
    version = len([e for e in core.journal.replay(task_id)
                   if e.event_type == "criterion.version_proposed" and e.payload["kind"] == "rule"
                   and e.payload["id"] == base_id]) + 1
    record = dict(rule, rule_id=base_id, version=version, status="proposed", supersedes=rule_ref,
                  adjudicated_by=adjudication_id, approval_kind="agent_verdict")
    artifact_id = core.artifacts.put("rule", record)
    core.journal.append(task_id, "criterion.version_proposed", actor=by, ids={"task_id": task_id},
                        payload={"kind": "rule", "id": base_id, "version": version, "artifact_id": artifact_id,
                                 "adjudicated_by": adjudication_id},
                        artifact_links=[{"kind": "rule", "id": artifact_id, "version": version}],
                        summary=summary)
    return f"{base_id}@v{version}"


def _record_attribute_version(core: Core, task_id: str, attribute_ref: str, attribute: dict[str, Any], *,
                              by: dict[str, Any], adjudication_id: str, summary: str) -> str:
    """Record a new version of an attribute, outside `criteria.propose` for the same reason as above.

    `propose` writes an attribute and a rule together and then consults the trigger table about the
    rule, so sending one edited attribute through it would propose the rule a second time and raise a
    fresh item on it -- the item this adjudication is resolving.
    """
    base_id = attribute_ref.split("@v")[0]
    criteria.check_attribute(attribute)
    version = len([e for e in core.journal.replay(task_id)
                   if e.event_type == "criterion.version_proposed" and e.payload["kind"] == "attribute"
                   and e.payload["id"] == base_id]) + 1
    record = dict(attribute, attribute_id=base_id, version=version, status="proposed", supersedes=attribute_ref,
                  adjudicated_by=adjudication_id, approval_kind="agent_verdict")
    artifact_id = core.artifacts.put("attribute", record)
    core.journal.append(task_id, "criterion.version_proposed", actor=by, ids={"task_id": task_id},
                        payload={"kind": "attribute", "id": base_id, "version": version, "artifact_id": artifact_id,
                                 "adjudicated_by": adjudication_id},
                        artifact_links=[{"kind": "attribute", "id": artifact_id, "version": version}],
                        summary=summary)
    return f"{base_id}@v{version}"


# --- route 4: the adjudicator ----------------------------------------------------------------------

def independence(roster: ModelRoster) -> dict[str, Any]:
    """Which adapter the adjudicator runs on, and the truth about how independent that is.

    The roster may bind every role to one adapter; the block then says so rather than claiming an
    independence the set-up does not have (ADR U-05). The precedent is `derivation_run`'s
    `independence` block, which records the proposer and critic families and whether the critic saw
    the proposer's rationale.
    """
    families = {}
    for role in ("proposer", "critic"):
        try:
            families[role] = roster.adapter(role).record.provider_family
        except ModelError:
            families[role] = None
    taken = {f for f in families.values() if f}
    bound = roster.roles.get("adjudicator")
    order = ([bound] if bound else []) + [n for n in sorted(roster.adapters) if n != bound]
    chosen = next((n for n in order if roster.adapters[n].record.provider_family not in taken), bound)
    if chosen is None:
        raise AdjudicationError("no adapter is bound to the adjudicator role, so a dispute cannot be adjudicated")
    family = roster.adapters[chosen].record.provider_family
    return {"adjudicator_adapter_id": chosen, "adjudicator_family": family,
            "adjudicator_model_id": roster.adapters[chosen].record.model_id,
            "proposer_family": families["proposer"], "critic_family": families["critic"],
            "bound_adapter_id": bound, "roster_offered_a_third_family": family not in taken,
            "distinct_from_proposer": family != families["proposer"],
            "distinct_from_critic": family != families["critic"],
            "adjudicator_saw_proposer_rationale": False}


def _dispute_view(attribute: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    """The disputed criterion as the blind critic saw it (`derivation_stages._view(blind=True)`).

    A registered record holds more than a pool item does, and two of the extra fields are the
    proposer speaking: `rationale`, which `_view` strips, and `expected_change`, which it withholds
    and which the registry stores *inside* the rule. Reducing both records to the proposal fields
    first is what makes the stripping reach it -- without that the adjudicator read the proposer's
    stated expectation in every dispute while the block said it was blind.
    """
    from .derivation import ATTRIBUTE_FIELDS, RULE_FIELDS
    from .derivation_stages import _view

    return _view({"item": {"attribute": {k: v for k, v in attribute.items() if k in ATTRIBUTE_FIELDS},
                           "rule": {k: v for k, v in rule.items() if k in RULE_FIELDS},
                           "supporting_claim_ids": attribute.get("supporting_claim_refs") or [],
                           "falsification_test": rule.get("falsification_test"),
                           "expected_change": rule.get("expected_change")}}, 0, blind=True)


def cited_claims(core: Core, task_id: str, item: dict[str, Any], attribute: dict[str, Any]) -> list[dict[str, Any]]:
    """The admitted claims this criterion cites, from the task stream and the run the item names.

    WHY beside `_cited_claims`: that one reads nothing unless the definition states a bound there
    would be something to trace, which is what keeps `route_preview` cheap for the four routes that
    cite no claim. A revision and a dispute need the claims whatever the definition says.
    """
    cited = set(attribute.get("supporting_claim_refs") or [])
    if not cited:
        return []
    bundle = item.get("inspection_bundle") or {}
    streams = [task_id] + ([bundle["derivation_run"]] if bundle.get("derivation_run") else [])
    return [c for c in ledger.claims(core, streams) if c["claim_id"] in cited]


def _adjudicate_dispute(core: Core, task_id: str, item: dict[str, Any], rule: dict[str, Any],
                        attribute: dict[str, Any], *, roster: ModelRoster, budget: Any = None) -> dict[str, Any]:
    from .derivation import _claims_block

    bundle = item.get("inspection_bundle") or {}
    marker = independence(roster)
    claims = cited_claims(core, task_id, item, attribute)
    view = _dispute_view(attribute, rule)
    content = (f"Objective: {task_mod.get(core, task_id)['objective_text']}\n\n"
               f"Criterion under dispute:\n{json.dumps(view, ensure_ascii=False, indent=1)}\n\n"
               f"The critic's open findings:\n"
               f"{json.dumps(bundle['open_critic_findings'], ensure_ascii=False, indent=1)}\n\n"
               f"Cited claims ({len(claims)}):\n{_claims_block(claims)}")
    # The adjudicator must not run on the adapter the proposer or the critic used where the roster
    # offers another, so the call goes through a roster whose adjudicator role is the chosen adapter.
    bench = ModelRoster(roster.adapters, {**roster.roles, "adjudicator": marker["adjudicator_adapter_id"]})
    response = call_role(core, bench, task_id, ModelRequest(
        role="adjudicator", system=ADJUDICATOR_SYSTEM, messages=[{"role": "user", "content": content}],
        response_schema=ADJUDICATION_SCHEMA, max_tokens=4000,
        metadata={"question": "adjudicate a proposer/critic dispute"}), ids={"task_id": task_id}, budget=budget)
    answer = response.data
    verdict = vocab.require("adjudication_verdict", answer["verdict"])
    offered = {c["claim_id"] for c in claims}
    return {"verdict": verdict, "reasoning": answer["reasoning"][:2000],
            "cited_claim_ids": sorted(set(answer.get("cited_claim_ids") or []) & offered),
            "uncited_ids_refused": sorted(set(answer.get("cited_claim_ids") or []) - offered),
            "revised_rule": answer.get("revised_rule") or None, "independence": marker,
            "request_id": response.request_id}


def _apply_revision(rule: dict[str, Any], revision: dict[str, Any], attribute: dict[str, Any], *,
                    claims: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """The revised rule, or the original with the reason the revision was refused, and the diff of both.

    The whole revised object is revalidated: the fields a revision may set at all, how each change
    relates to the original (`bound_support.revision_relation`), the registry invariants, the support
    for every number the revised rule compares a candidate against, and the authority that object
    then needs. Measured on this checkout: `>= 30` -> `>= 90` was applied with no refusal, having
    passed a schema check and a rule-kind check that neither establish support for 90 nor say which
    way the change points (R7).

    What may be applied:
      * weaker or neutral, and still supported and no more demanding of authority -- applied;
      * stronger in rule kind or in an on-state policy -- refused, because an agent that could
        revise a preference into a hard exclusion would have acquired through the dispute route
        exactly the authority routes 2 and 3 deny it;
      * stronger in the cutoff -- applied only where the cited claims state the number it moves to
        and the authority requirement does not grow, which is the one sense in which a tightening
        does not bypass the support and authority checks (§6 F4);
      * not decidable as either -- refused, and the record says an explicit review is required
        rather than guessing: a comparator that reverses, a unit the rule did not have, a relabelled
        cutoff basis and a changed predicate are not two settings of one requirement.
    """
    unknown = sorted(set(revision) - set(bound_support.REVISABLE_FIELDS))
    revised = dict(rule, **{k: revision[k] for k in bound_support.REVISABLE_FIELDS if k in revision})
    relation = bound_support.revision_relation(rule, revised)
    record = {"diff": relation["diff"], "relation": relation["relation"], "changes": relation["changes"],
              "fields_refused": unknown, "requires_explicit_review": False, "refused": ""}

    def refuse(reason: str, *, review_required: bool = False) -> tuple[dict[str, Any], str, dict[str, Any]]:
        return rule, reason, dict(record, refused=reason, requires_explicit_review=review_required)

    if unknown:
        return refuse(f"a revision may not set {', '.join(unknown)}; those fields are not this rule's to change",
                      review_required=True)
    if revision.get("rule_kind") == "hard_exclusion":
        return refuse("a revision may not make a rule a hard exclusion")
    if revised.get("cutoff_basis") == "expert_set":
        return refuse("a revision may not claim an expert set the cutoff")
    stronger = [c for c in relation["changes"] if c["relation"] == "stronger"]
    undecidable = [c for c in relation["changes"] if c["relation"] == "not_decidable"]
    if undecidable:
        return refuse("the revision is neither weaker nor stronger than the rule it revises, so a person has to "
                      "judge it: " + "; ".join(c["why"] for c in undecidable), review_required=True)
    if any(c["field"] != "cutoff" for c in stronger):
        return refuse("a revision may only weaken a rule: "
                      + "; ".join(c["why"] for c in stronger if c["field"] != "cutoff"))
    try:
        criteria.check_rule(revised, attribute)
    except criteria.InvariantViolation as violation:
        return refuse(f"the revised rule failed a registry invariant: {violation}")
    support = bound_support.validate(attribute, revised, claims=claims)
    record["bound_support"] = support["states"]
    if support["blocking"]:
        return refuse("the revised rule's bound is not supported by the claims the criterion cites: "
                      + "; ".join(bound_support.messages(support)))
    if stronger and not any(bound["trace"] for bound in support["bounds"]
                            if bound["parameter_path"] == "rule.cutoff.value"):
        return refuse("a revision may tighten a cutoff only to a number the cited claims state, and none of them "
                      "states this one: " + "; ".join(c["why"] for c in stronger))
    owed_before = {r["reason"] for r in criteria.authority_requirements(rule, attribute)}
    owed_after = criteria.authority_requirements(revised, attribute, support=support)
    added = [r for r in owed_after if r["reason"] not in owed_before]
    if added:
        return refuse("the revised rule would need an authority the rule it revises does not: "
                      + "; ".join(r["detail"] for r in added), review_required=True)
    return revised, "", record


# --- adjudicating -----------------------------------------------------------------------------------

def adjudicate(core: Core, item: dict[str, Any], *, roster: ModelRoster | None = None,
               budget: Any = None) -> dict[str, Any]:
    """Resolve one open review queue item without a person, and record how.

    Raises `AdjudicationError` when the item is not resolvable this way at all (not a rule version,
    already resolved, or a dispute with no adjudicator to call). Never creates an `hd_`.
    """
    if item["subject"]["kind"] != "rule_version":
        raise AdjudicationError(f"{item['item_id']} is a {item['subject']['kind']} item; only a rule version "
                                f"can be resolved without a person")
    if item["state"] not in ("open", "in_review"):
        raise AdjudicationError(f"{item['item_id']} is {item['state']}")
    task_id = item["stream_id"]
    context = task_mod.get(core, task_id)
    rule_ref = item["subject"]["id"]
    rule = criteria.load(core, rule_ref, task_id)
    attribute = criteria.load(core, rule["attribute_ref"], task_id)
    route, restated = route_of(rule, attribute, context, item, _cited_claims(core, task_id, attribute, item))
    adjudication_id = new_id("adj")
    by, dispute, revision = MACHINE, None, None

    if route == "dispute_adjudicated":
        if roster is None:
            raise AdjudicationError(f"{item['item_id']} is a proposer/critic dispute and needs the adjudicator "
                                    f"role; no model roster was given")
        dispute = _adjudicate_dispute(core, task_id, item, rule, attribute, roster=roster, budget=budget)
        by = make_actor("agent", f"adjudicator:{dispute['independence']['adjudicator_adapter_id']}", "adjudicator",
                        model_family=dispute["independence"]["adjudicator_family"],
                        version=dispute["independence"]["adjudicator_model_id"])
        if dispute["verdict"] == "uphold_proposal":
            resolution, reason = "approve", "the critic's findings do not stand against the claims the criterion cites"
        elif dispute["verdict"] == "revise":
            revised, refused, revision = _apply_revision(rule, dispute["revised_rule"] or {}, attribute,
                                                         claims=cited_claims(core, task_id, item, attribute))
            if refused:
                resolution, reason = "demote_to_exploratory_consideration", refused
            else:
                rule, resolution = revised, "approve"
                reason = ("the dispute was settled by a change to the rule: "
                          + "; ".join(c["why"] for c in revision["changes"]))
        elif dispute["verdict"] == "uphold_objection":
            resolution = "demote_to_exploratory_consideration"
            reason = "the critic's finding stands, so the criterion does not score as proposed"
        else:
            resolution = "demote_to_exploratory_consideration"
            reason = "the adjudicator could not settle the dispute on the evidence before it"
    elif route == "task_constraint_restated":
        resolution = "approve"
        reason = (f"the cutoff restates {restated['field']} of {restated['task_context_ref']} "
                  f"({restated['constraint_text']!r}), which the task context states itself")
    elif route == "definition_restated":
        resolution = "declare_value_transform"
        reason = (f"the attribute's definition states {restated['quantity_text']} and the attribute declared no "
                  f"transformation, so every cell carried the raw value its source returns; the transformation is "
                  f"declared as the definition already describes it, on a bound claims "
                  f"{', '.join(restated['claim_ids'])} state, and the definition itself is unchanged")
    elif route == "irreversible_without_authority":
        resolution = "demote_to_preference"
        reason = ("a hard exclusion deletes candidates from the result; an agent may not do that on its own "
                  "authority, so the rule keeps measuring and stops excluding")
    else:
        resolution = "demote_to_exploratory_consideration"
        reason = (f"cutoff_basis {rule['cutoff_basis']} makes the cutoff an expert's judgement, and no expert "
                  f"has given one")

    # WHY the routes compose: a disputed proposal may itself be a hard exclusion or an expert-set
    # cutoff, and `criteria.propose` raises the dispute item *instead of* the confirmation item for
    # it. Approving on the adjudicator's verdict alone would hand the dispute route exactly the
    # authority routes 2 and 3 withhold, so an approved rule is still put through them.
    if resolution == "approve" and rule["cutoff_basis"] == "expert_set":
        resolution = "demote_to_exploratory_consideration"
        reason += "; its cutoff is still expert_set, which no agent can supply"
    elif resolution == "approve" and rule["rule_kind"] == "hard_exclusion" \
            and restated_constraint(rule, attribute, context) is None:
        resolution = "demote_to_preference"
        reason += "; it is still a hard exclusion the task text does not state, so it stops excluding"

    kind = RESOLUTIONS[resolution] or rule["rule_kind"]
    rewritten = _demoted(rule, kind)
    attribute_ref_after, edits = rule["attribute_ref"], []
    if resolution == "declare_value_transform":
        declared = restated["value_transform"]
        attribute_ref_after = _record_attribute_version(
            core, task_id, rule["attribute_ref"], dict(attribute, value_transform=declared), by=by,
            adjudication_id=adjudication_id,
            summary=f"{rule['attribute_ref']} declares {declared['kind']} as its definition states it "
                    f"({adjudication_id})")
        # The definition is this route's whole authority, so it is the one field the edit may not
        # touch: a rewritten definition would be the agent saying what the quantity is.
        edits = [{"target": rule["attribute_ref"], "target_after": attribute_ref_after,
                  "field": "value_transform", "from": None, "to": declared}]
        rewritten = dict(rewritten, attribute_ref=attribute_ref_after)
    changed = rewritten != criteria.load(core, rule_ref, task_id)
    rule_ref_after = rule_ref if not changed else _record_rule_version(
        core, task_id, rule_ref, rewritten, by=by, adjudication_id=adjudication_id,
        summary=(f"{rule_ref} reads {attribute_ref_after} after {adjudication_id} ({route})"
                 if edits else f"{rule_ref} {rule['rule_kind']} -> {kind} by {adjudication_id} ({route})"))
    scores = rewritten["rule_kind"] == "preference"

    record = {
        "adjudication_id": adjudication_id, "queue_item_ref": item["item_id"], "subject": item["subject"],
        "task_id": task_id, "task_context_id@v": f"{task_id}@v{context['version']}",
        "route": vocab.require("adjudication_route", route), "resolution": resolution, "basis": route,
        "reason_text": reason, "authority": vocab.require("decision_authority", "machine_adjudication"),
        # Never `human_scientific_approval`: this is an agent's verdict and the record says so in the
        # same field an `hd_` uses to say the opposite.
        "approval_kind": vocab.require("approval_kind", "agent_verdict"),
        "confirmed_by_a_person": False, "actor": by, "adjudicated_at": utc_now(),
        "cites": restated or ({"claim_ids": dispute["cited_claim_ids"]} if dispute else {}),
        "rule_ref_before": rule_ref, "rule_ref_after": rule_ref_after,
        "rule_kind_before": criteria.load(core, rule_ref, task_id)["rule_kind"],
        "rule_kind_after": criteria.load(core, rule_ref_after, task_id)["rule_kind"],
        "attribute_ref_before": rule["attribute_ref"], "attribute_ref_after": attribute_ref_after,
        # The edit this adjudication made to the criterion itself, in the shape an `hd_` records its
        # own edits; empty for the four routes that change nothing but the rule's kind.
        "edits": edits,
        "scores_candidates": scores,
        # Both versions and a field-level diff of the revision, applied or refused (§6 F4).
        "revision": revision,
        "requires_explicit_review": bool(revision and revision["requires_explicit_review"]),
        "verdict": dispute["verdict"] if dispute else None,
        "reasoning": dispute["reasoning"] if dispute else None,
        "cited_claim_ids": dispute["cited_claim_ids"] if dispute else [],
        "independence": dispute["independence"] if dispute else None,
    }
    artifact_id = core.artifacts.put("machine_adjudication", record)
    # WHY `decision.recorded` and not a new event kind: `human.review_decided` is the `hd_` path and
    # must stay the `hd_` path, and `exchange.adjudicated` closes one proposer/critic exchange turn,
    # which three of the four routes never open. `decision.recorded` is the registered kind for a
    # decision artifact carrying an independence declaration (design §4.1, module.md C8).
    core.journal.append(task_id, "decision.recorded", actor=by, ids={"task_id": task_id},
                        payload=dict(record, artifact_id=artifact_id),
                        artifact_links=[{"kind": "machine_adjudication", "id": artifact_id}],
                        summary=f"machine adjudication {route}: {rule_ref} -> {record['rule_kind_after']} "
                                f"(no person confirmed it)")
    return record


def adjudicate_open(core: Core, task_id: str | None = None, *, roster: ModelRoster | None = None,
                    only_item: str | None = None, budget: Any = None) -> list[dict[str, Any]]:
    """Adjudicate the open rule-version items of one task (or every task), oldest first.

    An item this cannot resolve is left open with the reason, never half-resolved: the queue is the
    record of what still needs a person.
    """
    from . import review

    streams = [task_id] if task_id else core.journal.streams("task_")
    items = review.items(core, streams)
    out = []
    for item in sorted(items.values(), key=lambda i: i["created_at"]):
        if only_item and item["item_id"] != only_item:
            continue
        if item["state"] not in ("open", "in_review"):
            continue
        try:
            out.append(adjudicate(core, item, roster=roster, budget=budget))
        except (AdjudicationError, ModelError) as error:
            out.append({"queue_item_ref": item["item_id"], "subject": item["subject"], "route": None,
                        "resolution": None, "left_open_because": str(error)})
    return out


def records(core: Core, task_id: str) -> list[dict[str, Any]]:
    """Every machine adjudication recorded against one task, oldest first."""
    return [core.artifacts.payload(e.payload["artifact_id"]) for e in core.journal.replay(task_id)
            if e.event_type == "decision.recorded" and e.payload.get("adjudication_id")]


def by_rule_version(core: Core, task_id: str) -> dict[str, dict[str, Any]]:
    """Adjudications keyed by the exact rule version each one left standing (`rule_ref_after`).

    WHY the version and not the rule's base id: a later derivation round can promote the same
    criterion again, which proposes a new version and raises a fresh review item. Keyed by base id,
    that new version would enter a confirmed set on the strength of an adjudication of the version
    before it -- a rule nothing had looked at, carrying another rule's authority.
    """
    out: dict[str, dict[str, Any]] = {}
    for record in records(core, task_id):
        out[record["rule_ref_after"]] = record
    return out


def reopen(core: Core, item: dict[str, Any], *, by: dict[str, Any], reason_text: str) -> str:
    """Withdraw a machine adjudication and raise a fresh item on the same subject, for a person.

    WHY this exists: `review.decide` refuses an item whose state is not open, which is what keeps an
    adjudicated item from being quietly re-badged as an expert decision. Without a way back, though,
    running with nobody to ask became a one-way door -- an expert arriving later could not overrule
    the agent on anything it had already resolved. This keeps both records: the adjudication stays
    in the journal as what the system did while no person was available, and the new item carries
    the subject to a terminal. Withdrawing is not deciding: it leaves the subject unresolved.
    """
    if item.get("state") != "machine_adjudicated":
        raise AdjudicationError(f"item {item['item_id']} is {item.get('state')}, not machine-adjudicated")
    if not reason_text.strip():
        raise AdjudicationError("say why the adjudication is being withdrawn")
    core.journal.append(item["stream_id"], "human.review_withdrawn", actor=by,
                        ids={"review_request_id": item["item_id"]},
                        payload={"item_id": item["item_id"], "withdrew_adjudication_id": item.get("adjudication_id"),
                                 "reason_text": reason_text},
                        summary=f"withdrew the agent's verdict on {item['subject']['kind']} {item['subject']['id']}")
    return review.request(core, item["stream_id"], subject=item["subject"],
                          why_expert_required=f"an agent resolved this without a person "
                                              f"({item.get('adjudication_route')}); withdrawn: {reason_text}",
                          requested_by=by, inspection_bundle=item.get("inspection_bundle") or {})
