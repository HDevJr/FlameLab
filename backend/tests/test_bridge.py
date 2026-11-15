import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.platform import Services
from backend.app.simulation import bridge as b
from backend.app.simulation.executor import FakeExecutor


@pytest.fixture
def client():
    Services.executor = FakeExecutor()
    return TestClient(app)


def make(client, **kw):
    response = client.post('/api/cases', json=kw)
    assert response.status_code == 201, response.text
    return response.json()['data']['content']['case_id']


def approve(client, cid):
    return client.post(f'/api/cases/{cid}/review', json={'reviewer':'Ana Souza', 'notes':'Defaults técnicos aceitos, sem reprodução NASA', 'accepted_defaults':True})


def test_case_requires_review_and_worker_publishes_manifest(client):
    cid = make(client)
    assert client.post('/api/simulations', json={'case_id':cid}).status_code == 422
    assert approve(client,cid).status_code == 200
    a,built = b.build(cid,1),b.build(cid,1)
    assert a == built
    result = client.post('/api/simulations',json={'case_id':cid})
    assert result.status_code == 202, result.text
    rid = result.json()['data']['run_id']
    Services.sim()._execute(rid)
    run = Services.sim().get_run(rid)
    assert run['state'] == 'COMPLETED' and run['demo'] is True and run['scope'] == 'DEMO'
    assert any(a['kind']=='MANIFEST_JSON' for a in run['artifacts'])
    assert run['results']['comparison']['status']=='UNAVAILABLE'


def test_m1_is_resolved_without_copy_or_execution(client):
    exp = Services.catalog().experiment('BASS2-M1')
    before = json.dumps(exp, sort_keys=True)
    result = client.get('/api/experiments/BASS2-M1/simulation-preparation').json()['data']
    assert len(result['gaps']) == 12 and len(result['observables']) == 3
    assert result['state']=='MODEL_NOT_APPROVED'
    assert 'flame_spread_rate' in {p['parameter'] for p in result['observables']}
    cid = make(client, profile_id=b.FLAME_SPREAD.model_id, experiment_id='BASS2-M1')
    approve(client,cid)
    assert client.post('/api/simulations',json={'case_id':cid}).status_code==422
    assert json.dumps(Services.catalog().experiment('BASS2-M1'),sort_keys=True)==before


@pytest.mark.parametrize('body',[
    {'experiment_id':'BASS2-M1'}, {'profile_version':'bad'}, {'profile_id':'bad'}, {'fds_text':'&HEAD /'},
    {'assumptions':[{'parameter':'t_end','value':5,'unit':'s'}]},
])
def test_invalid_cases(client,body):
    assert client.post('/api/cases',json=body).status_code==422


def assumption(**kw):
    return {'parameter':'t_end','value':0.1,'unit':'min','source':'Engineering note', 'source_type':'ENGINEERING_ASSUMPTION',
            'justification':'Short technical check','author':'Author One','limitations':'No NASA fidelity',**kw}


@pytest.mark.parametrize('patch',[
    {'parameter':'flame_spread_rate'}, {'value':100}, {'unit':'mm'}, {'source':''}, {'source_type':'NASA_EXPERIMENT'},
])
def test_rejected_assumptions(client,patch):
    assert client.post('/api/cases',json={'assumptions':[assumption(**patch)]}).status_code==422


def test_conversion_independent_review_and_versions(client):
    req={'assumptions':[assumption()]}
    cid=make(client,**req)
    assert b.load(cid)['content']['values']['t_end']==6
    assert client.post(f'/api/cases/{cid}/review',json={'reviewer':'Author One','notes':'accept these values','accepted_defaults':True}).status_code==422
    approve(client,cid)
    assert client.post(f'/api/cases/{cid}/versions',json=req).json()['data']['content']['version']==2
    assert b.validate(cid,2)['blockers']==['INDEPENDENT_REVIEW_REQUIRED']
    assert b.validate(cid,1)['state']=='EXECUTION_READY'


def test_tamper_and_resource_readiness(client):
    cid=make(client);approve(client,cid)
    assert 'EXECUTOR_UNAVAILABLE' in b.validate(cid,1,False)['blockers']
    path=b._path(cid,1); d=json.loads(path.read_text());d['content']['values']['t_end']=60;path.write_text(json.dumps(d))
    assert client.post('/api/simulations',json={'case_id':cid}).status_code==422


def test_same_configuration_same_fds_across_independent_cases(client):
    first,second=make(client),make(client)
    approve(client,first);approve(client,second)
    assert b.build(first,1)[:2]==b.build(second,1)[:2]


def test_profile_revision_invalidates_approval(client,monkeypatch):
    cid=make(client);approve(client,cid)
    monkeypatch.setattr(b,'VERSION','2.0.0')
    assert b.validate(cid,1)['state']=='MODEL_NOT_APPROVED'
    assert client.post('/api/simulations',json={'case_id':cid}).status_code==422


def test_unknown_revision_target_and_nonfinite_values(client):
    assert client.post('/api/cases/CASE-missing/versions',json={}).status_code==404
    assert client.post('/api/cases',json={'assumptions':[assumption(value=True)]}).status_code==422


def test_queued_case_rechecks_review_before_worker(client):
    cid=make(client);approve(client,cid)
    rid=client.post('/api/simulations',json={'case_id':cid}).json()['data']['run_id']
    b._path(cid,1).with_suffix('.review.json').unlink()
    Services.sim()._execute(rid)
    assert Services.sim().get_run(rid)['state']=='BLOCKED'
