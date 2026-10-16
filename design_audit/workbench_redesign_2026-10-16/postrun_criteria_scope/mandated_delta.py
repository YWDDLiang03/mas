"""Add a read-only, evidence-backed mandated-stage Added projection to the draft."""
from pathlib import Path


def extend(proposed: dict[str, str], root: Path) -> None:
    path = 'src/mas/ui/read_model.py'
    source = proposed[path]
    needle = '''            counts = {key: value for key, value in (result or {}).items() if isinstance(value, (int, float, bool))} if isinstance(result, dict) else {}
'''
    addition = '''            if name == "mandated" and isinstance(result, list):
                refs = [{"rule_ref": item["rule_ref"], "attribute_ref": item["attribute_ref"]}
                        for item in result if isinstance(item, dict) and item.get("rule_ref") and item.get("attribute_ref")]
                body["mandated_result_refs"] = refs if len(refs) == len(result) else None
'''
    assert needle in source
    source = source.replace(needle, addition + needle, 1)
    helper = '''    @staticmethod
    def _mandated_added(db: sqlite3.Connection, task_id: str, opened: int | None,
                        closed: int | None, body: dict[str, Any]) -> None:
        """Count template-created rule bindings, not attribute/rule pairs twice."""
        body.update(added=None, added_count_basis="unavailable_stage_bounds", added_event_refs=[])
        if opened is None or closed is None:
            return
        expected = body.get("mandated_result_refs")
        expected_pairs = {(item["rule_ref"], item["attribute_ref"]) for item in expected} if expected is not None else None
        if expected is not None and len(expected_pairs) != len(expected):
            body["added_count_basis"] = "ambiguous_recorded_result"
            return
        rows = db.execute("SELECT r.ref,r.source_row,r.artifact_id,r.body,a.body AS attribute_body,ch.body AS creation_body "
            "FROM criterion_versions r LEFT JOIN criterion_versions a ON a.task_id=r.task_id "
            "AND a.ref=json_extract(r.body,'$.attribute_ref') AND a.kind='attribute' "
            "LEFT JOIN criterion_changes ch ON ch.source_row=r.source_row AND ch.task_id=r.task_id "
            "WHERE r.task_id=? AND r.kind='rule' AND r.source_row>? AND r.source_row<? ORDER BY r.source_row",
            (task_id, opened, closed)).fetchall()
        verified = []
        for row in rows:
            rule = _record(row)
            pair = row["ref"], rule.get("attribute_ref")
            if expected_pairs is not None and pair not in expected_pairs:
                continue
            attribute = json.loads(row["attribute_body"]) if row["attribute_body"] else {}
            creation = json.loads(row["creation_body"]) if row["creation_body"] else {}
            origin = attribute.get("derived_from") or {}
            who = creation.get("actor") or {}
            if (not is_task_mandated(attribute) or str(origin.get("task_context", "")).split("@v")[0] != task_id
                    or who.get("kind") != "system" or who.get("id") != "objective-criteria"
                    or creation.get("kind") != "rule" or creation.get("ref") != row["ref"] or not creation.get("id")):
                body["added_count_basis"] = "unverified_task_binding_creation"
                return
            verified.append({"rule_ref": row["ref"], "attribute_ref": pair[1], "event_id": creation["id"],
                             "source_row": row["source_row"], "rule_artifact_id": row["artifact_id"],
                             "source_field": origin.get("field")})
        pairs = {(item["rule_ref"], item["attribute_ref"]) for item in verified}
        if expected_pairs is not None and pairs != expected_pairs:
            body["added_count_basis"] = "incomplete_recorded_result_creations"
            return
        if not verified and expected_pairs is None:
            body["added_count_basis"] = "no_creation_proof"
            return
        body.update(added=len(verified), added_event_refs=verified,
                    added_count_basis="recorded_result_and_task_binding_events" if expected_pairs is not None
                                      else "task_binding_events_between_stage_boundaries")

'''
    needle = '    @staticmethod\n    def _stages('
    assert needle in source
    source = source.replace(needle, helper + needle, 1)
    source = source.replace('SELECT s.body,s.closed_row,r.state AS run_state FROM stages s',
                            'SELECT s.body,s.opened_row,s.closed_row,r.state AS run_state FROM stages s', 1)
    needle = '''            for key in ("before_count", "after_count", "added", "modified", "merged", "removed", "pending", "started_at", "finished_at"):
'''
    addition = '''            if body.get("stage") == "mandated":
                ReadModel._mandated_added(db, task_id, row["opened_row"], row["closed_row"], body)
'''
    assert needle in source
    proposed[path] = source.replace(needle, addition + needle, 1)

    path = 'tests/test_read_model.py'
    needle = 'actor={"id": "test"}, **fields)'
    assert needle in proposed[path]
    proposed[path] = proposed[path].replace(needle, 'actor=fields.pop("actor", {"id": "test"}), **fields)', 1)
    proposed[path] += '''

def test_mandated_added_uses_created_bindings_and_repairs_legacy_cache_on_read(setup):
    journal, model = setup
    journal.event("run_a", "stage.opened", {"stage": "mandated", "iteration": 0,
                  "before_count": 0, "count_basis": "active_registered_plus_unregistered_proposals"})
    refs = []
    for index in range(6):
        attr_ref, rule_ref = f"attr_required_{index}@v1", f"rule_required_{index}@v1"
        attr = journal.artifact("attribute", {"attribute_id": attr_ref.split("@v")[0], "version": 1,
            "name": f"Task requirement {index}", "proposed_by": {"role": "adapter_template"},
            "derived_from": {"task_context": "task_a@v1", "field": f"scope_entities[{index}]"}})
        journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": attr_ref.split("@v")[0],
            "version": 1, "artifact_id": attr}, actor={"kind": "system", "id": "objective-criteria"})
        rule = journal.artifact("rule", {"rule_id": rule_ref.split("@v")[0], "version": 1,
            "attribute_ref": attr_ref, "rule_kind": "preference"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": rule_ref.split("@v")[0],
            "version": 1, "artifact_id": rule}, actor={"kind": "system", "id": "objective-criteria"})
        refs.append({"attribute_ref": attr_ref, "rule_ref": rule_ref})
    journal.event("run_a", "stage.closed", {"stage": "mandated", "iteration": 0, "result": refs,
                  "before_count": 0, "after_count": 6, "count_basis": "active_registered_plus_unregistered_proposals"})
    model.sync()
    stage = model.stages("task_a")["items"][0]
    assert stage["before_count"] == 0 and stage["after_count"] == stage["added"] == 6
    assert stage["added_count_basis"] == "recorded_result_and_task_binding_events"
    assert len(stage["added_event_refs"]) == 6  # Six conditions, not twelve attribute/rule events.
    with model._cache() as db:
        saved = json.loads(db.execute("SELECT body FROM stages WHERE stage_id=?", (stage["stage_id"],)).fetchone()[0])
        saved.pop("mandated_result_refs")
        saved["added"] = 0
        db.execute("UPDATE stages SET body=? WHERE stage_id=?", (json.dumps(saved), stage["stage_id"]))
        db.commit()
    legacy = model.stages("task_a")["items"][0]
    assert legacy["added"] == 6 and legacy["added_count_basis"] == "task_binding_events_between_stage_boundaries"
    journal.event("run_a", "stage.closed", {"stage": "mandated", "iteration": 9, "result": refs})
    model.sync()
    unknown = model.stages("task_a")["items"][-1]
    assert unknown["added"] is None and unknown["added_count_basis"] == "unavailable_stage_bounds"
'''
