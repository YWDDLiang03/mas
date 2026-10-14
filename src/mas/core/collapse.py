"""Collapsing a quantity the registry holds twice into one attribute (design §4.10, §5.6).

The criterion registry is append-only, so a duplicate that has already been promoted cannot be
withdrawn -- and the pool's merge stage only ever groups *pool candidates*, so a promoted pair is
past the one stage that could have combined them. Measured on the live manuscript registry, 14
October 2026: ten promoted rules covered five quantities, because each of the five required
receptors carried `{receptor}-curated-potency` (ChEMBL, `question_kind: pchembl_values`) and
`{receptor}-affinity-on-the-independent-expert-curation` (IUPHAR/BPS, `gtopdb_affinity`) with
identical unit (pChEMBL), direction, aggregation (median), acceptable sources
(`curated_measurement`) and subject (`target_chembl_id`). Every receptor was therefore scored twice
and five quantities that do not exist inflated the coverage denominator: 34 of 3,177 compounds
cleared the 0.5 ranking floor where 99 clear it once each receptor is one quantity.

WHY this is deterministic, with no model call: two promoted attributes that share a
`derivation_stages.quantity_key` are the same quantity *by construction* -- same capability set,
same canonical unit, same direction, same subject parameters -- so declaring one attribute that
reads both routes adds no judgement to the store. The authority is a fact already in the store,
exactly as in `adjudication`'s `task_constraint_restated` route, where the authority is the user's
own task text. Design §S4 routed "a merge touching an already-promoted criterion" to an expert; the
human-in-the-loop feature has been withdrawn, so that route is closed and this one has to stand on
what the records say rather than on anyone's judgement.

WHY it writes two versions (the attribute and its rule): the sweep loads the attribute the *rule*
names (`controller` reads `entries[].attribute_ref`, which `confirm_rule_set` copies from
`rule["attribute_ref"]`), so a new attribute version nothing points at would leave every cell
reading one database while the registry said the quantity read two. The rule version changes that
one field and nothing else: same kind, same predicate form, same cutoff, same basis. The collapse is
about the attribute; it does not re-decide the rule.

WHY the pool's change-record vocabulary and no new event kind: this is a criterion changing state,
which is what `criterion.change_recorded` records, and `criterion_change_operation` already has
`merge` while `criterion_pool_state` already has `merged_away` for a criterion folded into another
and `promoted` for one that is in the registry. The payload is *not* marked `pool`, so `pool.fold`
and `pool.trajectory` -- which key on `cri_` lineages -- do not see registry refs in their counts.

WHY the record says a machine did it: nobody confirmed this. The record carries `approval_kind:
software_status`, `confirmed_by_a_person: False` and a `system` actor, the same way an
`adjudication` record carries `agent_verdict`; `confirm_rule_set` lists the surviving rules in
`machine_collapsed[]` and gives the rule set an acceptance reason, so a collapsed registry cannot
read as `prespecified`.
"""

from __future__ import annotations

import re
from typing import Any

from . import criteria, review, vocab
from .assessor import canonical_unit
from .canonical import canonical_text
from .clock import utc_now
from .derivation_stages import quantity_key
from .ids import new_id
from .journal import actor as make_actor
from .runtime import Core

# The collapse adds no judgement of its own, so its actor is the software, not an agent. The person
# who ran the command is recorded separately, as `ran_by`: they chose to run it, they did not decide it.
COLLAPSE = make_actor("system", "criterion-collapse", "registry")

# What the group's rules must agree on before their attributes may be collapsed. A different kind,
# predicate form or cutoff is a real disagreement about how to score one quantity, not a duplicate,
# and this module has no authority to settle one.
RULE_AGREEMENT = ("rule_kind", "predicate_form", "cutoff", "cutoff_basis")
RULE_DEFAULTS = {"predicate_form": "threshold", "cutoff": None}

_WORDS = re.compile(r"[a-z0-9]+")


class CollapseError(ValueError):
    """A collapse or withdrawal that cannot be applied at all."""


def _route_label(route: dict[str, Any]) -> str:
    route = route if isinstance(route, dict) else {}
    return route.get("question_kind") or route.get("capability") or "?"


def _ref(record: dict[str, Any], kind: str) -> str:
    return f"{record[f'{kind}_id']}@v{record['version']}"


