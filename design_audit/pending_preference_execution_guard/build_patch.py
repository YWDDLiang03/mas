"""Prepare a reviewable patch and isolated overlay. Never edit the active source tree."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OVERLAY = HERE / 'preview'
changes = {}


def replace(text, before, after):
    assert text.count(before) == 1, (before[:100], text.count(before))
    return text.replace(before, after)


helper = '''def preference_execution_problems(attribute: dict[str, Any], rule: dict[str, Any]) -> list[str]:
    """Mechanical scoring readiness, independent of scientific approval. Pure; hard rules unchanged."""
    if rule.get("rule_kind") != "preference":
        return []
    predicate = rule.get("predicate_form", "threshold")
    cutoff = rule.get("cutoff")
    if cutoff is None:
        if predicate != "ordering":
            return [f"preference has no executable predicate: {predicate!r} needs a declared comparison "
                    "cutoff; no cutoff or pass value is inferred"]
        if attribute.get("direction") not in ("higher_better", "lower_better"):
            return ["preference ordering requires higher_better or lower_better; "
                    f"{attribute.get('direction')!r} defines no executable order"]
        # Preserve the assessor's existing numeric categorical/ordinal encodings. Their type
        # label or lack of a physical unit alone does not make an explicit order unexecutable.
        return []
    if not isinstance(cutoff, dict) or not cutoff:
        return ["preference has no executable comparison: cutoff must be a non-empty comparison record"]
    try:
        check_rule(rule, attribute)
    except InvariantViolation as error:
        return [f"preference comparison is not executable: {error}"]
    return []


def preference_execution_findings(core: Core, task_id: str, *,
                                 rule_set: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Read-only findings for active proposals, or the exact entries of a selected frozen set."""
    entries = (rule_set["entries"] if rule_set is not None else
               [{"rule_ref": f"{rule['rule_id']}@v{rule['version']}", "attribute_ref": rule["attribute_ref"]}
                for rule in registered_rule_records(core, task_id)])
    findings = []
    for entry in entries:
        rule = load(core, entry["rule_ref"], task_id)
        attribute = load(core, entry["attribute_ref"], task_id)
        problems = preference_execution_problems(attribute, rule)
        if problems:
            findings.append({"rule_ref": entry["rule_ref"], "attribute_ref": entry["attribute_ref"],
                             "scope": "rule", "reason_kind": "non_executable_preference",
                             "reason": "; ".join(problems), "problems": problems})
    return findings


