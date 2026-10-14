"""Machine adjudication (C18, beside the Human Review Queue): resolving a queue item with no person.

A `machine_adjudication` (`adj_`) resolves one review queue item so a run can proceed when no expert
is available. It is not an expert decision and never becomes one. It carries `approval_kind:
agent_verdict`, never `human_scientific_approval`; it folds the queue item into its own state
(`machine_adjudicated`), not `decided`; and every rule it touches carries `authority:
machine_adjudication` into the rule set, its acceptance label and the board. `review.decide` is
untouched by this module: an `hd_` is still created only by a person confirming at a terminal.

Four routes, chosen by *why* the item needed an expert (`criteria.needs_expert`):

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

WHY a demotion is a new rule version rather than a field on the entry: the assessor reads
`rule["rule_kind"]` from the rule record it loads (`assessor.assess_cell`, `roll_up`), so a demotion
recorded only on the rule-set entry would leave a hard exclusion still excluding candidates while
every surface said it had been demoted.
"""

from __future__ import annotations

import json
import re
from typing import Any

from . import criteria, ledger, review, vocab
from .clock import utc_now
from .ids import new_id
from .journal import actor as make_actor
from .models import ModelError, ModelRequest, ModelRoster, call_role
from .runtime import Core
from . import task as task_mod

# One line per route, in the order `route_of` tries them: what the route does to the rule.
ROUTE_EFFECT = {
    "task_constraint_restated": "approve the rule unchanged, citing the task-context field it restates",
    "no_authority_available": "demote the rule to an exploratory consideration, so it stops scoring",
    "irreversible_without_authority": "demote the hard exclusion to a preference, so no candidate is removed",
    "dispute_adjudicated": "put the dispute to the adjudicator, blind to the proposer's rationale",
}
ROUTES = tuple(ROUTE_EFFECT)
VERDICTS = ("uphold_proposal", "uphold_objection", "revise", "cannot_resolve")
# The rule kind each resolution leaves behind; `approve` leaves the kind the proposal had.
RESOLUTIONS = {"approve": None, "demote_to_preference": "preference",
               "demote_to_exploratory_consideration": "exploratory_consideration"}

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
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


class AdjudicationError(RuntimeError):
    """An item that cannot be adjudicated at all: not a rule version, or no adjudicator to call."""


def _words(text: str) -> set[str]:
    return {w.strip(".") for w in _WORDS.findall((text or "").lower())} - _STOP - {""}


def _numbers(text: str) -> set[str]:
    return {n.rstrip("0").rstrip(".") if "." in n else n for n in _NUMBER.findall(text or "")}


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


# --- route selection ----------------------------------------------------------------------------

def _is_dispute(item: dict[str, Any]) -> bool:
    return bool((item.get("inspection_bundle") or {}).get("open_critic_findings"))


def route_of(rule: dict[str, Any], attribute: dict[str, Any], context: dict[str, Any],
             item: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """The route that resolves this item, and the restated constraint when route 1 applies.

    Order matters where a rule qualifies for more than one route, and it runs from the most
    conservative outcome to the least: an `expert_set` hard exclusion is demoted to a
    non-scoring exploratory consideration rather than to a scoring preference, because the
    authority its cutoff claims (an expert's judgement) is the one thing missing.
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
    except (KeyError, StopIteration):
        return dict(unknown, why_not="the rule or the task context this item names is not in this store root")
    route, _restated = route_of(rule, attribute, context, item)
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


def _adjudicate_dispute(core: Core, task_id: str, item: dict[str, Any], rule: dict[str, Any],
                        attribute: dict[str, Any], *, roster: ModelRoster, budget: Any = None) -> dict[str, Any]:
    from .derivation import _claims_block

    bundle = item.get("inspection_bundle") or {}
    marker = independence(roster)
    streams = [task_id] + ([bundle["derivation_run"]] if bundle.get("derivation_run") else [])
    cited = set(attribute.get("supporting_claim_refs") or [])
    claims = [c for c in ledger.claims(core, streams) if c["claim_id"] in cited]
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


def _apply_revision(rule: dict[str, Any], revision: dict[str, Any], attribute: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """The revised rule, or the original with the reason the revision was refused.

    A revision may only weaken: an agent that could revise a preference into a hard exclusion would
    have acquired, through the dispute route, exactly the authority routes 2 and 3 deny it.
    """
    fields = ("predicate_form", "cutoff", "cutoff_basis", "on_missing", "on_inapplicable", "on_conflict")
    revised = dict(rule, **{k: revision[k] for k in fields if k in revision})
    if revision.get("rule_kind") == "hard_exclusion":
        return rule, "a revision may not make a rule a hard exclusion"
    if revised.get("cutoff_basis") == "expert_set":
        return rule, "a revision may not claim an expert set the cutoff"
    try:
        criteria.check_rule(revised, attribute)
    except criteria.InvariantViolation as violation:
        return rule, f"the revised rule failed a registry invariant: {violation}"
    return revised, ""


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
    route, restated = route_of(rule, attribute, context, item)
    adjudication_id = new_id("adj")
    by, dispute = MACHINE, None

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
            revised, refused = _apply_revision(rule, dispute["revised_rule"] or {}, attribute)
            if refused:
                resolution, reason = "demote_to_exploratory_consideration", refused
            else:
                rule, resolution = revised, "approve"
                reason = "the dispute was settled by a change to the rule"
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
    changed = rewritten != criteria.load(core, rule_ref, task_id)
    rule_ref_after = rule_ref if not changed else _record_rule_version(
        core, task_id, rule_ref, rewritten, by=by, adjudication_id=adjudication_id,
        summary=f"{rule_ref} {rule['rule_kind']} -> {kind} by {adjudication_id} ({route})")
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
        "scores_candidates": scores,
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
