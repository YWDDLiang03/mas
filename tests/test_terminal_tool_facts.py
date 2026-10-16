"""Interrupted sweeps preserve facts without inheriting their decisions."""
import pytest

from mas.core import existing_research, task
from mas.core.broker import Broker, ProviderResponse, ToolContract
from mas.core.budget import Budget
from mas.core.canonical import sha256_hex
from mas.core.controller import _ExistingFactsBroker
from mas.core.journal import actor
from tests.fakes import FakeProperty

WHO = actor('agent', 'terminal-facts-test', 'retriever')
INPUT = {'identifier': 'K1', 'property': 'MW'}


def source(core, task_id, name, state, *, value=300, case_id=None):
    binding = {'task_context_id@v': f'{task_id}@v1', 'run_purpose': 'sweep', 'case_id@v': case_id}
    artifact = core.artifacts.put('run_binding', binding)
    core.journal.append(name, 'run.created', actor=WHO, payload={'task_id': task_id, 'binding_artifact_id': artifact},
                        state_to='queued')
    broker = Broker(core)
    broker.register(FakeProperty({('K1', 'MW'): value}))
    result = broker.call(name, 'property_estimate', 'computed_property', INPUT, requesting_actor=WHO)
    core.journal.append(name, f'run.{state}', actor=WHO, state_to=state)
    return result


@pytest.mark.parametrize('state', ['cancelled', 'failed', 'unresolved'])
def test_terminal_sources_replay_only_finished_tool_facts_when_explicitly_enabled(core, state):
    result = source(core, 'task_source', 'run_partial', state)
    provider = FakeProperty({('K1', 'MW'): 999})
    broker = Broker(core)
    broker.register(provider)
    with pytest.raises(ValueError, match='not a completed run'):
        broker.seed_cache_from_runs(['run_partial'])
    pin = core.journal.last_seq('run_partial')
    manifest = broker.seed_cache_from_runs(['run_partial'], allow_terminal_sources=True,
                                          source_pins={'run_partial': pin})
    replay = _ExistingFactsBroker(broker).call('run_new', 'property_estimate', 'computed_property', INPUT,
                                              requesting_actor=WHO)
    assert replay == result and provider.calls == 0
    assert manifest['reuses_decisions'] is False
    assert manifest['sources'][0]['execution_state'] == state
    assert 'completed_event_id' not in manifest['sources'][0]
    assert len(next(iter(broker._replay_cache.values()))['source_artifact_sha256']) == 64
    assert [event.event_type for event in core.journal.replay('run_new')] == ['tool.returned']


@pytest.mark.parametrize('state', ['started', 'paused'])
def test_active_or_paused_sources_remain_forbidden(core, state):
    core.journal.append('run_active', 'run.created', actor=WHO, state_to='queued')
    core.journal.append('run_active', 'run.' + state, actor=WHO, state_to='running' if state == 'started' else state)
    with pytest.raises(ValueError, match='not a terminated public run'):
        Broker(core).seed_cache_from_runs(['run_active'], allow_terminal_sources=True)


def test_source_manifest_pins_related_terminal_facts_and_preserves_completed_precedence(core):
    tid, _ = task.record_version(core, {'objective_text': 'Saved fact fixture', 'mode': 'exploratory',
        'evaluation_scope': 'fixture', 'candidate_universe': {'members': ['K1']}}, by=WHO)
    source(core, tid, 'run_interrupted', 'cancelled', value=400)
    source(core, tid, 'run_completed', 'completed', value=300)
    source(core, tid, 'run_case_bound', 'completed', case_id='case_do_not_read@v1')
    source(core, 'task_unrelated', 'run_unrelated', 'completed')
    manifest = existing_research.evaluation_fact_sources(core, tid)
    assert [row['run_id'] for row in manifest['source_runs']] == ['run_completed', 'run_interrupted']
    proof = dict(manifest)
    assert proof.pop('sha256') == sha256_hex(proof)
    assert manifest['reuses_decisions'] is False
    broker = Broker(core)
    broker.register(FakeProperty({}))
    broker.seed_cache_from_runs([row['run_id'] for row in manifest['source_runs']], allow_terminal_sources=True,
                                source_pins={row['run_id']: row['pinned_seq'] for row in manifest['source_runs']})
    assert _ExistingFactsBroker(broker).call('run_new', 'property_estimate', 'computed_property', INPUT,
                                            requesting_actor=WHO).values[0]['value'] == 300


