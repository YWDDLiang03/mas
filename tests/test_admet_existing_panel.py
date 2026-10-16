"""Saved-panel projection regression checks; no predictor or descriptor calculation is run."""
import json
from pathlib import Path

import pytest

from mas.adapters.predict import admet


@pytest.fixture
def saved(tmp_path, monkeypatch):
    records = [json.loads(line) for line in (Path(__file__).parent / 'fixtures/admet_worker_output.jsonl').read_text().splitlines()]
    meta = next(row for row in records if row['kind'] == 'meta')
    row = next(row for row in records if row['kind'] == 'row' and row.get('values'))
    universe = tmp_path / 'universe_chembl.json'
    universe.write_text(json.dumps({'source': 'recorded worker fixture', 'universe': [
        {'inchikey': 'EXACT-KEY', 'chembl_id': 'CHEMBL1'}, {'inchikey': 'MISSING-KEY', 'chembl_id': 'CHEMBL2'}]}))
    (tmp_path / 'universe_smiles.json').write_text(json.dumps({'CHEMBL1': row['smiles'], 'CHEMBL2': 'CCO'}))
    cache = admet.PanelCache(tmp_path / 'cache')
    record = dict(row, predictor=meta, panel_version=admet.PANEL_VERSION)
    cache._store(record)
    def forbidden(*args, **kwargs):
        raise AssertionError('saved projection must never compute or start an interpreter')
    for method in ('row', 'warm', '_run'):
        monkeypatch.setattr(cache, method, forbidden)
    structures = admet.StructureIndex(universe)
    projection = admet.ExistingPanelProjection(structures, cache)
    return admet.AdmetPrediction(structures, cache, existing=projection), cache, record


def test_whole_saved_panel_serves_exact_new_endpoint_without_inference(saved):
    provider, cache, record = saved
    assert provider.existing_response('admet_prediction', {'identifier': 'EXACT-KEY', 'endpoint': 'BBB_Martins'}) is None
    manifest = provider.pin_existing_cache()
    assert manifest['covered_candidates'] == 1 and manifest['endpoint_counts']['BBB_Martins'] == 1
    response = provider.existing_response('admet_prediction', {'identifier': 'EXACT-KEY', 'endpoint': 'BBB_Martins'})
    assert response.values[0]['value'] == record['values']['BBB_Martins']
    assert response.values[0]['determination_basis'] == 'predicted'
    assert response.local_derivation['cache_file_sha256'] == manifest['entries'][0]['cache_file_sha256']
    assert response.local_derivation['manifest_digest'] == manifest['manifest_digest']
    assert response.local_derivation['charged_tool_calls'] == 0


def test_pin_preserves_original_bytes_and_never_adds_later_cache(saved):
    provider, cache, record = saved
    first = provider.pin_existing_cache()
    changed = json.loads(json.dumps(record))
    changed['values']['BBB_Martins'] = 0.123456
    cache._store(changed)
    cache._store(dict(record, smiles='CCO'))
    assert provider.pin_existing_cache() == first
    response = provider.existing_response('admet_prediction', {'identifier': 'EXACT-KEY', 'endpoint': 'BBB_Martins'})
    assert response.values[0]['value'] == record['values']['BBB_Martins']
    assert provider.existing_response('admet_prediction', {'identifier': 'MISSING-KEY', 'endpoint': 'BBB_Martins'}) is None


@pytest.mark.parametrize('damage', ['wrong_structure', 'wrong_package_version', 'nonfinite_value'])
def test_malformed_or_mismatched_panel_is_not_reinterpreted(saved, damage):
    provider, cache, record = saved
    path = cache.path(record['smiles'])
    if damage == 'wrong_structure':
        record['smiles'] = 'another structure'
    elif damage == 'wrong_package_version':
        record['predictor']['version'] = 'unverified-version'
    else:
        record['values']['BBB_Martins'] = float('nan')
    path.write_text(json.dumps(record))
    assert provider.pin_existing_cache()['covered_candidates'] == 0
    assert provider.existing_response('admet_prediction', {'identifier': 'EXACT-KEY', 'endpoint': 'BBB_Martins'}) is None


def test_descriptor_basis_is_separate_and_identity_must_agree(saved):
    prediction, cache, record = saved
    descriptor = admet.AdmetComputedDescriptors(prediction.structures, cache, existing=prediction._existing)
    descriptor.pin_existing_cache()
    for endpoint in admet.DESCRIPTOR_PROJECTIONS:
        inputs = {'identifier': 'EXACT-KEY', 'endpoint': endpoint}
        old = prediction.existing_response('admet_prediction', inputs)
        new = descriptor.existing_response('admet_computed_property', inputs)
        assert old.values[0]['value'] == new.values[0]['value'] == record['values'][endpoint]
        assert old.values[0]['determination_basis'] == 'predicted'
        assert new.values[0]['determination_basis'] == new.values[0]['value_kind'] == 'derived'
        assert new.values[0]['conditions']['algorithm_source_version'] == '2.0.1'
        assert not new.values[0]['conditions']['computation_performed_now']
    assert descriptor.contract.evidence_kind_produced == 'database_entry'
    assert descriptor.existing_response('admet_computed_property', {'identifier': 'EXACT-KEY', 'endpoint': 'BBB_Martins'}) is None
    assert prediction.existing_response('admet_prediction', {'identifier': 'EXACT-KEY', 'endpoint': 'BBB_Martins',
        'identifiers': [{'scheme': 'inchikey', 'value': 'DIFFERENT-KEY'}]}) is None
