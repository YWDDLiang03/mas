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
           wording), then the adjudicator decides; a reduction may cite only its parents' claims, and
           inherits the quantity its group already agreed on instead of restating it.
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

from . import bound_support, criteria, vocab
from .assessor import DEFAULT_DETERMINATION_BASES, canonical_unit, family_aggregation_execution
from .canonical import canonical_text
from .derivation import (CRITIC_SYSTEM, CRITIQUE_SCHEMA, PROPOSAL_SCHEMA, PROPOSER_SYSTEM, REVISER_SYSTEM,
                         SCHEMA_BLOCK_FORMS,
                         REVISION_CHECKS, REVISION_SCHEMA, _claims_block, _normalize_proposal, validate_proposal)
from .ids import slug
from .journal import actor as make_actor
from .models import ModelError, ModelRequest, ModelRoster, call_role
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

# The registered reductions over a family, offered to the adjudicator and enforced by the gate.
FAMILY_AGGREGATIONS = tuple(vocab.DOMAINS["criterion_family_aggregation"])

MERGE_SCHEMA = {
    "type": "object", "required": ["decisions"],
    "properties": {"decisions": {"type": "array", "items": {
        "type": "object", "required": ["group", "action", "reason"],
        "properties": {"group": {"type": "integer"},
                       "action": {"type": "string", "enum": ["merge", "consolidate", "keep_separate"]},
                       "merged": {"type": "object", "properties": {"attribute": {"type": "object", "properties": {
                           # The merged attribute may keep every route its parents had, which is how two
                           # bindings of one quantity become one attribute read from both databases.
                           "evidence_requests": {"type": "array", "items": {"type": "object"}}}}}},
                       # A consolidation carries the same criterion fields as a merge plus the three that make
                       # the abstraction checkable: which members it folds in (so it may take part of a group,
                       # and so a reviewer sees what was subsumed), the property it claims they share, and how
                       # the family reduces to one number.
                       "consolidated": {
                           "type": "object", "required": ["members", "shared_property", "family_aggregation"],
                           "properties": {"members": {"type": "array", "items": {"type": "integer"}},
                                          "shared_property": {"type": "string"},
                                          "family_aggregation": {"type": "string",
                                                                 "enum": list(FAMILY_AGGREGATIONS)},
                                          "attribute": {"type": "object", "properties": {
                                              "evidence_requests": {"type": "array",
                                                                    "items": {"type": "object"}}}}}},
                       "reason": {"type": "string"}}}}},
}

ADJUDICATOR_SYSTEM = (
    "You decide what each group of candidate screening criteria becomes. Three answers are available and "
    "`keep_separate` is as legitimate as either reduction: `merge` when the members are one quantity described "
    "more than once, `consolidate` when they are genuinely different measurements of one screen-relevant family, "
    "`keep_separate` when neither holds. "
    "Merge a group only "
    "when its members measure the same quantity, in the same unit and direction, for the same purpose; the merged "
    "criterion keeps the clearest definition and cites the claims (from the members' citations only) that support "
    "it. Otherwise keep the members separate and say what distinguishes them. Never name a specific candidate "
    "compound. "
    "A reduction states only what it decides: a `name` of its own, a `definition`, the `rule`, "
    "`supporting_claim_ids`, `expected_change`, `falsification_test`, the `evidence_requests` it keeps, and, for a "
    "consolidation, `members`, `shared_property` and `family_aggregation`. The name is required and no member's "
    "name can stand in for it -- a family named after one of its endpoints misdescribes itself -- so name the "
    "quantity the child measures. "
    "What the group already settled is filled in for you and is not yours to restate: `unit`, `direction`, "
    "`value_transform`, `measurement_kind`, `acceptable_value_sources` and `acceptable_determination_bases` come "
    "from the members, which are in one group because they agree on them. Write none of those six. A value that "
    "contradicts what the members agree on refuses the reduction rather than overriding them; and where the "
    "members do not agree on one of the six -- on what evidence may answer them, or on what kind of value "
    "answers them -- the reduction is refused rather than rescoping a member's evidence silently, so consolidate "
    "the members that agree and leave the others out. "
    "Members may differ only in which database answers the same question -- the same measurement curated by two "
    "sources. That is one quantity: merge them and give the merged attribute evidence_requests, the list of the "
    "members' evidence routes to keep, so the merged criterion reads both sources and pools their values under its "
    "aggregation. Keep a route only if a member declared it; a merge may not reach for a source no member had. "
    "A group of distinct measurements is not a merge, and the pool still has to reduce from many derived "
    "criteria to the few a screen decides on. That is `consolidate`: a family of specific endpoints replaced by "
    "the one criterion a screen would actually apply -- eight grade >=3 toxicity incidences by one grade >=3 "
    "toxicity burden. A consolidation gives `consolidated` with the criterion's own fields and three more: "
    "`members`, the indices within the group it folds in (two or more; one member is not a family, and all of "
    "them must sit in one dimension); `shared_property`, what those endpoints have in common and why that "
    "property decides a screen -- a restatement of the unit or the dimension (\"they are all percentages\") is "
    "refused, so name the substance; and `family_aggregation`, how the family reduces to one number, one of "
    + "|".join(FAMILY_AGGREGATIONS) +
    ". Those are the reductions that are computed rather than merely recorded, so nothing else is accepted: "
    "`worst_member` scores the least favourable member, which is the largest value when the direction is "
    "lower_better and the smallest when it is higher_better, and so is open only to a group whose members "
    "declare one of those two -- read it off them, as it is the group's direction the child inherits; "
    "`median_of_members` scores the median and works under any direction. Your choice sets the "
    "consolidated attribute's own `aggregation` -- do not try to coordinate the two yourself, and expect the "
    "aggregation you write on a consolidated attribute to be replaced by the one your family reduction "
    "implies. "
    "It may cite only its members\' claims, and may read only the sources its members read: a literature-bound "
    "family may carry a query written for the family it now stands for, but no consolidation reaches for a "
    "capability, a question kind or a target no member declared. "
    "Consolidate nothing you cannot justify by a shared property that matters at screening time: a criterion so "
    "abstract that nobody can compute it, or that a reviewer cannot object to because it no longer says which "
    "endpoints it stands for, is worse than the family it replaced, and saying what distinguishes the members "
    "is the right answer whenever that is what you find. Keep each decision\'s `reason` specific to its group."
)

BATCH = {"critic": 30, "distill": 25, "refine": 20}
# Members offered to the adjudicator as one merge group. A whole unit-and-direction bucket can run to
# dozens of criteria, and a prompt that large is one no model reads carefully and no reviewer can
# check; a bucket wider than this is split into several groups instead.
MERGE_GROUP_MAX = 8
_WORDS = re.compile(r"[a-z0-9]+")
_STOP = {"the", "of", "a", "an", "in", "to", "and", "or", "for", "with", "by", "at", "on", "as", "is"}


