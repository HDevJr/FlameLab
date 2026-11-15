"""BL-17 contracts: no external calls, no scientific promotion, no real executor."""
import copy
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import guided_review as g
from backend.app.api.platform import Services
from backend.app.main import app
from backend.app.simulation import bridge
from backend.app.simulation.executor import FakeExecutor

PID = bridge.FLAME_SPREAD.model_id
ROOT = '/api/experiments/BASS2-M1/guided-review'


@pytest.fixture
def client():
    Services.executor = FakeExecutor()
    return TestClient(app)


def get(client):
    r = client.get(ROOT)
    assert r.status_code == 200, r.text
    return r.json()['data']


def proposal(**kw):
    return {'value':15.0, 'unit':'cm', 'source':'Relatório científico complementar, seção experimental',
            'location':'p. 55', 'evidence':'Amostra do ensaio M1 com comprimento explicitamente indicado.',
            'author':'Pessoa Autora', **kw}


def decide(client, data, action, index=0, **kw):
    return client.post(ROOT + '/' + data['tasks'][index]['gap_id'], json={
        'expected_revision': data['revision'], 'action': action, 'author': 'Pessoa Autora', **kw})


def submit(client, index=0, **kw):
    d = get(client)
    response = decide(client, d, 'SOURCE', index, proposal=proposal(**kw))
    assert response.status_code == 200, response.text
    return response.json()['data']


def test_real_twelve_stable_order_source_links_and_separate_blockers(client):
    data = get(client)
    assert len(data['tasks']) == 12
    assert [t['parameter'] for t in data['tasks']] == g.ORDER
    exp = Services.catalog().experiment('BASS2-M1')
    shuffled = copy.deepcopy(exp)
    shuffled['gaps'].reverse()
    assert [t['gap_id'] for t in g.view(shuffled, PID)['tasks']] == [t['gap_id'] for t in data['tasks']]
    assert len(exp['parameters']) == 9 and exp['review']['reviewed'] == 9
    assert data['readiness']['generator_approved'] is False
    assert data['readiness']['pending'] and not data['readiness']['can_execute']
    assert data['tasks'][0]['possible_sources_pt']
    assert data['tasks'][0]['known'][0]['evidence'][0]['document_id']


def test_frontend_fixture_matches_live_wire_contract(client):
    from pathlib import Path
    fixture=json.loads(Path('frontend/src/fixtures/guided_review_m1.json').read_text(encoding='utf-8'))
    live=get(client)
    assert set(fixture)==set(live)
    assert fixture['profile']==live['profile']
    for expected,actual in zip(fixture['tasks'],live['tasks'],strict=True):
        assert set(expected)==set(actual)
        for field in ('parameter','gap_id','schema','required','assumption_allowed','impact_pt','why_pt'):
            assert expected[field]==actual[field]


def test_persist_submission_resume_and_immutable_case_without_promotion(client):
    before = json.dumps(Services.catalog().experiment('BASS2-M1'), sort_keys=True)
    data = submit(client)
    first = data['tasks'][0]
    assert first['state'] == 'SOURCE_SUBMITTED' and first['current']['review_state'] == 'PENDING'
    assert first['current']['normalized']['value'] == pytest.approx(.15)
    case = bridge.load(first['current']['case_id'], first['current']['case_version'])
    assert case['content']['assumptions'] == [] and case['content']['values'] == {}
    assert case['content']['guided_review']['usage'] == 'DOCUMENTATION_ONLY_NOT_GENERATOR_INPUT'
    assert bridge.validate(case['content']['case_id'],1)['state'] == 'MODEL_NOT_APPROVED'
    moved = client.post(ROOT + '/cursor', json={'expected_revision':data['revision'], 'gap_id':data['tasks'][1]['gap_id']}).json()['data']
    Services.reset()
    restored = get(client)
    assert restored['cursor'] == moved['tasks'][1]['gap_id']
    assert restored['tasks'][0]['current']['proposal']['value'] == 15
    assert restored['resolved'] == 0
    assert json.dumps(Services.catalog().experiment('BASS2-M1'), sort_keys=True) == before
    assert 'sample_length' in restored['readiness']['pending']


def test_draft_defer_not_found_history_and_stale_revision(client):
    d = get(client)
    body = {'draft':{'value':'unfinished', 'author':'Pessoa Autora'}}
    first = decide(client,d,'DRAFT',**body)
    assert first.status_code == 200
    assert first.json()['data']['tasks'][0]['state'] == 'IN_PROGRESS'
    assert decide(client,d,'DRAFT',**body).status_code == 409
    d = get(client)
    assert decide(client,d,'DEFER',notes='Buscar a tese relacionada').status_code == 200
    d = get(client)
    assert d['tasks'][0]['state'] == 'OPEN' and d['tasks'][0]['current']['draft']['value'] == 'unfinished'
    assert decide(client,d,'NOT_FOUND',notes='Consultei o capítulo e a tese, sem identificação de M1.').status_code == 200
    d = get(client)
    assert d['tasks'][0]['state'] == 'BLOCKED' and len(d['tasks'][0]['history']) == 3
    assert [e['case_version'] for e in d['tasks'][0]['history']] == [1,2,3]


