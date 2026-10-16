"""Prepare only; never edit the live Python or React source tree."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'postrun_criteria_scope'
OUT.mkdir(exist_ok=True)

frozen_helper = '''    @staticmethod
    def _frozen_criteria(db: sqlite3.Connection, task_id: str, frozen: dict[str, Any]) -> list[dict[str, Any]]:
        """Read exact enabled versions from the cache, including versions since revised."""
        rows = []
        for entry in frozen.get("entries") or []:
            ref = entry.get("rule_ref")
            rule_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=? AND kind='rule'",
                                  (task_id, ref)).fetchone()
            rule = _record(rule_row)
            attribute_ref = entry.get("attribute_ref") or rule.get("attribute_ref")
            attr_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=? AND kind='attribute'",
                                  (task_id, attribute_ref)).fetchone()
            if not rule_row or not attr_row:
                raise ProjectionNotReady("The prepared criterion version is not cached yet.")
            attribute = _record(attr_row)
            latest = _record(db.execute("SELECT body FROM criteria_listing WHERE task_id=? "
                                       "AND json_extract(body,'$.rule_ref')=?", (task_id, ref)).fetchone())
            body = ReadModel._summary(ref, attr_row["version"], attribute, rule, "in_evaluation",
                attribute_ref=attribute_ref, rule_ref=ref, registered=True,
                current=bool(latest.get("current")), pending_review=bool(latest.get("pending_review")),
                frozen_rule_set_ref=frozen.get("rule_set_ref"))
            for key in ("parents", "children", "stage", "iteration", "stage_id", "reason"):
                if latest.get(key) is not None:
                    body[key] = latest[key]
            rows.append({"task_id": task_id, "criterion_id": ref, "version": attr_row["version"],
                         "kind": "registry", "artifact_id": attr_row["artifact_id"], "body": _json(body)})
        return rows

'''

criteria_method = '''    def criteria(self, task_id: str, *, page: int = 1, page_size: int = PAGE_SIZE, q: str = "",
                 state: str = "", stage: str = "", cursor: str | None = None, **filters: Any) -> dict[str, Any]:
        if cursor:
            page = int(cursor)
        page, page_size, offset = _page(page, page_size)
        with self._cache() as db:
            meta = self._ready(db)
            self._task(db, task_id)
            frozen = self._meta(db).get(f"frozen:{task_id}")
            clauses, values = ["c.task_id=?"], [task_id]
            prefix, relation = "", "criteria_listing c"
            scope = "stage" if stage else "pending" if state == "pending" else "all"
            if stage:
                prefix = ("WITH selected AS (SELECT criterion_id,max(source_row) AS source_row FROM criterion_changes "
                          "WHERE task_id=? AND stage_id=? GROUP BY criterion_id), "
                          "stage_rows AS (SELECT ch.task_id,ch.criterion_id,json_extract(ch.body,'$.after') AS body,"
                          "json_extract(ch.body,'$.after.name') AS name,json_extract(ch.body,'$.after.state') AS state,"
                          "json_extract(ch.body,'$.after.role') AS role FROM criterion_changes ch JOIN selected s ON ch.source_row=s.source_row) ")
                relation = "stage_rows c"
                values = [task_id, stage, task_id]
            elif state == "working":
                scope = "frozen" if frozen is not None else "working"
                if frozen is not None:
                    rows = self._frozen_criteria(db, task_id, frozen)
                    prefix = ("WITH frozen_rows AS (SELECT ? AS task_id,json_extract(value,'$.criterion_id') AS criterion_id,"
                              "json_extract(value,'$.name') AS name,json_extract(value,'$.state') AS state,"
                              "json_extract(value,'$.role') AS role,value AS body FROM json_each(?)) ")
                    relation = "frozen_rows c"
                    values = [task_id, _json([_record(row) for row in rows]), task_id]
            if state and state != "all":
                if state in ("active", "working"):
                    if stage:
                        clauses.append("c.state IN ('candidate','needs_refine','deferred_next_round','promoted','active')")
                    elif state == "active" or frozen is None:
                        clauses.append("json_extract(c.body,'$.current')=1")
                elif state == "review":
                    clauses.append("json_extract(c.body,'$.current')=1 AND json_extract(c.body,'$.pending_review')=1")
                elif state == "pending":
                    if stage:
                        clauses.append("c.state IN ('candidate','needs_refine','deferred_next_round','pending')")
                    else:
                        reasons = ["coalesce(json_extract(c.body,'$.registered'),0)=0",
                                   "json_extract(c.body,'$.pending_review')=1"]
                        if frozen is not None:
                            reasons.append("NOT EXISTS (SELECT 1 FROM json_each(?) enabled WHERE enabled.value=json_extract(c.body,'$.rule_ref'))")
                            values.append(_json([entry["rule_ref"] for entry in frozen.get("entries") or [] if entry.get("rule_ref")]))
                        clauses.append("json_extract(c.body,'$.current')=1 AND (" + " OR ".join(reasons) + ")")
                elif state == "merged":
                    clauses.append("c.state IN ('merged','merged_away')")
                elif state == "retired":
                    clauses.append("c.state IN ('retired','withdrawn','filtered_out')")
                else:
                    clauses.append("c.state=?")
                    values.append(state)
            if q:
                clauses.append("(c.name LIKE ? ESCAPE '\\\\' OR c.criterion_id LIKE ? ESCAPE '\\\\' OR json_extract(c.body,'$.definition') LIKE ? ESCAPE '\\\\')")
                values.extend([_like(q)] * 3)
            if filters.get("role"):
                clauses.append("c.role=?")
                values.append(filters["role"])
            where = " AND ".join(clauses)
            total = db.execute(f"{prefix}SELECT count(*) FROM {relation} WHERE {where}", values).fetchone()[0]
            items = [_record(row) for row in db.execute(f"{prefix}SELECT c.body FROM {relation} WHERE {where} ORDER BY c.criterion_id LIMIT ? OFFSET ?", (*values, page_size, offset))]
            result = self._paged(items, total, page, page_size, meta)
            result["criteria_scope"] = scope
            if not stage and frozen is not None:
                result["rule_set_ref"] = frozen.get("rule_set_ref")
            return result

'''

test_case = '''

def test_working_scope_pins_frozen_versions_and_pending_filters_before_paging(setup):
    journal, model = setup

    def propose(name, version=1, title=None):
        attr = journal.artifact("attribute", {"attribute_id": f"attr_{name}", "version": version,
                                 "name": title or f"Endpoint {name.upper()}", "definition": "Test endpoint"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": f"attr_{name}",
                      "version": version, "artifact_id": attr})
        rule = journal.artifact("rule", {"rule_id": f"rule_{name}", "version": version,
                                 "attribute_ref": f"attr_{name}@v{version}", "rule_kind": "preference"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": f"rule_{name}",
                      "version": version, "artifact_id": rule})

    for name in "abc":
        propose(name)
    journal.event("run_a", "stage.opened", {"stage": "propose", "iteration": 0})
    journal.change()
    journal.event("run_a", "stage.closed", {"stage": "propose", "iteration": 0})
    model.sync()
    assert model.criteria("task_a", state="working")["total"] == 4
    frozen = journal.artifact("rule_set", {"entries": [
        {"rule_ref": "rule_a@v1", "attribute_ref": "attr_a@v1"},
        {"rule_ref": "rule_b@v1", "attribute_ref": "attr_b@v1"}]})
    journal.event("task_a", "criterion.version_approved", {"artifact_id": frozen, "rule_set_ref": "rules@v1"})
    journal.event("task_a", "human.review_requested", {"item_id": "q_b", "subject": {"kind": "rule_version", "id": "rule_b@v1"}})
    propose("a", 2, "Revised endpoint A")
    model.sync()
    working = model.criteria("task_a", state="working", page_size=1)
    assert working["criteria_scope"] == "frozen" and working["rule_set_ref"] == "rules@v1"
    assert working["total"] == 2 and len(working["items"]) == 1 and working["has_more"]
    assert model.criteria("task_a", state="working", page=2, page_size=1)["total"] == 2
    assert model.criteria("task_a", state="working", q="Revised")["total"] == 0
    frozen_a = model.criteria("task_a", state="working", q="Endpoint A")["items"][0]
    assert frozen_a["criterion_id"] == "rule_a@v1" and frozen_a["version"] == 1
    assert model.criterion("task_a", frozen_a["criterion_id"])["name"] == "Endpoint A"
    pending = model.criteria("task_a", state="pending", page_size=1)
    assert pending["total"] == 4 and len(pending["items"]) == 1 and pending["has_more"]
    assert model.criteria("task_a", state="pending", q="Endpoint C")["total"] == 1
    assert model.criteria("task_a", state="active")["total"] == 4  # Compatibility API still exposes the working universe.
    stage = model.stages("task_a")["items"][0]["stage_id"]
    assert model.criteria("task_a", stage=stage)["total"] == 1
    assert model.criteria("task_a", state="working", stage=stage)["total"] == 1
'''

proposed: dict[str, str] = {}
source = (ROOT / 'src/mas/ui/read_model.py').read_text(encoding='utf-8')
start = source.index('    def criteria(self, task_id: str,')
end = source.index('    @staticmethod\n    def _paged(', start)
replacement = source[:start] + frozen_helper + criteria_method + source[end:]
needle = '''    def _resolve_criterion(db: sqlite3.Connection, task_id: str, wanted: str) -> sqlite3.Row:
'''
new = '''    def _resolve_criterion(db: sqlite3.Connection, task_id: str, wanted: str) -> sqlite3.Row | dict[str, Any]:
        if "@v" in wanted:
            frozen = ReadModel._meta(db).get(f"frozen:{task_id}")
            if frozen is not None and any(entry.get("rule_ref") == wanted for entry in frozen.get("entries") or []):
                return next(row for row in ReadModel._frozen_criteria(db, task_id, frozen) if row["criterion_id"] == wanted)
'''
assert needle in replacement
proposed['src/mas/ui/read_model.py'] = replacement.replace(needle, new, 1)

path = 'web/client/src/pages/CriteriaPage.tsx'
source = (ROOT / path).read_text(encoding='utf-8')
replacement = "import { useEffect } from 'react';\n" + source
replacement = replacement.replace('export function CriteriaPage(', 'type CriteriaViewPage = Page<Criterion> & { criteria_scope?: string; rule_set_ref?: string };\n\nexport function CriteriaPage(', 1)
replacement = replacement.replace("{ query: '', state: 'active', stage: '', page: 1 }", "{ query: '', state: 'working', stage: '', page: 1 }")
replacement = replacement.replace('  const { query, state, stage, page } = filters;', '''  const { query, stage } = filters;
  const state = filters.state === 'active' ? 'working' : filters.state;
  const page = filters.state === 'active' ? 1 : filters.page;
  useEffect(() => {
    if (filters.state === 'active') setFilters(current => ({ ...current, state: 'working', page: 1 }));
  }, [filters.state, setFilters]);''')
replacement = replacement.replace('useResource<Page<Criterion>>(', 'useResource<CriteriaViewPage>(')
replacement = replacement.replace("id === stage ? 'active' : ''", "id === stage ? 'working' : ''")
replacement = replacement.replace("setState('active')", "setState('working')")
replacement = replacement.replace("state !== 'active'", "state !== 'working'")
needle = '  const lineageNames = new Map('
position = replacement.index(needle)
replacement = replacement[:position] + '''  const scopeCaption = state === 'working'
    ? resource.data?.criteria_scope === 'frozen'
      ? t('Criteria enabled in the latest prepared evaluation. Pending work is listed separately.', '最近准备的评估所启用的标准。待处理工作单独列出。')
      : t('The current working set while criteria are being developed.', '标准生成与整理中的当前工作集。')
    : state === 'pending'
      ? resource.data?.rule_set_ref
        ? t('Unregistered proposals, open reviews and current rules outside the prepared evaluation.', '未注册提案、待复核项目，以及未入选本次评估的当前规则。')
        : t('Unregistered proposals and current review items.', '未注册提案和当前待复核项目。')
      : t('Open a criterion to explore its evidence and changes.', '打开一条标准，查看其证据与变化。');
''' + replacement[position:]
replacement = replacement.replace("t('Open a criterion to explore its evidence and changes.', '打开一条标准，查看其证据与变化。')}><div", "scopeCaption}><div")
old = "{['active', 'pending', 'merged', 'retired'].map(value => <option key={value} value={value}>{stateText(value, t)}</option>)}"
new = "<option value=\"working\">{t('Working criteria', '当前标准')}</option><option value=\"pending\">{t('Pending', '待处理')}</option>{['merged', 'retired'].map(value => <option key={value} value={value}>{stateText(value, t)}</option>)}"
assert old in replacement
proposed[path] = replacement.replace(old, new, 1)

path = 'web/client/src/i18n.tsx'
source = (ROOT / path).read_text(encoding='utf-8')
needle = "    active: ['Active', '当前使用'],"
assert needle in source
proposed[path] = source.replace(needle, "    in_evaluation: ['In evaluation', '参与评估'],\n" + needle, 1)
path = 'tests/test_read_model.py'
proposed[path] = (ROOT / path).read_text(encoding='utf-8') + test_case

import sys
sys.path.insert(0, str(OUT))
from exact_details import extend
extend(proposed, ROOT)
from mandated_delta import extend as extend_mandated_delta
extend_mandated_delta(proposed, ROOT)
from lineage_details import extend as extend_lineage_details
extend_lineage_details(proposed, ROOT)

manifest, changes = {}, []
for path, text in proposed.items():
    original = (ROOT / path).read_text(encoding='utf-8')
    target = OUT / 'proposed' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8', newline='\n')
    manifest[path] = {'before_sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                      'after_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    changes.extend(difflib.unified_diff(original.splitlines(keepends=True), text.splitlines(keepends=True),
                                       fromfile='a/' + path, tofile='b/' + path))
(OUT / 'working_criteria.patch').write_text(''.join(changes), encoding='utf-8', newline='\n')
(OUT / 'patch_manifest.json').write_text(json.dumps({'status': 'prepared_not_applied', 'files': manifest}, indent=2) + '\n', encoding='utf-8')
print(OUT / 'working_criteria.patch')
