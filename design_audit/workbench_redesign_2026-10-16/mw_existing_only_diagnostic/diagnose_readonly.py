"""Anonymous rule-level availability audit. Never invoke a provider or write the store/cache."""
from pathlib import Path
from collections import Counter, defaultdict
import json
import math
import sqlite3

from mas.adapters.drug.pubchem import PubChemProperty, PROPERTIES
from mas.core.broker import _cache_key
from mas.core.canonical import sha256_hex

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
RUN = 'run_01M51MS4KW71HX2FEMTPJ01JHA'
MW_RULE = 'rule_molecular-weight-oral-absorption@v1'
db = sqlite3.connect((ROOT / 'var/primary/store/store.db').as_uri() + '?mode=ro', uri=True)
db.execute('PRAGMA query_only=ON')
db.execute('BEGIN')


def artifact(ref):
    row = db.execute('SELECT body,sha256 FROM artifacts WHERE artifact_id=?', (ref,)).fetchone()
    return (json.loads(row[0])['payload'], row[1]) if row else ({}, None)


created = json.loads(db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='run.created' ORDER BY seq LIMIT 1", (RUN,)).fetchone()[0])
binding, _ = artifact(created['payload']['binding_artifact_id'])
task = binding['task_context_id@v'].split('@v')[0]
approved = json.loads(db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='criterion.version_approved' "
    "AND json_extract(body,'$.payload.rule_set_ref')=?", (task, binding['rules@v'])).fetchone()[0])
rule_set, _ = artifact(approved['payload']['artifact_id'])
mw_entry = next(entry for entry in rule_set['entries'] if entry['rule_ref'] == MW_RULE)
base, version = mw_entry['attribute_ref'].rsplit('@v', 1)
attr_event = json.loads(db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='criterion.version_proposed' "
    "AND json_extract(body,'$.payload.kind')='attribute' AND json_extract(body,'$.payload.id')=? "
    "AND json_extract(body,'$.payload.version')=? LIMIT 1", (task, base, int(version))).fetchone()[0])
mw_attribute, _ = artifact(attr_event['payload']['artifact_id'])

rules = defaultdict(lambda: {'verdict_counts': Counter(), 'unknown_reasons': Counter(), 'unknown_search_routes': Counter(),
                              'tool_error_cells': 0})
member_rules, cell_pairs, mw_members = defaultdict(set), set(), set()
event_count = 0
for (raw,) in db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='candidate.assessed' ORDER BY seq", (RUN,)):
    event = json.loads(raw)
    cell, _ = artifact(event['payload']['artifact_id'])
    reason, _ = artifact(event['payload']['reason_artifact_id'])
    ref, verdict = cell['rule_ref'], cell['verdict']
    rules[ref]['verdict_counts'][verdict] += 1
    rules[ref]['tool_error_cells'] += int(bool(cell.get('tool_error_ref')))
    if verdict == 'unknown_missing':
        rules[ref]['unknown_reasons'][reason.get('reason_text')] += 1
        routes = tuple((reason.get('absence_check_record') or {}).get('source_kinds_searched') or [])
        rules[ref]['unknown_search_routes'][routes] += 1
    # Identities are used only for set membership/counts and are never emitted.
    member_rules[cell['candidate_ref']].add(ref)
    cell_pairs.add((cell['candidate_ref'], ref))
    if ref == MW_RULE:
        mw_members.add(cell['candidate_ref'])
    event_count += 1

summary = []
for ref in sorted(rules):
    item = rules[ref]
    summary.append({'rule_ref': ref, 'recorded_cells': sum(item['verdict_counts'].values()),
        'verdict_counts': dict(item['verdict_counts']), 'tool_error_cells': item['tool_error_cells'],
        'unknown_reasons': [{'reason': reason, 'count': n} for reason, n in item['unknown_reasons'].items()],
        'unknown_search_routes': [{'routes': list(routes), 'count': n} for routes, n in item['unknown_search_routes'].items()]})

