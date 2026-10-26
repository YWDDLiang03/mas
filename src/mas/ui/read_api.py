"""Small HTTP-neutral adapter for read-model query parameters and CSV export."""

from __future__ import annotations

import csv
import io
from typing import Any, Mapping

from mas.ui.read_model import ReadModel


def _value(query: Mapping[str, Any], name: str, default: Any = "") -> Any:
    value = query.get(name, default)
    return value[0] if isinstance(value, (list, tuple)) and value else value


def page_parameters(query: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return {"page": max(1, int(_value(query, "page", 1))),
                "page_size": max(1, min(200, int(_value(query, "page_size", 50)))),
                "q": str(_value(query, "q", ""))}
    except (TypeError, ValueError) as exc:
        raise ValueError("page and page_size must be integers") from exc


class ReadAPI:
    def __init__(self, model: ReadModel):
        self.model = model
        from mas.ui.score_details import ScoreDetails
        self.score_details = ScoreDetails(model)

    def get(self, task_id: str, resource: str, query: Mapping[str, Any] | None = None,
            wanted: str | None = None) -> dict[str, Any]:
        query = query or {}
        if resource == "overview":
            return self.model.overview(task_id)
        if resource == "stages":
            return self.model.stages(task_id)
        if resource == "scores" and wanted:
            return self.score_details.get(task_id, wanted, snapshot=_value(query, "snapshot", None))
        if resource == "evidence-sources":
            from mas.ui.evidence_groups import source_groups
            params = page_parameters(query)
            params['page_size'] = max(1, min(50, int(_value(query, 'page_size', 20))))
            return source_groups(self.model, task_id, **params, snapshot=_value(query, 'snapshot', None),
                kind=str(_value(query, 'kind', 'literature')),
                **{key: str(_value(query, key, '')) for key in
                   ('criterion_ref', 'attribute_ref', 'rule_ref', 'candidate_ref', 'source_id')})
        if resource == "snapshots":
            return self.model.snapshots(task_id)
        if resource == "research-briefs":
            service = getattr(self.model,"brief_service",None)
            if service is None:
                return {"task_id":task_id,"status":"not_configured","generation":"GET never calls a model"}
            return service.get(task_id,wanted) if wanted else service.overview(task_id)
        if resource == "criteria":
            if wanted:
                return self.model.criterion(task_id, wanted, snapshot=_value(query, "snapshot", None))
            return self.model.criteria(task_id, **page_parameters(query), state=str(_value(query, "state")),
                                       stage=str(_value(query, "stage")))
        if resource == "candidates":
            snapshot = _value(query, "snapshot", None)
            if wanted:
                return self.model.candidate(task_id, wanted, snapshot=snapshot)
            return self.model.candidates(task_id, **page_parameters(query), snapshot=snapshot,
                                         status=str(_value(query, "status", "qualified")),
                                         selection=str(_value(query, "selection", "")),
                                         evidence_profile=str(_value(query, "evidence_profile", "")))
        if resource == "evidence":
            if wanted:
                try:
                    return self.model.evidence_detail(task_id, wanted, snapshot=_value(query,"snapshot",None),
                        criteria_page=int(_value(query,"criteria_page",1)),candidate_page=int(_value(query,"candidate_page",1)),
                        link_page_size=int(_value(query,"link_page_size",50)))
                except (TypeError, ValueError) as exc:
                    raise ValueError("evidence link pages must be integers") from exc
            return self.model.evidence(task_id, **page_parameters(query), snapshot=_value(query,"snapshot",None),
                **{key:str(_value(query,key,"")) for key in
                   ("criterion_ref","attribute_ref","rule_ref","candidate_ref","source_id","claim_id")})
        raise KeyError(f"unknown workbench resource {resource}")

    def export_csv(self, task_id: str, snapshot: str | None = None) -> str:
        stream = io.StringIO(newline="")
        fields = ("candidate_ref", "label", "qualification", "evaluation_mode", "position", "score",
                  "hard_passed", "hard_total", "preference_coverage", "evidence_coverage", "reason",
                  "missing", "skip_reason", "rank_note", "snapshot_id", "legacy_rank_only",
                  "selection_decision", "confirmed_mandatory_failure", "eligibility_state", "eligibility_reason_code", "required_supported", "required_total",
                  "unresolved_requirements", "recorded_reason", "evidence_profile", "selection_policy", "selection_reason_code")
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(self.model.export_rows(task_id, snapshot))
        return stream.getvalue()
