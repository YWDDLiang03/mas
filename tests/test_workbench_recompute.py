from types import SimpleNamespace

import pytest

from mas.core.controller import RunError
from mas.core.investigation import start_with_compatible_reuse


def test_changed_tool_contract_recomputes_with_the_same_budget_and_profile():
    calls, decisions = [], []
    def start(task_id, **options):
        calls.append((task_id, options))
        if options['reuse_from_run_id']:
            raise RunError('rejected_invalid', 'reuse policy drift: tool_availability_snapshot')
        return 'run_fresh'
    result = start_with_compatible_reuse(SimpleNamespace(start=start), 'task_example',
        reuse_from_run_id='run_old', on_recompute=decisions.append,
        measurement_profile_ref='art_current', budget_envelope={'usd': 1}, execute=False)
    assert result == 'run_fresh' and len(calls) == 2
    assert dict(calls[0][1], reuse_from_run_id=None) == calls[1][1]
    assert decisions[0]['decision'] == 'evaluate_fresh_under_current_profile'


def test_other_start_errors_are_not_treated_as_reuse_incompatibility():
    calls = []
    def start(task_id, **options):
        calls.append(task_id)
        raise RunError('rejected_invalid', 'frozen profile differs from current task')
    with pytest.raises(RunError, match='frozen profile'):
        start_with_compatible_reuse(SimpleNamespace(start=start), 'task_example', reuse_from_run_id='run_old')
    assert calls == ['task_example']