'''

path = 'src/mas/core/criteria.py'
original = (ROOT / path).read_text(encoding='utf-8')
updated = replace(original, 'def _versions(core: Core, task_id: str, kind: str, base_id: str) -> list[dict[str, Any]]:',
                  helper + 'def _versions(core: Core, task_id: str, kind: str, base_id: str) -> list[dict[str, Any]]:')
updated = replace(updated,
    'for capability in (row.get("capabilities") or [row["capability"]])}))',
    'for capability in (row.get("capabilities") or [row.get("capability")]) if capability}))')
updated = replace(updated,
    '    entries, deferred, machine_adjudicated, collapsed_away = [], [], [], []\n',
    '    entries, deferred, machine_adjudicated, collapsed_away = [], [], [], []\n'
    '    execution_findings = {row["rule_ref"]: row for row in preference_execution_findings(core, task_id)}\n')
updated = replace(updated,
    '        attr = load(core, rule["attribute_ref"], task_id)\n'
    '        # Which of this attribute\'s routes this run holds out,',
    '        attr = load(core, rule["attribute_ref"], task_id)\n'
    '        if rule_ref in execution_findings:\n'
    '            # Keep the proposal active and auditable, but never put a non-executable\n'
    '            # preference into scoring or its coverage denominator. Approval cannot invent\n'
    '            # an absent comparison. This is a rule deferral, not a capability deferral.\n'
    '            deferred.append(execution_findings[rule_ref])\n'
    '            continue\n'
    '        # Which of this attribute\'s routes this run holds out,')
updated = replace(updated,
    '                                 + (f"; {held} were held out over bound support" if held else ""))',
    '                                 + (f"; {held} were held out over bound support" if held else "")\n'
    '                                 + ("; non-executable preferences: " + "; ".join(\n'
    '                                     f"{row[\'rule_ref\']}: {row[\'reason\']}" for row in execution_findings.values())\n'
    '                                    if execution_findings else ""))')
changes[path] = (original, updated)

path = 'src/mas/core/measurement.py'
original = (ROOT / path).read_text(encoding='utf-8')
updated = replace(original,
    '    rule_set = criteria.rule_set(core, task_id, rule_set_ref)\n'
    '    required_binding_check = check_required_anchors(core, task_id, rule_set=rule_set)',
    '    rule_set = criteria.rule_set(core, task_id, rule_set_ref)\n'
    '    execution_findings = criteria.preference_execution_findings(core, task_id, rule_set=rule_set)\n'
    '    if execution_findings:\n'
    '        raise MeasurementError("selected scoring set contains non-executable preferences; confirm a new "\n'
    '                               "rule set to defer them before registering a new measurement: " + "; ".join(\n'
    '                                   f"{row[\'rule_ref\']}: {row[\'reason\']}" for row in execution_findings))\n'
    '    required_binding_check = check_required_anchors(core, task_id, rule_set=rule_set)')
changes[path] = (original, updated)

path = 'src/mas/core/criteria_export.py'
original = (ROOT / path).read_text(encoding='utf-8')
updated = replace(original,
    '        reason = f"{deferred[\'capability\']} was held out of this run: {deferred.get(\'reason\') or \'no reason recorded\'}"',
    '        reason = (deferred.get("reason") if deferred.get("reason_kind") == "non_executable_preference" else\n'
    '                  f"{deferred[\'capability\']} was held out of this run: {deferred.get(\'reason\') or \'no reason recorded\'}")')
changes[path] = (original, updated)

path = 'src/mas/cli/main.py'
original = (ROOT / path).read_text(encoding='utf-8')
updated = replace(original,
    '                print(f"  deferred {item[\'rule_ref\']} ({item[\'capability\']}): {item[\'reason\']}")',
    '                label = item.get("capability") or item.get("reason_kind") or "rule"\n'
    '                print(f"  deferred {item[\'rule_ref\']} ({label}): {item[\'reason\']}")')
changes[path] = (original, updated)

test = '''"""Prospective preference execution guard. Synthetic temporary stores; no model/network."""
import json
import pytest

from mas.adapters.drug.registration import EVIDENCE_CATALOG
from mas.adapters.drug.universe import UniverseRecordField
from mas.core import assessor, criteria, criteria_export, ledger, measurement, review, task
from mas.core.journal import actor

