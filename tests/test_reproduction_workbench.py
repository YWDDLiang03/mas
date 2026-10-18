"""A fixed factual collection is selectable without pretending it is a research run."""
import json

from mas.core import task
from mas.core.canonical import sha256_hex
from mas.core.journal import actor
from mas.core.runtime import Core
from mas.ui.operations import OperationManager
from mas.ui.workbench_api import WorkbenchAPI


def test_evidence_only_collection_is_selectable_and_new_setup_keeps_recorded_input(tmp_path):
    workspace=tmp_path/'workspace'
    with Core.open(workspace/'store') as core:
        source={'source_id':'src_portable_fixture','title':'Fixture source'}
        sr=core.artifacts.put('source',source)
        claim={'claim_id':'claim_portable_fixture','source_ref':source['source_id'],'admission_state':'admitted',
               'normalized_statement':'An explicitly synthetic observation.'}
        cr=core.artifacts.put('claim',claim)
        facts=core.artifacts.put('existing_fact_manifest',{'source_task_id':'task_prior',
            'claims':[{'claim_id':claim['claim_id'],'artifact_id':cr,'sha256':sha256_hex(claim)}],
            'source_records':{source['source_id']:{'artifact_id':sr,'sha256':sha256_hex(source)}}})
        base={'objective_text':'Compare fixture candidates','mode':'exploratory','evaluation_scope':'fixture',
              'candidate_universe':{'members':['fixture_candidate']},'evidence_fact_manifest_ref':facts}
        by=actor('tool','portable-test')
        recorded,_=task.record_version(core,dict(base,title='Recorded fixture',
            original_user_input={'objective':'Compare fixture candidates','source_task_id':'task_prior',
                                 'evidence_mode':'existing_only','evaluation_mode':'staged'}),by=by)
        prepared,_=task.record_version(core,dict(base,title='Fixture evidence',purpose='evidence_collection'),by=by)
    (workspace/'reproduction-import.json').write_text(json.dumps({'task_id':recorded}),encoding='utf-8')
    fresh={'objective':'Compare fixture candidates','source_task_id':prepared,
           'evidence_mode':'existing_only','evaluation_mode':'staged'}
    (workspace/'reproduction-live-input.json').write_text(json.dumps({'input':fresh}),encoding='utf-8')
    ops=OperationManager(workspace/'store',working_directory=tmp_path)
    api=WorkbenchAPI(ops)
    try:
        api.model.sync()
        data=api.bootstrap()
        assert [t['task_id'] for t in data['tasks']]==[recorded]
        assert len(data['evidence_sources'])==1
        assert data['evidence_sources'][0]['task_id']==prepared
        assert data['evidence_sources'][0]['claim_count']==1
        assert data['defaults']['source_task_id']==prepared
        overview=api.get(f'/api/workbench/tasks/{recorded}/overview',{})
        assert overview['input']['source_task_id']=='task_prior'
        assert overview['new_study_input']['source_task_id']==prepared
        with Core.open(workspace/'store',read_only=True) as core:
            assert task.get(core,recorded)['original_user_input']['source_task_id']=='task_prior'
            assert not list(core.journal.of_type('criterion.version_proposed'))
    finally:
        api.close();ops.close()
