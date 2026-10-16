"""The route alias observed in the first real workbench run stays a hard condition."""
from mas.adapters.drug.registration import objective_templates
from mas.core.budget import Budget
from mas.core.investigation import _normalize
from test_criteria_pool import roster_for


def test_normalized_administration_route_remains_bound_to_hard_oral_condition(core):
    response = {'title': 'Oral candidates', 'objective': 'Identify an orally administered candidate',
        'mode': 'conditional', 'targets': [], 'questions': [],
        'constraints': [{'text': 'Oral administration is required.', 'kind': 'administration_route', 'hardness': 'hard'}]}
    result = _normalize(core, roster_for(lambda request: response), 'task_normalization_regression',
                        {'objective': response['objective']}, {}, Budget({'llm_turns': 1}))
    conditions = objective_templates({'scope_entities': [], 'constraints': result['constraints']})
    hard = [item for item in conditions if item['rule']['rule_kind'] == 'hard_exclusion']
    assert len(hard) == 1
    assert hard[0]['source_field'] == 'constraints[0]'
    assert hard[0]['attribute']['evidence_request']['parameters']['field'] == 'oral'
    assert result['constraints'][0]['text'] == response['constraints'][0]['text']
    assert result['constraints'][0]['hardness'] == 'hard'
