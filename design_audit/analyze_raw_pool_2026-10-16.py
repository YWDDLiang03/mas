"""Pinned, read-only raw proposal diagnosis; never execute a pruning stage."""
import json
from collections import Counter, defaultdict
from pathlib import Path

from mas.adapters.drug.registration import EVIDENCE_CATALOG
from mas.core import assessor, criteria, criteria_export, derivation, derivation_stages as stages, ledger, pool, task
from mas.core.canonical import canonical_text, sha256_hex
from mas.core.runtime import Core

TASK = "task_01M51AQ0JK0MYN47806ZD5XS1B"
RUN = "run_01M51AQ43WQQPDQZVD9GADSVTB"
PIN = 3560


def describe(entry):
    item = entry["item"]
    return {"criterion_id": entry["criterion_id"], "version": entry["version"], "dimension": item.get("dimension"),
        "name": item["attribute"].get("name"), "unit": item["attribute"].get("unit"),
        "aggregation": item["attribute"].get("aggregation", "consensus"), "measurement_kind": item["attribute"].get("measurement_kind"),
        "routes": criteria.evidence_routes(item["attribute"]), "rule": item["rule"], "problems": item.get("validator_problems") or []}


def main():
    with Core.open("var/primary/store", read_only=True) as source:
        core, pin = criteria_export.pinned(source, TASK, PIN)
        entries = pool.active(pool.fold(core, TASK))
        registered, registered_rules = criteria.registered_attributes(core, TASK), criteria.registered_rule_records(core, TASK)
        claims = {c["claim_id"]: c for c in ledger.claims(core, [TASK])}
        context = task.get(core, TASK)
        refs = [label for seed in context.get("seed_candidates", []) if seed.get("is_reference_outcome")
                for label in [seed["candidate_ref"], *seed.get("aliases", [])]]
        qgroups, operational, strict, key_decisions = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(set)
        anchored, different_decision, clean, missing_support, validation = [], [], [], [], []
        problem_counts, problem_messages = Counter(), Counter()
        route_units, extra_parameters, categorical_numeric = [], [], []
        subset_anchor, categories, categorical_no_predicate = [], Counter(), []
        for entry in entries:
            item, attr, rule = entry["item"], entry["item"]["attribute"], entry["item"]["rule"]
            qkey, dkey = canonical_text(stages.quantity_key(attr)), stages.decision_key(rule)
            qgroups[qkey].append(entry)
            key_decisions[qkey].add(dkey)
            strict[canonical_text({"attribute": {k: v for k, v in attr.items() if k != "rationale" and k != "bound_support"}, "decision": dkey})].append(entry)
            questions = {r.get("question_kind") for r in criteria.evidence_routes(attr)}
            family = ("target_potency" if questions & {"pchembl_values", "gtopdb_affinity"} else "target_engagement_or_breadth" if "mechanism_records" in questions
                      else "predicted_property" if "admet_prediction" in questions else "computed_descriptor" if "computed_property" in questions
                      else "record_flag" if "record_field" in questions else "literature_quantity" if "search" in questions else "other")
            categories[family] += 1
            if not criteria.is_literature_bound(attr):
                signature = canonical_text({"quantity": qkey, "routes": sorted(criteria.route_key(r) for r in criteria.evidence_routes(attr)),
                    "kind": attr.get("measurement_kind"), "aggregation": attr.get("aggregation", "consensus"),
                    "value_sources": sorted(attr.get("acceptable_value_sources") or []),
                    "bases": sorted(attr.get("acceptable_determination_bases") or assessor.DEFAULT_DETERMINATION_BASES),
                    "precedence": attr.get("determination_basis_precedence"), "existence_semantics": attr.get("existence_semantics"), "decision": dkey})
                operational[signature].append(entry)
            match = stages.duplicate_of_registered(attr, registered, rule=rule, registered_rules=registered_rules)
            quantity_match = stages.duplicate_of_registered(attr, registered)
            if match:
                anchored.append({**describe(entry), "anchor": match})
            elif quantity_match:
                different_decision.append({**describe(entry), "anchor": quantity_match})
            problems = derivation.validate_proposal(item, claims_by_id=claims, reference_labels=refs, catalog=EVIDENCE_CATALOG)
            if attr.get("measurement_kind") == "categorical" and rule.get("rule_kind") == "preference" and rule.get("cutoff") is None:
                categorical_no_predicate.append({**describe(entry), "validator_clean": not problems})
            for anchor in registered:
                asked = {criteria.route_key(r) for r in criteria.evidence_routes(attr)}
                offered = {criteria.route_key(r) for r in criteria.evidence_routes(anchor)}
                if asked and asked <= offered and stages.quantity_key(attr)[1:] == stages.quantity_key(anchor)[1:]:
                    subset_anchor.append({"criterion_id": entry["criterion_id"], "anchor_ref": f"{anchor['attribute_id']}@v{anchor['version']}",
                        "validator_clean": not problems, "same_aggregation": attr.get("aggregation", "consensus") == anchor.get("aggregation", "consensus"),
                        "capability_key_differs": stages.quantity_key(attr)[0] != stages.quantity_key(anchor)[0]})
                    break
            if problems:
                validation.append({"criterion_id": entry["criterion_id"], "problems": problems})
            for problem in set(problems):
                problem_counts[problem.split(":", 1)[0]] += 1
                problem_messages[problem] += 1
            cited = [ref for ref in item.get("supporting_claim_ids") or [] if ref in claims]
            if not cited:
                missing_support.append(entry["criterion_id"])
            if not problems and not match and cited:
                clean.append(entry)
            for route in criteria.evidence_routes(attr):
                catalog = next((c for c in EVIDENCE_CATALOG if c["capability"] == route.get("capability") and c["question_kind"] == route.get("question_kind")), None)
                if not catalog:
                    continue
                params = route.get("parameters") or {}
                extras = sorted(set(params) - set(catalog.get("parameters") or {}))
                if extras:
                    extra_parameters.append({"criterion_id": entry["criterion_id"], "question_kind": route.get("question_kind"), "extra_parameters": extras})
                units = catalog.get("units") or {}
                if not isinstance(units, dict):
                    continue
                property_key = next((params[key] for key in ("property", "endpoint", "field") if params.get(key) in units), None)
                returned = [units[property_key]] if property_key in units else list(units.values())
                returned = {assessor.canonical_unit(unit) for unit in returned}
                target = assessor.canonical_unit(attr.get("unit"))
                if attr.get("measurement_kind") == "quantitative" and target and returned and not any(
                    unit == target or assessor.unit_conversion(unit, target) is not None for unit in returned):
                    route_units.append({**describe(entry), "catalog_returns": sorted(str(u) for u in returned),
                        "would_be_caught_by_current_validator": bool(problems), "source_question": route.get("question_kind")})
                if attr.get("measurement_kind") == "categorical" and returned and None not in returned:
                    categorical_numeric.append({**describe(entry), "catalog_returns": sorted(str(u) for u in returned)})
        op_dupes = [members for members in operational.values() if len(members) > 1]
        strict_dupes = [members for members in strict.values() if len(members) > 1]
        clean_ids = {e["criterion_id"] for e in clean}
        clean_dupes = [[e for e in group if e["criterion_id"] in clean_ids] for group in operational.values()]
        clean_dupes = [group for group in clean_dupes if len(group) > 1]
        merge_groups = stages.merge_groups(clean)
        q_summary = [{"quantity_key": json.loads(key), "n": len(items), "decision_variants": len(key_decisions[key]),
                      "examples": [describe(item) for item in items[:3]]} for key, items in qgroups.items()]
        report = {"task_id": TASK, "run_id": RUN, "task_pinned_seq": pin,
            "scope": "unfinished raw proposals, not a pruning or promotion result", "writes_primary": 0, "calls_models": 0,
            "pool_count": len(entries), "pool_states": dict(Counter(e["state"] for e in entries)),
            "dimensions": dict(Counter(e["item"].get("dimension") for e in entries)),
            "rule_kinds": dict(Counter(e["item"]["rule"].get("rule_kind") for e in entries)),
            "route_property_families": dict(categories),
            "strict_same_definition_decision_groups": len(strict_dupes),
            "strict_same_definition_decision_items": sum(map(len, strict_dupes)),
            "strict_same_definition_decision_excess": sum(len(g)-1 for g in strict_dupes),
            "clean_operational_duplicate_excess": sum(len(g)-1 for g in clean_dupes),
            "database_subset_anchor_quantity_matches": len(subset_anchor),
            "database_subset_anchor_validator_clean": sum(e["validator_clean"] for e in subset_anchor),
            "database_subset_anchor_same_aggregation": sum(e["same_aggregation"] for e in subset_anchor),
            "categorical_preference_without_predicate_n": len(categorical_no_predicate),
            "categorical_preference_without_predicate_clean_n": sum(e["validator_clean"] for e in categorical_no_predicate),
            "anchor_count": len(registered), "anchor_duplicates_n": len(anchored),
            "anchor_measurement_different_decision_n": len(different_decision), "no_cited_support_n": len(missing_support),
            "validation_problem_items_n": len(validation), "current_validator_clean_n": len(entries) - len(validation),
            "validation_problem_classes": dict(problem_counts), "top_problem_messages": problem_messages.most_common(15),
            "nonliterature_operational_duplicate_groups": len(op_dupes),
            "nonliterature_operational_duplicate_items": sum(map(len, op_dupes)),
            "nonliterature_operational_duplicate_excess": sum(len(group)-1 for group in op_dupes),
            "quantity_bucket_count": len(qgroups), "quantity_bucket_decision_count": sum(map(len, key_decisions.values())),
            "clean_unregistered_precritic_candidates_n": len(clean),
            "clean_precritic_merge_groups": len(merge_groups), "clean_precritic_grouped_items": sum(map(len, merge_groups)),
            "route_unit_incompatible_items_n": len({e['criterion_id'] for e in route_units}),
            "route_unit_incompatible_validator_clean_n": len({e['criterion_id'] for e in route_units if not e['would_be_caught_by_current_validator']}),
            "categorical_bound_numeric_items_n": len({e['criterion_id'] for e in categorical_numeric}),
            "extra_parameter_keys": dict(Counter(key for row in extra_parameters for key in row["extra_parameters"])),
            "route_question_kinds": dict(Counter(route.get("question_kind") for entry in entries for route in criteria.evidence_routes(entry["item"]["attribute"]))),
            "quantity_buckets": sorted(q_summary, key=lambda row: -row["n"]), "anchor_duplicates": anchored,
            "anchor_measurement_different_decisions": different_decision,
            "operational_duplicate_examples": [[describe(entry) for entry in group[:3]] for group in sorted(op_dupes, key=lambda g: -len(g))[:10]],
            "route_unit_incompatibilities": route_units, "categorical_numeric_bindings": categorical_numeric,
            "extra_parameters": extra_parameters, "validation_problems": validation,
            "database_subset_anchor_details": subset_anchor, "categorical_preference_without_predicate": categorical_no_predicate,
            "pool_snapshot_sha256": pool.pool_hash(pool.fold(core, TASK)),
            "backend_source_sha256": "0e7bdc522692d5b4f87586ff8538afdc301f04cb5c7628d8d12f7f10acde039e"}
    out = Path("design_audit/raw_pool_3560_2026-10-16.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in (
        "quantity_buckets", "anchor_duplicates", "anchor_measurement_different_decisions", "operational_duplicate_examples", "route_unit_incompatibilities",
        "categorical_numeric_bindings", "extra_parameters", "validation_problems", "top_problem_messages",
        "database_subset_anchor_details", "categorical_preference_without_predicate")}, ensure_ascii=True))
    print(json.dumps({"top_problem_messages": report["top_problem_messages"][:8]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
