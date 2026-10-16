import json
from copy import deepcopy

from mas.ui.workspace_display import WorkspaceDisplay


def test_archive_removes_old_choices_without_changing_records_or_hiding_future_research(tmp_path):
    path = tmp_path / 'display.json'
    path.write_text(json.dumps({'version': 1, 'archived_task_ids': ['old'],
        'archived_workflow_ids': ['orphan'], 'archived_draft_ids': ['draft_old'],
        'archived_snapshot_ids': ['failed_snapshot'], 'archived_library_ids': ['fixture'],
        'task_labels': {'kept': 'Comprehensive study'},
        'snapshot_labels': {'result': 'Complete evaluation'}}))
    display = WorkspaceDisplay(path)
    records = [{'task_id': 'old', 'title': 'Original'}, {'task_id': 'kept', 'title': 'Recorded title'},
               {'task_id': 'future', 'title': 'New study'}]
    original = deepcopy(records)
    shown = display.tasks(records)
    assert [row['task_id'] for row in shown] == ['kept', 'future']
    assert shown[0]['title'] == 'Comprehensive study' and shown[0]['recorded_title'] == 'Recorded title'
    assert records == original
    assert not display.workflow_visible({'workflow_id': 'previous', 'task_id': 'old'})
    assert not display.workflow_visible({'workflow_id': 'orphan', 'task_id': None})
    assert display.workflow_visible({'workflow_id': 'starting', 'task_id': None})
    assert display.drafts([{'draft_id': 'draft_old'}, {'draft_id': 'draft_new'}]) == [{'draft_id': 'draft_new'}]
    assert display.libraries([{'id': 'fixture'}, {'id': 'uploaded_new'}]) == [{'id': 'uploaded_new'}]
    assert display.snapshots([{'snapshot_id': 'failed_snapshot'}, {'snapshot_id': 'result'}]) == [
        {'snapshot_id': 'result', 'label': 'Complete evaluation'}]


def test_missing_display_configuration_preserves_normal_workspace(tmp_path):
    display = WorkspaceDisplay(tmp_path / 'not_created.json')
    rows = [{'task_id': 'task_a', 'title': 'My research'}]
    assert display.tasks(rows) == rows
    assert display.workflow_visible({'task_id': 'task_a', 'workflow_id': 'wf_a'})
