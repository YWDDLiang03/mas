"""Typed administration-route facts from a fixed admitted clinical-claim cache.

No retrieval, document reading or model calls. Original numeric claims are never
edited: a Boolean route assertion is a separate, traceable projection.
"""
from __future__ import annotations

import copy
import json
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any

from mas.core.canonical import sha256_hex

POLICY_VERSION = "clinical_route_projection_v1"
EXISTENCE_SEMANTICS = {"kind": "documented_existence_v1", "property": "administration_route", "value": "oral"}


def supports_attribute(attribute: dict[str, Any]) -> bool:
    return (attribute.get("aggregation") == "any_true" and attribute.get("measurement_kind") == "categorical"
            and attribute.get("unit") is None and attribute.get("existence_semantics") == EXISTENCE_SEMANTICS)


def load_source_records(core, source_refs) -> dict[str, dict[str, Any]]:
    """Pin only existing source metadata. sha256 is the canonical payload hash.

    Selection happens once at pin time; runtime must reload the returned artifact
    ids and verify these hashes rather than call this helper to select newer data.
    """
    refs = sorted({str(ref) for ref in source_refs if ref})
    found = {}
    for start in range(0, len(refs), 400):
        batch = refs[start:start + 400]
        rows = core.store.db.execute("SELECT artifact_id,body,sha256 FROM artifacts WHERE kind='source' "
            "AND json_extract(body,'$.payload.source_id') IN (" + ",".join("?" for _ in batch) + ") ORDER BY created_at, artifact_id", batch)
        for artifact_id, body, digest in rows:
            envelope = json.loads(body)
            if sha256_hex(envelope) != digest:
                raise ValueError(f"cached source artifact hash differs: {artifact_id}")
            source = envelope["payload"]
            found[source["source_id"]] = {"source": source, "artifact_id": artifact_id, "sha256": sha256_hex(source)}
    return found


def _norm(value):
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub("[‐‑‒–—−]", "-", text)
    return re.sub(r"\s*-\s*", "-", " ".join(text.split()))


