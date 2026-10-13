"""Stages of the criteria pool workflow (design §5.6): propose broadly, then filter, distill,
merge and refine, iterating; promote the survivors into the registry at the end of a round.

Each stage is one or more batched model calls followed by a deterministic gate; the
gate, not the model, decides what enters the pool's next state:

  PROPOSE  proposer, recall-first: everything the claims support. Only the
           reference-candidate scan refuses entry; other validator findings ride along.
  FILTER   deterministic first (registered duplicates, no supporting claim, unbound
           evidence requests), then a blind critic on its own queue. Failures send an
           item to refinement; an item still blocked after it was refined is filtered out.
  DISTILL  proposer: sharpen each candidate (operational definition, most informative
           measurable quantity, justified direction); revisions are re-validated.
  MERGE    deterministic pairing (same evidence route, unit and direction, overlapping
           wording), then the adjudicator decides; a merge may cite only its parents' claims.
  REFINE   proposer with the reviser prompt fixes validator problems and critic
           findings; after `max_refines` attempts an item waits for the next round.
  PROMOTE  a final blind check, then criteria.propose: clean items are registered as
           proposed, items with open critic findings go to the review queue as disputes,
           items that cannot be registered wait for the next round. Expert gates
           (hard exclusions, expert-set cutoffs) apply exactly as for any proposal.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from . import criteria
from .assessor import canonical_unit
from .derivation import (CRITIC_SYSTEM, CRITIQUE_SCHEMA, PROPOSAL_SCHEMA, PROPOSER_SYSTEM, REVISER_SYSTEM,
                         REVISION_CHECKS, REVISION_SCHEMA, _claims_block, _normalize_proposal, validate_proposal)
from .ids import slug
from .journal import actor as make_actor
from .models import ModelRequest, ModelRoster, call_role
from .pool import Pool, active
from .runtime import Core

POOL_SYSTEM = PROPOSER_SYSTEM + (
    " This is the broad first pass of an iterative workflow. Propose every distinct criterion the claims support for "
    "the dimension named below, including weaker or overlapping ones: later stages filter, sharpen, merge and refine "
    "the pool, so err on the side of recall. Each proposal must still cite the claims that support it."
)

DISTILL_SCHEMA = {
    "type": "object", "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "required": ["index", "action", "reason"],
        "properties": {"index": {"type": "integer"}, "action": {"type": "string", "enum": ["keep", "revise", "withdraw"]},
                       "proposal": {"type": "object"}, "reason": {"type": "string"}}}}},
}

DISTILLER_SYSTEM = PROPOSER_SYSTEM + (
    " You are now distilling a pool of candidate criteria. For each item: keep it if it is already precise; revise "
    "it to be sharper and more decision-useful (an operational definition; the most informative measurable quantity "
    "its cited claims support, preferring a quantitative measure with a unit when the claims carry values; a "
    "direction and rule kind justified by the objective; cutoffs only from cited values); or withdraw it if no "
    "sharpened form is supported by its claims. Keep each item's meaning and do not merge items here: a later stage "
    "merges. Cite only claims already cited by the item."
)

MERGE_SCHEMA = {
    "type": "object", "required": ["decisions"],
    "properties": {"decisions": {"type": "array", "items": {
        "type": "object", "required": ["group", "action", "reason"],
        "properties": {"group": {"type": "integer"}, "action": {"type": "string", "enum": ["merge", "keep_separate"]},
                       "merged": {"type": "object"}, "reason": {"type": "string"}}}}},
}

ADJUDICATOR_SYSTEM = (
    "You adjudicate whether groups of candidate screening criteria measure the same property. Merge a group only "
    "when its members measure the same quantity, in the same unit and direction, for the same purpose; the merged "
    "criterion keeps the clearest definition and cites the claims (from the members' citations only) that support "
    "it. Otherwise keep the members separate and say what distinguishes them. Never name a specific candidate "
    "compound. A merged criterion has the same fields as the members: attribute, rule, supporting_claim_ids, "
    "expected_change, falsification_test."
)

BATCH = {"critic": 30, "distill": 25, "refine": 20}
_WORDS = re.compile(r"[a-z0-9]+")
_STOP = {"the", "of", "a", "an", "in", "to", "and", "or", "for", "with", "by", "at", "on", "as", "is"}


def _chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


@dataclass
class StageContext:
    core: Core
    roster: ModelRoster
    task_id: str
    run_id: str
    task_context: dict[str, Any]
    catalog: list[dict[str, Any]]
    claims_by_id: dict[str, dict[str, Any]]
    reference_labels: list[str]
    pool: Pool
    budget: Any = None
    max_refines: int = 2
    critiques: dict[tuple[str, int], list[dict[str, Any]]] = field(default_factory=dict)
    adjudicated: set[frozenset] = field(default_factory=set)
    request_ids: list[str] = field(default_factory=list)

    @property
    def ids(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "run_id": self.run_id}

    def call(self, role: str, system: str, content: str, schema: dict[str, Any], question: str, max_tokens: int = 12000):
        response = call_role(self.core, self.roster, self.run_id, ModelRequest(
            role=role, system=system, messages=[{"role": "user", "content": content}], response_schema=schema,
            max_tokens=max_tokens, metadata={"question": question}), ids=self.ids, budget=self.budget)
        self.request_ids.append(response.request_id)
        return response

    def validate(self, item: dict[str, Any]) -> list[str]:
        return validate_proposal(item, claims_by_id=self.claims_by_id, reference_labels=self.reference_labels,
                                 catalog=self.catalog)

    def registered_keys(self) -> set[str]:
        return {criteria.evidence_key(a) for a in criteria.registered_attributes(self.core, self.task_id)}

    def base_prompt(self) -> str:
        c = self.task_context
        return (f"Objective: {c['objective_text']}\nConstraints: {json.dumps(c.get('constraints', []), ensure_ascii=False)}\n"
                f"Scope entities: {json.dumps(c.get('scope_entities', []), ensure_ascii=False)}\n"
                f"Criteria already in the registry (do not duplicate them): "
                f"{json.dumps([a['name'] for a in criteria.registered_attributes(self.core, self.task_id)], ensure_ascii=False)}\n\n"
                f"Evidence catalog (bind each attribute's evidence_request to one entry):\n"
                f"{json.dumps(self.catalog, ensure_ascii=False, indent=1)}\n\n"
                "Attribute fields: name, definition, measurement_kind (quantitative|ordinal|categorical|"
                "qualitative_determination), unit, direction (higher_better|lower_better|within_range|target_value|"
                "non_directional|undetermined), acceptable_value_sources (evidence kinds: curated_measurement, "
                "database_entry, peer_reviewed, preprint, reference_text (textbooks), tertiary_reference "
                "(encyclopedias, wikis), user_supplied_document), aggregation (max|min|median|consensus), "
                "evidence_request {capability, question_kind, identifier_scheme, parameters}, rationale.\n"
                "Rule fields: rule_kind (hard_exclusion|preference|exploratory_consideration), predicate_form "
                "(threshold|ordering), cutoff {comparator (>=|<=|>|<|==), value, unit} or null, cutoff_basis "
                "(source_stated_value|none_evidence_insufficient), on_missing/on_inapplicable/on_conflict "
                "(unknown_no_penalty|unknown_blocks_recommendation|route_to_human).\n")

    def cited_block(self, items: list[dict[str, Any]]) -> str:
        cited = sorted({c for item in items for c in item.get("supporting_claim_ids") or [] if c in self.claims_by_id})
        return _claims_block([self.claims_by_id[c] for c in cited])


def _item(proposal: dict[str, Any], **extra) -> dict[str, Any]:
    p = _normalize_proposal(proposal)
    return {"attribute": p.get("attribute", {}), "rule": p.get("rule", {}),
            "supporting_claim_ids": list(p.get("supporting_claim_ids") or []),
            "expected_change": p.get("expected_change", ""), "falsification_test": p.get("falsification_test", ""),
            **extra}


def _view(entry: dict[str, Any], index: int, *, blind: bool = False) -> dict[str, Any]:
    item = entry["item"]
    attribute = {k: v for k, v in item["attribute"].items() if not (blind and k == "rationale")}
    view = {"index": index, "attribute": attribute, "rule": item["rule"],
            "supporting_claim_ids": item["supporting_claim_ids"], "falsification_test": item.get("falsification_test")}
    if not blind:
        view["expected_change"] = item.get("expected_change")
    return view


# --- PROPOSE -------------------------------------------------------------------------------

def propose(ctx: StageContext, dimension: dict[str, str], claims: list[dict[str, Any]]) -> dict[str, Any]:
    in_pool = [e["item"]["attribute"].get("name") for e in active(ctx.pool.fold())]
    content = (ctx.base_prompt() + f"Dimension for this pass: {dimension['dimension']} - {dimension['focus']}\n"
               f"Criteria already in the pool (propose only distinct ones): {json.dumps(in_pool, ensure_ascii=False)}\n\n"
               f"Claims ({len(claims)}):\n{_claims_block(claims)}")
    response = ctx.call("proposer", POOL_SYSTEM, content, PROPOSAL_SCHEMA, f"propose pool: {dimension['dimension']}")
    added, refused = [], []
    for proposal in response.data["proposals"]:
        item = _item(proposal, dimension=dimension["dimension"])
        problems = ctx.validate(item)
        if any(p.startswith("reference_candidate_scan") for p in problems):
            refused.append({"name": item["attribute"].get("name"), "reason": "names the disclosed reference outcome"})
            continue
        item["validator_problems"] = problems
        added.append(ctx.pool.add(item, reason_text=f"proposed for {dimension['dimension']}"))
    return {"added": len(added), "refused_at_entry": refused,
            "considered_and_rejected": response.data.get("considered_and_rejected", [])}


# --- FILTER ----------------------------------------------------------------------------------

def _critique(ctx: StageContext, entries: list[dict[str, Any]], question: str) -> None:
    """Blind critique of entries not yet critiqued at their current version; results kept per (id, version)."""
    todo = [e for e in entries if (e["criterion_id"], e["version"]) not in ctx.critiques]
    for batch in _chunks(todo, BATCH["critic"]):
        views = [_view(e, i, blind=True) for i, e in enumerate(batch)]
        response = ctx.call("critic", CRITIC_SYSTEM, f"Objective: {ctx.task_context['objective_text']}\n\nProposals:\n"
                            f"{json.dumps(views, ensure_ascii=False, indent=1)}\n\nCited claims:\n"
                            f"{ctx.cited_block([e['item'] for e in batch])}", CRITIQUE_SCHEMA, question, max_tokens=8000)
        findings = [f for f in response.data["findings"] if f.get("referent")]
        for index, entry in enumerate(batch):
            ctx.critiques[(entry["criterion_id"], entry["version"])] = [f for f in findings if f["proposal_index"] == index]


def _failures(findings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fails = [f for f in findings if f["verdict"] == "fail"]
    blocking = [f for f in fails if f.get("severity") == "blocking"]
    material = [f for f in fails if f.get("severity", "material") == "material" and f["check"] in REVISION_CHECKS]
    return blocking, material


def filter_stage(ctx: StageContext, iteration: int) -> dict[str, Any]:
    pool = ctx.pool.at("filter", iteration)
    registered = ctx.registered_keys()
    stats = {"filtered_out": 0, "to_refine": 0, "kept": 0}
    survivors = []
    for entry in active(pool.fold(), ("candidate", "needs_refine")):
        item = entry["item"]
        cited = [c for c in item.get("supporting_claim_ids") or [] if c in ctx.claims_by_id]
        if criteria.evidence_key(item["attribute"]) in registered:
            pool.set_state(entry, "filtered_out", operation="remove", reason_kind="duplicate_of_registered")
            stats["filtered_out"] += 1
        elif not cited:
            pool.set_state(entry, "filtered_out", operation="remove", reason_kind="no_supporting_claim",
                           reason_text="none of the cited claims is in the ledger")
            stats["filtered_out"] += 1
        else:
            problems = ctx.validate(item)
            if problems and entry["state"] == "candidate":
                pool.set_state(entry, "needs_refine", operation="revise", reason_kind="validator_findings",
                               reason_text="; ".join(problems)[:500], item=dict(item, validator_problems=problems))
                stats["to_refine"] += 1
            elif not problems:
                survivors.append(entry)
    _critique(ctx, survivors, "critique pool")
    for entry in survivors:
        blocking, material = _failures(ctx.critiques[(entry["criterion_id"], entry["version"])])
        refined = int(entry["item"].get("refine_count") or 0)
        if blocking and refined >= ctx.max_refines:
            pool.set_state(entry, "filtered_out", operation="remove", reason_kind="critic_blocking_after_refinement",
                           reason_text="; ".join(f["finding"] for f in blocking)[:500])
            stats["filtered_out"] += 1
        elif blocking or material:
            pool.set_state(entry, "needs_refine", operation="revise", reason_kind="critic_findings",
                           reason_text="; ".join(f["finding"] for f in blocking + material)[:500],
                           item=dict(entry["item"], critic_findings=blocking + material))
            stats["to_refine"] += 1
        else:
            if entry["state"] == "needs_refine":
                pool.set_state(entry, "candidate", operation="reinstate", reason_kind="checks_passed")
            stats["kept"] += 1
    return stats


# --- DISTILL ---------------------------------------------------------------------------------

def distill_stage(ctx: StageContext, iteration: int) -> dict[str, Any]:
    pool = ctx.pool.at("distill", iteration)
    stats = {"revised": 0, "kept": 0, "withdrawn": 0, "to_refine": 0}
    for batch in _chunks(active(pool.fold(), ("candidate",)), BATCH["distill"]):
        views = [_view(e, i) for i, e in enumerate(batch)]
        response = ctx.call("proposer", DISTILLER_SYSTEM, ctx.base_prompt() + "\nItems to distill:\n"
                            + json.dumps(views, ensure_ascii=False, indent=1) + "\n\nCited claims:\n"
                            + ctx.cited_block([e["item"] for e in batch]), DISTILL_SCHEMA, "distill pool")
        for decision in response.data["items"]:
            if not 0 <= decision["index"] < len(batch):
                continue
            entry = batch[decision["index"]]
            if decision["action"] == "withdraw":
                pool.set_state(entry, "withdrawn", operation="remove", reason_kind="withdrawn_by_distiller",
                               reason_text=decision["reason"])
                stats["withdrawn"] += 1
            elif decision["action"] == "revise" and decision.get("proposal"):
                item = _item(dict(entry["item"], **decision["proposal"]), dimension=entry["item"].get("dimension"),
                             refine_count=entry["item"].get("refine_count", 0))
                if set(item["supporting_claim_ids"]) - set(entry["item"]["supporting_claim_ids"]):
                    stats["kept"] += 1   # distilling may not reach for new evidence; the earlier version stands
                    continue
                problems = ctx.validate(item)
                state = "needs_refine" if problems else "candidate"
                pool.revise(entry, dict(item, validator_problems=problems), state=state, reason_kind="distilled",
                            reason_text=decision["reason"])
                stats["to_refine" if problems else "revised"] += 1
            else:
                stats["kept"] += 1
    return stats


# --- MERGE -----------------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return {w for w in _WORDS.findall(text.lower()) if w not in _STOP}


def _overlap(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Word overlap of two attributes: the higher of name-only and name+definition Jaccard."""
    def jaccard(x: set[str], y: set[str]) -> float:
        return len(x & y) / len(x | y) if x and y else 0.0
    names = jaccard(_tokens(a.get("name", "")), _tokens(b.get("name", "")))
    full = jaccard(_tokens(f"{a.get('name', '')} {a.get('definition', '')}"),
                   _tokens(f"{b.get('name', '')} {b.get('definition', '')}"))
    return max(names, full)