def _quantity(attribute: dict[str, Any]) -> dict[str, Any]:
    """The grouping key in words, from the same primitives `quantity_key` hashes it from."""
    routes = criteria.evidence_routes(attribute)
    return {"capabilities": sorted({(r or {}).get("capability") or "" for r in routes}),
            "unit": canonical_unit(attribute.get("unit")), "direction": attribute.get("direction"),
            "subject": sorted({f"{k}={v}" for r in routes for k, v in criteria.subject_parameters(r).items()})}


def _rule_field(rule: dict[str, Any], field: str) -> Any:
    return rule.get(field, RULE_DEFAULTS.get(field))


def _disagreements(group: list[dict[str, Any]]) -> list[str]:
    first = group[0]
    out = []
    for member in group[1:]:
        for field in RULE_AGREEMENT:
            mine, theirs = _rule_field(first["rule"], field), _rule_field(member["rule"], field)
            if canonical_text(mine) != canonical_text(theirs):
                out.append(f"{member['rule_ref']} has {field} {theirs!r} where {first['rule_ref']} has {mine!r}")
    return out


def _words_of_one_route(attribute: dict[str, Any], routes: list[dict[str, Any]]) -> dict[str, Any]:
    """The words the surviving definition shares with exactly one of the pooled routes, or {}.

    WHY this reports words rather than claiming the definition "names a single source": a question
    kind mixes the database that answers with the measurement it answers about (`gtopdb_affinity` is
    IUPHAR/BPS *and* affinity), so a definition saying "affinity" shares a word with one route while
    naming no source at all. Stating the overlap and the route it is in is true; deciding which of
    the two it was would be this module reading prose, which it cannot do.

    WHY it only reports at all: the definition is prose a proposer or an adapter template wrote, and
    the one authority here is that the routes ask one question -- not that it can say in words what
    that question is. Rewriting prose heuristically is how a registry acquires a definition nobody
    wrote. The attribute's own unit is subtracted first, because `pChEMBL` names the scale every
    route reports on rather than the database that answers; without that, the surviving manuscript
    definition ("Median pChEMBL value over curated point measurements against CSF1R (CHEMBL1844)")
    would read as pointing at ChEMBL when it points at the scale.
    """
    words = set(_WORDS.findall((attribute.get("definition") or "").lower()))
    words -= set(_WORDS.findall((canonical_unit(attribute.get("unit")) or "").lower()))
    shared = {_route_label(r): sorted(words & set(_WORDS.findall(_route_label(r).lower()))) for r in routes}
    hits = {label: found for label, found in shared.items() if found}
    if len(hits) != 1:
        return {}
    label, found = next(iter(hits.items()))
    return {"route": label, "words": found}


def _members(core: Core, task_id: str) -> list[dict[str, Any]]:
    """Every attribute version a registered rule reads, with that rule, in promotion order.

    WHY it starts from the rules rather than from `criteria.registered_attributes`: a rule names one
    attribute *version*, and that version is what the sweep loads (`confirm_rule_set` copies
    `rule["attribute_ref"]` onto the entry, and `controller` reads the entry). Keyed on the latest
    attribute version instead, the supersession would name a version no rule reads, and the
    duplicate would go on scoring while the collapse record said it had been merged away.

    An attribute no rule names scores nothing, so nothing here reaches it: there is no duplication
    to remove and no rule whose agreement could be checked.
    """
    order: dict[str, int] = {}
    rules: dict[str, dict[str, Any]] = {}
    for position, event in enumerate(core.journal.replay(task_id)):
        if event.event_type != "criterion.version_proposed":
            continue
        if event.payload["kind"] == "attribute":
            order.setdefault(event.payload["id"], position)
        else:
            rules[event.payload["id"]] = core.artifacts.payload(event.payload["artifact_id"])   # latest version wins
    superseded = superseded_attributes(core, task_id)
    reading: dict[str, list[dict[str, Any]]] = {}
    for rule in rules.values():
        reading.setdefault(rule["attribute_ref"], []).append(rule)
    out = []
    for attribute_ref, naming in reading.items():
        if attribute_ref in superseded:
            continue        # a live collapse already merged it away; collapsing it again would loop
        attribute = criteria.load(core, attribute_ref, task_id)
        naming = sorted(naming, key=lambda r: r["rule_id"])
        out.append({"attribute": attribute, "attribute_ref": attribute_ref, "name": attribute.get("name"),
                    "rule": naming[0], "rule_ref": _ref(naming[0], "rule"),
                    "rules_naming_it": [_ref(r, "rule") for r in naming],
                    "promoted_at": order.get(attribute_ref.split("@v")[0], 0)})
    return out