def _chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


# WHY one batch may fail without taking the round with it: `call_role` repairs an unparseable reply
# once and then raises, and every stage ran its batches in a bare loop, so a single bad reply ended
# the whole derivation. Measured on the clean derivation of 14 October 2026 -- after 1.5 hours, 24
# documents read, 597 claims admitted and 59 proposals pruned to 38 -- `refine` at iteration 2 hit
# `parse_failed: no JSON value found in the model reply` on one batch and the run died with nothing
# promoted. A reasoning model that occasionally answers in prose is a property of the provider, not a
# reason to discard the work. An unresolved batch is a legitimate outcome once it is labelled: the
# items keep whatever state they already had, the failure is counted in the stage's own stats, and
# promotion sees a smaller pool rather than none. A budget refusal still propagates untouched --
# that is the run being told to stop, which is different from a provider stumbling.
def _for_each_batch(items: list, size: int, stats: dict[str, Any], handle) -> None:
    for batch in _chunks(items, size):
        try:
            handle(batch)
        except ModelError as error:
            if error.error_class == "quota_exhausted":
                raise
            stats["batches_unresolved"] = stats.get("batches_unresolved", 0) + 1
            stats.setdefault("unresolved_reasons", []).append(f"{error.error_class}: {error}"[:200])


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

    def registered(self) -> list[dict[str, Any]]:
        return criteria.registered_attributes(self.core, self.task_id)

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
                "acceptable_determination_bases (defaults to measured and derived), "
                "value_transform when the attribute is about a derived quantity rather than the value the source "
                "returns -- {kind: excess_above|shortfall_below|distance_outside_band, bound or low and high, "
                "basis, source_refs}; without it the raw value is what gets ranked, however the definition "
                "describes the quantity, "
                "evidence_request {capability, question_kind, identifier_scheme, parameters} -- or "
                "evidence_requests [{...}, {...}] when one quantity is read from several catalog entries "
                "(same unit, same direction, same subject parameters), whose values are then pooled under "
                "this attribute's aggregation, rationale.\n"
                + SCHEMA_BLOCK_FORMS)

    def cited_block(self, items: list[dict[str, Any]]) -> str:
        cited = sorted({c for item in items for c in item.get("supporting_claim_ids") or [] if c in self.claims_by_id})
        return _claims_block([self.claims_by_id[c] for c in cited])


def _item(proposal: dict[str, Any], **extra) -> dict[str, Any]:
    p = _normalize_proposal(proposal)
    return {"attribute": p.get("attribute", {}), "rule": p.get("rule", {}),
            "supporting_claim_ids": list(p.get("supporting_claim_ids") or []),
            "expected_change": p.get("expected_change", ""), "falsification_test": p.get("falsification_test", ""),
            **extra}


# WHY a stage that rebuilds an item has to be told what to carry over: `_item` keeps the five fields a model
# authors plus whatever `**extra` names, while `pool.ITEM_FIELDS` persists five more -- so every field the pool
# keeps and a model does not write is dropped unless the rebuilding stage hands it back. That has now been the
# shape of two defects: `refine_count`, which `_record` dropped so the repair budget reset on every fold, and
# `consolidation`, which `distill_stage` and `refine_stage` dropped so a revised consolidated criterion kept
# the `aggregation` its consolidation chose and lost the list of endpoints it subsumed -- the one thing a
# reviewer can object to an abstraction with.
#
# Carried over here, because each is a fact about the lineage rather than about the text a reviser rewrites:
#   `dimension`      a revision sharpens a criterion; it does not move it to another dimension.
#   `refine_count`   the repair budget is cumulative, so a revision does not earn back an attempt.
#   `consolidation`  the record of what this abstraction replaced -- carried only when it is still true.
# Deliberately *not* carried over, and listed so that the absence reads as a decision: `validator_problems`,
# which every revising stage recomputes against the revised item before it stores one, and `critic_findings`,
# which are findings against the version the revision supersedes. `filter_stage` re-critiques each version and
# `promote` critiques the version it promotes, so neither is lost by being cleared -- while carrying either
# forward would make the pool and the criterion card state an objection to text that no longer exists.
#
# The attribute fields that fix *what* is measured, as opposed to how well it is worded. Compared
# case- and whitespace-insensitively, and with the routes keyed on `_source_key`, so sharpening a literature
# query -- a retrieval knob, the same one a consolidation is allowed to rewrite for the family it now stands
# for -- is not a change of quantity, while reaching for another source or subject is. `name` counts because
# `criteria.evidence_key` identifies a literature-bound attribute by its name and unit, and every consolidated
# family so far is literature-bound; `value_transform` counts for the reason `quantity_key` carries it (F5), a
# transform being what makes "molecular weight" and "the excess above 500 g/mol" two quantities. The fields
# that say which evidence may answer the question (`acceptable_value_sources`,
# `acceptable_determination_bases`) are deliberately absent: they change what counts as an answer, not what
# was asked, and the family was never a claim about either.
_MEASURED_BY = ("name", "definition", "unit", "direction", "measurement_kind")


def _measured_as(attribute: dict[str, Any]) -> dict[str, Any]:
    """What this attribute measures: the quantity it names, the scale it is on, the reduction over its
    claims, and the source and subject of every route that answers it."""
    measured = {field: " ".join(str(attribute.get(field) or "").lower().split()) for field in _MEASURED_BY}
    # `criteria.check_attribute` reads a missing aggregation as `consensus`, so the two spellings of the
    # default are one value here and only a real change of reduction counts as one.
    measured["aggregation"] = attribute.get("aggregation") or "consensus"
    measured["value_transform"] = canonical_text(attribute.get("value_transform"))
    measured["routes"] = sorted({_source_key(route) for route in criteria.evidence_routes(attribute)})
    return measured