def merge_groups(entries: list[dict[str, Any]], *, overlap: float = 0.35) -> list[list[dict[str, Any]]]:
    """Connected groups of items with the same evidence route, unit and direction and overlapping wording."""
    def route(e):
        a = e["item"]["attribute"]
        request = a.get("evidence_request") or {}
        return (request.get("capability"), request.get("question_kind"), canonical_unit(a.get("unit")), a.get("direction"))

    groups = []
    by_route: dict[tuple, list[dict[str, Any]]] = {}
    for entry in entries:
        by_route.setdefault(route(entry), []).append(entry)
    for members in by_route.values():
        parent = {e["criterion_id"]: e["criterion_id"] for e in members}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, a in enumerate(members):
            for b in members[i + 1:]:
                same_key = criteria.evidence_key(a["item"]["attribute"]) == criteria.evidence_key(b["item"]["attribute"])
                if same_key or _overlap(a["item"]["attribute"], b["item"]["attribute"]) >= overlap:
                    parent[find(a["criterion_id"])] = find(b["criterion_id"])
        clusters: dict[str, list[dict[str, Any]]] = {}
        for entry in members:
            clusters.setdefault(find(entry["criterion_id"]), []).append(entry)
        groups += [c for c in clusters.values() if len(c) > 1]
    return groups