def plan(core: Core, task_id: str) -> list[dict[str, Any]]:
    """One entry per group of promoted attributes that ask one question for one quantity.

    Nothing is written. Each entry names the earliest-promoted member as the survivor, the union of
    the group's routes in a stable order (the survivor's own first), and `refused[]` -- the reasons
    this group may not be collapsed, which is empty for a group that may.
    """
    # A member a person withdrew a collapse from is live again, so it groups again. Re-collapsing it
    # would overrule the withdrawal on the next run of the command, which is the one thing a reversal
    # must not be, so the group is refused and says whose decision it would be overruling.
    withdrawn = {m["attribute_ref"]: record["collapse_id"] for record in records(core, task_id)
                 if record["withdrawn"] for m in record["superseded"]}
    # A collapse stops the merged-away rules scoring. Where a person approved one of them, that is
    # the software overruling an expert decision, which no amount of "the routes ask one question"
    # authorises: the group is refused and the person is left to collapse it themselves.
    approved = {item["subject"]["id"] for item in review.items(core, [task_id]).values()
                if item["subject"]["kind"] == "rule_version" and item["state"] == "decided"
                and item.get("decision") in ("approve", "approve_with_edits")}
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for member in _members(core, task_id):
        groups.setdefault(quantity_key(member["attribute"]), []).append(member)
    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        out.append(_group_plan(sorted(members, key=lambda m: (m["promoted_at"], m["attribute_ref"])),
                               withdrawn, approved))
    return sorted(out, key=lambda g: g["surviving"]["attribute_ref"])


def _group_plan(members: list[dict[str, Any]], withdrawn: dict[str, str], approved: set[str]) -> dict[str, Any]:
    survivor, others = members[0], members[1:]
    refused = [f"a person withdrew {withdrawn[m['attribute_ref']]}, which had merged {m['attribute_ref']} away; "
               f"collapsing it again would overrule them"
               for m in members if m["attribute_ref"] in withdrawn]
    refused += [f"an expert approved {m['rule_ref']}, and this collapse would stop it scoring; a person has to "
                f"collapse what a person confirmed" for m in others if m["rule_ref"] in approved]
    refused += [f"{m['attribute_ref']} is read by {len(m['rules_naming_it'])} rules "
                f"({', '.join(m['rules_naming_it'])}); which one keeps the quantity is not a fact in the store"
                for m in members if len(m["rules_naming_it"]) > 1]
    # Two rules reading two versions of one attribute is one registration read twice, not one quantity
    # registered twice, and merging a *later* version of an attribute into its own earlier one would be
    # the collapse undoing whatever wrote it.
    bases = [m["attribute_ref"].split("@v")[0] for m in members]
    refused += [f"{m['attribute_ref']} and another member are both versions of {base}; this collapses "
                f"registrations of one quantity, not versions of one registration"
                for m, base in zip(members, bases) if bases.count(base) > 1]
    # WHY a group needs subject parameters: the quantity key is (capability set, canonical unit, direction,
    # subject parameters), and the first three do not identify a measurement. A capability is a transport --
    # `interaction_evidence_lookup` answers `pchembl_values`, `gtopdb_affinity` and `mechanism_records` alike --
    # so what pins one quantity is the subject. With `target_chembl_id=CHEMBL1844`, pChEMBL and `higher_better`
    # the key really does name one measurement, which is the case this exists for. With no subject it degenerates:
    # on the literature fixtures in `tests/test_criteria_pool.py`, "Oral bioavailability" (%, higher_better) and
    # "Plasma protein binding" (%, higher_better) share a key exactly, and nothing else here would tell them
    # apart -- `merge_groups` falls back to a wording test for subject-less items and the collapse has no
    # equivalent. Refusing is what keeps "no judgement was added" true rather than merely asserted.
    subjects = [criteria.subject_parameters(route) for m in members
                for route in criteria.evidence_routes(m["attribute"])]
    refused += ([f"{survivor['attribute_ref']} and its group state no subject parameters, so their shared "
                 f"quantity key is a unit and a direction; that does not identify one measurement"]
                if not any(subjects) else [])
    refused += _disagreements(members) if not refused else []
    before = criteria.evidence_routes(survivor["attribute"])
    after, seen = list(before), {criteria.route_key(r) for r in before}
    for member in others:
        for route in criteria.evidence_routes(member["attribute"]):
            if criteria.route_key(route) not in seen:
                seen.add(criteria.route_key(route))
                after.append(route)
    return {
        "quantity": _quantity(survivor["attribute"]),
        "surviving": {"attribute_ref": survivor["attribute_ref"], "rule_ref": survivor["rule_ref"],
                      "name": survivor["name"], "attribute": survivor["attribute"], "rule": survivor["rule"]},
        "superseded": [{"attribute_ref": m["attribute_ref"], "rule_ref": m["rule_ref"], "name": m["name"],
                        "routes": [_route_label(r) for r in criteria.evidence_routes(m["attribute"])],
                        "routes_already_covered": [_route_label(r) for r in criteria.evidence_routes(m["attribute"])
                                                   if criteria.route_key(r) in {criteria.route_key(b) for b in before}]}
                       for m in others],
        "routes_before": [_route_label(r) for r in before], "routes_after": [_route_label(r) for r in after],
        "_routes_after": after,          # the route records themselves, for `_apply`; not for printing
        "definition_shares_words_with_one_route": _words_of_one_route(survivor["attribute"], after),
        "refused": refused,
    }