def _measures_differently(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Which of those fields a revision changed, named so a refusal can say which it was."""
    was, now = _measured_as(before), _measured_as(after)
    return [field for field in sorted(was) if was[field] != now[field]]


def _revised(entry: dict[str, Any], proposal: dict[str, Any], *,
             refine_count: int) -> tuple[dict[str, Any] | None, str | None]:
    """The item a revision of `entry` produces, or the reason it is refused; exactly one of the two.

    WHY a revision of a *consolidated* criterion can be refused rather than carried forward or stripped:
    `consolidation.subsumes` is a claim about the criterion as it stands -- that these specific endpoints are
    what this one screening criterion now stands for -- and the gate that admitted it checked the family
    against that criterion's unit, direction, dimension and family reduction (`_consolidation`). The
    distiller and the reviser see neither the family nor the record: `_view` hands them the abstraction's own
    fields, so neither can judge whether those endpoints still share the property under a redefinition.
    Of the three things that can happen to the list, the commitment the pool is reported under -- every
    criteria count published together with its consolidations and what each one subsumed -- rules out two:
    carrying it onto a criterion that now measures something else states as reviewed a fact nobody checked,
    and dropping it leaves a reduced pool unauditable exactly where the headline count rests. So the earlier
    version stands, the refusal is recorded in the stage result, and the pool keeps a consolidation that is
    still true of the criterion carrying it. Nothing is stuck: a consolidated criterion that should measure
    something else can be consolidated again by the adjudicator, which is shown the members and has its
    shared property and its reduction re-checked, and a revision that only sharpens the wording, the rule,
    the expected change or the falsification test applies as it always did.
    """
    item = _item(proposal, dimension=entry["item"].get("dimension"), refine_count=refine_count)
    consolidation = (entry["item"] or {}).get("consolidation")
    if not consolidation:
        return item, None
    changed = _measures_differently(entry["item"].get("attribute") or {}, item["attribute"])
    if changed:
        return None, (f"this criterion consolidates {len(consolidation.get('subsumes') or [])} endpoint(s) on "
                      f"the shared property {str(consolidation.get('shared_property'))[:120]!r}, and the "
                      f"revision changes what it measures ({', '.join(changed)}), which that family was never "
                      f"checked against; v{entry['version']} stands and the family may be consolidated again")
    return dict(item, consolidation=consolidation), None


def _not_revised(stats: dict[str, Any], entry: dict[str, Any], reason: str) -> None:
    """A revision the gate did not apply. Nothing is written to the pool, because nothing about the lineage
    changed; the reason travels in the stage result, which is where `merge_stage` already records the
    reductions it refused and which `_stage_recorder` journals and stores as a `derivation_stage`."""
    stats["refused"] = stats.get("refused", 0) + 1
    stats.setdefault("not_revised", []).append({"criterion_id": entry["criterion_id"], "version": entry["version"],
                                                "name": (entry["item"].get("attribute") or {}).get("name"),
                                                "reason": reason[:500]})


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

def duplicate_of_registered(attribute: dict[str, Any],
                            registered: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The registered attribute that already asks everything this proposal asks about one quantity.

    Two tests, and a proposal that fails neither survives:

      * `criteria.evidence_key` equality -- the registry invariant that two attributes asking the
        same tools the same questions are one attribute.
      * the same `quantity_key` and a route set that is a *subset* of the registered attribute's.

    WHY the subset test had to be added: `evidence_key` hashes the whole route set, so once a
    receptor's potency is registered as one attribute reading both curations
    (`{pchembl_values, gtopdb_affinity}`), a fresh single-route proposal for the IUPHAR/BPS half of
    it does not match and is promoted. That rebuilds exactly the duplication the registration
    template was changed to remove -- measured on the manuscript registry, 14 October 2026: ten
    promoted rules for five quantities, each receptor scored twice. `merge_groups` cannot catch it
    either, because it groups pool candidates and the registered attribute is not one, so the group
    has a single member and is dropped.

    WHY a subset and not an overlap: a proposal offering a route the registered attribute does *not*
    have asks something the registry never asks. That is new evidence, and dropping it silently
    would be the opposite error and the worse one, so it survives and the pool may promote it; the
    pair is then one quantity registered twice, which `core/collapse.py` collapses.

    Literature-bound attributes keep `evidence_key`'s own identity (name and unit) and are left out
    of the subset test: their route parameters are a query template, a retrieval knob rather than a
    subject, so two attributes about different quantities can share one route and route coverage
    says nothing about which quantity is meant.
    """
    asked = {criteria.route_key(r) for r in criteria.evidence_routes(attribute)}
    key, literature = quantity_key(attribute), criteria.is_literature_bound(attribute)
    for other in registered:
        routes = criteria.evidence_routes(other)
        covered = sorted({_route_name(r) for r in routes if criteria.route_key(r) in asked})
        # WHY the retrieval match is no longer sufficient on its own (F5): `evidence_key` hashes
        # capability, question kind and parameters -- a *retrieval* identity, the thing that makes two
        # calls interchangeable for caching. Two attributes can ask one tool one question and compute
        # different quantities from the answer: molecular weight and the excess of molecular weight
        # above a bound read the same PubChem field. Dropping one as a duplicate of the other retires a
        # derived criterion against the measurement it was derived from. So a shared retrieval identity
        # is a hint, and the quantity has to agree before anything is refused.
        if criteria.evidence_key(attribute) == criteria.evidence_key(other) and quantity_key(other) == key:
            why = "it asks the same tools the same questions about the same quantity"
        elif not literature and quantity_key(other) == key and asked <= {criteria.route_key(r) for r in routes}:
            why = f"every route this proposal asks is one of its own ({', '.join(covered)})"
        else:
            continue
        return {"attribute_ref": f"{other.get('attribute_id')}@v{other.get('version')}", "name": other.get("name"),
                "why": why, "already_covered": covered,
                "asks": sorted({_route_name(r) for r in routes})}
    return None


def _route_name(route: dict[str, Any]) -> str:
    route = route if isinstance(route, dict) else {}
    return route.get("question_kind") or route.get("capability") or "?"


def duplicate_reason(found: dict[str, Any]) -> str:
    """Why a proposal was refused as a duplicate, for the change record and the pool trajectory.

    It names the registered attribute, which of the two tests matched, and what that attribute asks,
    because `duplicate_of_registered` is now a subset test: "already registered" no longer means the
    two attributes are identical, and a reader of the trajectory has no other way to tell which of
    the registry's questions this proposal was asking again.
    """
    return (f"{found['attribute_ref']} ({found['name']}) already asks this quantity: {found['why']}; "
            f"it asks {', '.join(found['asks'])}")


def _critique(ctx: StageContext, entries: list[dict[str, Any]], question: str,
              stats: dict[str, Any] | None = None) -> None:
    """Blind critique of entries not yet critiqued at their current version; results kept per (id, version).

    A batch whose reply cannot be used leaves its items uncritiqued, which `filter_stage` already
    reads as "the critic said nothing" -- so the pass continues and the omission is counted rather
    than ending the round.
    """
    todo = [e for e in entries if (e["criterion_id"], e["version"]) not in ctx.critiques]
    for batch in _chunks(todo, BATCH["critic"]):
        try:
            views = [_view(e, i, blind=True) for i, e in enumerate(batch)]
            response = ctx.call("critic", CRITIC_SYSTEM, f"Objective: {ctx.task_context['objective_text']}\n\nProposals:\n"
                                f"{json.dumps(views, ensure_ascii=False, indent=1)}\n\nCited claims:\n"
                                f"{ctx.cited_block([e['item'] for e in batch])}", CRITIQUE_SCHEMA, question, max_tokens=8000)
            findings = [f for f in response.data["findings"] if f.get("referent")]
            for index, entry in enumerate(batch):
                ctx.critiques[(entry["criterion_id"], entry["version"])] = [f for f in findings if f["proposal_index"] == index]
        except ModelError as error:
            if error.error_class == "quota_exhausted":
                raise
            if stats is not None:
                stats["critique_batches_unresolved"] = stats.get("critique_batches_unresolved", 0) + 1


def _failures(findings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fails = [f for f in findings if f["verdict"] == "fail"]
    blocking = [f for f in fails if f.get("severity") == "blocking"]
    material = [f for f in fails if f.get("severity", "material") == "material" and f["check"] in REVISION_CHECKS]
    return blocking, material


def filter_stage(ctx: StageContext, iteration: int) -> dict[str, Any]:
    pool = ctx.pool.at("filter", iteration)
    registered = ctx.registered()
    stats = {"filtered_out": 0, "to_refine": 0, "kept": 0}
    survivors = []
    for entry in active(pool.fold(), ("candidate", "needs_refine")):
        item = entry["item"]
        cited = [c for c in item.get("supporting_claim_ids") or [] if c in ctx.claims_by_id]
        duplicate = duplicate_of_registered(item["attribute"], registered)
        if duplicate is not None:
            pool.set_state(entry, "filtered_out", operation="remove", reason_kind="duplicate_of_registered",
                           reason_text=duplicate_reason(duplicate))
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
    _critique(ctx, survivors, "critique pool", stats)
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
    stats: dict[str, Any] = {"revised": 0, "kept": 0, "withdrawn": 0, "to_refine": 0, "refused": 0}
    for batch in _chunks(active(pool.fold(), ("candidate",)), BATCH["distill"]):
        try:
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
                    item, refused = _revised(entry, dict(entry["item"], **decision["proposal"]),
                                             refine_count=int(entry["item"].get("refine_count") or 0))
                    if refused:
                        _not_revised(stats, entry, refused)
                        continue
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
        except ModelError as error:
            if error.error_class == "quota_exhausted":
                raise
            stats["batches_unresolved"] = stats.get("batches_unresolved", 0) + 1
            stats.setdefault("unresolved_reasons", []).append(f"{error.error_class}: {error}"[:160])
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


def _subject(attribute: dict[str, Any]) -> list[str]:
    """What the attribute's routes are about: the subject-identifying parameters over all of them."""
    return sorted({canonical_text([k, v]) for route in criteria.evidence_routes(attribute)
                   for k, v in criteria.subject_parameters(route).items()})


def quantity_key(attribute: dict[str, Any]) -> tuple:
    """What an attribute measures, as a groupable key: capabilities, canonical unit, direction, subject.

    WHY the question kind is not in it: `question_kind` names *which database answers*
    (`pchembl_values` is ChEMBL, `gtopdb_affinity` is IUPHAR/BPS), so keying on it put the two
    bindings of one quantity in different buckets, where no amount of adjudication could reach them.
    Measured on the manuscript registry: ten promoted rules, five quantities, every receptor scored
    twice.
    """
    # WHY the transform is in it (F5): the key is meant to say what an attribute measures, and a
    # declared `value_transform` changes exactly that -- "molecular weight" and "the excess of
    # molecular weight above 500 g/mol" share a capability, a unit, a direction and a subject while
    # being different quantities, one of them derived from the other. Leaving it out let a raw
    # quantity and its own transform group as one thing, so a merge or a duplicate check could
    # collapse a derived criterion into the measurement it was derived from and call it redundant.
    # The transform's kind and parameters are both included: an excess above 500 and an excess above
    # 300 are no more the same quantity than either is the raw value.
    routes = criteria.evidence_routes(attribute)
    capabilities = tuple(sorted({(route or {}).get("capability") or "" for route in routes}))
    return (capabilities, canonical_unit(attribute.get("unit")), attribute.get("direction"),
            canonical_text(_subject(attribute)), canonical_text(attribute.get("value_transform")))


def merge_groups(entries: list[dict[str, Any]], *, overlap: float = 0.35) -> list[list[dict[str, Any]]]:
    """Connected groups of items that measure one quantity, for the adjudicator to decide on.

    Same capability, unit, direction and subject parameters groups unconditionally: one subject
    measured in one unit in one direction is far stronger evidence of one quantity than any wording
    similarity. Measured on the pair this exists for -- a receptor's curated potency from ChEMBL and
    the same affinity from IUPHAR/BPS -- name Jaccard is 0.14 and name+definition 0.10, under the
    0.35 the overlap test needs, because one definition is terse and the other is verbose prose. So
    wording is the wrong signal whenever the routes already say what the quantity is about. Items
    with no subject parameters (literature-bound ones, whose parameters are a query template) keep
    the wording test.
    """
    groups = []
    by_route: dict[tuple, list[dict[str, Any]]] = {}
    for entry in entries:
        by_route.setdefault(quantity_key(entry["item"]["attribute"]), []).append(entry)
    for members in by_route.values():
        parent = {e["criterion_id"]: e["criterion_id"] for e in members}
        # The key carries the subject, so every member of this bucket shares it; one member decides.
        same_subject = bool(_subject(members[0]["item"]["attribute"]))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, a in enumerate(members):
            for b in members[i + 1:]:
                same_key = criteria.evidence_key(a["item"]["attribute"]) == criteria.evidence_key(b["item"]["attribute"])
                # WHY a subject-less bucket now groups on the bucket rather than on wording: for a
                # literature-bound criterion the subject is empty -- a query template is a retrieval
                # knob, not a subject -- so grouping fell through to a name+definition Jaccard of at
                # least `overlap`. Measured: the pair this stage exists for scores 0.14 on names and
                # 0.10 with definitions, because one definition is terse and the other is verbose
                # prose, and the clean derivation of 14 October 2026 produced 59 literature-bound
                # proposals of which merge grouped zero across every iteration. The design is
                # "deterministic pairing, then the adjudicator decides", and a pairing this strict
                # means the adjudicator is never asked: the reduction from many proposals to few
                # quantities cannot happen at all. Sharing a canonical unit, a direction and a
                # dimension is a weak signal on its own, which is exactly why it is handed to a model
                # that reads the definitions rather than used to merge anything by itself. Every
                # candidate merge still has to survive `ctx.validate`, may cite only its parents'
                # claims and may not reach for a route neither parent had.
                same_bucket = not same_subject and not same_key and \
                    a["item"].get("dimension") == b["item"].get("dimension")
                if same_subject or same_key or same_bucket \
                        or _overlap(a["item"]["attribute"], b["item"]["attribute"]) >= overlap:
                    parent[find(a["criterion_id"])] = find(b["criterion_id"])
        clusters: dict[str, list[dict[str, Any]]] = {}
        for entry in members:
            clusters.setdefault(find(entry["criterion_id"]), []).append(entry)
        for cluster in clusters.values():
            if len(cluster) < 2:
                continue
            if len(cluster) <= MERGE_GROUP_MAX:
                groups.append(cluster)
                continue
            # A bucket wider than one prompt is split, with the most similarly worded items adjacent
            # so a split does not separate the pair most likely to be one quantity. Wording is a poor
            # grouping test -- which is why it no longer gates grouping -- but it is a fair ordering.
            ordered = sorted(cluster, key=lambda e: (e["item"]["attribute"].get("name") or "").lower())
            groups += [ordered[i:i + MERGE_GROUP_MAX] for i in range(0, len(ordered), MERGE_GROUP_MAX)
                       if len(ordered[i:i + MERGE_GROUP_MAX]) > 1]
    return groups


# Words that say only what the merge group already said: a group shares a unit, a direction and (for a
# consolidation) a dimension, so repeating those back is not a shared property. WHY this list exists at all:
# the failure mode of an abstraction is breadth, and "they are all percentages" is both true of the group and
# no reason to replace eight measurements with one. Stems are compared, so a plural or a longer form of a
# word the group already carries ("toxicities" against the dimension `toxicological_safety`) does not count
# as substance either.
_FAMILY_GENERIC = {
    "they", "them", "these", "those", "this", "that", "are", "all", "also", "same", "each", "every", "both",
    "member", "members", "criterion", "criteria", "endpoint", "endpoints", "item", "items", "measure", "measured",
    "measures", "measurement", "measurements", "quantity", "quantities", "value", "values", "number", "numbers",
    "count", "counts", "unit", "units", "scale", "percent", "percentage", "percentages", "pct", "proportion",
    "proportions", "fraction", "fractions", "share", "rate", "rates", "ratio", "incidence", "incidences",
    "frequency", "frequencies", "higher", "lower", "better", "worse", "direction", "dimension", "reported",
}
# WHY two and not one: a single surviving word is what a restatement of the unit leaves behind once any
# qualifier is added to it -- "all are event percentages" leaves one ("event"), and it still says nothing a
# screen can apply. Measured against this group's own unit, direction and dimension: "they are all
# percentages" and "all of these toxicity endpoints are incidence rates" leave zero, "severe haematological
# toxicity" leaves two, "grade >=3 toxicity requiring dose reduction" five, and the kind of property worth
# consolidating on sixteen. So the floor refuses the empty claims and binds on nothing a reviewer would read
# as a property.
_SHARED_PROPERTY_MIN_NEW_WORDS = 2


def _stem(word: str) -> str:
    """A crude stem, enough to see that two tokens say one thing: a long word by its first five characters, a
    short one by itself without a trailing plural."""
    return word[:5] if len(word) > 5 else word.rstrip("s")


def _substantive_words(text: str, already_said: str) -> set[str]:
    """Stems of `text` that neither `already_said` nor the measurement-generic vocabulary already carries."""
    known = {_stem(w) for w in _tokens(already_said)} | {_stem(w) for w in _FAMILY_GENERIC}
    return {_stem(w) for w in _tokens(text)} - known


def _consolidation(group: list[dict[str, Any]], declared: dict[str, Any],
                   attribute: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """The members a consolidation subsumes, why it is refused -- or None when it stands -- and the
    attribute `aggregation` that computes its declared family reduction.

    Four refusals live here, and each one is the abstraction failing to be checkable rather than the
    criterion failing to validate (`merge_stage` still applies the merge gate's own three):

      * fewer than two usable members: one endpoint is not a family, and the group would lose a lineage
        and gain an abstraction of it in exchange for nothing.
      * members from more than one dimension: a family spanning safety and pharmacokinetics has no shared
        property a single screening criterion can state, however the two are worded.
      * a shared property that is empty, or that only repeats the unit, direction or dimension the group
        already agrees on.
      * a family aggregation that would not be computed: outside `criterion_family_aggregation`, so the
        reduction is prose nobody can compute, or registered but with no executable reduction for this
        attribute's direction (`assessor.family_aggregation_execution`) -- `worst_member` over a
        `within_range` attribute names no end of the scale as the worst one.

    The third return value is what makes the declaration more than a declaration: the aggregation the
    assessor will actually run, which `merge_stage` writes onto the consolidated attribute.
    """
    members, seen = [], set()
    for index in declared.get("members") or []:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(group) or index in seen:
            continue
        seen.add(index)
        members.append(group[index])
    if len(members) < 2:
        return members, (f"consolidation names {len(members)} usable member(s) of the {len(group)} in the group; "
                         f"a family is two or more endpoints"), None
    dimensions = sorted({str(e["item"].get("dimension") or "") for e in members})
    if len(dimensions) > 1:
        return members, (f"consolidation spans dimensions {dimensions}; one screening criterion cannot state a "
                         f"property shared across them"), None
    shared = str(declared.get("shared_property") or "").strip()
    already_said = f"{attribute.get('unit') or ''} {attribute.get('direction') or ''} {dimensions[0]}"
    substantive = _substantive_words(shared, already_said)
    if len(substantive) < _SHARED_PROPERTY_MIN_NEW_WORDS:
        return members, (f"shared_property {shared!r} says nothing the group's unit, direction and dimension do "
                         f"not already say, so there is no property to screen on"), None
    family = str(declared.get("family_aggregation") or "")
    try:
        vocab.require("criterion_family_aggregation", family)
    except vocab.VocabularyViolation as violation:
        return members, f"family_aggregation is not computable: {violation}", None
    executes_as, problem = family_aggregation_execution(family, attribute.get("direction"))
    if problem:
        return members, f"family_aggregation is not computable: {problem}", None
    return members, None, executes_as


def _source_key(route: Any) -> str:
    """A route's source and subject, without the retrieval knobs that say how hard to look.

    WHY a consolidation's route reach is measured on this and a merge's on `criteria.route_key`: for a
    literature-bound family every member's route is `literature_retrieval/search` differing only in its
    `query_template`, which `criteria.RETRIEVAL_PARAMETERS` already classifies as "how hard to look for a
    quantity rather than which quantity is meant". Keyed on the full route, a consolidated criterion could
    only ever carry one member's query -- eight grade >=3 toxicity endpoints would reduce to a criterion
    that searches for diarrhea and claims to measure toxicity burden. Keyed on the source and subject, it
    asks the same source about the same subject with a query for the family it now stands for, and a reach
    for a capability, a question or a target no member had is still refused.
    """
    route = route if isinstance(route, dict) else {}
    return canonical_text([route.get("capability"), route.get("question_kind"), criteria.subject_parameters(route)])


# WHY a reduction's child inherits instead of restating: `merge_groups` forms a group only from items whose
# `quantity_key` agrees, so the group has already established the quantity and the scale before the
# adjudicator is asked anything. Asking it for those fields again asks it to restate a finding, and refusing
# the reduction when it does not makes the gate -- not the judgement -- decide what the pool reduces to.
# Measured on the merge of 14 October 2026, the first time this project ever reached the adjudicator: of 9
# groups over 75 repaired candidates it proposed a reduction for 4 and kept 5 separate with specific
# pharmacological reasons, and all 4 reductions were refused here. Three consolidations because the child
# omitted `direction`, so `worst_member` had no end of the scale to call worst, while every member of each of
# those groups declared one (`lower_better` in two of them, `higher_better` in the bioavailability one); one
# merge because the child omitted `name` and `acceptable_value_sources`, which left two
# `literature_retrieval/search` routes returning `peer_reviewed` claims the attribute no longer admitted,
# while both members declared `["peer_reviewed"]`. Replayed against those nine groups, the inheritance below
# compiles all three consolidations (`worst_member` as `max`, `max` and `min`) into attributes that satisfy
# the registry invariants.
#
# The split, and why it is where it is:
#   `_FIXED_BY_GROUPING`   the fields `quantity_key` groups on. Members cannot disagree on them, and a subset
#                          of a group agrees exactly as the group does, so they are inherited before a
#                          consolidation's `members` are resolved -- which is what the three refused
#                          consolidations needed, `_consolidation` reading the direction to compile
#                          `worst_member`.
#   `_AGREED_BY_MEMBERS`   the fields that say which evidence may answer the question and what a value must
#                          look like. Not keyed, so they are inherited only where every member the reduction
#                          actually folds in says the same thing, measured over those members and not over
#                          the group: a consolidation names the subset it subsumes, so a member whose
#                          evidence policy differs can be left out instead of refusing the whole family.
# Still the adjudicator's, because the group settles none of them: the name, the definition, the rule, which
# of the members' claims support the child, which of their routes it keeps, and -- for a consolidation --
# the members, the shared property and the family reduction (whose `aggregation` `merge_stage` derives).
#
# Where the members disagree the reduction is refused rather than the gate picking an answer: all three of
# those fields decide which claims `assessor.usable_claims` keeps, so admitting a kind a member did not
# accept scores that member's cell on evidence it refused, dropping a kind every member accepted empties a
# cell that then reads as "no data" rather than as a narrowing, and the measurement kind decides whether a
# claim's value counts as a value at all. None of that is the adjudicator's to decide for a member it is
# retiring, and a consolidation can still fold in the subset that does agree. Measured over every lineage
# this store holds (802 candidate versions, 27 groups `merge_groups` forms over them): members disagree on
# the value sources in 2 groups, on the effective determination bases in 1, and on the measurement kind in 2
# (both unitless, mixing ordinal with qualitative and qualitative with categorical members) -- and on none of
# the three in any of the 9 groups of the live merge, so the refusal costs no reduction that has ever been
# proposed while the completion rescues 4.
_FIXED_BY_GROUPING = ("unit", "direction", "value_transform")
_AGREED_BY_MEMBERS = ("measurement_kind", "acceptable_value_sources", "acceptable_determination_bases")


def _acts_as(attribute: dict[str, Any], field: str) -> Any:
    """What an attribute really acts under for one inherited field, so two spellings of one answer are one
    answer: an absent `acceptable_determination_bases` is the assessor's default pair (which is what the
    cell is scored under), a unit is its canonical form, a transform its canonical text."""
    value = attribute.get(field)
    if field == "acceptable_determination_bases":
        return tuple(sorted(value or DEFAULT_DETERMINATION_BASES))
    if field == "acceptable_value_sources":
        return tuple(sorted(value or ()))
    if field == "unit":
        return canonical_unit(value)
    if field == "value_transform":
        return canonical_text(value)
    return value or None


def _determined(members: list[dict[str, Any]], fields: tuple[str, ...]) -> tuple[dict[str, Any], str | None]:
    """What these members have already settled among `fields`, or the reason they settle nothing.

    The literal value is what is handed on, not the canonical form: `%` and `percent` are one unit here but
    `criteria.check_rule` compares the attribute's unit with the cutoff's literally, so inventing a spelling
    no member wrote would be a change of its own.
    """
    attributes = [e["item"]["attribute"] for e in members]
    determined = {}
    for field in fields:
        answers = {_acts_as(attribute, field) for attribute in attributes}
        if len(answers) > 1:
            return {}, (f"the members do not agree on {field} "
                        f"({' vs '.join(sorted({str(a.get(field)) for a in attributes}))}), so the reduction has "
                        f"nothing to inherit and any single answer would change what at least one member's "
                        f"cell is scored on; consolidate the members that agree instead")
        if attributes[0].get(field) is not None:
            determined[field] = attributes[0][field]
    return determined, None


def _cutoff_restated(attribute: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    """The rule with its cutoff written in the attribute's own spelling of the group's unit.

    WHY the gate restates it: `criteria.check_rule` compares the two literally, while `assessor.UNIT_SYNONYMS`
    maps spellings one to one and converts nothing (`percent` *is* `%`, `hr` *is* `h`), so a cutoff written in
    a synonym of the inherited unit -- or a number left without one, which can only be in the attribute's unit
    -- would be refused for a spelling, and refused by the inheritance rather than by anything the child got
    wrong. A cutoff in a canonically different unit is a number compared against the wrong scale, and
    `check_rule` still refuses it.
    """
    cutoff = rule.get("cutoff")
    if not isinstance(cutoff, dict) or not attribute.get("unit") or cutoff.get("unit") == attribute["unit"]:
        return rule
    if cutoff.get("unit") and canonical_unit(cutoff["unit"]) != canonical_unit(attribute["unit"]):
        return rule
    return dict(rule, cutoff=dict(cutoff, unit=attribute["unit"]))


def _inherited_from(members: list[dict[str, Any]], fields: tuple[str, ...],
                    proposal: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """`proposal` completed with what `members` settled among `fields`, or the reason this reduction is
    refused -- the members disagreeing, or the child contradicting what they agree on.

    A field the child states is never overwritten: a child declaring another direction, or another set of
    admissible sources, is asserting something about the quantity its group was formed on, and completing
    silently over it would hide exactly the claim a reviewer would want refused.
    """
    determined, problem = _determined(members, fields)
    if problem:
        return proposal, problem
    attribute = dict(proposal.get("attribute") or {})
    for field, settled in determined.items():
        if attribute.get(field) in (None, "", [], {}):
            attribute[field] = settled
        elif _acts_as(attribute, field) != _acts_as({field: settled}, field):
            return proposal, (f"the child declares {field} {attribute[field]!r} while the members it reduces agree "
                              f"on {settled!r}; a reduction inherits what its group measures rather than "
                              f"restating it")
    return dict(proposal, attribute=attribute, rule=_cutoff_restated(attribute, proposal.get("rule") or {})), None


def _merged_consolidation(parents: list[dict[str, Any]],
                          item: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """The consolidation record a merged child inherits from its parents, or why this merge is refused.

    WHY a merge has to answer this at all: a `merge` claims its members were one quantity all along, so a
    member that stands for a family of endpoints hands that family to the child -- and the child is a new
    lineage whose item is built from the adjudicator's declaration, which carries no consolidation. Dropped,
    the family disappears from the surviving criterion's card while the consolidated parent sits in
    `merged_away` and is counted nowhere: the audit line vanishes at the one point the pool got smaller.

    Two merges are refused rather than guessed at:

      * more than one consolidated member -- the child would have to state two shared properties and two
        family reductions, and a family of families is a `consolidate` over them, which recomputes both;
      * a child measuring differently from its consolidated parent -- the family was never checked against
        the quantity the child declares, which is the reasoning in `_revised`: a merge is not the place to
        redefine what an abstraction stands for.
    """
    inherited = [(p, (p["item"] or {}).get("consolidation")) for p in parents if (p["item"] or {}).get("consolidation")]
    if not inherited:
        return None, None
    if len(inherited) > 1:
        return None, (f"{len(inherited)} members are consolidations, each standing for its own family; one "
                      f"merged criterion cannot state both shared properties, and a family of families is a "
                      f"consolidation over them rather than a merge")
    parent, consolidation = inherited[0]
    changed = _measures_differently(parent["item"].get("attribute") or {}, item["attribute"])
    if changed:
        return None, (f"the merged criterion would inherit {parent['criterion_id']}@v{parent['version']}'s "
                      f"consolidation of {len(consolidation.get('subsumes') or [])} endpoint(s) while measuring "
                      f"something else ({', '.join(changed)}), which that family was never checked against")
    return dict(consolidation, carried_from=f"{parent['criterion_id']}@v{parent['version']}"), None


def _reach_beyond_parents(item: dict[str, Any], parents_claims: set[str], parents_routes: set[str],
                          child_routes: set[str]) -> str | None:
    """What this child asks for that its parents did not have, named so the refusal record says which it was."""
    cited = set(item["supporting_claim_ids"])
    if not cited:
        return "the child cites no supporting claim"
    if not cited <= parents_claims:
        return f"the child cites claims no parent had: {sorted(cited - parents_claims)}"
    if not child_routes <= parents_routes:
        return f"the child declares {len(child_routes - parents_routes)} evidence route(s) no parent declared"
    return None


def merge_stage(ctx: StageContext, iteration: int, *, overlap: float = 0.35) -> dict[str, Any]:
    """Two reductions over one set of groups: `merge` for one quantity described twice, `consolidate` for a
    family of distinct endpoints a screen applies as one criterion.

    WHY the second one exists: grouping on a shared unit and direction first produced groups on 14 October
    2026 -- 10 of them over the live pool of 89 proposals -- and two of those were eight *distinct* toxicity
    endpoints each (any-grade incidences; grade >=3 incidences). `merge`'s own rule, "the same
    quantity, in the same unit and direction, for the same purpose", correctly answers keep-separate for all
    sixteen, so duplication was never what stood between 89 proposals and the roughly 11 attributes an expert
    screens on. The system generates granular endpoints where a screen decides on aggregates, and the missing
    operation is the one that abstracts a family into the criterion that decides. Its risk is the opposite of
    the merge's: not a lost distinction but a criterion too broad to compute or to argue with, which is why a
    consolidation has to name the shared property, the members it subsumes and the aggregation that reduces
    them before this gate applies it.
    """
    pool = ctx.pool.at("merge", iteration)
    groups = [g for g in merge_groups(active(pool.fold(), ("candidate",)), overlap=overlap)
              if frozenset((e["criterion_id"], e["version"]) for e in g) not in ctx.adjudicated]
    # WHY the groups that were *not* reduced carry their reasons into the stage result (which
    # `_stage_recorder` writes to the journal and a `derivation_stage` artifact): an applied merge or
    # consolidation records its own reason on the change record, and these two outcomes record nothing
    # anywhere else. The counts alone are what made "zero merges across every historical round" unreadable
    # -- a reader could not tell a pool of genuinely distinct criteria from a gate refusing every reduction
    # the adjudicator proposed, and those call for opposite repairs.
    stats: dict[str, Any] = {"groups": len(groups), "merged": 0, "consolidated": 0, "kept_separate": 0,
                             "refused": 0, "not_reduced": []}
    if not groups:
        return stats
    views = [{"group": gi, "members": [_view(e, mi) for mi, e in enumerate(g)]} for gi, g in enumerate(groups)]
    response = ctx.call("adjudicator", ADJUDICATOR_SYSTEM, f"Objective: {ctx.task_context['objective_text']}\n\nGroups:\n"
                        + json.dumps(views, ensure_ascii=False, indent=1) + "\n\nCited claims:\n"
                        + ctx.cited_block([e["item"] for g in groups for e in g]), MERGE_SCHEMA, "adjudicate merges")
    for group in groups:
        ctx.adjudicated.add(frozenset((e["criterion_id"], e["version"]) for e in group))

    def not_reduced(index: int, outcome: str, action: Any, reason: str) -> None:
        stats[outcome] += 1
        stats["not_reduced"].append({"group": index, "outcome": outcome, "action": action, "reason": reason[:500]})

    for decision in response.data["decisions"]:
        if not 0 <= decision["group"] < len(groups):
            continue
        group = groups[decision["group"]]
        action = decision.get("action")
        declared = decision.get("consolidated") if action == "consolidate" else decision.get("merged")
        if action not in ("merge", "consolidate") or not declared:
            not_reduced(decision["group"], "kept_separate", action, decision.get("reason") or "")
            continue
        # The quantity and its scale, inherited before anything reads them: `_consolidation` needs the
        # child's direction to know which end of the scale `worst_member` scores, and that is where the
        # three consolidations of 14 October 2026 were refused for a direction all their members declared.
        declared, problem = _inherited_from(group, _FIXED_BY_GROUPING, declared)
        if problem:
            not_reduced(decision["group"], "refused", action, problem)
            continue
        parents = group
        consolidation = None
        if action == "consolidate":
            parents, problem, executes_as = _consolidation(group, declared, declared.get("attribute") or {})
            if problem:
                not_reduced(decision["group"], "refused", action, problem)
                continue
            adjudicator_said = (declared.get("attribute") or {}).get("aggregation")
            consolidation = {"shared_property": str(declared["shared_property"]).strip(),
                             "family_aggregation": declared["family_aggregation"],
                             # The aggregation the declared family reduction compiles to. It is recorded and,
                             # below, written onto the attribute, which is the only half of this pair the
                             # assessor ever reads: a consolidated criterion reaches `assess_cell` as one
                             # attribute over one pooled claim set, with no family left to reduce, so a
                             # `family_aggregation` that is not compiled into `aggregation` is a declaration
                             # the score ignores -- what this field was when it was first added.
                             "executes_as_aggregation": executes_as,
                             # The adjudicator is asked for the attribute's fields, `aggregation` among them,
                             # and it has no way to know which one its family reduction implies. Deriving is
                             # what keeps the two from disagreeing; naming the derived-over declaration is
                             # what keeps the derivation from being silent.
                             **({"replaced_declared_aggregation": adjudicator_said}
                                if adjudicator_said and adjudicator_said != executes_as else {}),
                             # The ids and names of what this criterion stands for, resolved here rather than
                             # taken from the reply: the adjudicator never sees a criterion id, and a reviewer
                             # who cannot follow the abstraction back to the endpoints it replaced cannot object
                             # to it, which is the difference between an abstraction and information loss.
                             "subsumes": [{"criterion_id": e["criterion_id"], "version": e["version"],
                                           "name": e["item"]["attribute"].get("name")} for e in parents]}
        route_key = _source_key if action == "consolidate" else criteria.route_key
        parents_claims = {c for e in parents for c in e["item"]["supporting_claim_ids"]}
        parents_routes = {route_key(r) for e in parents
                          for r in criteria.evidence_routes(e["item"]["attribute"])}
        # A merged child inherits the largest repair count in its group, never a fresh budget: otherwise
        # merging two items that had each been revised to their limit would hand the result an untouched
        # allowance, and the cheapest way past `max_refines` would be to merge.
        item = _item(declared, dimension=parents[0]["item"].get("dimension"),
                     refine_count=max(int(e["item"].get("refine_count") or 0) for e in parents),
                     **({"consolidation": consolidation} if consolidation else {}))
        # The rest of the inheritance, measured over the members this reduction folds in rather than over
        # the whole group: a consolidation names its subset, so what counts as an answer is what that
        # subset accepts, and a member whose evidence policy differs is left out instead of refusing the
        # family. Before `ctx.validate`, so a child silent about an agreed field is completed, not refused.
        item, problem = _inherited_from(parents, _AGREED_BY_MEMBERS, item)
        if problem:
            not_reduced(decision["group"], "refused", action, problem)
            continue
        if consolidation:
            # Written before the validator and before the pool, so what is stored, scored and exported is one
            # value: the declared reduction and the executed aggregation cannot drift apart afterwards
            # because only one of them was ever authored.
            item["attribute"]["aggregation"] = consolidation["executes_as_aggregation"]
        else:
            # A merge over a group that contains a consolidated member carries that member's family forward
            # or is refused; it may not quietly retire the record of what the abstraction replaced.
            inherited, problem = _merged_consolidation(parents, item)
            if problem:
                not_reduced(decision["group"], "refused", action, problem)
                continue
            if inherited:
                item["consolidation"] = inherited
        child_routes = {route_key(r) for r in criteria.evidence_routes(item["attribute"])}
        # An invalid child, one citing evidence its parents did not, or one reaching for a data source no
        # parent was bound to, is not applied: a reduction combines what the pool already has, and that holds
        # for a consolidation exactly as for a merge -- an abstraction is still not a licence to read a source
        # or cite a claim the family never had.
        reach = _reach_beyond_parents(item, parents_claims, parents_routes, child_routes)
        problems = ctx.validate(item)
        if problems or reach:
            not_reduced(decision["group"], "refused", action, "; ".join(problems) if problems else reach)
            continue
        if action == "consolidate":
            pool.consolidate(parents, dict(item, validator_problems=[]), reason_text=decision["reason"])
            stats["consolidated"] += 1
        else:
            pool.merge(parents, dict(item, validator_problems=[]), reason_text=decision["reason"])
            stats["merged"] += 1
    return stats


# --- REFINE ----------------------------------------------------------------------------------

def refine_stage(ctx: StageContext, iteration: int) -> dict[str, Any]:
    pool = ctx.pool.at("refine", iteration)
    stats: dict[str, Any] = {"revised": 0, "withdrawn": 0, "still_failing": 0, "deferred": 0, "refused": 0}
    for batch in _chunks(active(pool.fold(), ("needs_refine",)), BATCH["refine"]):
        try:
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
                item, refused = _revised(entry, dict(entry["item"], **revision["proposal"]), refine_count=count)
                if refused:
                    # The attempt is not charged to `refine_count`: the budget bounds how often one proposal
                    # is rewritten, and a rewrite that was never applied is not one of those times. The item
                    # keeps `needs_refine`, so a later iteration may repair it without redefining it, and
                    # `promote` defers it if its validator problems are still open.
                    _not_revised(stats, entry, refused)
                    continue
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
        except ModelError as error:
            if error.error_class == "quota_exhausted":
                raise
            stats["batches_unresolved"] = stats.get("batches_unresolved", 0) + 1
            stats.setdefault("unresolved_reasons", []).append(f"{error.error_class}: {error}"[:160])
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
    registered = ctx.registered()
    candidates = active(pool.fold(), ("candidate", "needs_refine"))
    out = {"accepted": [], "disputed": [], "deferred": [], "duplicates": []}
    _critique(ctx, [e for e in candidates if not ctx.validate(e["item"])],
              "final check before promotion", out)
    for entry in candidates:
        item = entry["item"]
        duplicate = duplicate_of_registered(item["attribute"], registered)
        if duplicate is not None:
            pool.set_state(entry, "filtered_out", operation="remove", reason_kind="duplicate_of_registered",
                           reason_text=duplicate_reason(duplicate))
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
            # The promotion site: the registry is told what stands behind each of this criterion's
            # numbers, so the authority it needs is computed from the whole decision-bearing object
            # rather than from the rule's two fields (`core/bound_support.py`, §6 F2/F3).
            support = bound_support.validate(attribute, rule, claims=[ctx.claims_by_id[c] for c in
                                                                      item["supporting_claim_ids"]
                                                                      if c in ctx.claims_by_id])
            attr_ref, rule_ref = criteria.propose(ctx.core, ctx.task_id, attribute, rule, by=by_proposer,
                                                  dispute=dispute, support=support)
        except criteria.InvariantViolation as violation:
            pool.set_state(entry, "deferred_next_round", operation="defer", reason_kind="registry_invariant",
                           reason_text=str(violation))
            out["deferred"].append({"criterion_id": entry["criterion_id"], "name": item["attribute"].get("name"),
                                    "problems": [str(violation)]})
            continue
        # The freshly registered attribute joins the set this loop tests against, so a second pool
        # item measuring the same quantity is refused in this same promotion pass.
        registered.append(dict(attribute, version=int(attr_ref.split("@v")[1])))
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
