"""Prepare query-only registered-version history repair; do not edit active code."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'postrun_revision_history'
OUT.mkdir(exist_ok=True)

helper = '''    @staticmethod
    def _registered_version_history(db: sqlite3.Connection, task_id: str,
                                    refs: list[str | None]) -> list[dict[str, Any]]:
        """Follow immutable supersedes links, keeping attribute and rule records separate."""
        pending = [(ref, None) for ref in refs if ref]
        visited, history = set(), []
        while pending:
            ref, expected_kind = pending.pop()
            if ref in visited:
                continue
            visited.add(ref)
            row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=?",
                             (task_id, ref)).fetchone()
            if not row or (expected_kind is not None and row["kind"] != expected_kind):
                continue
            kind, record = row["kind"], _record(row)
            if kind not in ("attribute", "rule"):
                continue
            previous_ref = record.get("supersedes")
            previous_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=? AND kind=?",
                                      (task_id, previous_ref, kind)).fetchone() if previous_ref else None
            previous = _record(previous_row) if previous_row else None
            metadata = _record(db.execute("SELECT body FROM criterion_changes WHERE task_id=? AND source_row=?",
                                          (task_id, row["source_row"])).fetchone())
            # Only the version's own revision metadata describes this transition. A later
            # adjudication can copy the previous version's metadata into a new artifact.
            revision = record.get("workbench_revision") or {}
            is_revision = (bool(previous_ref) and isinstance(revision, dict)
                           and revision.get(f"source_{kind}_ref") == previous_ref)
            reason = revision.get("reason") if is_revision else None
            reason_source = "workbench_revision" if isinstance(reason, str) and reason.strip() else None
            if reason_source is None:
                reason = record.get("rationale") or metadata.get("reason")
                reason_source = "rationale" if reason is not None else None
            item = dict(metadata)
            item.update(ref=ref, kind=kind, version=row["version"], source_row=row["source_row"],
                        artifact_id=row["artifact_id"], supersedes=previous_ref,
                        before_ref=previous_ref, after_ref=ref, before=previous, after=record,
                        predecessor_missing=bool(previous_ref and previous_row is None),
                        operation="revise" if previous_ref else metadata.get("operation"),
                        reason=reason, reason_source=reason_source)
            history.append(item)
            if previous_ref:
                pending.append((previous_ref, kind))
            if kind == "rule" and record.get("attribute_ref"):
                pending.append((record["attribute_ref"], "attribute"))
        return sorted(history, key=lambda item: item["source_row"])

'''

path = 'src/mas/ui/read_model.py'
original = (ROOT / path).read_text(encoding='utf-8')
needle = '    def criterion(self, task_id: str, wanted: str) -> dict[str, Any]:\n'
assert original.count(needle) == 1
replacement = original.replace(needle, helper + needle, 1)
old = '''            history = [_record(change) for change in db.execute(f"SELECT body FROM criterion_changes WHERE task_id=? AND criterion_id IN ({marks}) ORDER BY source_row", (task_id, *history_ids))]
'''
new = '''            history_rows = db.execute(f"SELECT source_row,body FROM criterion_changes WHERE task_id=? AND criterion_id IN ({marks}) ORDER BY source_row", (task_id, *history_ids)).fetchall()
            history = [_record(change) for change in history_rows]
            if row["kind"] == "registry":
                registered = self._registered_version_history(db, task_id, [body.get("rule_ref"), body.get("attribute_ref")])
                if registered:
                    by_row = {change["source_row"]: change for change in registered}
                    # Pool/stage changes keep their original before/after and reason.
                    by_row.update({change["source_row"]: _record(change) for change in history_rows
                                   if _record(change).get("kind") not in ("attribute", "rule")})
                    history = [by_row[source_row] for source_row in sorted(by_row)]
'''
assert replacement.count(old) == 1
proposed = {path: replacement.replace(old, new, 1)}

test_case = '''


def test_registered_history_follows_exact_supersedes_without_mixing_record_kinds(setup):
    journal, model = setup

    def record(kind, base, version, **values):
        payload = {f"{kind}_id": base, "version": version, **values}
        ref = journal.artifact(kind, payload)
        journal.event("task_a", "criterion.version_proposed", {"kind": kind, "id": base,
                      "version": version, "artifact_id": ref})

    record("attribute", "attr_endpoint", 1, name="Endpoint", definition="Original definition",
           direction="higher_better", unit="log reciprocal", rationale="Original rationale")
    record("rule", "rule_endpoint", 1, attribute_ref="attr_endpoint@v1", rule_kind="preference",
           predicate_form="ordering")
    revision = {"source_attribute_ref": "attr_endpoint@v1", "source_rule_ref": "rule_endpoint@v1",
                "reason": "Correct the direction before evaluation", "changes": {"attribute": {"direction": "lower_better"}}}
    record("attribute", "attr_endpoint", 2, name="Endpoint", definition="Corrected definition", unit="log reciprocal",
           direction="lower_better", supersedes="attr_endpoint@v1", rationale="Original rationale",
           workbench_revision=revision)
    record("rule", "rule_endpoint", 2, attribute_ref="attr_endpoint@v2", rule_kind="preference",
           predicate_form="ordering", supersedes="rule_endpoint@v1", workbench_revision=revision)
    # A subsequent version exists, but opening v2 must not silently include its future.
    record("attribute", "attr_endpoint", 3, name="Endpoint", definition="Later definition", unit="log reciprocal",
           direction="lower_better", supersedes="attr_endpoint@v2", rationale="Later rationale", workbench_revision=revision)
    record("rule", "rule_endpoint", 3, attribute_ref="attr_endpoint@v3", rule_kind="preference",
           predicate_form="ordering", supersedes="rule_endpoint@v2", workbench_revision=revision)
    model.sync()
    first = model.criterion("task_a", "rule_endpoint@v1")
    revised = model.criterion("task_a", "rule_endpoint@v2")
    history = {change["ref"]: change for change in revised["history"]}
    assert set(history) == {"attr_endpoint@v1", "rule_endpoint@v1", "attr_endpoint@v2", "rule_endpoint@v2"}
    assert {change["ref"] for change in first["history"]} == {"attr_endpoint@v1", "rule_endpoint@v1"}
    attr, rule = history["attr_endpoint@v2"], history["rule_endpoint@v2"]
    assert attr["before"]["direction"] == "higher_better" and attr["after"]["direction"] == "lower_better"
    assert attr["before"]["definition"] == "Original definition" and attr["after"]["definition"] == "Corrected definition"
    assert "rule_kind" not in attr["before"] and "rule_kind" not in attr["after"]
    assert rule["before"]["attribute_ref"] == "attr_endpoint@v1" and rule["after"]["attribute_ref"] == "attr_endpoint@v2"
    assert "direction" not in rule["before"] and "direction" not in rule["after"]
    assert attr["reason"] == rule["reason"] == revision["reason"]
    assert attr["reason_source"] == rule["reason_source"] == "workbench_revision"
    assert not attr["predecessor_missing"] and not rule["predecessor_missing"]
    latest = {change["ref"]: change for change in model.criterion("task_a", "rule_endpoint@v3")["history"]}
    assert latest["attr_endpoint@v3"]["reason"] == "Later rationale"  # Copied v2 metadata is not a new reason.
    assert latest["rule_endpoint@v3"]["reason"] is None


def test_registered_history_keeps_missing_predecessor_unknown(setup):
    journal, model = setup
    attr = journal.artifact("attribute", {"attribute_id": "attr_orphan", "version": 2,
        "name": "Orphan endpoint", "direction": "lower_better", "supersedes": "attr_orphan@v1"})
    journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": "attr_orphan", "version": 2, "artifact_id": attr})
    rule = journal.artifact("rule", {"rule_id": "rule_orphan", "version": 2, "attribute_ref": "attr_orphan@v2",
        "rule_kind": "preference", "supersedes": "rule_orphan@v1"})
    journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": "rule_orphan", "version": 2, "artifact_id": rule})
    model.sync()
    history = model.criterion("task_a", "rule_orphan@v2")["history"]
    assert len(history) == 2
    assert all(change["before"] is None and change["predecessor_missing"] and change["reason"] is None for change in history)
    assert {change["before_ref"] for change in history} == {"attr_orphan@v1", "rule_orphan@v1"}
'''

path = 'tests/test_read_model.py'
proposed[path] = (ROOT / path).read_text(encoding='utf-8') + test_case
manifest, diff = {}, []
for path, text in proposed.items():
    original = (ROOT / path).read_text(encoding='utf-8')
    target = OUT / 'proposed' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8', newline='\n')
    manifest[path] = {'before_sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                      'after_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    diff.extend(difflib.unified_diff(original.splitlines(keepends=True), text.splitlines(keepends=True),
                                   fromfile='a/' + path, tofile='b/' + path))
(OUT / 'registered_revision_history.patch').write_text(''.join(diff), encoding='utf-8', newline='\n')
(OUT / 'patch_manifest.json').write_text(json.dumps({'status': 'prepared_not_applied', 'files': manifest}, indent=2) + '\n', encoding='utf-8')
print(OUT / 'registered_revision_history.patch')