def _reason(group: dict[str, Any]) -> str:
    quantity = group["quantity"]
    return (f"{len(group['superseded']) + 1} promoted attributes ask one question for one quantity: capabilities "
            f"{', '.join(quantity['capabilities'])}, unit {quantity['unit']}, direction {quantity['direction']}, "
            f"subject {', '.join(quantity['subject']) or 'none'}. Each was scored separately and each counted "
            f"once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute "
            f"{group['surviving']['attribute_ref']} is re-versioned declaring every route the group asks "
            f"({', '.join(group['routes_after'])}) and the others are merged away pointing at it. No judgement "
            f"was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and "
            f"the subject parameters. No person confirmed it.")


def _change(core: Core, task_id: str, *, collapse_id: str, criterion_id: str, version: int, operation: str,
            state: str, reason_kind: str, reason_text: str, targets_in: list[str], targets_out: list[str],
            by: dict[str, Any], artifact_id: str | None = None, extra: dict[str, Any] | None = None) -> None:
    vocab.require("criterion_change_operation", operation)
    vocab.require("criterion_pool_state", state)
    payload = {"collapse": True, "collapse_id": collapse_id, "change_id": new_id("chg"),
               "criterion_id": criterion_id, "version": version, "operation": operation, "state": state,
               "targets_in": targets_in, "targets_out": targets_out, "reason_kind": reason_kind,
               "reason_text": reason_text[:2000], "artifact_id": artifact_id, **(extra or {})}
    core.journal.append(task_id, "criterion.change_recorded", actor=by, ids={"task_id": task_id}, payload=payload,
                        artifact_links=[{"kind": "criterion_collapse", "id": artifact_id}] if artifact_id else [],
                        summary=f"{operation} {criterion_id}@v{version} -> {state} by {collapse_id} "
                                f"(no person confirmed it)")