def merge_stage(ctx: StageContext, iteration: int, *, overlap: float = 0.35) -> dict[str, Any]:
    pool = ctx.pool.at("merge", iteration)
    groups = [g for g in merge_groups(active(pool.fold(), ("candidate",)), overlap=overlap)
              if frozenset((e["criterion_id"], e["version"]) for e in g) not in ctx.adjudicated]
    stats = {"groups": len(groups), "merged": 0, "kept_separate": 0, "refused": 0}
    if not groups:
        return stats
    views = [{"group": gi, "members": [_view(e, mi) for mi, e in enumerate(g)]} for gi, g in enumerate(groups)]
    response = ctx.call("adjudicator", ADJUDICATOR_SYSTEM, f"Objective: {ctx.task_context['objective_text']}\n\nGroups:\n"
                        + json.dumps(views, ensure_ascii=False, indent=1) + "\n\nCited claims:\n"
                        + ctx.cited_block([e["item"] for g in groups for e in g]), MERGE_SCHEMA, "adjudicate merges")
    for group in groups:
        ctx.adjudicated.add(frozenset((e["criterion_id"], e["version"]) for e in group))
    for decision in response.data["decisions"]:
        if not 0 <= decision["group"] < len(groups):
            continue
        group = groups[decision["group"]]
        if decision["action"] != "merge" or not decision.get("merged"):
            stats["kept_separate"] += 1
            continue
        parents_claims = {c for e in group for c in e["item"]["supporting_claim_ids"]}
        item = _item(decision["merged"], dimension=group[0]["item"].get("dimension"))
        problems = ctx.validate(item)
        if problems or not item["supporting_claim_ids"] or not set(item["supporting_claim_ids"]) <= parents_claims:
            stats["refused"] += 1   # an invalid merge, or one citing evidence its parents did not, is not applied
            continue
        pool.merge(group, dict(item, validator_problems=[]), reason_text=decision["reason"])
        stats["merged"] += 1
    return stats


