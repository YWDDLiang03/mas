"""Fresh criterion generation from a pinned, previously admitted evidence collection.

Only evidence crosses the task boundary. Pool versions, rules, adjudications and
scores do not. This is distinct from reducing an inherited registry.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from . import criteria, derivation, derivation_run as runs, derivation_stages as stages, ledger, pool, task
from .canonical import sha256_hex
from .clock import utc_now
from .journal import actor
from .models import ModelError


def evaluation_fact_sources(core, source_task_id: str) -> dict[str, Any]:
    """Pin completed tool facts in the selected public task's evaluation ancestry.

    A terminal sweep may have useful completed requests even when no snapshot was
    published. Only that run's immutable successful/empty tool results cross this
    boundary; its rules, assessments, rankings and decisions do not. Existing
    completed-source ordering is retained, with interrupted sources appended.
    """
    ancestors, current = [], source_task_id
    while current and current not in ancestors:
        if not current.startswith('task_'):
            raise ValueError('Saved tool facts require a public task source.')
        ancestors.append(current)
        context = task.get(core, current)
        current = context.get('derived_from_task_id') or (context.get('inheritance') or {}).get('source_task_id')
    public = ('default', 'public')
    records = {}
    for (raw,) in core.store.db.execute(
            "SELECT body FROM events WHERE event_type='run.created' "
            "AND coalesce(json_extract(body,'$.payload.task_id'),json_extract(body,'$.ids.task_id')) "
            "IN (SELECT value FROM json_each(?)) "
            "ORDER BY recorded_at,stream_id", (json.dumps(ancestors),)):
        event = json.loads(raw)
        if event.get('visibility', 'default') not in public or event.get('ids', {}).get('case_id'):
            continue
        run_id = event['stream_id']
        if not run_id.startswith('run_'):
            continue
        row = core.store.db.execute(
            "SELECT body FROM events WHERE stream_id=? AND event_type IN "
            "('run.created','run.started','run.resumed','run.paused','run.completed','run.cancelled','run.failed','run.unresolved') "
            "ORDER BY seq DESC LIMIT 1", (run_id,)).fetchone()
        last = json.loads(row[0]) if row else None
        if not last or last['event_type'] not in ('run.completed', 'run.cancelled', 'run.failed', 'run.unresolved'):
            continue
        if last.get('visibility', 'default') not in public:
            continue
        ref = event['payload'].get('binding_artifact_id')
        kind = core.store.db.execute('SELECT kind FROM artifacts WHERE artifact_id=?', (ref,)).fetchone() if ref else None
        if not kind or kind[0] != 'run_binding':
            continue
        envelope = core.artifacts.get(ref) if ref else None
        if (not envelope or envelope['kind'] != 'run_binding' or
                envelope.get('visibility', 'default') not in public):
            continue
        binding = envelope['payload']
        if (binding.get('case_id@v') or binding.get('case_id') or
                binding.get('run_purpose', 'sweep') != 'sweep' or
                binding.get('operation') == 'derive_existing_evidence'):
            continue
        if not core.store.db.execute(
                "SELECT 1 FROM events WHERE stream_id=? AND event_type='tool.returned' "
                "AND json_extract(body,'$.payload.outcome') IN ('ok','empty') "
                "AND coalesce(json_extract(body,'$.visibility'),'default') IN ('default','public') LIMIT 1",
                (run_id,)).fetchone():
            continue
        records[run_id] = {'run_id': run_id, 'task_id': event['payload'].get('task_id') or event['ids']['task_id'],
            'pinned_seq': core.journal.last_seq(run_id), 'execution_state': last.get('state_to'),
            'terminal_event_id': last['event_id'], 'terminal_seq': last['seq'],
            'binding_artifact_id': ref, 'binding_sha256': sha256_hex(binding),
            'reuse_from_run_id': binding.get('reuse_from_run_id'),
            'continues_run_id': binding.get('continues_run_id')}
    ordered = sorted(records.values(), key=lambda row: row['execution_state'] != 'completed')
    manifest = {'policy': 'public_terminal_completed_tool_facts_v1', 'source_task_id': source_task_id,
        'source_task_seq': core.journal.last_seq(source_task_id),
        'task_ancestry': ancestors, 'source_runs': ordered,
        'selection': 'completed_sources_then_interrupted_sources; first_source_then_first_event',
        'accepted_tool_outcomes': ['ok', 'empty'], 'reuses_decisions': False,
        'reads_new_evidence': False}
    manifest['sha256'] = sha256_hex(manifest)
    return manifest


def source_runs(core, source_task_id: str) -> list[str]:
    """Resolve the public research-evidence ancestry, without opening case artifacts."""
    try:
        found = runs.registered_reduction_sources(core, source_task_id)
    except runs.DerivationError:
        found = []
    if found:
        return list(dict.fromkeys(found))
    result = []
    for (body,) in core.store.db.execute(
        "SELECT body FROM events WHERE event_type='run.created' "
        "AND json_extract(body,'$.payload.task_id')=? ORDER BY recorded_at", (source_task_id,)
    ):
        event = json.loads(body)
        binding = core.artifacts.payload(event['payload']['binding_artifact_id'])
        if binding.get('operation') == 'derive_existing_evidence' and binding.get('evidence_manifest_ref'):
            manifest = core.artifacts.payload(binding['evidence_manifest_ref'])
            result.extend(source['run_id'] for source in manifest['source_runs'])
            continue
        if binding.get('run_purpose') == 'criteria_derivation':
            result.append(event['stream_id'])
    return list(dict.fromkeys(result))


def pin_evidence(core, source_task_id: str, reference_labels=()) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    streams = source_runs(core, source_task_id)
    if not streams:
        raise ValueError('The selected evidence collection contains no recorded research evidence.')
    rows = []
    for stream in streams:
        pin = core.journal.last_seq(stream)
        rows.append({'run_id': stream, 'pinned_seq': pin})
    admitted, artifacts = {}, {}
    for row in rows:
        for (body,) in core.store.db.execute(
            "SELECT body FROM events WHERE stream_id=? AND seq<=? AND event_type='evidence.admitted' ORDER BY seq",
            (row['run_id'], row['pinned_seq'])):
            event = json.loads(body)
            claim = core.artifacts.payload(event['payload']['artifact_id'])
            if claim.get('admission_state') == 'admitted' and event.get('visibility', 'default') == 'default':
                admitted[claim['claim_id']] = claim
                artifacts[claim['claim_id']] = event['payload']['artifact_id']
    if not admitted:
        raise ValueError('The selected collection contains no admitted claims.')
    selected, seen, omitted = {}, {}, []
    for key, claim in sorted(admitted.items()):
        text = ' '.join(str(claim.get(field) or '') for field in ('normalized_statement', 'claim_text', 'entities'))
        if any(re.search(r'(?<![\w-])' + re.escape(label) + r'(?![\w-])', text, re.I) for label in reference_labels if label):
            omitted.append({'claim_id': key, 'reason': 'reference_candidate_named_in_derivation_evidence'})
            continue
        meaning = sha256_hex({k: v for k, v in claim.items() if k in
            ('source_ref', 'location', 'claim_type', 'normalized_statement', 'scope', 'value', 'unit', 'entities', 'polarity')})
        if meaning in seen:
            omitted.append({'claim_id': key, 'reason': 'exact_duplicate_source_claim', 'retained_claim_id': seen[meaning]})
            continue
        selected[key] = claim
        seen[meaning] = key
    manifest = {'source_task_id': source_task_id, 'source_task_seq': core.journal.last_seq(source_task_id),
                'source_runs': rows, 'claims': [{'claim_id': key, 'sha256': sha256_hex(value), 'artifact_id': artifacts[key]}
                                             for key, value in sorted(selected.items())],
                'source_admitted_claim_count': len(admitted), 'omitted': omitted,
                'reads_new_literature': False, 'copies_existing_criteria': False,
                'created_at': utc_now(), 'author_exposure': 'exposed'}
    return manifest, list(selected.values())


class ControlledContext(stages.StageContext):
    observer: Callable | None = None
    checkpoint: Callable | None = None

    def call(self, role, system, content, schema, question, max_tokens=12000):
        if self.checkpoint and not isinstance(self.budget, runs._ActivityBudget):
            self.checkpoint(self.run_id, stage_boundary=False)
        if self.observer:
            self.observer('activity', {'run_id': self.run_id, 'role': role, 'message': question})
        response = super().call(role, system, content, schema, question, max(max_tokens, 24000))
        if self.observer:
            self.observer('usage', {'run_id': self.run_id, 'budget': self.budget.snapshot()})
        return response

    def base_prompt(self):
        return super().base_prompt() + (
            '\nResearch-workbench policy: first enumerate distinct decision-relevant properties, then '
            'consolidate them into a concise operational set, approximately 10 to 30 independent criteria '
            'when the evidence supports that. The number is a quality target, not a quota. Multiple '
            'citations for one property are evidence, not extra votes. Preserve distinct conditions and '
            'endpoints when merging would alter their meaning. Explain each retention and removal. '
            'A hard exclusion requires direct evidence supporting both its threshold and its necessity '
            'for the stated task. Predicted endpoints are auxiliary preferences or considerations, '
            'never hard exclusions. Descriptive ranges alone do not establish a required cutoff. '
            'A drug-specific or regimen-specific observation should not become a universal screening '
            'requirement: state its applicability explicitly. Prefer transferable decision-level '
            'properties over separate criteria for each individual citation or symptom description. '
            'Criterion content must not be selected to improve a named reference candidate.\n')


def _checkpoint_history(core, run_id, implementation, manifest_ref, grouped, batch_size):
    """Reuse persisted work, never just a successful but unapplied model response."""
    completed, stage_refs, slices, slice_refs = {}, [], {}, []
    for parent in runs._chain_runs(core, run_id):
        binding = runs._binding_of(core, parent)
        if (binding.get('evidence_manifest_ref') != manifest_ref
                or binding.get('proposal_claim_batch_size', 400) != batch_size):
            continue
        events = core.journal.replay(parent)
        same_code = binding.get('implementation') == implementation
        for event in events:
            p = event.payload
            if event.event_type == 'stage.closed':
                name = p.get('stage') or ''
                if same_code or name in ('evidence', 'mandated') or name.startswith('propose:'):
                    completed[(name, p.get('iteration'))] = p.get('result')
                    stage_refs.append({'run_id': parent, 'seq': event.seq, 'stage': name,
                                       'iteration': p.get('iteration'), 'result_artifact_id': p.get('result_artifact_id')})
            elif event.event_type == 'proposal.slice_completed':
                dimension, index = p.get('dimension'), p.get('slice')
                if dimension not in grouped or not isinstance(index, int) or index < 1:
                    continue
                expected = grouped[dimension][(index - 1) * batch_size:index * batch_size]
                if (p.get('claim_ids') != [c['claim_id'] for c in expected]
                        or p.get('claims_sha256') != sha256_hex(expected)
                        or p.get('ordered_claim_ids_sha256') != sha256_hex([c['claim_id'] for c in grouped[dimension]])):
                    raise ValueError('The proposal checkpoint has different evidence or batch ordering.')
                slices.setdefault(dimension, set()).add(index)
                slice_refs.append({'run_id': parent, 'seq': event.seq, 'dimension': dimension,
                                   'slice': index, 'basis': 'persisted_slice_completion'})
            elif event.event_type == 'agent.finished' and p.get('schema_ok') and p.get('trace_blob'):
                # Older code wrote no explicit slice event. A subsequent logical call or closed
                # stage proves propose() returned and applied this response before proceeding.
                applied = any(later.event_type in ('agent.started', 'stage.closed')
                              for later in events if later.seq > event.seq)
                if not applied:
                    continue
                trace = core.artifacts.payload(p['trace_blob'])
                question = (trace.get('request') or {}).get('metadata', {}).get('question', '')
                match = re.fullmatch(r'propose pool: ([\w-]+)(?: \(slice (\d+)/(\d+)\))?', question)
                if not match or match[1] not in grouped:
                    continue
                dimension, index = match[1], int(match[2] or 1)
                planned = max(1, (len(grouped[dimension]) + batch_size - 1) // batch_size)
                if int(match[3] or 1) != planned:
                    raise ValueError('The legacy proposal checkpoint has a different batch plan.')
                slices.setdefault(dimension, set()).add(index)
                slice_refs.append({'run_id': parent, 'seq': event.seq, 'dimension': dimension,
                                   'slice': index, 'trace_blob': p['trace_blob'],
                                   'basis': 'successful_response_followed_by_next_work_boundary'})
    return completed, stage_refs, slices, slice_refs


def _explicit_evidence(core, manifest_ref: str, supplied_claims=None, reference_labels=()):
    """Validate a fixed admitted collection, including uploads with no source runs."""
    manifest = core.artifacts.payload(manifest_ref)
    rows = manifest.get('claims')
    if not isinstance(rows, list) or not isinstance(manifest.get('source_runs'), list):
        raise ValueError('An explicit evidence manifest needs fixed claim rows and source_runs (possibly empty).')
    for row in manifest.get('sources') or []:
        envelope = core.artifacts.get(row['artifact_id'])
        source = envelope['payload']
        if (envelope['kind'] != 'source' or source.get('source_id') != row['source_ref']
                or sha256_hex(source) != row['sha256']):
            raise ValueError('The explicit evidence manifest has a changed source record.')
    claims, seen_ids = [], set()
    for row in rows:
        envelope = core.artifacts.get(row['artifact_id'])
        claim = envelope['payload']
        if (envelope['kind'] != 'claim' or claim.get('admission_state') != 'admitted'
                or claim.get('claim_id') != row['claim_id'] or sha256_hex(claim) != row['sha256']
                or row['claim_id'] in seen_ids):
            raise ValueError('The explicit evidence collection contains a changed, duplicate or non-admitted claim.')
        claims.append(claim)
        seen_ids.add(row['claim_id'])
    if supplied_claims is not None and supplied_claims != claims:
        raise ValueError('Supplied claims differ from the explicit evidence manifest or its fixed order.')
    retained, omitted = [], []
    for row, claim in zip(rows, claims):
        text = ' '.join(str(claim.get(field) or '') for field in ('normalized_statement', 'claim_text', 'entities'))
        if any(re.search(r'(?<![\w-])' + re.escape(label) + r'(?![\w-])', text, re.I)
               for label in reference_labels if label):
            omitted.append({'claim_id': row['claim_id'], 'reason': 'reference_candidate_named_in_derivation_evidence'})
        else:
            retained.append((row, claim))
    if omitted:
        manifest = dict(manifest, input_manifest_ref=manifest_ref, claims=[r for r, _ in retained],
                        omitted=[*(manifest.get('omitted') or []), *omitted], created_at=utc_now())
        manifest_ref = core.artifacts.put('existing_evidence_manifest', manifest)
    return manifest_ref, manifest, [c for _, c in retained]


def derive(core, roster, task_id: str, *, source_task_id: str | None = None, dimensions, catalog, templates,
           by, settings, implementation, budget, observer=None, checkpoint=None,
           resume_run_id: str | None = None, evidence_manifest_ref: str | None = None,
           claims: list[dict[str, Any]] | None = None):
    """Run genuine proposals and pruning over saved claims, with stage checkpoints."""
    context = task.get(core, task_id)
    if resume_run_id is None and (pool.fold(core, task_id) or criteria.registered_attributes(core, task_id)):
        raise ValueError('Fresh evidence-based generation requires an empty criterion registry and pool.')
    if resume_run_id:
        binding = runs._binding_of(core, resume_run_id)
        if binding.get('operation') != 'derive_existing_evidence' or binding['task_context_id@v'].split('@')[0] != task_id:
            raise ValueError('The checkpoint belongs to a different generation task.')
        manifest = core.artifacts.payload(binding['evidence_manifest_ref'])
        if evidence_manifest_ref and evidence_manifest_ref not in (
                binding['evidence_manifest_ref'], manifest.get('input_manifest_ref')):
            raise ValueError('The requested evidence manifest differs from the generation checkpoint.')
        supplied_claims = claims
        # Artifact order is part of the batch plan. Re-querying ledger stream order changes
        # which evidence belongs to a completed slice even when its membership is identical.
        claims = [core.artifacts.payload(row['artifact_id']) for row in manifest['claims']]
        if any(c['claim_id'] != row['claim_id'] or sha256_hex(c) != row['sha256']
               for c, row in zip(claims, manifest['claims'])):
            raise ValueError('The fixed evidence collection differs from its checkpoint.')
        if supplied_claims is not None:
            input_ref = evidence_manifest_ref or binding['evidence_manifest_ref']
            _explicit_evidence(core, input_ref, supplied_claims)
        source_task_id = binding.get('source_task_id', source_task_id)
        run_id = resume_run_id
        ids = {'task_id': task_id, 'run_id': run_id}
    else:
        reference_labels = [label for seed in context.get('seed_candidates', []) if seed.get('is_reference_outcome')
                            for label in [seed.get('candidate_ref'), *(seed.get('aliases') or [])] if label]
        if evidence_manifest_ref:
            manifest_ref, manifest, claims = _explicit_evidence(core, evidence_manifest_ref, claims, reference_labels)
            source_task_id = manifest.get('source_task_id')
        else:
            if claims is not None:
                raise ValueError('Explicit claims require an immutable evidence_manifest_ref.')
            if not source_task_id:
                raise ValueError('Choose a source task or an explicit evidence manifest.')
            manifest, claims = pin_evidence(core, source_task_id, reference_labels)
            manifest_ref = core.artifacts.put('existing_evidence_manifest', manifest)
        run_id, ids, binding = runs._open_run(
            core, task_id, by=by, roster=roster, parents=[], continues_run_id=None,
            purpose_note='Generate new criteria from an existing evidence collection', settings=settings,
            implementation=implementation, binding_extra={'operation': 'derive_existing_evidence',
                'reads_new_evidence': False, 'evidence_manifest_ref': manifest_ref,
                'source_task_id': source_task_id, 'initial_pool_count': 0, 'initial_registry_count': 0,
                'stages': list(runs.DEFAULT_STAGES), 'inner_iterations': settings['criteria.inner_iterations'],
                'evidence_mode': 'existing_only', 'copies_existing_criteria': False,
                'proposal_claim_batch_size': 100, 'model_output_token_floor': 24000})
    routing = []
    grouped = runs._route_claims(claims, dimensions, routing_log=routing)
    batch_size = binding.get('proposal_claim_batch_size', 400)
    completed, inherited_stages, completed_slices, inherited_slices = _checkpoint_history(
        core, run_id, implementation, binding['evidence_manifest_ref'], grouped, batch_size)
    if resume_run_id and binding.get('implementation') != implementation:
        parents = runs._chain_runs(core, resume_run_id)
        old_binding = binding
        terminal = {'run.completed', 'run.failed', 'run.cancelled', 'run.unresolved'}
        if not any(e.event_type in terminal for e in core.journal.replay(resume_run_id)):
            runs._emit(core, resume_run_id, 'run.cancelled', ids=ids, state_to='cancelled',
                       termination_reason='cancelled',
                       payload={'continuation_reason': 'continued_with_revised_implementation'},
                       summary='Preserved completed generation work for a versioned implementation correction')
        run_id, ids, binding = runs._open_run(
            core, task_id, by=by, roster=roster, parents=parents, continues_run_id=resume_run_id,
            purpose_note='Continue saved generation with corrected criterion validation', settings=settings,
            implementation=implementation, binding_extra={
                'operation': 'derive_existing_evidence', 'reads_new_evidence': False,
                'evidence_manifest_ref': old_binding['evidence_manifest_ref'], 'source_task_id': source_task_id,
                'initial_pool_count': len(pool.active(pool.fold(core, task_id))),
                'initial_registry_count': len(criteria.registered_rule_records(core, task_id)),
                'stages': list(runs.DEFAULT_STAGES), 'inner_iterations': settings['criteria.inner_iterations'],
                'evidence_mode': 'existing_only', 'copies_existing_criteria': False,
                'proposal_claim_batch_size': batch_size, 'model_output_token_floor': 24000,
                'inherited_stage_refs': inherited_stages, 'inherited_proposal_slice_refs': inherited_slices,
                'continuation_reason': 'implementation_correction_preserving_paid_generation'})
    elif resume_run_id:
        runs._emit(core, run_id, 'run.resumed', ids=ids, state_to='running',
                   summary='Continued from persisted generation checkpoints')
    if observer:
        observer('created', {'run_id': run_id, 'continues_run_id': binding.get('continues_run_id'),
            'claims': len(claims), 'evidence_manifest_ref': binding['evidence_manifest_ref']})

    def count():
        folded = pool.fold(core, task_id)
        return len(criteria.registered_rule_records(core, task_id)) + len(pool.active(folded))

    def stage(name, iteration, fn):
        if (name, iteration) in completed:
            return completed[(name, iteration)]
        if checkpoint:
            checkpoint(run_id)
        before = count()
        before_hash = pool.pool_hash(pool.fold(core, task_id))
        key = sha256_hex({'run_id': run_id, 'stage': name, 'iteration': iteration, 'input': before_hash})
        phase = 'evidence' if name == 'evidence' else 'propose' if name.startswith(('propose', 'mandated')) else 'refine'
        if observer:
            observer('stage', {'phase': phase, 'stage': name, 'iteration': iteration, 'run_id': run_id,
                               'before_count': before, 'message': f'{name} · iteration {iteration}'})
        runs._emit(core, run_id, 'stage.opened', ids=ids,
                   payload={'stage': name, 'iteration': iteration, 'stage_key': key, 'before_count': before,
                            'count_basis': 'active_registered_plus_unregistered_proposals'})
        result = fn()
        after = count()
        artifact = core.artifacts.put('derivation_stage', {'stage': name, 'iteration': iteration, 'result': result,
            'input_pool_hash': before_hash, 'output_pool_hash': pool.pool_hash(pool.fold(core, task_id)),
            'before_count': before, 'after_count': after})
        runs._emit(core, run_id, 'stage.closed', ids=ids, state_to='completed',
                   payload={'stage': name, 'iteration': iteration, 'stage_key': key, 'result_artifact_id': artifact,
                            'result': result, 'before_count': before, 'after_count': after,
                            'count_basis': 'active_registered_plus_unregistered_proposals',
                            'pool_changed': before_hash != pool.pool_hash(pool.fold(core, task_id))})
        if observer:
            observer('stage_finished', {'phase': phase, 'stage': name, 'iteration': iteration,
                                        'before_count': before, 'after_count': after, 'result': result})
        return result

    record = {'task_id': task_id, 'run_id': run_id, 'chain_id': binding['chain_id'],
              'round_index': binding['round_index'], 'continues_run_id': binding.get('continues_run_id'),
              'operation': 'derive_existing_evidence', 'evidence_manifest_ref': binding['evidence_manifest_ref'],
              'initial_pool_count': binding['initial_pool_count'], 'initial_registry_count': binding['initial_registry_count'],
              'inherited_stage_refs': inherited_stages, 'inherited_proposal_slice_refs': inherited_slices,
              'inherited_claim_routing_artifact_id': None}
    try:
        record['evidence'] = stage('evidence', 0, lambda: {'claims_reused': len(claims), 'documents_read': 0,
                                                        'new_searches': 0, 'criteria_copied': 0})
        record['mandated'] = stage('mandated', 0, lambda: derivation.objective_criteria(core, task_id, templates=templates, by=by))
        # Publish provenance-preserving claim references on the fresh task so validators and
        # adjudicators resolve citations without inheriting a criterion or its authority.
        existing_ids = {c['claim_id'] for c in ledger.claims(core, [task_id])}
        for claim in claims:
            if claim['claim_id'] not in existing_ids:
                pinned = next(c for c in manifest['claims'] if c['claim_id'] == claim['claim_id'])
                core.journal.append(task_id, 'evidence.admitted', actor=actor('tool', 'existing_evidence_collection'),
                    ids={'task_id': task_id, 'run_id': run_id},
                    payload={'claim_id': claim['claim_id'], 'artifact_id': pinned['artifact_id'],
                             'admission_state': 'admitted', 'reasons': claim.get('admission_reasons') or [],
                             'source_ref': claim.get('source_ref'), 'candidate_ref': claim.get('candidate_ref'),
                             'attribute_ref': claim.get('attribute_ref'), 'existing_evidence_reference': True,
                             'manifest_ref': binding['evidence_manifest_ref']},
                    artifact_links=[{'kind': 'claim', 'id': pinned['artifact_id']}],
                    summary='Reuse an admitted source claim with its original extraction identity')
        record['inherited_claim_routing_artifact_id'] = core.artifacts.put('inherited_claim_routing',
            {'policy': 'semantic_multilabel_v1', 'source_runs': manifest['source_runs'], 'routes': routing})
        base = runs._stage_context(core, roster, task_id, run_id, context=context, catalog=catalog,
                                  claims={c['claim_id']: c for c in claims}, budget=budget,
                                  max_refines=settings['criteria.max_refines'])
        ctx = ControlledContext(**base.__dict__)
        ctx.observer, ctx.checkpoint = observer, checkpoint
        ctx.proposal_claim_batch_size = binding.get('proposal_claim_batch_size', 400)
        ctx.completed_proposal_slices = completed_slices
        if checkpoint and budget is not None:
            ctx.budget = runs._ActivityBudget(budget, run_id, checkpoint)
        record['proposed'] = {}
        for dimension in dimensions:
            ctx.pool.at('propose', 0)
            record['proposed'][dimension['dimension']] = stage('propose:' + dimension['dimension'], 0,
                lambda d=dimension: stages.propose(ctx, d, grouped[d['dimension']]))
        record['iterations'] = []
        termination = runs._prune(ctx, stage, record['iterations'], stage_names=runs.DEFAULT_STAGES,
            inner_iterations=settings['criteria.inner_iterations'], stall_rounds=settings['criteria.stall_rounds'],
            merge_overlap=settings['criteria.merge_overlap'])
        record['promotion'] = stage('promote', 0, lambda: stages.promote(ctx, by_proposer=stages.proposer_actor(ctx)))
    except ModelError as error:
        if error.error_class != 'quota_exhausted':
            runs._fail(core, run_id, ids, error)
            raise
        termination = 'budget_exhausted'
    except InterruptedError as error:
        paused = getattr(error, 'paused', False)
        runs._emit(core, run_id, 'run.paused' if paused else 'run.cancelled', ids=ids, state_to='paused' if paused else 'cancelled',
                   termination_reason=None if paused else 'cancelled', summary='Paused at a checkpoint' if paused else 'Stopped at an investigation checkpoint')
        raise
    return runs._close_run(core, task_id, run_id, ids, record, roster=roster, budget=budget, termination=termination)