def _apply(core: Core, task_id: str, group: dict[str, Any], *, by: dict[str, Any]) -> dict[str, Any]:
    collapse_id = new_id("clp")
    survivor = group["surviving"]
    attribute_ref_after, rule_ref_after = survivor["attribute_ref"], survivor["rule_ref"]
    reason = _reason(group)
    if group["routes_after"] != group["routes_before"]:
        # The definition is left exactly as it stands: `_words_of_one_route` reports where it shares
        # words with one route, and reporting is as far as this module's authority reaches. A singular
        # `evidence_request` is dropped because the attribute now has several and a field naming one
        # of them as *the* request is what a later reader would take for the only one.
        attribute = dict(survivor["attribute"], evidence_requests=group["_routes_after"])
        attribute.pop("evidence_request", None)
        criteria.check_attribute(attribute)
        attribute_ref_after = criteria.record_version(
            core, task_id, "attribute", survivor["attribute_ref"], attribute, by=COLLAPSE,
            summary=f"{survivor['attribute_ref']} reads {len(group['routes_after'])} curations of one quantity "
                    f"after {collapse_id}", extra={"collapsed_by": collapse_id})
        rule = dict(survivor["rule"], attribute_ref=attribute_ref_after)
        criteria.check_rule(rule, attribute)
        rule_ref_after = criteria.record_version(
            core, task_id, "rule", survivor["rule_ref"], rule, by=COLLAPSE,
            summary=f"{survivor['rule_ref']} reads {attribute_ref_after} after {collapse_id}",
            extra={"collapsed_by": collapse_id})
    # A rule the trigger table gates loses its earlier decision with its version, exactly as it does
    # under `criteria.propose`, so the item is raised again rather than letting a hard exclusion drop
    # silently out of the next confirmed set.
    rule_after = criteria.load(core, rule_ref_after, task_id)
    item_id = None
    if rule_ref_after != survivor["rule_ref"] and criteria.needs_expert(rule_after):
        item_id = review.request(core, task_id, subject={"kind": "rule_version", "id": rule_ref_after,
                                                         "version": rule_after["version"],
                                                         "attribute_ref": attribute_ref_after},
                                 why_expert_required=f"the software collapsed {len(group['superseded']) + 1} "
                                                     f"registrations of one quantity into {attribute_ref_after} "
                                                     f"({collapse_id}); the trigger table gates this rule",
                                 requested_by=COLLAPSE)
    record = {
        "collapse_id": collapse_id, "task_id": task_id, "basis": "same_quantity_key",
        "quantity": group["quantity"], "reason_text": reason,
        # Never `human_scientific_approval` and never `agent_verdict`: no person confirmed this and no
        # agent judged it. It is a status the software computed from records already in the store.
        "approval_kind": vocab.require("approval_kind", "software_status"),
        "confirmed_by_a_person": False, "actor": COLLAPSE, "ran_by": by, "collapsed_at": utc_now(),
        "surviving": {"name": survivor["name"], "attribute_ref_before": survivor["attribute_ref"],
                      "attribute_ref_after": attribute_ref_after, "rule_ref_before": survivor["rule_ref"],
                      "rule_ref_after": rule_ref_after, "routes_before": group["routes_before"],
                      "routes_after": group["routes_after"]},
        "superseded": [dict(member) for member in group["superseded"]],
        "definition_shares_words_with_one_route": group["definition_shares_words_with_one_route"],
        "definition_text": survivor["attribute"].get("definition"), "review_item": item_id,
    }
    artifact_id = core.artifacts.put("criterion_collapse", record)
    for member in group["superseded"]:
        base_id, version = member["attribute_ref"].split("@v")
        _change(core, task_id, collapse_id=collapse_id, criterion_id=base_id, version=int(version),
                operation="merge", state="merged_away", reason_kind="one_quantity_registered_twice",
                reason_text=f"{member['attribute_ref']} ({member['name']}) asks the same quantity as "
                            f"{survivor['attribute_ref']}; its routes {', '.join(member['routes'])} are declared "
                            f"on {attribute_ref_after}, so {member['rule_ref']} stops scoring",
                targets_in=[member["attribute_ref"]], targets_out=[attribute_ref_after], by=COLLAPSE,
                extra={"superseded_rule_ref": member["rule_ref"]})
    base_id, version = attribute_ref_after.split("@v")
    _change(core, task_id, collapse_id=collapse_id, criterion_id=base_id, version=int(version), operation="merge",
            state="promoted", reason_kind="one_quantity_registered_twice", reason_text=reason,
            targets_in=[m["attribute_ref"] for m in group["superseded"]], targets_out=[attribute_ref_after],
            by=COLLAPSE, artifact_id=artifact_id)
    return record


def collapse(core: Core, task_id: str, *, by: dict[str, Any], dry_run: bool = True) -> dict[str, Any]:
    """Collapse every group of promoted attributes that ask one question for one quantity.

    `dry_run` defaults to True on purpose: this rewrites an append-only registry, so a caller that
    has not decided gets the plan, and only an explicit `dry_run=False` writes anything. A group
    whose rules disagree is refused and reported, never half-applied.
    """
    groups = plan(core, task_id)
    collapsed, refused = [], []
    for group in groups:
        if group["refused"]:
            refused.append(group)
        elif dry_run:
            collapsed.append(dict(group, collapse_id=None))
        else:
            collapsed.append(dict(group, collapse_id=_apply(core, task_id, group, by=by)["collapse_id"]))
    return {"task_id": task_id, "dry_run": dry_run, "collapsed": collapsed, "refused": refused}