OPERATOR = actor("human", "synthetic-guard-operator", "operator", identity_basis="recorded_attestation")
SPEC = {"objective_text": "Synthetic preference execution check", "mode": "exploratory", "scope_entities": [],
        "candidate_universe": {"kind": "enumerated_set", "members": ["synthetic"]}, "constraints": [],
        "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True}}
CAT = {"name": "Synthetic engagement on record", "definition": "A curated statement of target engagement",
       "measurement_kind": "categorical", "unit": None, "direction": "non_directional",
       "acceptable_value_sources": ["database_entry"], "acceptable_determination_bases": ["curated"],
       "aggregation": "consensus", "evidence_request": {"capability": "interaction_evidence_lookup",
       "question_kind": "mechanism_records", "parameters": {"target_chembl_id": "SYNTH_TARGET"}}}
QUANT = {"name": "Synthetic molecular weight", "definition": "Molecular weight of the candidate",
         "measurement_kind": "quantitative", "unit": "g/mol", "direction": "lower_better",
         "acceptable_value_sources": ["database_entry"], "aggregation": "median",
         "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                              "parameters": {"property": "MolecularWeight"}}}
NONE = {"rule_kind": "preference", "cutoff": None, "cutoff_basis": "none_evidence_insufficient"}
ORDER = dict(NONE, predicate_form="ordering")


def test_non_executable_preferences_remain_active_and_deferred_without_changing_hard_pending(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    pairs = []
    for attribute, rule in ((CAT, NONE),
                            (dict(QUANT, name="Unordered numeric preference", direction="non_directional"), ORDER),
                            (dict(CAT, name="Categorical ordering without a direction"), ORDER),
                            (QUANT, ORDER),
                            (dict(QUANT, name="Unresolved hard condition"), {"rule_kind": "hard_exclusion",
                             "cutoff": {"comparator": "<=", "value": 500, "unit": "g/mol"}, "cutoff_basis": "expert_set"})):
        pairs.append(criteria.propose(core, task_id, attribute, rule, by=OPERATOR))
    before = {ref: criteria.load(core, ref, task_id) for pair in pairs for ref in pair}
    queue = review.items(core, [task_id])
    with pytest.raises(criteria.InvariantViolation, match="await an expert decision"):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    selected_ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR, allow_pending=True)
    selected = criteria.rule_set(core, task_id, selected_ref)
    assert {row["rule_ref"] for row in selected["entries"]} == {pairs[3][1]}
    assert {row["rule_ref"] for row in selected["deferred"]} == {pair[1] for pair in pairs[:3]}
    assert all(row["reason_kind"] == "non_executable_preference" and row["scope"] == "rule" and row["problems"]
               for row in selected["deferred"])
    assert pairs[-1][1] in selected["pending"] and review.items(core, [task_id]) == queue
    assert criteria.registry_inventory(core, task_id)["active_registered_count"] == 5
    assert criteria.registry_inventory(core, task_id)["scoring_in_latest_frozen_set_count"] == 1
    assert criteria.deferred_capabilities(selected) == ()
    assert criteria.preference_execution_findings(core, task_id, rule_set=selected) == []
    for pair in pairs:
        for ref in pair:
            assert criteria.load(core, ref, task_id) == before[ref]
    for attr_ref, rule_ref in pairs[:3]:
        exported = criteria_export._use(rule_ref, attr_ref, [selected], None)
        assert exported["status"] == "deferred" and exported["reason"]
    profile = measurement.register(core, task_id, by=OPERATOR, rule_set_ref=selected_ref,
        primary_board="Synthetic execution guard", rationale="Mechanical scoring readiness",
        expected_effect="Do not count non-executable preferences")
    assert measurement.load(core, task_id, profile)["policy"]["scoring_policy"]["scoring_rule_refs"] == sorted(
        [pairs[3][1]])
    # allow_pending did not remove the unresolved hard constraint from the record.
    with pytest.raises(criteria.InvariantViolation, match="await an expert decision"):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR)


def test_valid_numeric_ordering_and_declared_boolean_comparison_remain_executable():
    assert criteria.preference_execution_problems(QUANT, ORDER) == []
    boolean = dict(NONE, predicate_form="categorical_membership", cutoff_basis="task_constraint",
                   cutoff={"comparator": "==", "value": True})
    assert criteria.preference_execution_problems(CAT, boolean) == []
    assert criteria.preference_execution_problems(CAT, dict(NONE, rule_kind="hard_exclusion")) == []
    attribute = dict(QUANT, attribute_id="attr_synthetic", version=1)
    rule = dict(ORDER, rule_id="rule_synthetic", version=1)
    observed = {"claim_id": "claim_synthetic", "source_ref": "src_synthetic", "admission_state": "admitted",
                "evidence_kind": "database_entry", "determination_basis": "derived", "value": 300, "unit": "g/mol"}
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "synthetic"}, attribute=attribute, rule=rule,
        rule_set_ref="rules@v1", claims=[observed], resolved=True, qualification_policy="qualification_first_v1")
    assert cell["verdict"] == "available" and cell["value"] == 300