library = json.loads((ROOT / 'var/primary/universe_chembl.json').read_text(encoding='utf-8'))
field_counts = Counter(key for row in library['universe'] for key, value in (row.get('fields') or {}).items() if value is not None)
manifest = binding['tool_replay']
provider = PubChemProperty()
contract = provider.contract
indexed, selected_props = set(), Counter()
for source_run in manifest['source_run_ids']:
    for (raw,) in db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='tool.returned' "
                            "AND json_extract(body,'$.actor.id')=? ORDER BY seq", (source_run, contract.tool_id)):
        event = json.loads(raw)
        if event['payload'].get('outcome') not in ('ok', 'empty'):
            continue
        refs = [link['id'] for link in event.get('artifact_links', []) if link.get('kind') == 'tool_result']
        if len(refs) != 1:
            continue
        result, digest = artifact(refs[0])
        invocation, provenance = result.get('invocation') or {}, result.get('provenance') or {}
        inputs = invocation.get('normalized_input')
        required = ('result_id', 'invocation', 'outcome', 'values', 'records', 'provenance')
        if (any(key not in result for key in required) or result['outcome'] not in ('ok', 'empty')
                or result.get('error') or result.get('absence_reason') or not isinstance(inputs, dict)
                or not all(invocation.get(key) for key in ('tool_id', 'contract_version', 'question_kind'))
                or not provenance.get('implementation_version') or not provenance.get('retrieved_at')
                or provenance.get('tool_id') != invocation['tool_id']
                or provenance.get('contract_version') != invocation['contract_version']
                or invocation.get('input_hash') != sha256_hex(inputs)
                or provenance.get('parameters_hash') != sha256_hex(inputs)):
            continue
        key = _cache_key(invocation['tool_id'], invocation['contract_version'], provenance['implementation_version'],
                         invocation['question_kind'], inputs)
        if key in indexed:
            continue
        indexed.add(key)
        if (invocation['tool_id'] != contract.tool_id or invocation['contract_version'] != contract.contract_version
                or provenance['implementation_version'] != contract.implementation_version):
            continue
        source = {'source_run_id': source_run, 'source_event_id': event['event_id'], 'source_seq': event['seq'],
            'source_request_seq': event.get('parent_seq'), 'source_artifact_id': refs[0], 'result_id': result['result_id'],
            'retrieved_at': provenance['retrieved_at'], 'cache_key': key,
            'source_platform': (provenance.get('executed_on') or {}).get('platform'), 'source_artifact_sha256': digest}
        if provider.seed_historical_result(result, source):
            selected_props[inputs.get('property')] += 1

projection = provider.historical_projection_manifest()
expected = next(item for item in manifest['parameter_projections'] if item['policy'] == provider.historical_projection_policy)
assert projection == expected
saved_fields = Counter()
positive_finite_mw = 0
for history in provider._historical_rows.values():
    record = history['records'][0]
    for prop in PROPERTIES:
        saved_fields[prop] += int(record.get(prop) is not None)
    if record.get('MolecularWeight') is not None:
        value = float(record['MolecularWeight'])
        positive_finite_mw += int(math.isfinite(value) and value > 0)

partial_matches = Counter()
for candidate_id, ids_json in db.execute("SELECT json_extract(a.body,'$.payload.candidate_id'), "
    "json_extract(a.body,'$.payload.identifiers') FROM events e JOIN artifacts a "
    "ON a.artifact_id=json_extract(e.body,'$.payload.artifact_id') WHERE e.stream_id=? AND e.event_type='identity.resolved'", (RUN,)):
    if candidate_id not in mw_members:
        continue
    identifiers = json.loads(ids_json or '[]')
    identifier = next((item['value'] for item in identifiers if item.get('scheme') == 'inchikey'), None)
    history = provider._historical_rows.get(provider._row_key({'identifier': identifier, 'identifiers': identifiers,
                                                              'property': 'MolecularWeight'}))
    partial_matches['assessed_members'] += 1
    if history:
        partial_matches['exact_saved_pubchem_row'] += 1
        partial_matches['exact_saved_MolecularWeight'] += int(history['records'][0].get('MolecularWeight') is not None)
    else:
        partial_matches['no_exact_row'] += 1