def records(core: Core, task_id: str) -> list[dict[str, Any]]:
    """Every collapse recorded against one task, oldest first, each saying whether it was withdrawn."""
    withdrawn = {e.payload["withdrew_collapse_id"] for e in core.journal.replay(task_id)
                 if e.event_type == "criterion.change_recorded" and e.payload.get("withdrew_collapse_id")}
    out = []
    for event in core.journal.replay(task_id):
        if event.event_type == "criterion.change_recorded" and event.payload.get("collapse") \
                and event.payload.get("artifact_id"):
            record = core.artifacts.payload(event.payload["artifact_id"])
            out.append(dict(record, withdrawn=record["collapse_id"] in withdrawn))
    return out


def live(core: Core, task_id: str) -> list[dict[str, Any]]:
    return [record for record in records(core, task_id) if not record["withdrawn"]]


def superseded_attributes(core: Core, task_id: str) -> dict[str, dict[str, Any]]:
    """Attribute versions a live collapse merged away, keyed by the exact version.

    WHY the version and not the base id, as in `adjudication.by_rule_version`: a later derivation
    round can promote a new version of a merged-away attribute, and that version is something nobody
    has collapsed. Keyed by base id it would stay out of every confirmed set on the strength of a
    collapse of the version before it -- a criterion silenced by a decision about a different one.
    """
    return {member["attribute_ref"]: record for record in live(core, task_id) for member in record["superseded"]}


def surviving_rules(core: Core, task_id: str) -> dict[str, dict[str, Any]]:
    """Rule versions that read an attribute version a collapse wrote, keyed by the rule version.

    WHY withdrawn collapses count here while `superseded_attributes` drops them: a withdrawal un-does
    the supersession, which is a fold, but it cannot un-write the attribute version -- the registry is
    append-only and the surviving rule still reads it. A rule set that forgot that would read as
    `prespecified` while scoring on a quantity definition the software assembled.
    """
    return {record["surviving"]["rule_ref_after"]: record for record in records(core, task_id)
            if record["surviving"]["rule_ref_after"] != record["surviving"]["rule_ref_before"]}


def withdraw(core: Core, task_id: str, collapse_id: str, *, by: dict[str, Any], reason_text: str) -> list[str]:
    """Undo one collapse, so its merged-away rules score again, and keep the collapse on the record.

    WHY this is not `adjudication.reopen`: `reopen` needs a review queue item folded to
    `machine_adjudicated`, which only a `machine_adjudication` record produces, and it reverses
    nothing in the registry -- it withdraws an agent's verdict and carries the subject back to a
    terminal. A collapse resolves no queue item and is no agent's verdict, and what has to come back
    is the supersession `confirm_rule_set` reads. So the reversal is recorded here, in `reopen`'s
    shape: the collapse stays in the journal as what the software did, withdrawing is not deciding,
    and it leaves the duplication unresolved rather than settled.

    The surviving attribute keeps its pooled version, because the registry is append-only and
    nothing is deleted; its rule still reads it. So a withdrawal returns a store where the quantity
    is registered twice again, which is the state a person is being asked about.
    """
    if not reason_text.strip():
        raise CollapseError("say why the collapse is being withdrawn")
    record = next((r for r in records(core, task_id) if r["collapse_id"] == collapse_id), None)
    if record is None:
        raise CollapseError(f"{task_id} has no collapse {collapse_id}")
    if record["withdrawn"]:
        raise CollapseError(f"{collapse_id} was already withdrawn")
    reinstated = []
    for member in record["superseded"]:
        base_id, version = member["attribute_ref"].split("@v")
        _change(core, task_id, collapse_id=collapse_id, criterion_id=base_id, version=int(version),
                operation="reinstate", state="promoted", reason_kind="collapse_withdrawn",
                reason_text=f"withdrawn: {reason_text}", targets_in=[record["surviving"]["attribute_ref_after"]],
                targets_out=[member["attribute_ref"]], by=by,
                extra={"withdrew_collapse_id": collapse_id, "superseded_rule_ref": member["rule_ref"]})
        reinstated.append(member["rule_ref"])
    return reinstated
