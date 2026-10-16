"""Versioned continuation preserves durable proposal slices; no provider or real store."""
import pytest

from mas.core import config, derivation_run, derivation_stages, existing_research, pool, task
from mas.core.canonical import sha256_hex
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core


def test_revised_implementation_forks_binding_and_skips_persisted_proposal_slices(tmp_path):
    root = tmp_path / 'store'
    by = actor('agent', 'continuation-test', 'operator')
    dimension = {'dimension': 'test_dimension', 'focus': 'Continuation checkpoint fixture'}
    claims = [{'claim_id': f'claim_fixture_{index}', 'normalized_statement': f'Test evidence {index}',
               'location': {'quoted_span': f'Test evidence {index}'},
               'source_ref': 'fixture-source', 'determination_basis': 'measured'}
              for index in (1, 2)]
    old_implementation, new_implementation = {'source_sha256': 'old'}, {'source_sha256': 'new'}
    adapter = ScriptedAdapter('local-script', lambda request: {'proposals': [], 'considered_and_rejected': []})
    roster = ModelRoster({'local-script': adapter}, {'proposer': 'local-script'})
    settings = config.resolve(project_file=None, environ={})
    with Core.open(root) as core:
        task_id, _ = task.record_version(core, {
            'objective_text': 'Persist and resume proposal work', 'mode': 'exploratory',
            'evaluation_scope': 'fixture only', 'candidate_universe': {'members': ['fixture']}}, by=by)
        manifest = {'claims': [{'claim_id': claim['claim_id'], 'sha256': sha256_hex(claim),
                                'artifact_id': core.artifacts.put('claim', claim)} for claim in claims],
                    'source_runs': []}
        manifest_ref = core.artifacts.put('existing_evidence_manifest', manifest)
        old_run, ids, old_binding = derivation_run._open_run(
            core, task_id, by=by, roster=roster, parents=[], continues_run_id=None,
            purpose_note='Checkpoint fixture', settings=settings, implementation=old_implementation,
            binding_extra={'operation': 'derive_existing_evidence', 'evidence_manifest_ref': manifest_ref,
                           'proposal_claim_batch_size': 1, 'initial_pool_count': 0, 'initial_registry_count': 0})
        for name in ('evidence', 'mandated'):
            derivation_run._emit(core, old_run, 'stage.closed', ids=ids,
                                 payload={'stage': name, 'iteration': 0, 'result': []})
        writer = pool.Pool(core, task_id, by=by, run_id=old_run).at('propose', 0)
        criterion_id = writer.add({'attribute': {'name': 'Durably added criterion'},
                                  'rule': {'rule_kind': 'preference'},
                                  'supporting_claim_ids': [claims[0]['claim_id']]},
                                 reason_text='Applied the first proposal slice')
        core.journal.append(old_run, 'proposal.slice_completed', actor=by, ids=ids, payload={
            'dimension': dimension['dimension'], 'slice': 1, 'slices': 2, 'batch_size': 1,
            'claim_ids': [claims[0]['claim_id']], 'claims_sha256': sha256_hex(claims[:1]),
            'ordered_claim_ids_sha256': sha256_hex([claim['claim_id'] for claim in claims]),
            'added_criterion_refs': [f'{criterion_id}@v1']})
        derivation_run._emit(core, old_run, 'run.paused', ids=ids, state_to='paused')

    class CapturedFork(Exception):
        pass

    captured = {}

    def observe(kind, detail):
        if kind == 'created':
            captured.update(detail)
            raise CapturedFork()  # Inspect the actual fork before generation can call a model.

    with Core.open(root) as core:
        with pytest.raises(CapturedFork):
            existing_research.derive(core, roster, task_id, source_task_id=task_id,
                dimensions=[dimension], catalog=[], templates=None, by=by, settings=settings,
                implementation=new_implementation, budget=None, observer=observe, resume_run_id=old_run)
        new_run = captured['run_id']
        assert new_run != old_run
        assert derivation_run._binding_of(core, old_run) == old_binding
        new_binding = derivation_run._binding_of(core, new_run)
        assert new_binding['continues_run_id'] == old_run
        assert new_binding['implementation'] == new_implementation
        assert new_binding['evidence_manifest_ref'] == manifest_ref
        assert new_binding['inherited_proposal_slice_refs'][0]['slice'] == 1
        terminal = core.journal.replay(old_run)[-1]
        assert terminal.event_type == 'run.cancelled'
        assert terminal.termination_reason == 'cancelled'
        assert terminal.payload['continuation_reason'] == 'continued_with_revised_implementation'
        _, _, completed, _ = existing_research._checkpoint_history(
            core, new_run, new_implementation, manifest_ref, {dimension['dimension']: claims}, 1)
        ctx = derivation_stages.StageContext(core, roster, task_id, new_run, task.get(core, task_id),
            [], {claim['claim_id']: claim for claim in claims}, [],
            pool.Pool(core, task_id, by=by, run_id=new_run).at('propose', 0),
            completed_proposal_slices=completed)
        ctx.proposal_claim_batch_size = 1
        result = derivation_stages.propose(ctx, dimension, claims)
        assert result['reused_slices'] == [1]
        assert [request.metadata['question'] for request in adapter.requests] == [
            'propose pool: test_dimension (slice 2/2)']
        assert len(pool.fold(core, task_id)) == 1

    with Core.open(root) as core:
        _, _, completed, _ = existing_research._checkpoint_history(
            core, new_run, new_implementation, manifest_ref, {dimension['dimension']: claims}, 1)
        assert completed == {dimension['dimension']: {1, 2}}