@pytest.mark.parametrize('index,value,unit',[(0,-1,'m'),(0,2,'s'),(0,.001,'mm'),(3,0,'Pa'),(4,-280,'°C'),(0,True,'m'),(0,'15','cm')])
def test_invalid_dimensions_domain_types_and_consistency(client,index,value,unit):
    d = get(client)
    p = proposal();p.update(value=value,unit=unit)
    assert decide(client,d,'SOURCE',index,proposal=p).status_code == 422
    assert get(client)['revision'] == 0


def test_celsius_normalization(client):
    d=submit(client,index=4,**{'value':20.0,'unit':'°C'})
    assert d['tasks'][4]['current']['normalized']['value'] == pytest.approx(293.15)


def test_hypothesis_requires_reference_justification_and_profile_permission(client):
    d = get(client)
    p = proposal();p.update(source='',justification='Proposta exploratória',limitations='Somente análise preliminar')
    assert decide(client,d,'ASSUMPTION',proposal=p).status_code == 422
    p['source']='Referência bibliográfica com condições equivalentes'
    p['justification']=''
    assert decide(client,d,'ASSUMPTION',proposal=p).status_code == 422
    p['justification']='Comparação com geometria e material equivalentes'
    response=decide(client,d,'ASSUMPTION',proposal=p)
    assert response.status_code == 200, response.text
    event=response.json()['data']['tasks'][0]['current']
    assert event['state']=='ASSUMPTION_PROPOSED'
    assert event['assumption']['source_type']=='EXTERNAL_LITERATURE'
    d=get(client)
    assert not d['tasks'][8]['assumption_allowed']
    p.update(value=None,unit='n/a',details='Propriedades químicas documentadas para revisão especializada')
    assert decide(client,d,'ASSUMPTION',8,proposal=p).status_code == 422


def test_independent_review_never_approves_pmma_or_rewrites_original(client):
    d=submit(client)
    assert decide(client,d,'ACCEPT',author='Revisora Independente',notes='Conferi as evidências e o escopo').status_code==422
    d=decide(client,d,'REQUEST_REVIEW').json()['data']
    assert d['tasks'][0]['state']=='UNDER_REVIEW'
    assert decide(client,d,'ACCEPT',notes='Conferi o registro na fonte').status_code==422
    r=decide(client,d,'ACCEPT',author='Revisora Independente',notes='Conferi as evidências e o escopo')
    assert r.status_code==200,r.text
    d=r.json()['data']
    assert d['tasks'][0]['current']['review_state']=='ACCEPTED'
    assert d['tasks'][0]['state']=='UNDER_REVIEW' and d['resolved']==0
    assert not d['readiness']['can_execute']
    case=d['tasks'][0]['current']['case_id']
    assert client.post('/api/simulations',json={'case_id':case}).status_code==422
    prepared=client.get('/api/experiments/BASS2-M1/simulation-preparation').json()['data']
    assert prepared['guided_review']['tasks'][0]['current']==d['tasks'][0]['current']


def test_comparison_and_fidelity_gaps_are_not_execution_inputs(client):
    d=get(client)
    for index in (6,9,10,11):
        assert not d['tasks'][index]['required']
    assert 'não é uma entrada de execução' in d['tasks'][10]['impact_pt']
    assert d['tasks'][0]['required']
    compat=client.get('/api/experiments/BASS2-M1/compatibility').json()['data']
    assert not {'measurement_uncertainty','o2_time_profile','anemometer_location','flame_front_tracking_method'} & set(compat['missing'])
    items=next(d for d in compat['readiness']['dimensions'] if d['key']=='coverage')['items']
    assert len(items)==len(set(items))