# --- REFINE ----------------------------------------------------------------------------------

def refine_stage(ctx: StageContext, iteration: int) -> dict[str, Any]:
    pool = ctx.pool.at("refine", iteration)
    stats = {"revised": 0, "withdrawn": 0, "still_failing": 0, "deferred": 0}
    for batch in _chunks(active(pool.fold(), ("needs_refine",)), BATCH["refine"]):
        notes = [dict(_view(e, i), validator_problems=e["item"].get("validator_problems") or [],
                      critic_findings=e["item"].get("critic_findings") or []) for i, e in enumerate(batch)]
        response = ctx.call("proposer", REVISER_SYSTEM, ctx.base_prompt() + "\nProposals to revise or withdraw:\n"
                            + json.dumps(notes, ensure_ascii=False, indent=1) + "\n\nCited claims:\n"
                            + ctx.cited_block([e["item"] for e in batch]), REVISION_SCHEMA, "refine pool")
        for revision in response.data["revisions"]:
            if not 0 <= revision["index"] < len(batch):
                continue
            entry = batch[revision["index"]]
            count = int(entry["item"].get("refine_count") or 0) + 1
            if revision["action"] == "withdraw" or not revision.get("proposal"):
                pool.set_state(entry, "withdrawn", operation="remove", reason_kind="withdrawn_by_reviser",
                               reason_text=revision["reason"])
                stats["withdrawn"] += 1
                continue
            item = _item(dict(entry["item"], **revision["proposal"]), dimension=entry["item"].get("dimension"),
                         refine_count=count)
            problems = ctx.validate(item)
            if not problems:
                pool.revise(entry, dict(item, validator_problems=[]), state="candidate", reason_kind="refined",
                            reason_text=revision["reason"])
                stats["revised"] += 1
            elif count >= ctx.max_refines:
                pool.revise(entry, dict(item, validator_problems=problems), state="deferred_next_round",
                            reason_kind="still_failing_after_refinement", reason_text="; ".join(problems)[:500])
                stats["deferred"] += 1
            else:
                pool.revise(entry, dict(item, validator_problems=problems), state="needs_refine",
                            reason_kind="refined_still_failing", reason_text="; ".join(problems)[:500])
                stats["still_failing"] += 1
    return stats