@pytest.mark.parametrize("kind,unit", [("categorical", "phase"), ("ordinal", None)])
def test_existing_numeric_phase_and_unitless_ordinal_ordering_are_preserved(core, tmp_path, kind, unit):
    entry = next(row for row in EVIDENCE_CATALOG if row["question_kind"] == "record_field")
    assert entry["units"]["max_phase"] == "phase"
    path = tmp_path / "synthetic_universe.json"
    path.write_text(json.dumps({"source": "synthetic phase fixture", "universe": [
        {"inchikey": "SYNTH_A", "chembl_id": "SYNTH_CHEMBL_A", "max_phase": 2},
        {"inchikey": "SYNTH_B", "chembl_id": "SYNTH_CHEMBL_B", "max_phase": 4}]}))
    provider = UniverseRecordField(path)
    attribute = dict(CAT, name=f"Synthetic phase encoded as {kind}", measurement_kind=kind,
        unit=unit, direction="higher_better", acceptable_determination_bases=["measured"],
        evidence_request={"capability": "record_field_lookup", "question_kind": "record_field",
                          "parameters": {"field": "max_phase"}})
    assert criteria.preference_execution_problems(attribute, ORDER) == []
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    attr_ref, rule_ref = criteria.propose(core, task_id, attribute, ORDER, by=OPERATOR)
    selected_ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    selected = criteria.rule_set(core, task_id, selected_ref)
    assert [row["rule_ref"] for row in selected["entries"]] == [rule_ref] and selected["deferred"] == []
    cells = {}
    for key in ("SYNTH_A", "SYNTH_B"):
        response = provider.invoke("record_field", {"identifier": key, "field": "max_phase"})
        observed = response.values[0]
        claim = dict(claim_id=f"claim_{key}", source_ref="src_synthetic_phase", candidate_ref=key,
                     evidence_kind="database_entry", determination_basis="measured", value=observed["value"],
                     unit=observed["unit"], reading_depth="not_read",
                     location={"location_kind": "database_record", "locator_value": f"{key}:max_phase"})
        ledger.record_claim(core, task_id, claim, by=OPERATOR, admission_state="admitted",
                            admission_reasons=["synthetic local fixture"])
        cell, _ = assessor.assess_cell(candidate={"candidate_id": key},
            attribute=criteria.load(core, attr_ref, task_id), rule=criteria.load(core, rule_ref, task_id),
            rule_set_ref=selected_ref, claims=[dict(claim, admission_state="admitted")], resolved=True,
            qualification_policy="qualification_first_v1")
        assert cell["verdict"] == "available" and cell["value"] == observed["value"]
        cells[key] = [cell]
    scores = assessor.preference_scores(cells, {rule_ref: {"rule_kind": "preference", "predicate_form": "ordering",
        "direction": "higher_better"}}, {}, qualified_candidates=set(cells), qualification_policy="qualification_first_v1")
    assert scores == {"SYNTH_A": (0.0, 1.0), "SYNTH_B": (1.0, 1.0)}
'''
changes['tests/test_preference_execution_guard.py'] = ('', test)

patch, manifest = [], []
for path, (before, after) in changes.items():
    patch.extend(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                 fromfile='a/' + path if before else '/dev/null', tofile='b/' + path))
    destination = OVERLAY / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(after, encoding='utf-8', newline='\n')
    manifest.append({'path': path, 'base_sha256': hashlib.sha256(before.encode()).hexdigest() if before else None,
                     'patched_sha256': hashlib.sha256(after.encode()).hexdigest()})
(HERE / 'preference_execution_guard.patch').write_text(''.join(patch), encoding='utf-8', newline='\n')
(HERE / 'patch_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps({'patch': str(HERE / 'preference_execution_guard.patch'), 'files': len(changes)}))