def test_open_comparison_gap_does_not_block_input_coverage_but_open_required_gap_does(client):
    from backend.app.simulation.compatibility import assess, with_readiness, ALIASES
    exp=copy.deepcopy(Services.catalog().experiment('BASS2-M1'))
    exp['parameters']=[{'parameter':ALIASES.get(name,name),'label_pt':name,'original':{'value':1,'unit':'m'},
                        'role':'CONDICAO','status':'CONFERIDO_FONTE','review_scope':'FULL','integrity':{'status':'OK'}}
                       for name in bridge.FLAME_SPREAD.required_inputs]
    exp['gaps']=[next(gap for gap in exp['gaps'] if gap['parameter']=='measurement_uncertainty')]
    compat=with_readiness(exp,assess(exp,True),True)
    assert not compat['missing']
    assert next(d for d in compat['readiness']['dimensions'] if d['key']=='coverage')['status']=='COMPLETA'
    assert not compat['actions']['simulate']  # generator still missing
    exp['gaps'].append({'parameter':'sample_length','label_pt':'Comprimento da amostra','purpose_blocked':['FDS_REPRODUCTION']})
    assert 'sample_length' in assess(exp,True)['missing']


def test_resolution_requires_current_approved_profile_and_its_domain(client,monkeypatch):
    original=bridge.profiles
    def approved():
        all=original()
        all[1].update(approved=True,implemented=True)
        all[1]['parameters']=[{'name':'sample_length','unit':'m','min':.1,'max':.2,'assumption_allowed':False}]
        return all
    monkeypatch.setattr(bridge,'profiles',approved)
    d=submit(client)
    assert d['tasks'][0]['state']=='SOURCE_SUBMITTED'
    d=decide(client,d,'REQUEST_REVIEW').json()['data']
    d=decide(client,d,'ACCEPT',author='Revisora Independente',notes='Conferi o escopo e as dimensões').json()['data']
    assert d['tasks'][0]['state']=='RESOLVED_FOR_PROFILE'
    assert 'sample_length' in d['readiness']['satisfied']
    assert 'ambient_pressure' in d['readiness']['pending']
    assert not d['readiness']['can_execute']  # remaining inputs and physical verification still block
    changed=copy.deepcopy(Services.catalog().experiment('BASS2-M1'))
    changed['parameters'][0]['original']['raw_text']='Source has changed'
    assert g.view(changed,PID)['tasks'][0]['state']=='UNDER_REVIEW'
    monkeypatch.setattr(bridge,'profiles',original)
    assert get(client)['tasks'][0]['state']=='UNDER_REVIEW'


def test_complex_value_requires_structured_contract_never_scalar_or_free_text(client):
    # BL-17.2: o duto tem contrato de geometria; texto livre e escalar avulso são recusados.
    p=proposal();p.update(value=None,unit='n/a',details='Descrição das dimensões e condições da geometria na fonte científica.')
    r=decide(client,get(client),'SOURCE',2,proposal=p)
    assert r.status_code==422 and 'formulário estruturado' in r.text
    assert decide(client,get(client),'SOURCE',2,proposal=proposal()).status_code==422
    assert get(client)['revision']==0


def test_wrong_profile_ids_unknown_experiment_extra_fields_and_foreign_gap(client):
    assert client.get(ROOT+'?profile_id='+bridge.INTEGRATION.model_id).status_code==422
    assert client.get('/api/experiments/missing/guided-review').status_code==404
    d=get(client)
    r=client.post(ROOT+'/GAP-other',json={'action':'DEFER','expected_revision':0,'author':'Pessoa Autora','notes':'Voltar depois'})
    assert r.status_code==422
    assert decide(client,d,'SOURCE',proposal=proposal(),state='RESOLVED_FOR_PROFILE').status_code==422


def test_dylco_physics_not_supported_and_no_independent_case_link(client):
    exp=json.loads(__import__('pathlib').Path('frontend/src/fixtures/experiment_payload_backend_v2_1.json').read_text(encoding='utf-8'))
    d=g.view(exp,PID)
    assert not d['readiness']['supported'] and not d['readiness']['can_execute']
    assert not d['readiness']['pending']
    assert all(not t['assumption_allowed'] for t in d['tasks'])
    cid=client.post('/api/cases',json={}).json()['data']['content']['case_id']
    assert bridge.load(cid)['content']['experiment_id'] is None
    assert 'guided_review' not in bridge.load(cid)['content']


@pytest.mark.parametrize('tamper',['event','case','corrupt'])
def test_audit_integrity_detects_changes(client,tamper):
    d=submit(client)
    path=g._path('BASS2-M1',PID)
    if tamper=='case':
        event=d['tasks'][0]['current']
        cp=bridge._path(event['case_id'],1)
        case=json.loads(cp.read_text(encoding='utf-8'))
        case['content']['guided_review']['decision']['proposal']['value']=99
        cp.write_text(json.dumps(case),encoding='utf-8')
    elif tamper=='event':
        log=json.loads(path.read_text(encoding='utf-8'))
        log['events'][0]['author']='Outra pessoa'
        path.write_text(json.dumps(log),encoding='utf-8')
    else:
        path.write_text('{broken',encoding='utf-8')
    assert client.get(ROOT).status_code==422