def test_replay_reads_only_the_pinned_completed_tool_prefix(core):
    source(core, 'task_source', 'run_completed', 'completed')
    pin = core.journal.last_seq('run_completed')
    later = Broker(core)
    later.register(FakeProperty({('K2', 'MW'): 500}))
    later.call('run_completed', 'property_estimate', 'computed_property', {'identifier': 'K2', 'property': 'MW'},
               requesting_actor=WHO)
    broker = Broker(core)
    broker.register(FakeProperty({}))
    manifest = broker.seed_cache_from_runs(['run_completed'], allow_terminal_sources=True,
                                          source_pins={'run_completed': pin})
    assert manifest['cache_entries'] == 1
    assert manifest['sources'][0]['pinned_seq'] == pin


def test_existing_only_projects_pinned_cache_without_provider_dispatch_or_budget_charge(core):
    class CachedProvider:
        contract = ToolContract(tool_id='fixture_predict', capability='attribute_estimate',
            capability_kind='attribute_estimate', question_kinds=('endpoint',), contract_version='1',
            implementation_version='1', purpose_statement='Pinned fixture facts',
            evidence_kind_produced='model_prediction', claim_strength_ceiling='predicted')

        def invoke(self, *args):
            raise AssertionError('A cache projection must never dispatch the provider')

        def existing_response(self, question_kind, inputs):
            if inputs.get('identifier') != 'K1':
                return None
            return ProviderResponse(values=[{'name': 'endpoint', 'value': .3, 'unit': 'probability',
                                            'value_kind': 'predicted', 'determination_basis': 'predicted'}],
                source_retrieved_at='2026-10-01T00:00:00Z',
                local_derivation={'policy': 'fixture_cached_panel', 'manifest_digest': 'a' * 64,
                                  'cache_file_sha256': 'b' * 64, 'time_basis': 'cache_file_mtime'})

    broker = Broker(core)
    broker.register(CachedProvider())
    budget = Budget({'tool_calls': 0, 'llm_turns': 0})
    saved = _ExistingFactsBroker(broker)
    result = saved.call('run_new', 'attribute_estimate', 'endpoint', {'identifier': 'K1'},
                        requesting_actor=WHO, budget=budget)
    assert result.values[0]['value'] == .3 and result.values[0]['value_kind'] == 'predicted'
    assert result.provenance['derived_from']['cache_file_sha256'] == 'b' * 64
    assert result.provenance['retrieved_at'] == '2026-10-01T00:00:00Z'
    event, = core.journal.replay('run_new')
    assert event.event_type == 'tool.returned' and event.payload['charged_tool_calls'] == 0
    assert event.payload['fresh_tool_call'] is False
    missing = saved.call('run_missing', 'attribute_estimate', 'endpoint', {'identifier': 'K2'},
                         requesting_actor=WHO, budget=budget)
    assert missing.absence_reason == 'existing_evidence_unavailable'
    assert not budget.used


def test_changed_fact_manifest_forces_fresh_cells_instead_of_carrying_old_missing_values(core):
    from mas.core import ledger, measurement
    from mas.core.controller import RunController
    from mas.core.investigation import start_with_compatible_reuse
    from tests.test_qualification_first import _fixture
    from tests.test_run_end_to_end import OPERATOR

    tid, identities, evidence_hook, calls = _fixture(core)
    restored = False

    def facts(request):
        if not restored and request['rule']['rule_kind'] == 'preference':
            return [], None, ['old_cache_miss']
        return evidence_hook(request)

    options = {'adapter': {'adapter_id': 'synthetic', 'adapter_version': '1', 'primary_scheme': 'ik'},
               'identity_hook': identities, 'evidence_hook': facts}
    profile = measurement.register(core, tid, by=OPERATOR, primary_board='Old cache',
                                    rationale='Fixture', expected_effect='Missing facts remain unknown')
    old = RunController(core, Broker(core), evidence_manifest={'cache': 'old'}, **options)
    first = old.start(tid, by=OPERATOR, measurement_profile_ref=profile)
    old_seq = core.journal.last_seq(first)
    restored = True
    calls.clear()
    profile2 = measurement.register(core, tid, by=OPERATOR, primary_board='Pinned restored facts',
                                     rationale='Fixture', expected_effect='Recompute the new evidence contract')
    fresh = RunController(core, Broker(core), evidence_manifest={'cache': 'new'}, **options)
    reasons = []
    second = start_with_compatible_reuse(fresh, tid, by=OPERATOR, measurement_profile_ref=profile2,
                                         reuse_from_run_id=first, on_recompute=reasons.append)
    assert len(reasons) == 1 and 'evidence_manifest' in reasons[0]['reason']
    assert core.journal.last_seq(first) == old_seq
    observed = [core.artifacts.payload(event.payload['artifact_id']) for event in core.journal.replay(second)
                if event.event_type == 'candidate.assessed']
    assert ('alpha', 'preference') in calls
    assert next(row for row in observed if row['candidate_ref'] == 'alpha' and row['rule_kind'] == 'preference')['verdict'] == 'available'
    assert all(row['reuse']['decision'] != 'reused' for row in observed)
