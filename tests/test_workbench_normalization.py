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


def test_research_dimensions_follow_the_task_route_and_target_profile():
    from mas.adapters.drug.registration import research_dimensions
    context = {'scope_entities': [{'label': 'Example receptor', 'entity_kind': 'target'}],
               'constraints': [{'kind': 'route', 'text': 'Intravenous administration is required.'}]}
    dimensions = research_dimensions(context)
    assert dimensions[0]['focus'].endswith('Example receptor')
    assert dimensions[1]['dimension'] == 'administration_suitability'
    assert 'Intravenous' in dimensions[1]['focus']
    assert 'oral' not in dimensions[-1]['focus']
    context['constraints'][0]['text'] = 'Oral administration is required.'
    assert research_dimensions(context)[1]['dimension'] == 'oral_bioavailability'


def test_nonoral_requirement_keeps_its_own_meaning_and_binding():
    for requirement in ('Intravenous administration is required.', 'Non-oral administration is required.',
                        'Oral or intravenous administration is acceptable.'):
        template = objective_templates({'constraints': [{'text': requirement, 'kind': 'route', 'hardness': 'hard'}]})
        assert len(template) == 1 and template[0]['source_field'] == 'constraints[0]'
        assert requirement in template[0]['attribute']['definition']
        assert template[0]['rule']['rule_kind'] == 'hard_exclusion'
        assert template[0]['attribute']['evidence_request']['capability'] == 'literature_retrieval'


def test_fresh_retrieval_does_not_require_an_old_case_collection(monkeypatch):
    from types import SimpleNamespace
    import pytest
    from mas.core import investigation
    updates = []
    value = {'objective': 'A new target study', 'library_id': 'synthetic-library',
             'entity_type': 'drug', 'evidence_mode': 'retrieve', 'source_task_id': None}
    manager = SimpleNamespace(operations=SimpleNamespace(), _read=lambda key: {'input': value},
                              update=lambda *args, **kwargs: updates.append(kwargs))
    monkeypatch.setattr(investigation, 'libraries', lambda ops: [{'id': 'synthetic-library'}])
    class ModelPreparationReached(Exception):
        pass
    def stop_before_model_configuration(ops):
        raise ModelPreparationReached()
    monkeypatch.setattr(investigation, 'investigation_roster', stop_before_model_configuration)
    with pytest.raises(ModelPreparationReached):
        investigation.execute(manager, 'synthetic-workflow')
    assert updates == []
    value['evidence_mode'] = 'existing_only'
    investigation.execute(manager, 'synthetic-workflow')
    assert updates[-1]['questions'][0]['id'] == 'source_task_id'
