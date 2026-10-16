"""Immutable, span-checked literature supplements, attached to an explicit task version.

Selection is exploratory and recorded. A supplement reuses measurements for an exact
compound and target; it neither fills unrelated cells nor creates scoring criteria.
"""

from __future__ import annotations

import math
import re
from typing import Any

from . import ledger, reading, task
from .canonical import sha256_hex
from .clock import utc_now
from .journal import actor
from .runtime import Core


class SupplementError(ValueError):
    pass


def _identifiers(items: list[dict[str, Any]]) -> dict[str, str]:
    return {str(i["scheme"]).lower(): str(i["value"]).strip().upper()
            for i in items if i.get("scheme") and i.get("value")}


def create_verified(core: Core, *, source_run_id: str, document_ref: str,
                    candidate_identifiers: list[dict[str, str]], reviews: list[dict[str, Any]],
                    selection_rationale: str, by: dict[str, Any]) -> str:
    """Review every extraction, retaining exclusions as well as accepted measurements.

    Each review names claim_id, target_chembl_id, decision, reason and conditions.
    Included claims require conditions.target_variant == 'wild_type'; engineered
    assay constructs and unknown conditions are recorded separately in conditions.
    No caller-supplied number or quote can replace the original ledger claim.
    """
    if not selection_rationale.strip() or not _identifiers(candidate_identifiers):
        raise SupplementError("selection rationale and exact candidate identifiers are required")
    if not any(i.get("scheme") in ("inchikey", "chembl", "chembl_molecule") for i in candidate_identifiers):
        raise SupplementError("a structural or authoritative compound identifier is required")
    envelope = core.artifacts.get(document_ref)
    if envelope["kind"] != "document":
        raise SupplementError("document_ref must identify the original reader document")
    document = envelope["payload"]
    original = {c["claim_id"]: c for c in ledger.claims(core, [source_run_id], admitted_only=False)
                if c.get("document_artifact_id") == document_ref}
    reviewed = {r["claim_id"]: r for r in reviews}
    if not original or len(reviewed) != len(reviews) or set(reviewed) != set(original):
        raise SupplementError("review every extracted claim exactly once, including quarantined claims")
    passages = {p["passage_id"]: p for p in document["passages"]}
    accepted, excluded = [], []
    for claim_id, claim in original.items():
        review = reviewed[claim_id]
        if review.get("decision") not in ("include", "exclude") or not review.get("reason"):
            raise SupplementError(f"{claim_id}: explicit scope decision and reason are required")
        conditions = review.get("conditions") or {}
        if review["decision"] == "exclude":
            excluded.append({"claim_id": claim_id, "review": review})
            continue
        location = claim.get("location") or {}
        passage = passages.get(location.get("locator_value"))
        value = claim.get("value")
        verified = (claim.get("admission_state") == "admitted"
                    and claim.get("determination_basis") == "measured"
                    and claim.get("evidence_kind") == "peer_reviewed"
                    and location.get("span_checked_against_source") is True
                    and passage is not None
                    and reading.quote_found(location.get("quoted_span", ""), passage["text"])
                    and isinstance(value, (int, float)) and not isinstance(value, bool)
                    and math.isfinite(value) and value > 0
                    and reading.value_in_quote(float(value), location.get("quoted_span", "")))
        if not verified:
            raise SupplementError(f"{claim_id}: only admitted, span-checked point measurements may be reused")
        if conditions.get("target_variant") != "wild_type" or not review.get("target_chembl_id"):
            raise SupplementError(f"{claim_id}: include only explicitly reviewed wild-type target measurements")
        if re.search(r"\bmutant", (claim.get("scope") or {}).get("population_or_system") or "", re.I):
            raise SupplementError(f"{claim_id}: the original extraction identifies a mutant target")
        if not conditions.get("assay") or "unknown_conditions" not in conditions:
            raise SupplementError(f"{claim_id}: retain assay and unknown conditions")
        accepted.append({"target_chembl_id": review["target_chembl_id"], "claim": claim,
                         "scope_review": review})
    if not accepted:
        raise SupplementError("a verified supplement must contain at least one accepted measurement")
    record = {"supplement_version": 1, "source_run_id": source_run_id,
              "document_ref": document_ref, "document_sha256": sha256_hex(document),
              "source_ref": document["source_id"], "candidate_identifiers": candidate_identifiers,
              "claims": accepted, "excluded_claims": excluded,
              "selection": {"kind": "exploratory_known_gap_source", "rationale": selection_rationale,
                            "is_independent_candidate_search": False},
              "reviewed_by": by, "created_at": utc_now()}
    return core.artifacts.put("verified_supplement", record)