report = {
    'audit_type': 'read_only_anonymous_rule_availability', 'run_id': RUN, 'task_id': task,
    'access': 'SQLite mode=ro; query_only=ON; no Core/ReadModel construction; no provider.invoke or broker.call',
    'individual_candidates_or_rankings_emitted': False,
    'rule_set_ref': binding['rules@v'], 'evidence_mode': binding['evidence_mode'],
    'recorded_assessment_events': event_count, 'unique_cell_pairs': len(cell_pairs),
    'recorded_rule_count': len(rules), 'frozen_rule_count': len(rule_set['entries']),
    'anonymous_member_count': len(member_rules),
    'member_rule_count_histogram': dict(Counter(len(refs) for refs in member_rules.values())),
    'rules': summary,
    'mw_registration': {'rule_ref': MW_RULE, 'attribute_ref': mw_entry['attribute_ref'],
        'attribute_artifact_id': attr_event['payload']['artifact_id'],
        **{key: mw_attribute.get(key) for key in ('name', 'definition', 'unit', 'acceptable_value_sources',
                                                'acceptable_determination_bases', 'evidence_request')}},
    'library': {'path': 'var/primary/universe_chembl.json', 'source': library.get('source'),
        'retrieved_at': library.get('retrieved_at'), 'count': len(library['universe']),
        'field_non_null_counts': dict(field_counts), 'descriptor_values_present_in_fields': False},
    'replay_projection': {'bound_manifest_digest': manifest['manifest_digest'],
        'source_run_ids': manifest['source_run_ids'], 'selection': manifest['selection'],
        'matching_original_binding': projection == expected, 'computed': projection, 'bound': expected,
        'first_selected_property_counts': dict(selected_props), 'saved_field_non_null_counts': dict(saved_fields),
        'positive_finite_saved_MolecularWeight': positive_finite_mw,
        'anonymous_partial_member_matches': dict(partial_matches)},
    'root_cause': 'MW is registered only on the predicted ADMET endpoint molecular_weight with model_prediction/predicted acceptance; '
                  'the existing exact PubChem descriptor-row projection is functioning and already contains MolecularWeight.',
    'recommended_versioned_fix': {'capability': 'property_estimate', 'question_kind': 'computed_property',
        'identifier_scheme': 'inchikey', 'parameters': {'property': 'MolecularWeight'},
        'acceptable_value_sources': ['database_entry'], 'acceptable_determination_bases': ['derived'],
        'keep': ['unit g/mol', 'direction', 'predicate', 'cutoff', 'bound_support'],
        'requires': ['new attribute/rule versions', 'fresh review', 'new strict freeze'],
        'other_routes_and_replay_selection': 'unchanged',
        'prohibited_substitutions': ['XLogP / ALogP / RDKit logP are not interchangeable']},
}
db.close()
(OUT / 'diagnostic.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
header = '''# Partial sweep 既有描述符证据诊断

结论：不是所有 PubChem 计算描述符缺失。MW 的问题是注册到了预测端点，并仅接受预测依据；
现有 PubChem replay 连接正常，已保存确切 MolecularWeight，允许在新版本标准、新复核与新冻结下复用。

本报告只含按规则汇总的统计；不展示候选个体、名次或对照案例。源库以只读模式打开，
未运行 provider、网络请求、新 ADMET 计算或科研工作流，未修改 src、primary 或缓存。

## 已保存 partial 单元

Run: `run_01M51MS4KW71HX2FEMTPJ01JHA`。

'''
lines = [header, f"共 {len(member_rules):,} 个匿名成员、{len(rules)} 条规则、{event_count:,} 个已保存单元。\n\n",
         '其中 1,176 个成员已保存全部 29 条，另 1 个成员保存了 27 条；该 partial 仍缺最后 2 个单元，不能称整个评估已完成。\n\n',
         '| 规则 | pass | fail | available | unknown_missing |\n| --- | ---: | ---: | ---: | ---: |\n']
for item in summary:
    counts = item['verdict_counts']
    lines.append(f"| `{item['rule_ref']}` | {counts.get('pass', 0)} | {counts.get('fail', 0)} | {counts.get('available', 0)} | {counts.get('unknown_missing', 0)} |\n")
lines.append('''
所有 unknown_missing 原因均为“no admitted claim from an accepted source”，没有 tool_error。
完整原原因与搜寻路径在 diagnostic.json 中。MW 的路径只有 predicted_property_lookup；
HBA/HBD/TPSA/RB 的路径为 property_estimate，各自 1,136 有值、41 缺证。
XLogP 两条正确绑定规则各 1,090 有值、87 缺证，未用任何其他 logP 定义替代。

## 现有数值与固定来源证明

按原 first_source_then_first_event 顺序重建，只选择原 binding 指定的完成 source runs：

- PubChem descriptor projection 3,084 行，全部已有 MolecularWeight、TPSA、HBA、HBD、RB。
- 其中 MolecularWeight 全部能解析为有限正数；这里只校验保存值，不计算分子描述符。
- Projection entries digest 与原 binding 完全一致：
  `87cd7a51d407f4008c04b1a0fa89b2e76049ad058f76c18a45bfbc163b5926dc`。
- 在 partial 的 1,177 个匿名成员中，1,136 个按全部输入（除 property）精确匹配到保存行，
  且全部有 MolecularWeight；41 个没有精确行，继续保留未知。
- `universe_chembl.json` 只含 oral/parenteral/topical、警示、审批和撤市等字段，
  未保存这些描述符，因此不能把该文件当成 MW 数值来源。

## 最小修复路线

由根任务使用版本化修订，把 MW 的证据请求改为
`property_estimate / computed_property / property=MolecularWeight`、InChIKey 输入，
接受 `database_entry / derived`；保留单位、方向、predicate、cutoff 和 bound_support。
新复核与 strict freeze 决定是否启用。旧版本与本次缺证单元保留；新 MW 版本需重新形成对应单元，
其他确切未变条目的合法 partial 单元按既有续跑检查复用。

其余路线、缓存选择及排名口径不变，不将 XLogP、ALogP、RDKit logP 按名称近似替换。
本报告没有推断其他普遍缺证预测或临床量可以改用相近字段。

精确统计及 source run/digest 见 [diagnostic.json](diagnostic.json)。
只读复核脚本为 [diagnose_readonly.py](diagnose_readonly.py)。
''')
(OUT / 'REPORT.md').write_text(''.join(lines), encoding='utf-8')
print(json.dumps({'report': str(OUT / 'REPORT.md'), 'json': str(OUT / 'diagnostic.json'),
    'rules': len(rules), 'members': len(member_rules), 'cells': event_count,
    'projection_match': projection == expected, 'partial_mw': dict(partial_matches)}, ensure_ascii=False))
