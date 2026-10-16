"""Prepare latest-evaluation status presentation. Active source and dist stay untouched."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'postrun_evaluation_status'
OUT.mkdir(exist_ok=True)
proposed = {}

helper = '''    @staticmethod
    def _evaluation_context(db: sqlite3.Connection, task_id: str,
                            frozen: dict[str, Any] | None) -> dict[str, Any]:
        """Index one cached freeze and current queue once per request, never per row."""
        enabled = {entry["rule_ref"]: entry for entry in (frozen or {}).get("entries") or []}
        deferred, by_attribute, reviews = {}, {}, {}
        for entry in (frozen or {}).get("deferred") or []:
            deferred.setdefault(entry.get("rule_ref"), []).append(entry)
        for entry in [*enabled.values(), *((frozen or {}).get("deferred") or [])]:
            if entry.get("attribute_ref") and entry.get("rule_ref"):
                by_attribute.setdefault(entry["attribute_ref"], set()).add(entry["rule_ref"])
        for row in db.execute("SELECT item_id,subject_ref,state FROM reviews WHERE task_id=? ORDER BY item_id", (task_id,)):
            reviews.setdefault(row["subject_ref"], []).append({"item_ref": row["item_id"], "state": row["state"]})
        return {"frozen": frozen, "enabled": enabled, "deferred": deferred, "by_attribute": by_attribute,
                "pending": set((frozen or {}).get("pending") or []), "reviews": reviews}

    @staticmethod
    def _criterion_evaluation(body: dict[str, Any], context: dict[str, Any], *,
                              detail: bool = False) -> dict[str, Any]:
        """An evaluation membership reading, separate from registry/pool lifecycle state."""
        historical = {"state": "historical", "scope": "saved_version", "reason_kind": "historical_view"}
        if str(body.get("detail_ref") or "").startswith("change:"):
            return dict(historical, scope="stage_snapshot")
        frozen, ref = context["frozen"], body.get("rule_ref")
        if not ref:
            refs = context["by_attribute"].get(body.get("attribute_ref"), set())
            ref = next(iter(refs)) if len(refs) == 1 else None
        included = context["enabled"].get(ref)
        held = context["deferred"].get(ref, [])
        rule_held = [entry for entry in held if entry.get("scope", "rule") == "rule"]
        # An exact historical rule can still be enabled in the latest freeze. Otherwise
        # do not turn its absence from that freeze into a claim about its previous use.
        if included is None and not rule_held and ref not in context["pending"] and not body.get("current"):
            return historical
        if frozen is None:
            return {"state": "not_prepared", "scope": "latest_prepared_evaluation", "reason_kind": "not_prepared"}
        result = {"scope": "latest_prepared_evaluation", "rule_set_ref": frozen.get("rule_set_ref"),
                  "prepared_at": frozen.get("at"), "reason": None}
        if included is not None:
            result.update(state="enabled", reason_kind="enabled")
        elif rule_held:
            record = rule_held[0]
            result.update(state="deferred", reason_kind=record.get("reason_kind") or
                          ("capability_deferred" if record.get("capability") else "not_selected"),
                          reason=record.get("reason"))
        elif ref in context["pending"]:
            result.update(state="pending", reason_kind="review_pending")
        elif not body.get("registered"):
            result.update(state="pending", reason_kind="unregistered_proposal")
        else:
            result.update(state="pending", reason_kind="not_selected")
        records = ([included] if included is not None else []) + held
        review_refs = sorted({item for record in records for item in record.get("review_item_refs") or []})
        attempt_refs = sorted({attempt["attempt_ref"] for record in records for review in record.get("reviews") or []
                               for attempt in review.get("attempts") or [] if attempt.get("attempt_ref")})
        basis = {"source": "cached_frozen_rule_set", "rule_ref": ref,
                 "review_item_refs": review_refs, "attempt_refs": attempt_refs,
                 "queue_items": context["reviews"].get(ref, []), "queue_state_scope": "current_registry_queue"}
        if detail:
            basis["frozen_records"] = records
            basis["listed_pending_at_preparation"] = ref in context["pending"]
        result["basis"] = basis
        return result

'''
path = 'src/mas/ui/read_model.py'
source = (ROOT / path).read_text(encoding='utf-8')
needle = '    def criteria(self, task_id: str, *, page: int = 1, page_size: int = PAGE_SIZE, q: str = "",\n'
assert source.count(needle) == 1
source = source.replace(needle, helper + needle, 1)
needle = '            for item in items:\n                if not item.get("detail_ref"):'
assert source.count(needle) == 1
source = source.replace(needle, '            evaluation_context = self._evaluation_context(db, task_id, frozen)\n' + needle, 1)
needle = '            result = self._paged(items, total, page, page_size, meta)\n'
assert source.count(needle) == 1
source = source.replace(needle, '                item["evaluation"] = self._criterion_evaluation(item, evaluation_context)\n' + needle, 1)
needle = '            body["editable"] = not is_task_mandated(attribute)\n'
assert source.count(needle) == 1
source = source.replace(needle, needle + '''            frozen = self._meta(db).get(f"frozen:{task_id}")
            body["evaluation"] = self._criterion_evaluation(body, self._evaluation_context(db, task_id, frozen), detail=True)
''', 1)
proposed[path] = source

path = 'web/client/src/api/types.ts'
source = (ROOT / path).read_text(encoding='utf-8')
needle = 'export interface Criterion { criterion_id: string;'
new_type = '''export interface CriterionEvaluation { state: 'enabled' | 'deferred' | 'pending' | 'not_prepared' | 'historical'; scope: string; rule_set_ref?: string | null; prepared_at?: string | null; reason_kind: string; reason?: string | null; basis?: Record<string, unknown> }
'''
assert needle in source
proposed[path] = source.replace(needle, new_type + 'export interface Criterion { evaluation?: CriterionEvaluation; criterion_id: string;', 1)

path = 'web/client/src/components/CriteriaEvaluation.tsx'
assert not (ROOT / path).exists()
proposed[path] = '''import type { CriterionEvaluation } from '../api/types';
import { useI18n } from '../i18n';
import { Audit, Badge } from './UI';

export function CriteriaEvaluation({ value, compact = false }: { value?: CriterionEvaluation; compact?: boolean }) {
  const { t } = useI18n();
  if (!value) return null;
  const labels = {
    enabled: t('Enabled', '已启用'), deferred: t('Deferred', '已延后'), pending: t('Pending', '待处理'),
    not_prepared: t('Not prepared', '尚未准备'), historical: t('Saved version', '历史版本'),
  };
  const reasons: Record<string, string> = {
    enabled: t('Included in the latest prepared evaluation.', '已纳入最近准备的评估。'),
    unresolved_review: t('Review remains unresolved; this criterion is not enabled.', '复核尚未解决，此标准暂未启用。'),
    non_executable_preference: t('The scoring condition is not executable yet.', '计分条件尚不可执行。'),
    capability_deferred: t('The required evidence route is deferred.', '所需证据路线已延后处理。'),
    review_pending: t('Listed as pending when this evaluation was prepared.', '准备本次评估时，此标准仍待复核。'),
    unregistered_proposal: t('This proposal has not been registered for evaluation.', '此提案尚未注册为评估标准。'),
    not_selected: t('Not included; an exclusion reason is not recorded.', '尚未纳入，未记录具体排除理由。'),
    not_prepared: t('No evaluation has been prepared for this task.', '此任务尚未准备评估。'),
    historical_view: t('See the saved version and its change history.', '查看此保存版本及其变化历史。'),
  };
  const summary = reasons[value.reason_kind] || t('See the recorded decision for the reason.', '具体理由请查看处理记录。');
  const badge = <Badge state={value.state === 'enabled' ? 'completed' : ['deferred', 'pending'].includes(value.state) ? 'pending' : undefined} label={labels[value.state]} />;
  return compact ? <>{badge}<p className="cell-note">{summary}</p></> : <section className="notice"><div className="row spread"><strong>{value.state === 'historical' ? t('Saved version', '历史版本') : t('Latest prepared evaluation', '最近准备的评估')}</strong>{badge}</div><p>{summary}</p><Audit data={value} title={t('Decision record', '处理记录')} /></section>;
}
'''

path = 'web/client/src/pages/CriteriaPage.tsx'
source = (ROOT / path).read_text(encoding='utf-8')
source = source.replace("import { CriterionEditor } from '../components/CriterionEditor';", "import { CriterionEditor } from '../components/CriterionEditor';\nimport { CriteriaEvaluation } from '../components/CriteriaEvaluation';", 1)
needle = "<th>{t('State', '状态')}</th><th>{t('Evidence', '证据')}</th>"
assert source.count(needle) == 1
source = source.replace(needle, "<th>{t('Recorded state', '已记录状态')}</th><th>{t('Latest evaluation', '最近评估')}</th><th>{t('Evidence', '证据')}</th>", 1)
needle = '<td><Badge state={criterion.state} /></td><td className="numeric">'
assert source.count(needle) == 1
source = source.replace(needle, '<td><Badge state={criterion.state} /></td><td><CriteriaEvaluation value={criterion.evaluation} compact /></td><td className="numeric">', 1)
needle = '<p className="detail-definition">{detail.data.definition}</p>'
assert source.count(needle) == 1
source = source.replace(needle, needle + '<CriteriaEvaluation value={detail.data.evaluation} />', 1)
proposed[path] = source

path = 'scripts/accept_workbench_run.py'
source = (ROOT / path).read_text(encoding='utf-8')
source = source.replace('def criterion_cache_view(item: dict[str, Any]) -> dict[str, Any]:',
    'def criterion_cache_view(item: dict[str, Any], evaluation_context: dict[str, Any]) -> dict[str, Any]:', 1)
needle = '\n    value = dict(item)\n'
assert source.count(needle) == 1
source = source.replace(needle, '\n    from mas.ui.read_model import ReadModel' + needle, 1)
needle = '    return value\n\n\ndef measure('
assert source.count(needle) == 1
source = source.replace(needle, '    value["evaluation"] = ReadModel._criterion_evaluation(value, evaluation_context)\n' + needle, 1)
needle = '        return {"metadata": metadata, "summary": json.loads(summary_row["body"]),\n'
assert source.count(needle) == 1
source = source.replace(needle, '        evaluation_context = ReadModel._evaluation_context(database, task_id, ReadModel._meta(database).get(f"frozen:{task_id}"))\n' + needle, 1)
source = source.replace('criterion_cache_view(json.loads(row[0]))', 'criterion_cache_view(json.loads(row[0]), evaluation_context)', 1)
needle = '        inventory = criteria.registry_inventory(core, task_id)\n'
assert source.count(needle) == 1
source = source.replace(needle, '''        latest_prepared = None
        for (raw,) in database.execute("SELECT body FROM events WHERE stream_id=? AND event_type='criterion.version_approved' ORDER BY seq DESC", (task_id,)):
            prepared_event = json.loads(raw)
            if public(prepared_event):
                prepared_set = payload(core, prepared_event["payload"]["artifact_id"], {"rule_set"})
                latest_prepared = {"rule_set_ref": prepared_event["payload"].get("rule_set_ref"),
                    "entries": prepared_set.get("entries") or [], "deferred": prepared_set.get("deferred") or []}
                break
''' + needle, 1)
needle = '                "active_rule_refs": sorted(row["rule_ref"] for row in inventory["active"]),\n'
assert source.count(needle) == 1
source = source.replace(needle, needle + '                "latest_prepared": latest_prepared,\n', 1)
needle = '        checks.append(compare_stages("api_vs_service_cache.stages", api_stages, cached["stages"]))\n'
assert source.count(needle) == 1
source = source.replace(needle, '''        prepared = source["latest_prepared"]
        enabled = {entry["rule_ref"] for entry in (prepared or {}).get("entries") or []}
        held = {}
        for entry in (prepared or {}).get("deferred") or []:
            if entry.get("scope", "rule") == "rule":
                held.setdefault(entry["rule_ref"], entry)
        expected_evaluation, actual_evaluation = [], []
        for item in api_criteria:
            if not item.get("registered") or not item.get("current"):
                continue
            ref, evaluation = item.get("rule_ref"), item.get("evaluation") or {}
            expected_state = "enabled" if ref in enabled else "deferred" if ref in held else "pending" if prepared else "not_prepared"
            expected_evaluation.append({"rule_ref": ref, "state": expected_state,
                "rule_set_ref": prepared.get("rule_set_ref") if prepared else None,
                "reason": held[ref].get("reason") if ref in held and ref not in enabled else None})
            actual_evaluation.append({"rule_ref": ref, "state": evaluation.get("state"),
                "rule_set_ref": evaluation.get("rule_set_ref"), "reason": evaluation.get("reason")})
        checks.append(compare("api_vs_source.latest_prepared_evaluation_membership_and_reasons", actual_evaluation, expected_evaluation))
''' + needle, 1)
proposed[path] = source

test = '''


def test_latest_evaluation_status_preserves_registry_history_and_frozen_reasons(setup):
    journal, model = setup

    def register(name, version=1):
        attribute = journal.artifact("attribute", {"attribute_id": f"attr_{name}", "version": version, "name": name})
        journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": f"attr_{name}", "version": version, "artifact_id": attribute})
        rule = journal.artifact("rule", {"rule_id": f"rule_{name}", "version": version, "attribute_ref": f"attr_{name}@v{version}", "rule_kind": "preference"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": f"rule_{name}", "version": version, "artifact_id": rule})

    register("mw")
    register("anchor")
    model.sync()
    assert model.criterion("task_a", "rule_mw@v1")["evaluation"]["state"] == "not_prepared"
    first = journal.artifact("rule_set", {"entries": [{"rule_ref": "rule_mw@v1", "attribute_ref": "attr_mw@v1"}]})
    journal.event("task_a", "criterion.version_approved", {"rule_set_ref": "rules@v1", "artifact_id": first})
    register("mw", 2)
    record = {"rule_ref": "rule_mw@v2", "attribute_ref": "attr_mw@v2", "scope": "rule", "reason_kind": "unresolved_review",
        "reason": "Review is unresolved for the recorded cutoff", "review_item_refs": ["q_mw"],
        "reviews": [{"item_ref": "q_mw", "state": "open", "attempts": [{"attempt_ref": "art_attempt", "outcome": "unresolved", "reason_text": "Actual machine reason"}]}]}
    frozen = journal.artifact("rule_set", {"entries": [{"rule_ref": "rule_anchor@v1", "attribute_ref": "attr_anchor@v1"}], "deferred": [record]})
    journal.event("task_a", "human.review_requested", {"item_id": "q_mw", "subject": {"kind": "rule_version", "id": "rule_mw@v2"}})
    journal.event("task_a", "criterion.version_approved", {"rule_set_ref": "rules@v2", "artifact_id": frozen, "pending": ["rule_mw@v2"]})
    journal.event("run_a", "stage.opened", {"stage": "propose", "iteration": 0})
    change = journal.change()
    journal.event("run_a", "stage.closed", {"stage": "propose", "iteration": 0})
    model.sync()
    pending = model.criteria("task_a", state="pending", q="mw")["items"][0]
    assert pending["state"] == "active"  # Registry status is not rewritten.
    assert pending["evaluation"]["state"] == "deferred" and pending["evaluation"]["reason"] == record["reason"]
    assert pending["evaluation"]["basis"]["review_item_refs"] == ["q_mw"]
    detail = model.criterion("task_a", "rule_mw@v2")
    assert detail["evaluation"]["basis"]["frozen_records"] == [record]
    assert detail["evaluation"]["basis"]["attempt_refs"] == ["art_attempt"]
    assert model.criterion("task_a", "rule_anchor@v1")["evaluation"]["state"] == "enabled"
    historical = model.criterion("task_a", "rule_mw@v1")["evaluation"]
    assert historical == {"state": "historical", "scope": "saved_version", "reason_kind": "historical_view"}
    stage = model.criterion("task_a", "change:" + change["event_id"])["evaluation"]
    assert stage["state"] == "historical" and stage["scope"] == "stage_snapshot"
    assert model.criteria("task_a", state="working")["total"] == 1
'''
path = 'tests/test_read_model.py'
proposed[path] = (ROOT / path).read_text(encoding='utf-8') + test

manifest, changes = {}, []
for path, text in proposed.items():
    exists = (ROOT / path).exists()
    original = (ROOT / path).read_text(encoding='utf-8') if exists else ''
    target = OUT / 'proposed' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8', newline='\n')
    manifest[path] = {'before_sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest() if exists else None,
                      'after_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    changes.extend(difflib.unified_diff(original.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile='a/' + path if exists else '/dev/null', tofile='b/' + path))
(OUT / 'latest_evaluation_status.patch').write_text(''.join(changes), encoding='utf-8', newline='\n')
(OUT / 'patch_manifest.json').write_text(json.dumps({'status': 'prepared_not_applied', 'files': manifest}, indent=2) + '\n', encoding='utf-8')
print(OUT / 'latest_evaluation_status.patch')
