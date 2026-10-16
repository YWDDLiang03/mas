"""Extend only the prepared patch with version-pinned table-to-detail references."""
from pathlib import Path


def extend(proposed: dict[str, str], root: Path) -> None:
    path = 'src/mas/ui/read_model.py'
    source = proposed[path]
    helper = '''    @staticmethod
    def _exact_criterion(db: sqlite3.Connection, task_id: str, wanted: str) -> dict[str, Any] | None:
        """Resolve saved references without following an alias to a newer version."""
        if wanted.startswith("change:"):
            change = db.execute("SELECT * FROM criterion_changes WHERE task_id=? AND json_extract(body,'$.id')=?",
                                (task_id, wanted[len("change:"):])).fetchone()
        else:
            version_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=?", (task_id, wanted)).fetchone()
            if version_row:
                value = _record(version_row)
                is_rule = version_row["kind"] == "rule"
                attribute_ref = value.get("attribute_ref") if is_rule else wanted
                attr_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=? AND kind='attribute'",
                                      (task_id, attribute_ref)).fetchone()
                if not attr_row:
                    return None
                attribute = _record(attr_row)
                field = "rule_ref" if is_rule else "attribute_ref"
                latest = _record(db.execute(f"SELECT body FROM criteria_listing WHERE task_id=? "
                                 f"AND json_extract(body,'$.{field}')=?", (task_id, wanted)).fetchone())
                current_row = db.execute("SELECT body FROM criteria_listing WHERE task_id=? AND json_extract(body,'$.current')=1 "
                    f"AND json_extract(body,'$.{field}') IN (SELECT ref FROM criterion_versions WHERE task_id=? AND base_id=? AND kind=?)",
                    (task_id, task_id, version_row["base_id"], version_row["kind"])).fetchone()
                current = _record(current_row)
                body = ReadModel._summary(wanted, attr_row["version"], attribute, value if is_rule else {},
                    latest.get("state") or "historical", attribute_ref=attribute_ref,
                    rule_ref=wanted if is_rule else None, registered=True,
                    current=bool(latest.get("current")), detail_ref=wanted,
                    historical_version=not is_rule or not bool(latest.get("current")),
                    current_ref=current.get("rule_ref") if current else None)
                return {"criterion_id": wanted, "version": attr_row["version"], "kind": "registry",
                        "artifact_id": attr_row["artifact_id"], "body": _json(body)}
            if "@v" not in wanted:
                return None
            base, version = wanted.rsplit("@v", 1)
            if not version.isdigit():
                return None
            change = db.execute("SELECT * FROM criterion_changes WHERE task_id=? AND criterion_id=? AND version=? "
                                "AND json_extract(body,'$.kind') IS NULL AND json_extract(body,'$.after.name') IS NOT NULL "
                                "ORDER BY source_row DESC LIMIT 1",
                                (task_id, base, int(version))).fetchone()
        if not change:
            return None
        history = _record(change)
        body = dict(history.get("after") or {})
        if not body:
            return None
        latest_row = db.execute("SELECT * FROM criteria_current WHERE task_id=? AND criterion_id=?",
                                (task_id, change["criterion_id"])).fetchone()
        earlier = not latest_row or latest_row["updated_row"] != change["source_row"]
        if not earlier:
            current = db.execute("SELECT body FROM criteria_listing WHERE task_id=? AND criterion_id=?",
                                 (task_id, change["criterion_id"])).fetchone()
            body = _record(current) or body
        current_pool = db.execute("SELECT 1 FROM criterion_changes WHERE source_row=? AND json_extract(body,'$.kind') IS NULL "
                                  "AND json_extract(body,'$.after.name') IS NOT NULL", (latest_row["updated_row"],)).fetchone() if latest_row else None
        body.update(detail_ref=wanted, historical_version=earlier,
                    current_ref=f"{change['criterion_id']}@v{latest_row['version']}" if earlier and current_pool else None)
        return {"criterion_id": change["criterion_id"], "version": body.get("version"), "kind": "pool",
                "artifact_id": history.get("artifact_id"), "body": _json(body)}

'''
    needle = '    @staticmethod\n    def _frozen_criteria('
    assert needle in source
    source = source.replace(needle, helper + needle, 1)
    frozen_start = source.index('    def _frozen_criteria(')
    source = source[:frozen_start] + source[frozen_start:].replace('''            for key in ("parents", "children", "stage", "iteration", "stage_id", "reason"):
''', '''            version_info = ReadModel._exact_criterion(db, task_id, ref)
            detail = _record(version_info)
            body.update(detail_ref=ref, historical_version=detail.get("historical_version", False),
                        current_ref=detail.get("current_ref"))
            for key in ("parents", "children", "stage", "iteration", "stage_id", "reason"):
''', 1)
    old = '''        row = db.execute("SELECT * FROM criteria_listing WHERE task_id=? AND criterion_id=?", (task_id, wanted)).fetchone()'''
    new = '''        if wanted.startswith("change:") or "@v" in wanted:
            exact = ReadModel._exact_criterion(db, task_id, wanted)
            if exact is None:
                raise KeyError(f"no saved criterion version {wanted} in {task_id}")
            return exact
''' + old
    assert old in source
    source = source.replace(old, new, 1)
    old = '''json_extract(ch.body,'$.after') AS body,"
'''
    new = '''json_set(json_extract(ch.body,'$.after'),'$.detail_ref','change:' || json_extract(ch.body,'$.id')) AS body,"
'''
    assert old in source
    source = source.replace(old, new, 1)
    needle = '''            result = self._paged(items, total, page, page_size, meta)
'''
    insert = '''            for item in items:
                if not item.get("detail_ref"):
                    identity = item["criterion_id"]
                    item["detail_ref"] = (f"{identity}@v{item['version']}" if identity.startswith("cri_") and "@v" not in identity
                                          else item.get("rule_ref") or item.get("attribute_ref") or identity)
'''
    assert needle in source
    source = source.replace(needle, insert + needle, 1)
    proposed[path] = source

    path = 'web/client/src/api/types.ts'
    source = (root / path).read_text(encoding='utf-8')
    source = source.replace('export interface Criterion { criterion_id: string;', 'export interface Criterion { criterion_id: string; detail_ref?: string;', 1)
    source = source.replace('export interface CriterionDetail extends Criterion {', 'export interface CriterionDetail extends Criterion { historical_version?: boolean; current_ref?: string | null;', 1)
    proposed[path] = source
    path = 'web/client/src/pages/CriteriaPage.tsx'
    source = proposed[path]
    needle = 'type CriteriaViewPage = '
    helper = '''export function criterionDetailRef(criterion: Criterion) {
  if (criterion.detail_ref) return criterion.detail_ref;
  if (criterion.criterion_id.startsWith('cri_') && !criterion.criterion_id.includes('@v')) return `${criterion.criterion_id}@v${criterion.version}`;
  return criterion.rule_ref || criterion.attribute_ref || criterion.criterion_id;
}

'''
    assert needle in source
    source = source.replace(needle, helper + needle, 1)
    source = source.replace('onOpen(criterion.criterion_id)', 'onOpen(criterionDetailRef(criterion))')
    source = source.replace('{enabled && detail.data.editable === false &&', '''{detail.data.historical_version && <div className="notice"><p>{t('This saved version is read-only. Open the current criterion to make changes.', '此保存版本只供查看。需要修改时，请打开当前标准。')}</p>{detail.data.current_ref && <button onClick={() => onOpen(detail.data!.current_ref!)}>{t('Open current criterion', '打开当前标准')}</button>}</div>}{enabled && !detail.data.historical_version && detail.data.editable === false &&''')
    source = source.replace('{enabled && detail.data.editable !== false &&', '{enabled && !detail.data.historical_version && detail.data.editable !== false &&')
    proposed[path] = source

    path = 'tests/test_read_model.py'
    source = proposed[path]
    source += '''

def test_criterion_detail_refs_pin_pool_version_and_same_version_stage_state(setup):
    journal, model = setup
    journal.event("run_a", "stage.opened", {"stage": "propose", "iteration": 0})
    journal.change()
    journal.event("run_a", "stage.closed", {"stage": "propose", "iteration": 0})
    journal.event("run_a", "stage.opened", {"stage": "filter", "iteration": 0})
    journal.change("revise", "needs_refine", 2)
    journal.event("run_a", "stage.closed", {"stage": "filter", "iteration": 0})
    model.sync()
    stages = model.stages("task_a")["items"]
    proposal = model.criteria("task_a", stage=stages[0]["stage_id"])["items"][0]
    filtered = model.criteria("task_a", stage=stages[1]["stage_id"])["items"][0]
    assert proposal["detail_ref"].startswith("change:")
    assert model.criterion("task_a", proposal["detail_ref"])["version"] == 1
    assert model.criterion("task_a", "cri_a")["version"] == 2  # Base ID keeps existing latest semantics.
    assert model.criterion("task_a", "cri_a@v1")["version"] == 1
    journal.change("remove", "filtered_out", 2)  # State can change without changing item version.
    model.sync()
    current = model.criterion("task_a", "cri_a@v2")
    assert current["state"] == "retired" and current["raw_state"] == "filtered_out"
    old = model.criterion("task_a", filtered["detail_ref"])
    assert old["version"] == 2 and old["state"] == "needs_refine" and old["historical_version"]
    assert old["current_ref"] == "cri_a@v2"
    with pytest.raises(KeyError):
        model.criterion("task_a", "cri_a@v999")
'''
    source = source.replace('''    assert model.criterion("task_a", frozen_a["criterion_id"])["name"] == "Endpoint A"
''', '''    assert frozen_a["detail_ref"] == "rule_a@v1"
    assert model.criterion("task_a", frozen_a["detail_ref"])["name"] == "Endpoint A"
    assert model.criterion("task_a", frozen_a["detail_ref"])["historical_version"]
    assert model.criterion("task_a", "attr_a@v1")["name"] == "Endpoint A"
    assert model.criterion("task_a", "rule_a@v2")["name"] == "Revised endpoint A"
''', 1)
    proposed[path] = source
