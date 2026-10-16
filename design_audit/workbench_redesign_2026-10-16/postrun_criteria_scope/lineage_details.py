"""Enrich the prepared patch only; never modify the running implementation."""
from pathlib import Path


def extend(proposed: dict[str, str], root: Path) -> None:
    path = 'src/mas/ui/read_model.py'
    source = proposed[path]
    helper = '''    @staticmethod
    def _lineage_node(db: sqlite3.Connection, task_id: str, ref: str,
                      value: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read one saved version, without recursing into its lineage graph."""
        if value is None:
            try:
                value = _record(ReadModel._resolve_criterion(db, task_id, ref))
            except KeyError:
                return {"id": ref, "ref": ref, "missing": True}
        detail_ref = value.get("detail_ref") or value.get("rule_ref") or value.get("attribute_ref")
        if not detail_ref:
            identity = value.get("criterion_id") or ref
            detail_ref = (f"{identity}@v{value['version']}" if "@v" not in identity
                          and value.get("version") is not None else identity)
        return {"id": detail_ref, "ref": ref, "detail_ref": detail_ref,
                "criterion_id": value.get("criterion_id"), "name": value.get("name"),
                "version": value.get("version"), "definition": value.get("definition"),
                "state": value.get("state"), "missing": False}

'''
    needle = '    def criterion(self, task_id: str, wanted: str) -> dict[str, Any]:\n'
    assert needle in source
    source = source.replace(needle, helper + needle, 1)
    old = '''            nodes = [{"id": body["criterion_id"], "name": body.get("name")}]
            edges = []
            for direction, refs in (("parent", body.get("parents") or []), ("child", body.get("children") or [])):
                for ref in refs:
                    identity = ref.split("@v")[0]
                    nodes.append({"id": identity, "ref": ref})
                    edges.append({"source": identity if direction == "parent" else body["criterion_id"],
                                  "target": body["criterion_id"] if direction == "parent" else identity})
'''
    new = '''            root_node = self._lineage_node(db, task_id, wanted, body)
            nodes = [dict(root_node, relation="selected")]
            seen = {root_node["id"]}
            edges = []
            for direction, refs in (("parent", body.get("parents") or []), ("child", body.get("children") or [])):
                for ref in refs:
                    node = self._lineage_node(db, task_id, ref)
                    if node["id"] not in seen:
                        nodes.append(dict(node, relation=direction))
                        seen.add(node["id"])
                    edges.append({"source": node["id"] if direction == "parent" else root_node["id"],
                                  "target": root_node["id"] if direction == "parent" else node["id"]})
'''
    assert old in source
    proposed[path] = source.replace(old, new, 1)

    path = 'web/client/src/api/types.ts'
    source = proposed[path]
    old = 'export interface LineageNode { id?: string; ref?: string; name?: string; state?: string; operation?: string; parents?: string[] }'
    new = 'export interface LineageNode { id?: string; ref?: string; detail_ref?: string; criterion_id?: string; name?: string; version?: number; definition?: string; state?: string; operation?: string; relation?: string; missing?: boolean; parents?: string[] }'
    assert old in source
    proposed[path] = source.replace(old, new, 1)

    path = 'web/client/src/pages/CriteriaPage.tsx'
    source = proposed[path]
    source = source.replace("node.name || t('Linked criterion', '关联标准')", "node.name || t('Record missing', '记录缺失')")
    old = '<strong>{node.name || t(\'Record missing\', \'记录缺失\')}</strong>{node.state && <Badge state={node.state} />}{node.operation && <p>{node.operation}</p>}'
    new = '''<div className="detail-meta">{node.relation && <small>{node.relation === 'parent' ? t('Parent criterion', '父标准') : node.relation === 'child' ? t('Child criterion', '子标准') : t('Selected version', '当前查看版本')}</small>}{node.version != null && <span>v{node.version}</span>}{node.state && <Badge state={node.state} />}</div>{node.detail_ref && !node.missing ? <button className="name-button" onClick={() => onOpen(node.detail_ref!)}>{node.name || t('Criterion', '标准')}</button> : <strong>{node.name || t('Record missing', '记录缺失')}</strong>}{node.definition && <p>{node.definition}</p>}{node.missing && <Audit data={{ ref: node.ref }} title={t('Missing record reference', '缺失记录的引用')} />}{node.operation && <p>{operationText(node.operation, t)}</p>}'''
    assert old in source
    proposed[path] = source.replace(old, new, 1)

    path = 'tests/test_read_model.py'
    proposed[path] += '''

def test_lineage_nodes_resolve_saved_versions_and_preserve_new_child_history(setup):
    journal, model = setup

    def proposal(identity, name, definition, version=1, operation="add", state="candidate", parents=(), children=()):
        ref = journal.artifact("criterion_candidate", {"attribute": {"name": name, "definition": definition},
            "rule": {"rule_kind": "preference"}, "supporting_claim_ids": []})
        journal.event("task_a", "criterion.change_recorded", {"pool": True, "criterion_id": identity,
            "version": version, "artifact_id": ref, "state": state, "operation": operation, "stage": "merge",
            "iteration": 0, "round_run_id": "run_a", "targets_in": list(parents), "targets_out": list(children)})

    proposal("cri_left", "First original", "First original definition")
    proposal("cri_right", "Second original", "Second original definition")
    proposal("cri_child", "Merged criterion", "Combined definition", operation="merge",
             parents=("cri_left@v1", "cri_right@v1", "cri_missing@v1"))
    proposal("cri_left", "First original", "First original definition", operation="merge", state="merged_away",
             children=("cri_child@v1",))
    proposal("cri_left", "Later revision", "Must not replace original", version=2, operation="revise")
    model.sync()
    detail = model.criterion("task_a", "cri_child")
    nodes = {node["id"]: node for node in detail["lineage"]["nodes"]}
    first, second = nodes["cri_left@v1"], nodes["cri_right@v1"]
    assert first["name"] == "First original" and first["definition"] == "First original definition"
    assert first["version"] == 1 and first["state"] == "merged_away"
    assert second["name"] == "Second original" and second["definition"] == "Second original definition"
    assert nodes["cri_missing@v1"]["missing"] and "name" not in nodes["cri_missing@v1"]
    assert {edge["source"] for edge in detail["lineage"]["edges"]} == {"cri_left@v1", "cri_right@v1", "cri_missing@v1"}
    assert all(edge["target"] == "cri_child@v1" for edge in detail["lineage"]["edges"])
    assert len(detail["history"]) == 1 and detail["history"][0]["before"] is None
    parent_detail = model.criterion("task_a", first["detail_ref"])
    assert parent_detail["version"] == 1 and parent_detail["definition"] == first["definition"]
    child_node = next(node for node in parent_detail["lineage"]["nodes"] if node.get("relation") == "child")
    assert child_node["name"] == "Merged criterion" and child_node["detail_ref"] == "cri_child@v1"
'''
