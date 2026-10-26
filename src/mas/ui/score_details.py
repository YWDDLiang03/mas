"""Read-only explanations of saved weighted-preference scores.

Only the qualified cohort's exact cells are prepared, once per immutable snapshot.
This service never assesses a cell, writes a projection, or changes a saved score.
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from copy import deepcopy
import json
import math
import threading
from typing import Any

from mas.core.criteria import quantity_identity
from mas.ui.read_summaries import criterion_display_fields

METHOD = "weighted_preference_qualified_v1"
EXPLANATION_VERSION = "score_details_v1"
POLICY = "qualification_first_v1"
TOLERANCE = 1e-12
DIRECT_BASES = frozenset(("measured", "derived", "curated", "asserted"))


class _Unavailable(ValueError):
    pass


def _direct(cell):
    return (cell.get("verdict") in ("pass", "fail", "available")
            and bool(cell.get("value_source_claim_refs")) and not cell.get("tool_error_ref")
            and cell.get("determination_basis") in DIRECT_BASES
            and cell.get("value_kind") not in ("predicted", "simulated", "missing")
            and cell.get("direct_evidence", True) is not False)


def _matches(left, right):
    if left is None or right is None:
        return left is right
    return math.isclose(left, right, rel_tol=0, abs_tol=TOLERANCE)


def _normalization(population, direction):
    frequencies = Counter(population.values())
    n = len(population)
    scores = {}
    for candidate, value in population.items():
        worse = sum(count for other, count in frequencies.items()
                    if (other > value if direction == "lower_better" else other < value))
        equal = frequencies[value]
        scores[candidate] = {"worse": worse, "equal": equal,
                             "score": (worse + (equal - 1) / 2) / (n - 1) if n > 1 else 1.0}
    return {"n": n, "scores": scores}


class ScoreDetails:
    def __init__(self, model):
        self.model = model
        self._lock = threading.Lock()
        self._prepared: OrderedDict[tuple, dict[str, Any]] = OrderedDict()

    @staticmethod
    def _version(db, task_id, ref, kind, maximum):
        row = db.execute("SELECT body FROM criterion_versions WHERE task_id=? AND ref=? AND kind=? "
                         "AND source_row<=?", (task_id, ref, kind, maximum)).fetchone()
        if not row:
            raise _Unavailable("exact_frozen_version_unavailable")
        return json.loads(row["body"])

    def _cells(self, db, source, run_id, candidate, maximum, rules):
        rows = db.execute("SELECT * FROM assessments WHERE run_id=? AND candidate_ref=? AND source_row IN "
            "(SELECT max(source_row) FROM assessments WHERE run_id=? AND candidate_ref=? AND source_row<=? "
            "GROUP BY rule_ref) ORDER BY source_row", (run_id, candidate, run_id, candidate, maximum))
        cells = {}
        for row in rows:
            ref = row["rule_ref"]
            if ref not in rules:
                continue
            cell = self.model._artifact(source, row["artifact_id"], {"assessment"})
            if (not cell or cell.get("candidate_ref") != candidate or cell.get("rule_ref") != ref
                    or cell.get("attribute_ref") != rules[ref]["attribute_ref"]
                    or cell.get("rule_kind") != rules[ref]["rule_kind"]):
                raise _Unavailable("exact_snapshot_assessment_unavailable")
            cells[ref] = cell
        if set(cells) != set(rules):
            raise _Unavailable("incomplete_snapshot_assessments")
        return cells

    def _prepare(self, db, source, task_id, selected, info):
        ref = info.get("rules@v")
        frozen_event = source.execute("SELECT json_extract(body,'$.payload.artifact_id') FROM events "
            "WHERE stream_id=? AND event_type='criterion.version_approved' AND rowid<=? "
            "AND json_extract(body,'$.payload.rule_set_ref')=? "
            "AND coalesce(json_extract(body,'$.visibility'),'default') IN ('default','public') "
            "ORDER BY seq DESC LIMIT 1", (task_id, selected["published_row"], ref)).fetchone()
        frozen = self.model._artifact(source, frozen_event[0], {"rule_set"}) if frozen_event else {}
        if not frozen or frozen.get("rule_set_ref") != ref:
            raise _Unavailable("frozen_rule_set_unavailable")
        ordering = frozen.get("ordering_method") or {}
        if ordering.get("kind", "weighted_preference") != "weighted_preference":
            raise _Unavailable("unsupported_ordering_method")
        weights, rules = ordering.get("weight_vector") or {}, {}
        for entry in frozen.get("entries") or []:
            rule = self._version(db, task_id, entry["rule_ref"], "rule", selected["published_row"])
            attr = self._version(db, task_id, entry["attribute_ref"], "attribute", selected["published_row"])
            if rule.get("attribute_ref") != entry["attribute_ref"]:
                raise _Unavailable("frozen_attribute_binding_mismatch")
            weight = weights.get(entry["rule_ref"], 1.0)
            if type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0:
                raise _Unavailable("unsupported_weight")
            if (rule.get("rule_kind") == "preference" and rule.get("predicate_form", "threshold") == "ordering"
                    and attr.get("direction") not in ("higher_better", "lower_better")):
                raise _Unavailable("unsupported_ordering_direction")
            rules[entry["rule_ref"]] = {**rule, "attribute": attr, "quantity_key": quantity_identity(attr), "weight": weight}
        if not rules:
            raise _Unavailable("empty_frozen_rule_set")
        cohort = list(db.execute("SELECT candidate_ref,label FROM candidate_rows WHERE snapshot_id=? "
                                 "AND qualification='qualified' ORDER BY ordinal", (selected["snapshot_id"],)))
        labels = [{"candidate_ref": row["candidate_ref"], "label": row["label"]} for row in cohort]
        cells, suppressed = {}, {}
        for row in cohort:
            candidate = row["candidate_ref"]
            cells[candidate] = self._cells(db, source, selected["run_id"], candidate, selected["published_row"], rules)
            direct_keys = {rules[ref]["quantity_key"] for ref, cell in cells[candidate].items()
                           if rules[ref]["rule_kind"] == "preference" and _direct(cell)}
            suppressed[candidate] = {ref for ref, cell in cells[candidate].items()
                if rules[ref]["rule_kind"] == "preference" and not _direct(cell)
                and rules[ref]["quantity_key"] in direct_keys}
        normalizations = {}
        for ref, rule in rules.items():
            if rule["rule_kind"] != "preference" or rule.get("predicate_form", "threshold") != "ordering":
                continue
            population = {candidate: observations[ref]["value"] for candidate, observations in cells.items()
                if ref not in suppressed[candidate] and observations[ref].get("verdict") in ("pass", "available")
                and type(observations[ref].get("value")) in (int, float)
                and math.isfinite(observations[ref]["value"])}
            normalizations[ref] = _normalization(population, rule["attribute"]["direction"])
        return {"rules": rules, "cells": cells, "suppressed": suppressed, "normalizations": normalizations,
                "population_labels": labels, "population_count": len(cohort),
                "excluded_counts": {"hard": sum(rule["rule_kind"] == "hard_exclusion" for rule in rules.values()),
                                    "context": sum(rule["rule_kind"] == "exploratory_consideration" for rule in rules.values())}}

    def get(self, task_id: str, candidate_ref: str, snapshot: str | None = None) -> dict[str, Any]:
        with self.model._cache() as db, self.model._source() as source:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            self.model._ready(db)
            self.model._task(db, task_id)
            selected = self.model._snapshot_row(db, task_id, snapshot)
            if not selected:
                raise KeyError(f"no snapshot in {task_id}")
            info = json.loads(selected["body"])
            row = db.execute("SELECT body FROM candidate_rows WHERE snapshot_id=? AND candidate_ref=?",
                             (selected["snapshot_id"], candidate_ref)).fetchone()
            if not row:
                raise KeyError(f"no candidate {candidate_ref} in {selected['snapshot_id']}")
            candidate = json.loads(row["body"])
            result = {"snapshot_id": selected["snapshot_id"], "task_id": task_id, "run_id": selected["run_id"],
                "candidate_ref": candidate_ref, "label": candidate.get("label"), "score": candidate.get("score"),
                "position": candidate.get("position"), "qualification": candidate.get("qualification"),
                "rule_set_ref": info.get("rules@v"), "method": METHOD, "explanation_version": EXPLANATION_VERSION,
                "normalization_scope": "qualified_only", "population_count": None, "population_labels": [],
                "population_members": [],
                "score_numerator": None, "score_denominator": None, "coverage_numerator": None,
                "coverage_denominator": None, "coverage_floor": (info.get("reporting_tuple") or {}).get("ranking_coverage_floor"),
                "coverage": candidate.get("preference_coverage"), "rows": [], "available": False,
                "validation": {"matches": None, "absolute_tolerance": TOLERANCE}}
            if info.get("qualification_policy") != POLICY or info.get("legacy_rank_only"):
                result["unavailable_reason"] = "unsupported_qualification_policy"
                result["method"] = None
                return result
            if candidate.get("qualification") != "qualified":
                result["unavailable_reason"] = "candidate_not_qualified"
                return result
            identity = source.execute("SELECT kind,sha256 FROM artifacts WHERE artifact_id=?", (selected["artifact_id"],)).fetchone()
            if not identity or identity[0] != "leaderboard_snapshot":
                result["unavailable_reason"] = "snapshot_source_unavailable"
                return result
            key = (task_id, selected["snapshot_id"], selected["artifact_id"], identity[1], selected["published_row"], EXPLANATION_VERSION)
            try:
                with self._lock:
                    prepared = self._prepared.get(key)
                    if prepared is None:
                        prepared = self._prepare(db, source, task_id, selected, info)
                        self._prepared[key] = prepared
                        while len(self._prepared) > 8:
                            self._prepared.popitem(last=False)
                    self._prepared.move_to_end(key)
                if candidate_ref not in prepared["cells"]:
                    raise _Unavailable("candidate_not_in_saved_normalization_cohort")
                return self._explain(result, prepared, candidate_ref)
            except _Unavailable as error:
                result["unavailable_reason"] = str(error)
                return result

    @staticmethod
    def _explain(result, prepared, candidate):
        rules, cells = prepared["rules"], prepared["cells"][candidate]
        suppressed = prepared["suppressed"][candidate]
        rows = []
        for ref, rule in rules.items():
            if rule["rule_kind"] != "preference":
                continue
            attr, cell = rule["attribute"], cells[ref]
            kept = ref not in suppressed and cell.get("verdict") != "inapplicable"
            distribution = prepared["normalizations"].get(ref)
            stat = distribution["scores"].get(candidate) if distribution else None
            score = (stat["score"] if stat else None) if distribution is not None else (
                float(cell["verdict"] == "pass") if cell.get("verdict") in ("pass", "fail") else None)
            score = score if kept else None
            included, weight = score is not None, rule["weight"]
            reason = ("superseded_by_direct_same_quantity" if ref in suppressed else
                      "inapplicable" if cell.get("verdict") == "inapplicable" else
                      "included" if included else "no_usable_scoring_value")
            explanation = {
                "superseded_by_direct_same_quantity": "A direct observation covers the same quantity; this non-direct entry is excluded from score and coverage.",
                "inapplicable": "This preference is inapplicable and is excluded from score and coverage.",
                "no_usable_scoring_value": "This saved cell has no usable value for the scoring method. It is omitted from the score mean and remains in the coverage denominator.",
                "included": ("The predicted value contributes to score; it does not increase direct-evidence coverage."
                             if cell.get("determination_basis") == "predicted" else
                             "The assessed value contributes to the weighted preference mean."),
            }[reason]
            normalization = {"kind": "tied_empirical_percentile" if distribution is not None else "binary_verdict",
                "n": distribution["n"] if distribution is not None else None,
                "worse": stat["worse"] if stat else None, "equal": stat["equal"] if stat else None,
                "formula": ("(worse + (equal - 1) / 2) / (n - 1); n = 1 gives 1" if distribution is not None
                            else "pass = 1; fail = 0; unresolved values are omitted")}
            rows.append({"rule_ref": ref, "attribute_ref": rule["attribute_ref"], "detail_ref": ref,
                "assessment_id": cell.get("assessment_id"), "name": attr.get("name") or rule["attribute_ref"],
                **criterion_display_fields(attr),
                "definition": attr.get("definition"),
                "value": cell.get("value"), "unit": cell.get("unit"), "basis": cell.get("determination_basis"),
                "value_kind": cell.get("value_kind"), "verdict": cell.get("verdict"),
                "direction": attr.get("direction"), "predicate_form": rule.get("predicate_form", "threshold"),
                "cutoff": deepcopy(rule.get("cutoff")), "aggregation": attr.get("aggregation", "consensus"),
                "value_transform": deepcopy(attr.get("value_transform")), "weight": weight, "normalization": normalization,
                "comparison_score": score, "weighted_score": weight * score if included else None,
                "contribution": None, "included_in_score": included, "included_in_coverage": kept,
                "score_denominator_weight": weight if included else 0,
                "coverage_numerator_weight": weight if kept and _direct(cell) else 0,
                "coverage_denominator_weight": weight if kept else 0,
                "direct": _direct(cell), "suppressed": ref in suppressed, "reason": explanation, "reason_code": reason,
                "evidence_refs": list(cell.get("value_source_claim_refs") or [])})
        numerator = sum(row["weighted_score"] or 0 for row in rows)
        denominator = sum(row["score_denominator_weight"] for row in rows)
        coverage_numerator = sum(row["coverage_numerator_weight"] for row in rows)
        coverage_denominator = sum(row["coverage_denominator_weight"] for row in rows)
        score = numerator / denominator if denominator else None
        coverage = coverage_numerator / coverage_denominator if coverage_denominator else 0.0
        for row in rows:
            row["contribution"] = row["weighted_score"] / denominator if row["included_in_score"] and denominator else None
            row["effective_weight_fraction"] = row["weight"] / denominator if row["included_in_score"] and denominator else None
        score_match, coverage_match = _matches(score, result["score"]), _matches(coverage, result["coverage"])
        result.update(available=score_match and coverage_match,
            unavailable_reason=None if score_match and coverage_match else "stored_score_or_coverage_mismatch",
            population_count=prepared["population_count"],
            population_labels=[row["label"] for row in prepared["population_labels"]],
            population_members=[dict(row) for row in prepared["population_labels"]],
            score_numerator=numerator, score_denominator=denominator, coverage_numerator=coverage_numerator,
            coverage_denominator=coverage_denominator, recomputed_score=score, recomputed_coverage=coverage, rows=rows,
            excluded_counts={**prepared["excluded_counts"], "suppressed": len(suppressed),
                "unknown": sum(not row["included_in_score"] and not row["suppressed"] and row["verdict"] != "inapplicable" for row in rows),
                "inapplicable": sum(row["verdict"] == "inapplicable" for row in rows)},
            validation={"matches": score_match and coverage_match, "score_matches": score_match,
                "coverage_matches": coverage_match, "score_delta": score - result["score"]
                    if score is not None and result["score"] is not None else None, "absolute_tolerance": TOLERANCE})
        return result