class ClinicalRouteCache:
    supports_attribute = staticmethod(supports_attribute)

    def __init__(self, claims, sources_by_id, candidates, *, source_provenance=None, cutoff_date=None):
        self._facts = defaultdict(list)
        self._ids, aliases = {}, defaultdict(set)
        self._catalog = {}
        source_provenance = source_provenance or {}
        if isinstance(source_provenance, list):
            source_provenance = {row["claim_id"]: row for row in source_provenance}
        if isinstance(candidates, dict):
            candidates = candidates.get("universe", list(candidates.values()))
        for row in candidates:
            identifiers = {str(i["scheme"]): str(i["value"]) for i in row.get("identifiers", [])}
            key = row.get("inchikey") or identifiers.get("inchikey")
            canonical = row.get("candidate_id") or row.get("candidate_ref") or ("cand_inchikey-" + key if key else None)
            if canonical is None:
                continue
            self._catalog[canonical] = copy.deepcopy(row)
            for value in (canonical, key, "cand_inchikey-" + key if key else None,
                          row.get("chembl_id") or identifiers.get("chembl_id")):
                if value:
                    self._ids[_norm(value)] = canonical
            names = [row.get("name"), row.get("preferred_label"), *row.get("synonyms", [])]
            names += [a.get("alias") if isinstance(a, dict) else a for a in row.get("aliases", [])]
            for name in names:
                alias = _norm(name)
                if len(alias) >= 4:
                    aliases[alias].add(canonical)
        self._aliases = {alias: next(iter(ids)) for alias, ids in aliases.items() if len(ids) == 1}
        pattern = "|".join(re.escape(alias) for alias in sorted(self._aliases, key=lambda s: (-len(s), s)))
        self._matcher = re.compile(r"(?<![a-z0-9])(?:" + pattern + r")(?![a-z0-9])") if pattern else None
        counters = Counter()
        lineage = []
        seen = set()
        for claim in sorted(claims, key=lambda c: c.get("claim_id", "")):
            cid = claim.get("claim_id")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            lineage.append({"claim_id": cid, "sha256": sha256_hex(claim), "source_ref": claim.get("source_ref")})
            reason = self._admit(claim, sources_by_id, source_provenance.get(cid), cutoff_date)
            counters[reason] += 1
        self._manifest = {"policy": POLICY_VERSION, "cutoff_date": cutoff_date,
            "claims_digest": sha256_hex(lineage), "input_claim_count": len(lineage),
            "source_payload_hashes": {ref: sha256_hex(source) for ref, source in sorted(sources_by_id.items())},
            "candidate_catalog_sha256": sha256_hex(self._catalog), "unique_alias_count": len(self._aliases),
            "ambiguous_alias_count": sum(len(ids) > 1 for ids in aliases.values()), "outcomes": dict(counters),
            "projected_candidate_count": len(self._facts), "projected_fact_count": sum(map(len, self._facts.values())),
            "reads_new_literature": False, "calls_models": False}

    def manifest(self):
        return copy.deepcopy(self._manifest)

    @staticmethod
    def _clinical(claim, source):
        if source.get("source_status") != "peer_reviewed_paper":
            return False
        quote = (claim.get("location") or {}).get("quoted_span", "")
        scope = json.dumps(claim.get("scope") or {}, ensure_ascii=False)
        text = _norm(quote + " " + scope + " " + str(source.get("title", "")) + " " + str(claim.get("attribute_hint", "")))
        if re.search(r"\b(?:rats?|mice|mouse|murine|rodents?|rabbits?|dogs?|canine|monkeys?|in vitro|xenografts?)\b", text):
            return False
        kinds = _norm(" ".join(source.get("pub_types") or []))
        if "review" in kinds:
            return False
        human = re.search(r"\b(?:patients?|participants?|volunteers?|subjects?|women|woman|men|adults?|clinical)\b", text)
        primary = ("clinical trial" in kinds or "case reports" in kinds or
                   re.search(r"\b(?:study|trial|dose escalation|case report)\b", _norm(source.get("title"))))
        return bool(human and primary)

    def _admit(self, claim, sources, provenance, cutoff):
        if claim.get("admission_state") != "admitted":
            return "not_admitted"
        if claim.get("evidence_kind") != "peer_reviewed" or claim.get("determination_basis") in ("predicted", "simulated"):
            return "not_direct_clinical_source"
        location = claim.get("location") or {}
        checked = location.get("span_checked_against_source")
        if checked is False or not (checked is True or "quote_verified" in claim.get("admission_reasons", [])):
            return "span_not_verified"
        source = sources.get(claim.get("source_ref"))
        if not source:
            return "source_metadata_absent"
        if _norm(source.get("retraction_state")) in ("retracted", "withdrawn"):
            return "source_retracted"
        if cutoff:
            issued = str(source.get("issued_date") or "")
            if not re.match(r"^\d{4}(?:-\d\d-\d\d)?$", issued) or issued[:4] > cutoff[:4] or \
                    (len(issued) == 4 and issued == cutoff[:4]) or (len(issued) > 4 and issued > cutoff):
                return "publication_date_outside_or_unresolved"
        if not self._clinical(claim, source):
            return "not_unambiguous_human_clinical_context"
        quote = _norm(location.get("quoted_span"))
        if re.search(r"\b(?:will receive|will be administered|planned|proposed|could be administered|may be administered)\b", quote):
            return "prospective_or_conditional_route"
        hits = list(self._matcher.finditer(quote)) if self._matcher else []
        projected, pending_negative = 0, False
        for hit in hits:
            candidate = self._aliases[hit.group()]
            after = quote[hit.end():hit.end() + 160]
            negative = re.match(r"\s+(?:cannot|can not|must not)\s+(?:be\s+)?(?:administered|given|taken)\s+(?:orally|by mouth)\b", after)
            if negative and claim.get("scope_match") not in (True, "matched", "applicable", "exact"):
                pending_negative = True
                continue
            direct = re.match(r"\s+(?:(?:was|were|is|are|has been|had been)\s+)?(?:administered|given|taken|dosed)\s+(?:orally|by mouth)\b", after)
            bracket = re.match(r"\s*\(([^)]{1,100})\)", after)
            bracket_oral = bool(bracket and re.search(r"\d\s*(?:mg|ug|g)\b", bracket[1]) and re.search(r"\b(?:po|orally)\b", bracket[1]))
            before = quote[max(0, hit.start() - 60):hit.start()]
            oral_dose = bool(re.search(r"\d+(?:\.\d+)?\s*(?:mg|ug|g)(?:\s+(?:qd|bid|tid|once|twice|daily)){0,4}\s+oral\s*$", before)
                             and not re.search(r"\b(?:not|no|without)\b", before))
            if not (negative or direct or bracket_oral or oral_dose):
                continue
            proof_end = hit.end() + (negative.end() if negative else direct.end() if direct else bracket.end() if bracket_oral else 0)
            if any(other.start() >= hit.end() and other.start() < proof_end and self._aliases[other.group()] != candidate for other in hits):
                continue
            negative_flag = bool(negative)
            origin = {"policy": POLICY_VERSION, "claim_id": claim["claim_id"], "claim_sha256": sha256_hex(claim),
                "source_ref": claim["source_ref"], "source_sha256": sha256_hex(source), "source_provenance": provenance,
                "location": copy.deepcopy(location), "document_artifact_id": claim.get("document_artifact_id"),
                "determination_basis": claim.get("determination_basis"), "value": claim.get("value"), "unit": claim.get("unit"),
                "source_verification_status": claim.get("verification_status"), "source_scope_match": claim.get("scope_match")}
            key = sha256_hex({"origin": origin, "candidate": candidate, "assertion": not negative_flag})
            if any(item["projection_id"] == key for item in self._facts[candidate]):
                continue
            label = self._catalog[candidate].get("name") or self._catalog[candidate].get("preferred_label") or candidate
            statement = (f"An explicit clinical assertion records that {label} cannot be administered orally; its scope was already matched."
                         if negative_flag else f"A human clinical record documents oral administration of {label}.")
            self._facts[candidate].append({"projection_id": key, "source_ref": claim["source_ref"],
                "source_document_ref": claim.get("document_artifact_id"), "candidate_ref": candidate,
                "evidence_kind": claim["evidence_kind"], "determination_basis": "derived", "value": not negative_flag,
                "unit": None, "admission_state": "admitted", "admission_reasons": ["inherited_span_verified", "unique_candidate_alias", "explicit_human_route"],
                "location": copy.deepcopy(location), "reading_depth": claim.get("reading_depth") or "not_read", "polarity": "supports",
                "claim_text": location.get("quoted_span", ""), "claim_text_marker": "verbatim", "normalized_statement": statement,
                "scope": copy.deepcopy(claim.get("scope")), "scope_match": claim.get("scope_match", "unknown"),
                "verification_status": claim.get("verification_status", "unverified"), "derived_from": origin,
                "entity_binding": {"canonical_candidate_ref": candidate, "matched_alias": hit.group(), "rule": "unique_catalog_alias_in_route_clause"},
                "existence_evidence": {"property": "administration_route", "value": "oral", "assertion": "negative" if negative_flag else "positive",
                                       "scope_verified": bool(negative_flag)},
                "extraction_actor": {"kind": "tool", "id": POLICY_VERSION, "role": "deterministic_projection"}})
            projected += 1
        return "projected" if projected else "negative_scope_unresolved" if pending_negative else "no_explicit_bound_route_clause"

    def claims_for(self, identity, *, attribute_ref=None):
        if isinstance(identity, str):
            requested = identity
            options = [identity]
        else:
            requested = identity.get("candidate_id") or identity.get("candidate_ref")
            options = [requested, *[i.get("value") for i in identity.get("identifiers", [])]]
        matched = {self._ids[_norm(value)] for value in options if value and _norm(value) in self._ids}
        if len(matched) != 1:
            return []
        canonical = next(iter(matched))
        result = copy.deepcopy(self._facts.get(canonical, []))
        for claim in result:
            claim["candidate_ref"] = requested or canonical
            claim["attribute_ref"] = attribute_ref
            claim["claim_id"] = "claim_route_" + sha256_hex({"projection": claim["projection_id"],
                "candidate_ref": claim["candidate_ref"], "attribute_ref": attribute_ref})[:24]
        return result