def load(core: Core, ref: str) -> dict[str, Any]:
    cache = getattr(core, "_verified_supplements", None)
    if cache is None:
        cache = core._verified_supplements = {}
    if ref not in cache:
        envelope = core.artifacts.get(ref)
        if envelope["kind"] != "verified_supplement" or envelope["payload"].get("supplement_version") != 1:
            raise SupplementError(f"{ref} is not a verified supplement")
        record = envelope["payload"]
        if sha256_hex(core.artifacts.payload(record["document_ref"])) != record["document_sha256"]:
            raise SupplementError(f"{ref}: source document digest differs")
        cache[ref] = record
    return cache[ref]


def binding(core: Core, context: dict[str, Any]) -> dict[str, Any]:
    entries = [{"ref": ref, "digest": sha256_hex(load(core, ref))}
               for ref in sorted(set(context.get("verified_supplement_refs") or []))]
    return {"entries": entries, "digest": sha256_hex(entries)}


def attach(core: Core, task_id: str, supplement_ref: str, *, by: dict[str, Any]) -> tuple[str, int]:
    """Create a task version before freezing its profile; never edit a frozen version."""
    load(core, supplement_ref)
    context = task.get(core, task_id)
    refs = sorted(set(context.get("verified_supplement_refs") or []))
    if supplement_ref in refs:
        return task_id, context["version"]
    task_ref = f"{task_id}@v{context['version']}"
    for event in core.journal.replay(task_id):
        if event.event_type == "preregistration.recorded":
            policy = core.artifacts.payload(event.payload["artifact_id"]).get("policy", {})
            if policy.get("task_ref") == task_ref:
                raise SupplementError("task version already has a frozen profile; create a new reading first")
    for stream in core.journal.streams("run_"):
        events = core.journal.replay(stream, 1, 1)
        if events and events[0].event_type == "run.created" and events[0].payload.get("task_id") == task_id:
            run_binding = core.artifacts.payload(events[0].payload["binding_artifact_id"])
            if run_binding.get("task_context_id@v") == task_ref:
                # Registered reduction only changes the criteria and finishes before
                # evidence attachment in the normal workflow. Its old version and
                # binding remain immutable when attachment creates the next version.
                run_states = [event.state_to for event in core.journal.replay(stream)
                              if event.event_type.startswith("run.") and event.state_to]
                completed_reduction = (run_binding.get("run_purpose") == "criteria_derivation"
                                       and run_binding.get("operation") == "registered_reduction"
                                       and run_states and run_states[-1] == "completed")
                if not completed_reduction:
                    raise SupplementError("task version is already bound to a run; create a new reading first")
    spec = {k: v for k, v in context.items()
            if k not in ("task_context_id", "version", "supersedes", "created_by")}
    spec["verified_supplement_refs"] = sorted(refs + [supplement_ref])
    return task.record_version(core, spec, task_id=task_id, by=by)


def lookup(core: Core, refs: list[str] | tuple[str, ...], *, candidate: dict[str, Any],
           identity: dict[str, Any], attribute: dict[str, Any], cutoff_date: str | None = None) -> list[dict[str, Any]]:
    """Exact compound × target lookup, shared by every candidate in a bound run."""
    from . import criteria

    if attribute.get("measurement_kind") != "quantitative" or attribute.get("unit") != "pChEMBL":
        return []
    targets = {(r.get("parameters") or {}).get("target_chembl_id") for r in criteria.evidence_routes(attribute)} - {None}
    if not refs or not targets:
        return []
    identifiers = _identifiers(identity.get("identifiers") or [])
    out, seen = [], set()
    for ref in refs:
        record = load(core, ref)
        expected = _identifiers(record["candidate_identifiers"])
        shared = expected.keys() & identifiers.keys()
        if not shared or any(expected[k] != identifiers[k] for k in shared):
            continue
        document = core.artifacts.payload(record["document_ref"])
        issued = document.get("source_hit", {}).get("first_publication_date") or document.get("year")
        if cutoff_date and (not issued or str(issued)[:10] > cutoff_date):
            continue
        for entry in record["claims"]:
            claim = entry["claim"]
            if entry["target_chembl_id"] not in targets or claim["claim_id"] in seen:
                continue
            seen.add(claim["claim_id"])
            out.append(dict(claim, candidate_ref=candidate["candidate_id"],
                            attribute_ref=f"{attribute['attribute_id']}@v{attribute['version']}",
                            conditions=entry["scope_review"]["conditions"],
                            verified_supplement_ref=ref, reused_from_claim_id=claim["claim_id"]))
    return out


def record_reuse(core: Core, stream_id: str, claims: list[dict[str, Any]], *,
                 ids: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Expose reused claims in this run's ledger without changing their source records."""
    out = []
    who = actor("tool", "verified-supplement-lookup", "evidence_source")
    for claim in claims:
        claim_id = "claim_supp_" + sha256_hex({"stream_id": stream_id, "source_claim": claim["claim_id"],
                                               "attribute_ref": claim["attribute_ref"]})[:24]
        reused = dict(claim, claim_id=claim_id)
        ledger.record_claim(core, stream_id, reused, by=who, admission_state="admitted",
                            admission_reasons=claim["admission_reasons"], ids=ids)
        out.append(reused)
    return out
