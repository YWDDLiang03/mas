"""Pinned user observations for domain-neutral screening; no remote inference.

An upload establishes what its rows declare, not peer review or suitability.  The
workflow owns task creation and permission to run models.  This module supplies
local identity/evidence hooks and literal task-constraint templates only.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from typing import Any

from . import criteria, ledger
from .broker import ProviderResponse, ToolContract
from .canonical import canonical_text, sha256_hex

ADAPTER = {"adapter_id": "uploaded_candidates", "adapter_version": "1", "primary_scheme": "uploaded_id"}
DIMENSIONS = [{"dimension": "uploaded_properties", "focus":
    "Distinct task-relevant uploaded properties, retaining their exact conditions, units and declared evidence basis; "
    "no drug, receptor or administration assumptions. Observed values do not establish a required cutoff."}]
CAPABILITY = "uploaded_measurement_lookup"
TOOL_ID = "tool_uploaded_measurements"
PROJECTION_POLICY = "uploaded_exact_property_conditions_v1"
ROUTE_ENCODING_VERSION = "uploaded_condition_encoding_v2"


def route_conditions(value):
    """A text condition is a lossless description shorthand, never a fuzzy match."""
    if isinstance(value, str):
        return {"description": value}
    return value if isinstance(value, dict) else None


class UploadedRequirementsPending(ValueError):
    def __init__(self, findings):
        super().__init__("Clarify the uploaded task requirements before generating criteria.")
        self.findings = findings


class UploadedEvidence:
    def __init__(self, candidates, measurements, *, library_id: str, dataset_sha256: str,
                 source_provenance: dict | None = None):
        if not library_id or not dataset_sha256:
            raise ValueError("Uploads require a fixed library identity and dataset hash.")
        self.candidates, self.measurements = deepcopy(list(candidates)), deepcopy(list(measurements))
        self.library_id, self.dataset_sha256 = library_id, dataset_sha256
        self.source_provenance = deepcopy(source_provenance or {})
        self.by_id = {}
        for row in self.candidates:
            key = row.get("candidate_id")
            if not isinstance(key, str) or not key.strip() or key in self.by_id:
                raise ValueError("Each uploaded candidate needs a unique non-empty string candidate_id.")
            if row.get("entity_kind", "general") not in ("drug", "carrier", "general"):
                raise ValueError("Unsupported uploaded entity kind.")
            self.by_id[key] = row
        seen = set()
        for row in self.measurements:
            mid = row.get("measurement_id")
            if not isinstance(mid, str) or not mid or mid in seen:
                raise ValueError("Each observation needs a unique measurement_id.")
            seen.add(mid)
            if row.get("candidate_id") not in self.by_id:
                raise ValueError(f"Observation {mid} does not name a member of this candidate library.")
            if not isinstance(row.get("property_id"), str) or not row["property_id"].strip():
                raise ValueError(f"Observation {mid} needs a property_id.")
            if row["property_id"] != row["property_id"].strip():
                raise ValueError("property_id must be the trimmed uploaded property, without remapping.")
            if not isinstance(row.get("conditions", {}), dict):
                raise ValueError(f"Observation {mid} conditions must be an object.")
            if row.get("basis") not in criteria.DETERMINATION_BASES:
                raise ValueError(f"Observation {mid} needs an explicitly declared evidence basis.")
            value = row.get("value")
            if value is not None and type(value) not in (bool, int, float, str):
                raise ValueError(f"Observation {mid} has an unsupported value type.")
            if type(value) in (int, float) and not math.isfinite(value):
                raise ValueError(f"Observation {mid} must contain a finite number.")
        self.namespace = "upload:" + sha256_hex({"library_id": library_id,
            "candidates": self.candidates, "dataset_sha256": dataset_sha256})
        self._manifest = {"projection_policy": PROJECTION_POLICY, "library_id": library_id,
            "namespace": self.namespace, "dataset_sha256": dataset_sha256,
            "candidate_sha256": sha256_hex(self.candidates), "measurements_sha256": sha256_hex(self.measurements),
            "candidate_count": len(self.candidates), "measurement_count": len(self.measurements),
            "source_provenance": self.source_provenance, "reads_new_literature": False,
            "rows": [{"measurement_id": r["measurement_id"], "sha256": sha256_hex(r)} for r in self.measurements]}
        self._manifest["hash"] = sha256_hex(self._manifest)
        self._claims = None
        self._claims_by_key = {}

    def manifest(self):
        return deepcopy(self._manifest)

    @property
    def route_encoding_version(self):
        """Execution identity; deliberately separate from immutable factual rows."""
        return ROUTE_ENCODING_VERSION

    def property_catalog(self):
        """Metadata only: no candidate identities, observations, ranges or cutoffs."""
        result = {}
        for row in self.measurements:
            key = row["property_id"]
            item = result.setdefault(key, {"property_id": key, "property_label": row.get("property_label") or key,
                "units": [], "conditions": [], "bases": [], "value_types": []})
            for field, value in (("units", row.get("unit")), ("conditions", row.get("conditions") or {}),
                                 ("bases", row["basis"]), ("value_types", self._value_type(row.get("value")))):
                if value not in item[field]:
                    item[field].append(deepcopy(value))
        return [result[key] for key in sorted(result)]

    @staticmethod
    def _value_type(value):
        return "boolean" if type(value) is bool else "numeric" if type(value) in (int, float) else (
            "text" if isinstance(value, str) else "missing")

    def catalog(self):
        return [{"capability": CAPABILITY, "question_kind": "measurement", "identifier_scheme": "uploaded_id",
            "parameters": {"property": "Exact property_id from properties",
                           "conditions": {"description": "<exact recorded description text>"}},
            "units": "Each observation retains its declared unit; use only compatible scales.",
            "evidence_kind": "user_supplied_document", "properties": self.property_catalog(),
            "note": "Local uploaded observations only. Preserve conditions and explicit determination bases; "
                    "conditions must copy the complete recorded object from properties, for example "
                    "{\"description\": \"DLS; aqueous dispersion; 25 C\"}. A plain string is only the exact "
                    "shorthand for a description-only object; other condition keys are never discarded. "
                    "Unsupported or absent properties remain unknown. Never infer task cutoffs from these values."}]

    def identity_hook(self, request):
        records = []
        for key in request["members"]:
            row = self.by_id.get(key)
            records.append({"candidate_id": key, "input_label": key,
                "preferred_label": (row or {}).get("label") or key,
                "identifiers": ([{"scheme": "uploaded_id", "value": key, "scheme_authority": self.namespace}]
                                + deepcopy(row.get("identifiers") or [])) if row else [],
                "aliases": [], "identity_link_basis": "exact_identifier_match" if row else "unresolved",
                "identity_review_state": "not_required", "entity_kind": (row or {}).get("entity_kind", "general"),
                "upload_manifest_hash": self._manifest["hash"], "identity_namespace": self.namespace})
        return records

    def supports_attribute(self, attribute):
        return any(r.get("capability") == CAPABILITY and r.get("question_kind") == "measurement"
                   for r in criteria.evidence_routes(attribute))

    def claims_for(self, candidate_id, *, attribute_ref=None, attribute):
        if self._claims is None:
            raise ValueError("Materialize the pinned upload before assessing its observations.")
        routes = [r for r in criteria.evidence_routes(attribute)
                  if r.get("capability") == CAPABILITY and r.get("question_kind") == "measurement"]
        selected = {}
        for route in routes:
            parameters = route.get("parameters") or {}
            prop = parameters.get("property")
            conditions = route_conditions(parameters.get("conditions", {}))
            if conditions is None:
                continue
            for claim in self._claims_by_key.get((candidate_id, prop, canonical_text(conditions)), []):
                # Attribute binding is a projection; the original ledger claim stays unchanged.
                selected[claim["claim_id"]] = dict(claim, attribute_ref=attribute_ref)
        return deepcopy(list(selected.values()))

    def evidence_hook(self, request):
        attr = request["attribute"]
        claims = self.claims_for(request["candidate_id"], attribute=attr,
            attribute_ref=f"{attr['attribute_id']}@v{attr['version']}")
        reason = "matched" if claims else "no_exact_property_and_conditions" if self.supports_attribute(attr) else "unsupported_route"
        # Always handle generic mode, including missing data. Never fall through to a drug tool.
        return claims, None, [f"{PROJECTION_POLICY}:{ROUTE_ENCODING_VERSION}:{reason}:{self._manifest['hash']}"]

    def materialize(self, core, task_id: str, *, by):
        """Idempotently admit structure-checked rows without asserting scientific authority."""
        existing = {c["claim_id"]: c for c in ledger.claims(core, [task_id])}
        expected, sources = [], {}
        for row in self.measurements:
            digest = sha256_hex({"namespace": self.namespace, "dataset": self._manifest["hash"], "row": row})
            claim_id = "claim_uploaded_" + digest
            provenance = deepcopy(row.get("provenance") or self.source_provenance)
            if row.get("declared_source"):
                provenance.setdefault("declared_source", row["declared_source"])
            original_source = row.get("source_id") or provenance.get("filename") or "uploaded observations"
            source_ref = "src_uploaded_" + sha256_hex({"namespace": self.namespace,
                "dataset": self._manifest["hash"], "original_source_id": original_source,
                "declared_source": provenance.get("declared_source")})
            title = provenance.get("filename") or provenance.get("declared_source") or str(original_source)
            source = {"source_id": source_ref, "source_status": "user_supplied_document",
                "access_state": "full_text_available", "title": title,
                "identifiers": [{"scheme": "uploaded_source", "value": str(original_source)}],
                "version": self._manifest["hash"], "upload_namespace": self.namespace,
                "dataset_manifest_hash": self._manifest["hash"], "provenance": dict(self.source_provenance,
                    **{key: provenance[key] for key in ("filename", "content_sha256", "declared_source") if key in provenance})}
            if source_ref not in sources:
                ledger.put_source(core, source)
                sources[source_ref] = {"source_ref": source_ref, "artifact_id": core.artifacts.put("source", source),
                                       "sha256": sha256_hex(source)}
            statement = row.get("normalized_statement") or (
                f"{self.by_id[row['candidate_id']].get('label') or row['candidate_id']}: "
                f"{row.get('property_label') or row['property_id']} = {json.dumps(row.get('value'), ensure_ascii=False)} "
                f"{row.get('unit') or ''}; conditions: {canonical_text(row.get('conditions') or {})}; "
                f"declared basis: {row['basis']}")
            claim = {"claim_id": claim_id, "candidate_ref": row["candidate_id"], "source_ref": source_ref,
                "claim_type": "property_observation", "claim_text": statement, "normalized_statement": statement,
                "entities": [row["candidate_id"]], "attribute_hint": row["property_id"],
                "value": row.get("value"), "unit": row.get("unit"), "conditions": deepcopy(row.get("conditions") or {}),
                "scope": {"candidate_id": row["candidate_id"], "namespace": self.namespace,
                          "conditions": deepcopy(row.get("conditions") or {})},
                "determination_basis": row["basis"], "evidence_kind": "user_supplied_document",
                "source_status": "user_supplied_document", "reading_depth": "not_read",
                "location": {"location_kind": "uploaded_table_row",
                    "locator_value": deepcopy(row.get("source_locator") or {"filename": provenance.get("filename"),
                                                                             "row_number": row.get("row_number")}),
                    "quoted_span": canonical_text(row)},
                "upload": {"property_id": row["property_id"], "measurement_id": row["measurement_id"],
                    "manifest_hash": self._manifest["hash"], "row_sha256": sha256_hex(row),
                    "original_source_id": row.get("source_id"), "provenance": provenance}}
            if claim_id in existing:
                original = existing[claim_id]
                if any(original.get(key) != value for key, value in claim.items()):
                    raise ValueError("The persisted uploaded claim differs from its immutable row.")
            else:
                ledger.record_claim(core, task_id, claim, by=by, admission_state="admitted",
                    admission_reasons=["uploaded_row_structure_and_candidate_identity_checked", "basis_explicitly_declared"],
                    ids={"task_id": task_id})
            expected.append(claim_id)
        persisted = {c["claim_id"]: c for c in ledger.claims(core, [task_id], claim_ids=expected)}
        self._claims = [persisted[key] for key in expected]
        self._claims_by_key = {}
        for claim in self._claims:
            key = (claim["candidate_ref"], claim["upload"]["property_id"], canonical_text(claim["conditions"]))
            self._claims_by_key.setdefault(key, []).append(claim)
        artifacts = {json.loads(body)["payload"]["claim_id"]: json.loads(body)["payload"]["artifact_id"]
            for (body,) in core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='evidence.admitted' ORDER BY seq", (task_id,))}
        manifest = {"source_task_id": None, "admission_task_id": task_id, "source_runs": [],
            "claims": [{"claim_id": c["claim_id"], "artifact_id": artifacts[c["claim_id"]], "sha256": sha256_hex(c)}
                       for c in self._claims], "source_refs": sorted(sources),
            "sources": [sources[key] for key in sorted(sources)], "upload": self.manifest(),
            "source_admitted_claim_count": len(self._claims), "omitted": [],
            "reads_new_literature": False, "copies_existing_criteria": False, "author_exposure": "user_supplied"}
        ref = core.artifacts.put("existing_evidence_manifest", manifest)
        return {"claims": deepcopy(self._claims), "evidence_manifest_ref": ref, "manifest": manifest}

    def _constraint(self, constraint):
        prop = constraint.get("property_id")
        rows = [r for r in self.measurements if r["property_id"] == prop]
        if not rows:
            return None, "Name an uploaded property_id that implements this requirement."
        conditions = constraint.get("conditions")
        profiles = {canonical_text(r.get("conditions") or {}): r.get("conditions") or {} for r in rows}
        if conditions is None and len(profiles) == 1:
            conditions = next(iter(profiles.values()))
        if not isinstance(conditions, dict) or canonical_text(conditions) not in profiles:
            return None, "Specify which recorded experimental conditions this requirement applies to."
        rows = [r for r in rows if (r.get("conditions") or {}) == conditions]
        value, comparator = constraint.get("value"), constraint.get("comparator")
        if comparator not in criteria.COMPARATORS or value is None:
            return None, "State the comparison and its required value explicitly."
        if type(value) not in (bool, int, float, str):
            return None, "State a scalar numeric, Boolean or category requirement."
        kind = "quantitative" if type(value) in (int, float) else "categorical"
        if kind == "quantitative" and comparator in ("in", "not_in"):
            return None, "Numeric requirements need an explicit scalar comparison, not category membership."
        if kind == "categorical" and comparator not in ("==", "in", "not_in"):
            return None, "Categorical requirements support equality or explicit membership."
        if kind == "quantitative" and (not math.isfinite(value) or not constraint.get("unit")):
            return None, "State the numeric requirement's unit, including an explicit dimensionless unit when applicable."
        if constraint.get("direction") and constraint["direction"] not in criteria.DIRECTIONS:
            return None, "Specify a supported comparison direction for this property."
        expected_type = self._value_type(value[0] if isinstance(value, list) and value else value)
        if any(self._value_type(r.get("value")) not in (expected_type, "missing") for r in rows):
            return None, "The required value type differs from the uploaded property's declared values."
        unit = constraint.get("unit")
        from .assessor import canonical_unit, unit_conversion
        if any(canonical_unit(r.get("unit")) != canonical_unit(unit) and
               not (kind == "quantitative" and unit_conversion(r.get("unit"), unit)) for r in rows):
            return None, "The required unit does not match a supported conversion from the uploaded unit."
        return {"property_id": prop, "conditions": deepcopy(conditions), "rows": rows,
                "measurement_kind": kind, "unit": unit}, None

    def _scope(self, entity):
        """Bind a requested property; absence of a direction never creates a cutoff."""
        prop = entity.get("property_id") or entity.get("identifier")
        if entity.get("identifier_scheme") != "uploaded_property" or entity.get("identifier") != prop:
            return None, "Bind this scope to an exact uploaded property_id using identifier_scheme uploaded_property."
        rows = [row for row in self.measurements if row["property_id"] == prop]
        if not rows:
            return None, "Choose an existing uploaded property_id for this required scope."
        conditions = entity.get("conditions")
        profiles = {canonical_text(row.get("conditions") or {}): row.get("conditions") or {} for row in rows}
        if conditions is None and len(profiles) == 1:
            conditions = next(iter(profiles.values()))
        if not isinstance(conditions, dict) or canonical_text(conditions) not in profiles:
            return None, "Specify which exact recorded conditions apply to this required property."
        rows = [row for row in rows if (row.get("conditions") or {}) == conditions]
        types = {self._value_type(row.get("value")) for row in rows} - {"missing"}
        if len(types) != 1:
            return None, "This required property needs a consistent numeric, Boolean or category encoding."
        numeric = types == {"numeric"}
        unit = entity.get("unit")
        units = {row.get("unit") for row in rows}
        if unit is None and len(units) == 1:
            unit = next(iter(units))
        if numeric and not unit:
            return None, "Specify the required property's unit, including 1 for a dimensionless quantity."
        from .assessor import canonical_unit, unit_conversion
        if any(canonical_unit(row.get("unit")) != canonical_unit(unit) and not (
                numeric and unit_conversion(row.get("unit"), unit)) for row in rows):
            return None, "Choose a unit compatible with the recorded values and supported conversions."
        direction = entity.get("direction") or "non_directional"
        if direction not in ("higher_better", "lower_better", "non_directional", "undetermined"):
            return None, "State an explicit higher/lower preference, or request observation without a direction."
        if direction in ("higher_better", "lower_better") and not numeric:
            return None, "An ordered category requires an explicit numeric encoding; category labels alone do not define an order."
        return {"property_id": prop, "rows": rows, "conditions": deepcopy(conditions), "unit": unit,
                "measurement_kind": "quantitative" if numeric else "categorical", "direction": direction}, None

    def validate_task(self, context):
        findings = []
        for index, constraint in enumerate(context.get("constraints") or []):
            if constraint.get("hardness") != "hard":
                continue
            _, reason = self._constraint(constraint)
            if reason:
                findings.append({"unknown_id": "uploaded_constraint_" + sha256_hex({"constraint": constraint,
                    "manifest": self._manifest["hash"]})[:20], "question": reason + " Requirement: " + str(constraint.get("text") or ""),
                    "blocking": True, "resolution_state": "open", "field": f"constraints[{index}]",
                    "reason": reason, "original_constraint": deepcopy(constraint),
                    "available_properties": self.property_catalog()})
        scope_directions = {}
        for index, entity in enumerate(context.get("scope_entities") or []):
            if entity.get("role") == "required":
                mapped, reason = self._scope(entity)
                if mapped:
                    key = canonical_text({"property": mapped["property_id"], "conditions": mapped["conditions"],
                                          "unit": mapped["unit"]})
                    direction = mapped["direction"] if mapped["direction"] in ("higher_better", "lower_better") else None
                    if key in scope_directions and scope_directions[key] != direction:
                        reason = "Clarify the conflicting preference directions requested for this same property and conditions."
                    scope_directions[key] = direction
                if reason:
                    findings.append({"unknown_id": "uploaded_scope_" + sha256_hex(entity)[:20],
                        "question": reason + " Scope: " + str(entity.get("label") or entity.get("identifier")),
                        "blocking": True, "resolution_state": "open", "field": f"scope_entities[{index}]",
                        "reason": reason, "available_properties": self.property_catalog()})
        return findings

    def objective_templates(self, context):
        pending = self.validate_task(context)
        if pending:
            raise UploadedRequirementsPending(pending)
        result = []
        seen_scope = set()
        for index, entity in enumerate(context.get("scope_entities") or []):
            if entity.get("role") != "required":
                continue
            mapped, _ = self._scope(entity)
            prop, conditions = mapped["property_id"], mapped["conditions"]
            scope_key = canonical_text({"property": prop, "conditions": conditions, "unit": mapped["unit"]})
            if scope_key in seen_scope:
                continue
            seen_scope.add(scope_key)
            ordered = mapped["direction"] in ("higher_better", "lower_better")
            suffix = sha256_hex({"namespace": self.namespace, "scope": scope_key})[:24]
            from .assessor import DIRECT_BASES
            bases = sorted({row["basis"] for row in mapped["rows"]})
            bases = [basis for basis in bases if basis in DIRECT_BASES] or bases
            attr = {"attribute_id": "attr_uploaded_scope_" + suffix,
                "name": str(entity.get("label") or prop) + (" ordering" if ordered else " recorded observation"),
                "definition": f"Uploaded property {prop} under exact conditions {canonical_text(conditions)}; "
                    + (f"ordered by the user-declared direction {mapped['direction']}." if ordered else
                       "record its value and provenance without a pass/fail comparison or preference score."),
                "measurement_kind": mapped["measurement_kind"], "unit": mapped["unit"], "direction": mapped["direction"],
                "quantity_id": self.namespace + ":" + sha256_hex({"property": prop, "conditions": conditions}),
                "acceptable_value_sources": ["user_supplied_document"], "acceptable_determination_bases": bases,
                "aggregation": "consensus", "evidence_request": {"capability": CAPABILITY,
                    "question_kind": "measurement", "identifier_scheme": "uploaded_id",
                    "parameters": {"property": prop, "conditions": conditions}},
                "rationale": "The user requested direct evidence for this property; observation availability does not create a hard threshold."}
            if "predicted" in bases and len(bases) > 1:
                attr["determination_basis_precedence"] = [basis for basis in bases if basis != "predicted"] + ["predicted"]
            rule = {"rule_id": "rule_uploaded_scope_" + suffix,
                "rule_kind": "preference" if ordered else "exploratory_consideration",
                "predicate_form": "ordering" if ordered else "recorded_observation", "cutoff": None,
                "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_blocks_recommendation"}
            criteria.check_attribute(attr)
            criteria.check_rule(rule, attr)
            result.append({"source_field": f"scope_entities[{index}]", "attribute": attr, "rule": rule,
                           "preserve_task_binding": True})
        for index, constraint in enumerate(context.get("constraints") or []):
            if constraint.get("hardness") != "hard":
                continue
            mapped, _ = self._constraint(constraint)
            prop, conditions = mapped["property_id"], mapped["conditions"]
            bases = sorted({r["basis"] for r in mapped["rows"]})
            # Hard gates never substitute predictions for direct facts. All rows
            # remain in the ledger; accepting direct bases needs no invented
            # ordering among unlike kinds of direct evidence.
            from .assessor import DIRECT_BASES
            bases = [b for b in bases if b in DIRECT_BASES] or bases
            attr = {"name": str(constraint.get("text") or prop), "definition":
                f"User requirement, restated without a data-derived cutoff: {constraint.get('text') or prop}. "
                f"Uploaded property {prop}; conditions {canonical_text(conditions)}.",
                "measurement_kind": mapped["measurement_kind"], "unit": mapped["unit"],
                "direction": constraint.get("direction") or "non_directional",
                "quantity_id": self.namespace + ":" + sha256_hex({"property": prop, "conditions": conditions}),
                "acceptable_value_sources": ["user_supplied_document"], "acceptable_determination_bases": bases,
                "aggregation": "consensus", "evidence_request": {"capability": CAPABILITY,
                    "question_kind": "measurement", "identifier_scheme": "uploaded_id",
                    "parameters": {"property": prop, "conditions": conditions}},
                "rationale": constraint.get("text") or "Explicit user constraint"}
            if "predicted" in bases and len(bases) > 1:
                attr["determination_basis_precedence"] = [b for b in bases if b != "predicted"] + ["predicted"]
            rule = {"rule_kind": "hard_exclusion", "predicate_form":
                "threshold" if mapped["measurement_kind"] == "quantitative" else "categorical_membership",
                "cutoff": {"comparator": constraint["comparator"], "value": deepcopy(constraint["value"]), "unit": mapped["unit"]},
                "cutoff_basis": "task_constraint", "on_missing": "unknown_blocks_recommendation"}
            criteria.check_attribute(attr)
            criteria.check_rule(rule, attr)
            result.append({"source_field": f"constraints[{index}]", "attribute": attr, "rule": rule,
                           "preserve_task_binding": True})
        return result

    def register(self, broker):
        broker.register(_UploadedProvider(self))


class _UploadedProvider:
    """Advertise the same local-only capability in measurement tool manifests.

    Assessment uses evidence_hook so original admitted claims retain their source
    kind and locations instead of being restamped as database tool output.
    """
    def __init__(self, bundle):
        self.bundle = bundle
        self.contract = ToolContract(tool_id=TOOL_ID, capability=CAPABILITY, capability_kind="attribute_estimate",
            question_kinds=("measurement",), contract_version="1", implementation_version=
                PROJECTION_POLICY + ":" + bundle.route_encoding_version + ":" + bundle._manifest["hash"],
            purpose_statement="Read exact property/conditions from a pinned user observation dataset",
            evidence_kind_produced="user_supplied_document", claim_strength_ceiling="measured",
            determinism="deterministic", required_inputs=("identifier", "property"), identity_inputs=("identifier",),
            execution_location="in_process", license_id="user-supplied dataset; see source provenance",
            supported_platforms=(("linux", "checked"), ("windows", "checked")))

    def invoke(self, question_kind, inputs):
        claims = self.bundle.claims_for(inputs["identifier"], attribute={"evidence_request": {
            "capability": CAPABILITY, "question_kind": "measurement", "parameters": {
                "property": inputs["property"], "conditions": inputs.get("conditions", {})}}})
        return ProviderResponse(values=[{"name": c["upload"]["property_id"], "value": c["value"], "unit": c["unit"],
            "value_kind": "curated" if c["determination_basis"] in ("curated", "asserted") else c["determination_basis"],
            "source_record_ref": c["claim_id"]} for c in claims], records=claims,
            data_version=self.bundle._manifest["hash"], upstream_refs=sorted({c["source_ref"] for c in claims}))
