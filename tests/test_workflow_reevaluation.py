"""A new evaluation retains completed research and its accumulated budget."""
import json
from types import SimpleNamespace

import pytest

from mas.ui.workflows import PHASES, WorkflowManager


def test_reevaluation_keeps_research_budget_and_prior_evaluation(tmp_path):
    manager = WorkflowManager(SimpleNamespace(store_root=tmp_path / 'store'), SimpleNamespace())
    row = {'workflow_id': 'wf_test', 'task_id': 'task_test', 'state': 'cancelled', 'phase': 'screen',
           'input': {'objective': 'Synthetic retained research', 'budget_usd': 10},
           'run_id': 'run_old', 'snapshot_id': None, 'finished_at': '2026-10-16T00:00:00Z',
           'started_at': '2026-10-15T00:00:00Z', '_budget_used': {'usd': 4.25, 'llm_turns': 8},
           'budget': {'used_usd': 4.25, 'limit_usd': 10, 'cost_status': 'recorded_estimate'},
           '_run_history': ['run_derivation'], '_checkpoints': {
               'normalized': {'task_id': 'task_test'}, 'fact_bank': {'manifest_ref': 'art_fixed'},
               'derivation': {'run_id': 'run_derivation'}, 'review': {'completed_at': 'old'},
               'freeze': {'rule_set_ref': 'rules@v1'}, 'screen_started': {'run_id': 'run_old'}},
           'phases': [{'id': key, 'label': label, 'state': 'completed'} for key, label in PHASES]}
    with manager.db() as db:
        db.execute('INSERT INTO workflows VALUES (?,?,?)', ('wf_test', 'original', json.dumps(row)))
    launched = []
    manager._launch = launched.append
    manager.command('wf_test', 'reevaluate')
    after = manager._read('wf_test')
    assert launched == ['wf_test'] and after['state'] == 'queued'
    assert after['_budget_used'] == row['_budget_used'] and after['budget'] == row['budget']
    assert after['started_at'] == row['started_at']
    assert set(after['_checkpoints']) == {'normalized', 'fact_bank', 'derivation'}
    assert after['_checkpoints']['fact_bank'] == {'manifest_ref': 'art_fixed'}
    assert after['input']['reuse_from_run_id'] == 'run_old'
    assert after['_evaluation_history'][0]['checkpoints']['freeze'] == {'rule_set_ref': 'rules@v1'}
    assert after['_evaluation_history'][0]['state'] == 'cancelled'
    assert after['_run_history'] == ['run_derivation', 'run_old']
    with pytest.raises(ValueError, match='Stop the current evaluation'):
        manager.command('wf_test', 'reevaluate')
    manager.update('wf_test', state='cancelled', _budget_used={'usd': 10})
    with pytest.raises(ValueError, match='budget is exhausted'):
        manager.command('wf_test', 'reevaluate')
