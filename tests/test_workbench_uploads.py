import json

import pytest

from mas.ui.uploads import UploadStore, template


def library(store, content='candidate_id,name\n001,Carrier A\n002,Carrier B\n'):
    preview = store.preview({'kind': 'candidates', 'filename': 'candidates.csv', 'content': content,
                             'entity_type': 'carrier'})
    assert preview['can_commit']
    return store.commit(preview['upload_id'], {'mapping': preview['mapping'], 'entity_type': 'carrier'})


def test_mapping_preserves_ids_observation_context_and_immutable_versions(tmp_path):
    store = UploadStore(tmp_path / 'store')
    chosen = library(store)
    content = 'sample_id,endpoint,result,units,evidence_basis,condition,doi\n001,size,120,nm,measured,"DLS; 25 C",local notebook\n002,size,160,nm,predicted,"DLS; 25 C",local model\n'
    value = {'kind': 'measurements', 'filename': 'measurements.csv', 'content': content,
             'entity_type': 'carrier', 'library_id': chosen['library_id']}
    preview = store.preview(value)
    assert preview['can_commit'] and preview['valid_rows'] == 2
    result = store.commit(preview['upload_id'], {'mapping': preview['mapping'],
        'entity_type': 'carrier', 'library_id': chosen['library_id']})
    record = store.read(result['evidence_upload_id'])
    assert record['measurements'][0]['candidate_id'] == '001'
    assert record['measurements'][0]['value'] == 120
    assert record['measurements'][0]['conditions'] == {'description': 'DLS; 25 C'}
    assert record['measurements'][1]['basis'] == 'predicted'
    assert record['measurements'][0]['provenance']['scientific_review'] == 'not_performed'
    again = store.commit(preview['upload_id'], {'mapping': preview['mapping'],
        'entity_type': 'carrier', 'library_id': chosen['library_id']})
    assert again == result and store.read(result['evidence_upload_id']) == record
    changed = store.preview(dict(value, content=content.replace('120', '121')))
    replacement = store.commit(changed['upload_id'], {'mapping': changed['mapping'],
        'entity_type': 'carrier', 'library_id': chosen['library_id']})
    assert replacement['upload_id'] != result['upload_id']
    assert store.read(result['upload_id']) == record
    assert len(store.list_libraries()) == 1


@pytest.mark.parametrize('data,field', [
    ('003,size,10,nm,measured', 'candidate_id'),
    ('001,size,10,,measured', 'unit'),
    ('001,size,nan,nm,measured', 'value'),
    ('001,size,10,nm,peer_reviewed', 'basis'),
])
def test_bad_observations_are_located_and_cannot_be_committed(tmp_path, data, field):
    store = UploadStore(tmp_path / 'store')
    chosen = library(store)
    preview = store.preview({'kind': 'measurements', 'filename': 'data.csv',
        'content': 'candidate_id,property,value,unit,basis\n' + data + '\n',
        'entity_type': 'carrier', 'library_id': chosen['library_id']})
    assert not preview['can_commit']
    assert any(row.get('row') == 2 and row['field'] == field for row in preview['errors'])
    with pytest.raises(ValueError, match='Resolve'):
        store.commit(preview['upload_id'], {'mapping': preview['mapping'], 'library_id': chosen['library_id']})


def test_duplicate_ids_and_file_path_injection_do_not_create_candidate_libraries(tmp_path):
    store = UploadStore(tmp_path / 'store')
    preview = store.preview({'kind': 'candidates', 'filename': '../../candidates.csv',
        'content': 'candidate_id,name\n001,A\n001,B\n'})
    assert preview['filename'] == 'candidates.csv' and not preview['can_commit']
    assert preview['errors'][0]['row'] == 3
    with pytest.raises(ValueError, match='saved upload'):
        store.read('../../outside')
    assert not store.list_libraries()


def test_templates_link_without_guessing_evidence_basis_and_category_has_no_fake_unit(tmp_path):
    store = UploadStore(tmp_path / 'store')
    chosen = library(store, template('candidates'))
    preview = store.preview({'kind': 'measurements', 'filename': 'example.csv',
        'content': template('measurements'), 'library_id': chosen['library_id'], 'entity_type': 'carrier'})
    assert preview['can_commit']
    category = store.preview({'kind': 'measurements', 'filename': 'category.csv',
        'content': 'candidate_id,property,value,unit,basis\nEXAMPLE-A,stable,true,,measured\n',
        'library_id': chosen['library_id']})
    assert category['can_commit'] and category['_canonical'][0]['value'] is True
    assert category['_canonical'][0]['unit'] is None


def test_changed_committed_content_cannot_reuse_its_original_identity(tmp_path):
    store = UploadStore(tmp_path / 'store')
    chosen = library(store)
    path = store.root / (chosen['upload_id'] + '.json')
    record = json.loads(path.read_text(encoding='utf-8'))
    record['candidates'][0]['label'] = 'Changed outside the importer'
    path.write_text(json.dumps(record), encoding='utf-8')
    with pytest.raises(ValueError, match='changed outside'):
        store.read(chosen['upload_id'])
