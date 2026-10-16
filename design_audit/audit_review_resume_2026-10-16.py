"""Bounded read-only audit of one task's public review and logical agent records."""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from mas.core.adjudication import _dispute_view
from mas.core.canonical import sha256_hex

TASK = 'task_01M51AQ0JK0MYN47806ZD5XS1B'
PIN = 7968
OUTPUT = Path(__file__).with_name('review_resume_audit_7968_2026-10-16.json')
db = sqlite3.connect(Path('var/primary/store/store.db').resolve().as_uri() + '?mode=ro', uri=True, timeout=10)
db.execute('PRAGMA query_only=ON')
db.execute('BEGIN')
events = [json.loads(row[0]) for row in db.execute(
    "SELECT body FROM events WHERE stream_id=? AND seq<=? AND event_type IN "
    "('agent.started','agent.finished','decision.recorded','human.review_requested',"
    "'human.review_decided','human.review_withdrawn','criterion.version_proposed') ORDER BY seq", (TASK, PIN))]


def artifact(ref, kind):
    row = db.execute('SELECT body,kind FROM artifacts WHERE artifact_id=?', (ref,)).fetchone()
    assert row and row[1] == kind, (ref, kind)
    return json.loads(row[0])['payload']


records, items, decisions, starts = {}, {}, [], {}
for event in events:
    payload, kind = event['payload'], event['event_type']
    if kind == 'criterion.version_proposed':
        records[f"{payload['id']}@v{payload['version']}"] = artifact(payload['artifact_id'], payload['kind'])
    elif kind == 'human.review_requested':
        items[payload['item_id']] = dict(payload, stream_id=TASK)
    elif kind == 'human.review_decided' and payload.get('queue_item_ref') in items:
        items[payload['queue_item_ref']]['state'] = 'decided'
    elif kind == 'human.review_withdrawn' and payload.get('item_id') in items:
        items[payload['item_id']]['state'] = 'withdrawn'
    elif kind == 'decision.recorded' and payload.get('adjudication_id'):
        decisions.append(dict(payload, seq=event['seq']))
        if payload.get('queue_item_ref') in items:
            items[payload['queue_item_ref']]['state'] = 'machine_adjudicated'
    elif kind == 'agent.started' and payload.get('role') == 'adjudicator':
        starts[payload['request_id']] = event

by_view = defaultdict(list)
for item in items.values():
    if item['subject'].get('kind') != 'rule_version':
        continue
    rule = records.get(item['subject']['id'])
    if not rule or rule['attribute_ref'] not in records:
        continue
    attr = records[rule['attribute_ref']]
    by_view[sha256_hex(_dispute_view(attr, rule))].append(dict(item_id=item['item_id'],
        rule_ref=item['subject']['id'], attribute_ref=rule['attribute_ref'], name=attr['name'], state=item['state']))

finished, by_prompt = [], defaultdict(list)
for event in events:
    payload = event['payload']
    if event['event_type'] != 'agent.finished' or payload.get('role') != 'adjudicator':
        continue
    trace = artifact(payload['trace_blob'], 'trace')
    request = trace['request']
    content = request['messages'][0]['content']
    view = None
    for marker in ('Criterion under dispute:\n', 'Criterion:\n', 'Criterion: '):
        if marker in content:
            view = json.JSONDecoder().raw_decode(content.split(marker, 1)[1].lstrip())[0]
            break
    matches = by_view.get(sha256_hex(view), []) if view is not None else []
    try:
        answer = json.loads(trace['final_text'])
    except json.JSONDecodeError:
        answer = json.JSONDecoder().raw_decode(trace['final_text'][trace['final_text'].index('{'):])[0]
    prompt_hash = sha256_hex({key: request.get(key) for key in
                            ('role', 'system', 'messages', 'response_schema', 'max_tokens', 'temperature', 'metadata')})
    linked = [d for d in decisions if d.get('queue_item_ref') in {m['item_id'] for m in matches}
              and d['seq'] > event['seq']]
    row = dict(request_id=payload['request_id'], started_seq=starts[payload['request_id']]['seq'],
        finished_seq=event['seq'], finished_at=event['recorded_at'], trace_ref=payload['trace_blob'],
        schema_ok=payload['schema_ok'], outcome=payload.get('outcome'), cost_usd=payload.get('cost_usd'),
        cost_status=payload.get('cost_status'), prompt_sha256=prompt_hash, item_matches=matches,
        verdict=answer.get('verdict'), reasoning=answer.get('reasoning'),
        cited_claim_ids=answer.get('cited_claim_ids'), later_item_decision_refs=[d['artifact_id'] for d in linked])
    finished.append(row)
    by_prompt[prompt_hash].append(row)

duplicates = [dict(prompt_sha256=key, attempts=rows,
    unique_item_binding=len(rows[0]['item_matches']) == 1,
    later_duplicate_cost_usd=sum(row.get('cost_usd') or 0 for row in rows[1:]))
    for key, rows in by_prompt.items() if len(rows) > 1]
result = dict(task_id=TASK, task_pinned_seq=PIN, reads_case_or_rank=False, writes_primary=0,
    finished_adjudicator_count=len(finished), started_adjudicator_count=len(starts),
    unfinished_request_ids=sorted(set(starts) - {row['request_id'] for row in finished}),
    state_counts={state: sum(item['state'] == state for item in items.values())
                  for state in sorted({item['state'] for item in items.values()})},
    repeated_complete_prompt_groups=duplicates, finished=finished,
    note='A matching prompt with a unique item/version binding proves repeated logical adjudication; '
         'unfinished requests are not treated as completed attempts. Costs are recorded estimates.')
OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({key: value for key, value in result.items() if key not in ('finished', 'repeated_complete_prompt_groups')},
                 ensure_ascii=False))
print(json.dumps({'duplicate_groups': len(duplicates), 'unique_item_bindings': [d['unique_item_binding'] for d in duplicates],
    'repeated': [[(r['finished_seq'], r['request_id'], r['verdict'], [m['rule_ref'] for m in r['item_matches']])
                  for r in d['attempts']] for d in duplicates]}, ensure_ascii=False))
db.close()