STAGES = {"filter": filter_stage, "distill": distill_stage, "merge": merge_stage, "refine": refine_stage}


# --- PROMOTE ---------------------------------------------------------------------------------

def _ids_for(ctx: StageContext, entry: dict[str, Any]) -> tuple[str, str]:
    """Registry ids for a pool item: its earlier promotion's ids, else a name slug that does not
    collide with an attribute measuring something else."""
    if entry.get("promoted_as"):
        attr_ref, rule_ref = entry["promoted_as"]["attribute_ref"], entry["promoted_as"]["rule_ref"]
        return attr_ref.split("@v")[0], rule_ref.split("@v")[0]
    base = slug(entry["item"]["attribute"]["name"])[:60]
    taken = {a["attribute_id"] for a in criteria.registered_attributes(ctx.core, ctx.task_id)}
    candidate, n = base, 1
    while f"attr_{candidate}" in taken:
        n += 1
        candidate = f"{base}-{n}"
    return f"attr_{candidate}", f"rule_{candidate}"


def promote(ctx: StageContext, *, by_proposer: dict[str, Any]) -> dict[str, Any]:
    pool = ctx.pool.at("promote", 0)
    registered = ctx.registered_keys()
    candidates = active(pool.fold(), ("candidate", "needs_refine"))
    _critique(ctx, [e for e in candidates if not ctx.validate(e["item"])], "final check before promotion")
    out = {"accepted": [], "disputed": [], "deferred": [], "duplicates": []}
    for entry in candidates:
        item = entry["item"]
        if criteria.evidence_key(item["attribute"]) in registered:
            pool.set_state(entry, "filtered_out", operation="remove", reason_kind="duplicate_of_registered")
            out["duplicates"].append(item["attribute"].get("name"))
            continue
        problems = ctx.validate(item)
        if problems:
            pool.set_state(entry, "deferred_next_round", operation="defer", reason_kind="validator_findings",
                           reason_text="; ".join(problems)[:500])
            out["deferred"].append({"criterion_id": entry["criterion_id"], "name": item["attribute"].get("name"),
                                    "problems": problems})
            continue
        findings = ctx.critiques.get((entry["criterion_id"], entry["version"]), [])
        blocking, material = _failures(findings)
        attr_id, rule_id = _ids_for(ctx, entry)
        attribute = dict(item["attribute"], attribute_id=attr_id, rationale=item["attribute"].get("rationale", ""),
                         supporting_claim_refs=item["supporting_claim_ids"],
                         derived_from={"pool_criterion": f"{entry['criterion_id']}@v{entry['version']}",
                                       "derivation_run": ctx.run_id})
        rule = dict(item["rule"], rule_id=rule_id, expected_change=item.get("expected_change", ""),
                    falsification_test=item.get("falsification_test", ""),
                    dissent=[f for f in findings if f["verdict"] == "fail"])
        dispute = ({"open_critic_findings": blocking + material, "pool_criterion": entry["criterion_id"],
                    "derivation_run": ctx.run_id} if blocking or material else None)
        try:
            attr_ref, rule_ref = criteria.propose(ctx.core, ctx.task_id, attribute, rule, by=by_proposer, dispute=dispute)
        except criteria.InvariantViolation as violation:
            pool.set_state(entry, "deferred_next_round", operation="defer", reason_kind="registry_invariant",
                           reason_text=str(violation))
            out["deferred"].append({"criterion_id": entry["criterion_id"], "name": item["attribute"].get("name"),
                                    "problems": [str(violation)]})
            continue
        registered.add(criteria.evidence_key(attribute))
        pool.set_state(entry, "promoted", operation="promote", reason_kind="disputed" if dispute else "accepted",
                       extra={"promoted_as": {"attribute_ref": attr_ref, "rule_ref": rule_ref}})
        record = {"criterion_id": entry["criterion_id"], "attribute_ref": attr_ref, "rule_ref": rule_ref,
                  "name": attribute["name"], "rule_kind": rule["rule_kind"], "critic_findings": findings}
        out["disputed" if dispute else "accepted"].append(record)
    return out


def proposer_actor_for(roster: ModelRoster) -> dict[str, Any]:
    adapter = roster.adapter("proposer")
    return make_actor("agent", f"proposer:{adapter.record.model_id}", "proposer", model_family=adapter.record.provider_family)


def proposer_actor(ctx: StageContext) -> dict[str, Any]:
    return proposer_actor_for(ctx.roster)
