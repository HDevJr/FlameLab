"""BL-17.2 acceptance on BASS-II M1: typed contracts, auditable edits, continuity with preparation,
isolated TEST mode. No Gemini, no network, no real FDS (FakeExecutor)."""
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import gap_contracts as contracts, guided_review as g, units, workspace
from backend.app.api.platform import Services
from backend.app.main import app
from backend.app.paths import REPO_ROOT, var_dir
from backend.app.simulation import bridge
from backend.app.simulation.executor import FakeExecutor

PID = bridge.FLAME_SPREAD.model_id
ROOT = '/api/experiments/BASS2-M1/guided-review'
IDX = {p: i for i, p in enumerate(g.ORDER)}
HOLDER = {'shape': 'flat_plate', 'length': {'value': 12, 'unit': 'cm'}, 'width': {'value': 3, 'unit': 'cm'},
          'thickness': {'value': 2, 'unit': 'mm'}, 'coordinate_system': 'Origem na borda de ataque; x no sentido do escoamento; z normal à amostra',
          'position': {'x': 0, 'y': -0.5, 'z': -0.2, 'unit': 'cm'}, 'orientation': '+z', 'contact': 'full',
          'material_name': 'Material declarado pela fonte do suporte'}
FLOW = {'profile_type': 'uniform', 'reference_velocity': {'value': 9, 'unit': 'cm/s'}, 'direction': '+x',
        'temporal_behavior': 'steady', 'regime': 'laminar'}


@pytest.fixture
def client():
    Services.executor = FakeExecutor()
    return TestClient(app)


def base(**kw):
    return {'source': 'Relatório científico complementar, seção experimental', 'location': 'p. 55',
            'evidence': 'Trecho que sustenta a informação registrada para M1.', 'author': 'Pessoa Autora', **kw}


def hyp(**kw):
    return base(justification='Variante exploratória declarada para estudo de sensibilidade',
                limitations='Sem fidelidade experimental; somente análise preliminar', basis='ENGINEERING_ASSUMPTION', **kw)


def get(client, mode=None):
    r = client.get(ROOT + (f'?mode={mode}' if mode else ''))
    assert r.status_code == 200, r.text
    return r.json()['data']


def post(client, param, action, proposal=None, mode=None, **kw):
    d = get(client, mode)
    body = {'expected_revision': d['revision'], 'action': action, 'author': kw.pop('author', 'Pessoa Autora'), **kw}
    if proposal is not None:
        body['proposal'] = proposal
    return client.post(ROOT + '/' + d['tasks'][IDX[param]]['gap_id'] + (f'?mode={mode}' if mode else ''), json=body)


def ok(r):
    assert r.status_code == 200, r.text
    return r.json()['data']


def task(data, param):
    return data['tasks'][IDX[param]]


def row(data, param):
    return next(r for r in data['requirements'] if r['parameter'] == param)


# 1–3 ------------------------------------------------------------------ hypothetical scalars
@pytest.mark.parametrize('param,value,unit,si,si_unit', [
    ('sample_length', 12, 'cm', .12, 'm'), ('ambient_pressure', 1, 'atm', 101325, 'Pa'), ('ambient_temperature', 20, '°C', 293.15, 'K')])
def test_hypothetical_quantities_with_units_are_saved_explained_and_not_fds_inputs(client, param, value, unit, si, si_unit):
    d = ok(post(client, param, 'ASSUMPTION', hyp(structured={'quantity': {'value': value, 'unit': unit}})))
    t = task(d, param)
    assert t['state'] == 'ASSUMPTION_PROPOSED' and t['tier'] == 'HYPOTHESIS_PROPOSED'
    cur = t['current']
    assert cur['normalized']['value'] == pytest.approx(si) and cur['normalized']['unit'] == si_unit
    assert cur['proposal']['value'] == value and cur['proposal']['unit'] == unit  # original preserved
    assert cur['assumption']['source_type'] == 'ENGINEERING_ASSUMPTION'
    assert cur['hypothesis']['usage'] == 'EXPLORATORY_HYPOTHESIS_NOT_APPROVED'
    assert cur['conversions'] and cur['conversions'][0]['si'].endswith(si_unit)
    c = t['consequences']
    assert 'Hipótese computacional proposta' in c['saved_as_pt'] and 'Não pode ser usado como entrada FDS' in c['fds_use_pt']
    pending = {x['code'] for x in t['checks'] if not x['done']}
    assert {'INDEPENDENT_REVIEW', 'PROFILE_MAPPING', 'GENERATOR_APPROVED'} <= pending
    assert param in d['readiness']['pending'] and d['resolved'] == 0
    r = row(d, param)
    assert r['proposal']['kind'] == 'ASSUMPTION' and not r['satisfied'] and r['gap_id'] == t['gap_id']


# 4 ------------------------------------------------------------------ structured holder geometry
def test_structured_holder_geometry_hypothesis_with_conversions_and_unpresumed_material(client):
    d = ok(post(client, 'sample_holder_substrate', 'ASSUMPTION', hyp(structured=HOLDER)))
    t = task(d, 'sample_holder_substrate')
    norm = t['current']['normalized']
    assert t['state'] == 'ASSUMPTION_PROPOSED' and norm['kind'] == 'STRUCTURED'
    assert norm['values']['thickness']['si_value'] == pytest.approx(.002)
    assert norm['values']['position']['si']['y'] == pytest.approx(-.005)
    assert norm['physical_validation'] == 'DATA_CONTRACT_ONLY'
    assert 'thermal_properties' not in norm['values']  # nothing presumed from the material name
    assert 'Placa plana' in norm['summary_pt']
    assert t['current']['assumption'] is None and t['current']['hypothesis']['usage'] == 'EXPLORATORY_HYPOTHESIS_NOT_APPROVED'
    bad = dict(HOLDER, thickness={'value': 2, 'unit': 's'})
    assert post(client, 'sample_holder_substrate', 'SOURCE', base(structured=bad)).status_code == 422
    missing = {k: v for k, v in HOLDER.items() if k != 'position'}
    assert post(client, 'sample_holder_substrate', 'SOURCE', base(structured=missing), change_reason='Teste de recusa').status_code == 422


# 5 ------------------------------------------------------------------ flow contract
def test_flow_parameters_follow_contract_and_never_overwrite_published_velocity(client):
    before = json.dumps(Services.catalog().experiment('BASS2-M1'), sort_keys=True)
    series = dict(FLOW, temporal_behavior='table', velocity_series=[
        {'time': {'value': 10, 'unit': 's'}, 'velocity': {'value': 9, 'unit': 'cm/s'}},
        {'time': {'value': 5, 'unit': 's'}, 'velocity': {'value': 9, 'unit': 'cm/s'}}])
    r = post(client, 'inlet_flow_profile', 'SOURCE', base(structured=series))
    assert r.status_code == 422 and 'crescentes' in r.text
    d = ok(post(client, 'inlet_flow_profile', 'SOURCE', base(structured=dict(FLOW, reference_velocity={'value': 10, 'unit': 'cm/s'}))))
    t = task(d, 'inlet_flow_profile')
    assert t['state'] == 'SOURCE_SUBMITTED' and t['current']['normalized']['values']['reference_velocity']['si_value'] == pytest.approx(.1)
    assert any('Difere da velocidade publicada' in w for w in t['current']['warnings'])
    assert json.dumps(Services.catalog().experiment('BASS2-M1'), sort_keys=True) == before


# 6 ------------------------------------------------------------------ pyrolysis
def test_pyrolysis_absence_is_identified_and_hypothesis_is_never_allowed(client):
    d = get(client)
    t = task(d, 'pmma_pyrolysis_properties')
    assert t['policy']['mode'] == 'DRAFT_ONLY' and not t['assumption_allowed']
    assert t['contract']['kind'] == 'MATERIAL'
    material = {'material_name': 'PMMA (conforme a fonte)', 'material_model': 'single_step_arrhenius', 'properties': [
        {'property': 'density', 'value': {'value': 1.19, 'unit': 'g/cm3'}, 'source': 'Referência de propriedades citada', 'validity': '20 °C, sólido'}]}
    assert post(client, 'pmma_pyrolysis_properties', 'ASSUMPTION', hyp(structured=material)).status_code == 422
    d = ok(post(client, 'pmma_pyrolysis_properties', 'SOURCE', base(structured=material)))
    t = task(d, 'pmma_pyrolysis_properties')
    comp = t['current']['normalized']['completeness']
    assert comp['present'] == ['density'] and len(comp['missing']) == 8 and 'Energia de ativação (E)' in comp['missing_pt']
    assert t['current']['normalized']['values']['properties'][0]['value']['si_value'] == pytest.approx(1190)
    assert not next(c for c in t['checks'] if c['code'] == 'CONTRACT_COMPLETE')['done']
    stage = next(s for s in d['summary']['stages'] if s['key'] == 'MATERIAL_MODEL_VALIDATION')
    assert stage['status'] == 'BLOCKED' and '1 de 9' in stage['detail_pt']
    # a wrong-dimension property is refused
    wrong = dict(material, properties=[dict(material['properties'][0], property='activation_energy')])
    assert post(client, 'pmma_pyrolysis_properties', 'SOURCE', base(structured=wrong), change_reason='Corrigir propriedade').status_code == 422
    # an explicit, non-approved exploratory draft is allowed and flagged
    d = ok(post(client, 'pmma_pyrolysis_properties', 'EXPLORATORY_DRAFT', hyp(structured=material), change_reason='Converter em rascunho exploratório'))
    t = task(d, 'pmma_pyrolysis_properties')
    assert t['state'] == 'EXPLORATORY_DRAFT' and t['current']['hypothesis']['usage'] == 'EXPLORATORY_DRAFT_NOT_APPROVED_NEVER_FDS_INPUT'
    assert any(c['code'] == 'HYPOTHESIS_PERMITTED' and not c['done'] for c in t['checks'])
    assert 'nunca será entrada FDS' in t['consequences']['saved_as_pt']


# 7 ------------------------------------------------------------------ recovery and continuity
def test_saved_proposals_are_recovered_and_reappear_in_preparation(client):
    ok(post(client, 'duct_geometry', 'SOURCE', base(structured={
        'shape': 'rectangular', 'width': {'value': 8, 'unit': 'cm'}, 'height': {'value': 8, 'unit': 'cm'}, 'length': {'value': 50, 'unit': 'cm'},
        'coordinate_system': 'Origem no centro da entrada; x ao longo do duto', 'sample_position': {'x': 10, 'y': 0, 'z': 0, 'unit': 'cm'},
        'sample_orientation': '+z', 'flow_direction': '+x'})))
    Services.reset()
    d = get(client)
    t = task(d, 'duct_geometry')
    assert t['current']['proposal']['structured']['width'] == {'value': 8, 'unit': 'cm'}
    prep = client.get('/api/experiments/BASS2-M1/simulation-preparation').json()['data']['guided_review']
    r = row(prep, 'duct_geometry')
    assert r['proposal']['origin_pt'] == 'Evidência complementar' and 'Retangular' in r['proposal']['summary_pt']
    assert r['tier'] == 'EVIDENCE_SUBMITTED' and not r['satisfied'] and r['checks']
    assert 'Solicite revisão' in r['next_step_pt']
    for x in prep['requirements']:
        if x['category'] == 'DATA_INPUT':
            assert x['satisfied'] == (x['parameter'] in prep['readiness']['satisfied'])
    assert {x['parameter'] for x in prep['requirements'] if x['category'] == 'MODEL_DEVELOPMENT'} == set(prep['profile']['additional_requirements'])
    # with full interpretation reviews (as in the real workspace), published values appear as verified originals
    exp = json.loads(json.dumps(Services.catalog().experiment('BASS2-M1')))
    for p in exp['parameters']:
        p['review_scope'] = 'FULL'
    full = g.view(exp, PID)
    published = row(full, 'thickness')
    assert published['tier'] == 'PUBLISHED_VERIFIED' and published['original']['value'] == 1 and published['satisfied']
    assert full['summary']['requirements_satisfied'] == len(full['readiness']['satisfied']) == 5
    # narrower duct than the published sample width is physically inconsistent
    narrow = post(client, 'duct_geometry', 'SOURCE', base(structured={**t['current']['proposal']['structured'], 'width': {'value': 1, 'unit': 'cm'}}),
                  change_reason='Teste de consistência')
    assert narrow.status_code == 422 and 'menor que a largura publicada' in narrow.text


# 8 ------------------------------------------------------------------ auditable edits
def test_edits_require_reason_keep_history_and_reset_review(client):
    ok(post(client, 'sample_length', 'SOURCE', base(structured={'quantity': {'value': 15, 'unit': 'cm'}})))
    ok(post(client, 'sample_length', 'REQUEST_REVIEW'))
    edit = base(structured={'quantity': {'value': 16, 'unit': 'cm'}})
    r = post(client, 'sample_length', 'SOURCE', edit)
    assert r.status_code == 422 and 'motivo da alteração' in r.text
    assert post(client, 'sample_length', 'SOURCE', base(structured={'quantity': {'value': 15, 'unit': 'cm'}}), change_reason='Sem mudança').status_code == 422
    d = ok(post(client, 'sample_length', 'SOURCE', edit, change_reason='Valor corrigido conforme tabela da fonte'))
    t = task(d, 'sample_length')
    cur = t['current']
    assert cur['revises_revision'] == t['history'][1]['revision'] and cur['change_reason'].startswith('Valor corrigido')
    assert {'field': 'value', 'before': 15, 'after': 16} in cur['diff']
    assert cur['review_state'] == 'PENDING' and t['state'] == 'SOURCE_SUBMITTED'
    assert [h['action'] for h in t['history']] == ['SOURCE', 'REQUEST_REVIEW', 'SOURCE']
    assert t['history'][0]['proposal']['value'] == 15  # previous record untouched


# 9 ------------------------------------------------------------------ original data untouched
def test_original_scientific_data_is_never_modified(client):
    data_files = sorted((REPO_ROOT / 'data').rglob('*.json'))
    digest = lambda: {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in data_files}
    before_files, before_exp = digest(), json.dumps(Services.catalog().experiment('BASS2-M1'), sort_keys=True)
    ok(post(client, 'sample_length', 'ASSUMPTION', hyp(structured={'quantity': {'value': 12, 'unit': 'cm'}})))
    ok(post(client, 'inlet_flow_profile', 'SOURCE', base(structured=dict(FLOW, reference_velocity={'value': 20, 'unit': 'cm/s'}))))
    ok(post(client, 'sample_length', 'REQUEST_REVIEW'))
    ok(post(client, 'sample_length', 'ACCEPT', author='Revisora Independente', notes='Conferi fonte, valor e unidade'))
    Services.reset()
    assert digest() == before_files
    assert json.dumps(Services.catalog().experiment('BASS2-M1'), sort_keys=True) == before_exp
    exp = Services.catalog().experiment('BASS2-M1')
    assert next(p for p in exp['parameters'] if p['parameter'] == 'airflow_velocity')['original']['value'] == 9


# 10 ------------------------------------------------------------------ M1 stays blocked
def test_m1_remains_blocked_without_approved_physical_model(client):
    ok(post(client, 'sample_length', 'ASSUMPTION', hyp(structured={'quantity': {'value': 12, 'unit': 'cm'}})))
    ok(post(client, 'sample_length', 'REQUEST_REVIEW'))
    d = ok(post(client, 'sample_length', 'ACCEPT', author='Revisora Independente', notes='Conferi fonte, valor e unidade'))
    t = task(d, 'sample_length')
    assert t['tier'] == 'REVIEWED' and t['state'] == 'UNDER_REVIEW' and d['resolved'] == 0
    assert not d['readiness']['can_execute'] and not d['readiness']['generator_approved']
    stages = {s['key']: s['status'] for s in d['summary']['stages']}
    assert stages['GENERATOR_VALIDATION'] == 'NOT_IMPLEMENTED' and stages['EXECUTION_AUTHORIZATION'] == 'BLOCKED'
    ladder = {x['key']: x for x in d['summary']['ladder']}
    assert ladder['REVIEWED']['count'] == 1 and ladder['MODEL_APPROVED']['count'] == 0
    # reviewed hypothesis does not count as a satisfied requirement
    assert ladder['REQUIREMENT_SATISFIED']['count'] == len(d['readiness']['satisfied']) and ladder['REQUIREMENT_SATISFIED']['of'] == 13
    assert 'sample_length' not in d['readiness']['satisfied']
    assert t['next_step']['category'] == 'PHYSICS'
    assert bridge.validate(t['current']['case_id'], t['current']['case_version'])['state'] == 'MODEL_NOT_APPROVED'
    assert client.post('/api/simulations', json={'case_id': t['current']['case_id']}).status_code == 422
    assert 'PROPANE' not in json.dumps(bridge.load(t['current']['case_id'], t['current']['case_version'])['content']['values'])


# ------------------------------------------------------------------ TEST mode isolation
def test_test_mode_is_isolated_labelled_and_never_scientific(client):
    fake = base(source='Ambiente de teste — fonte sintética', evidence='Ambiente de teste sem fonte', structured={'quantity': {'value': 3, 'unit': 'mm'}})
    assert post(client, 'sample_length', 'SOURCE', fake).status_code == 422  # scientific mode refuses test content
    assert get(client)['revision'] == 0
    r = post(client, 'sample_length', 'SOURCE', dict(fake, structured={'quantity': {'value': 3, 'unit': 's'}}), mode='TEST')
    assert r.status_code == 422  # types and units are still enforced in TEST mode
    d = ok(post(client, 'sample_length', 'SOURCE', fake, mode='TEST'))
    t = task(d, 'sample_length')
    assert d['mode'] == 'TEST' and t['current']['mode'] == 'TEST'
    assert any(f['code'] == 'TEST_MODE' for f in t['quality_flags'])
    assert t['consequences']['saved_as_pt'].startswith('TESTE')
    assert get(client)['revision'] == 0 and get(client)['tasks'][0]['current'] is None
    assert (var_dir() / workspace.TEST_ROOT / 'guided_reviews' / 'BASS2-M1').exists()
    assert not (var_dir() / 'guided_reviews' / 'BASS2-M1').exists()
    cid = t['current']['case_id']
    assert client.get(f'/api/cases/{cid}').status_code == 404  # never a scientific case
    with workspace.use_mode('TEST'):
        assert bridge.load(cid, 1)['content']['guided_review']['usage'] == 'TEST_ONLY_SYNTHETIC_NOT_SCIENTIFIC'
    ok(post(client, 'sample_length', 'REQUEST_REVIEW', mode='TEST'))
    d = ok(post(client, 'sample_length', 'ACCEPT', mode='TEST', author='Outra Pessoa', notes='Revisão de teste da interface'))
    assert task(d, 'sample_length')['state'] != 'RESOLVED_FOR_PROFILE'
    assert any(c['code'] == 'SCIENTIFIC_RECORD' and not c['done'] for c in task(d, 'sample_length')['checks'])


def test_legacy_test_like_and_duplicated_records_are_flagged_not_counted(client):
    exp = Services.catalog().experiment('BASS2-M1')
    d = get(client)
    log = g._load('BASS2-M1', PID)
    text = 'O ensaio utiliza amostras planas; o relatório menciona perdas de calor para o porta-amostra metálico.'
    for param, details, source in (('inlet_flow_profile', 'Ambiente de teste', 'ambiente de teste'),
                                   ('sample_holder_substrate', text, 'NASA/TM-20210011385, capítulo 5'),
                                   ('duct_geometry', text, 'NASA/TM-20210011385, capítulo 5')):
        g._append(log, 'BASS2-M1', PID, {'gap_id': task(d, param)['gap_id'], 'parameter': param, 'action': 'SOURCE', 'author': 'Pessoa',
                                        'state': 'SOURCE_SUBMITTED', 'review_state': 'PENDING', 'proposal_kind': 'SOURCE',
                                        'proposal': {'value': None, 'unit': 'n/a', 'details': details, 'source': source, 'location': 'p. 58',
                                                     'evidence': details, 'author': 'Pessoa', 'justification': '', 'limitations': ''},
                                        'normalized': {'kind': 'DOCUMENT', 'details': details, 'physical_validation': 'REQUIRES_SPECIALIST_SCHEMA'}})
    d = g.view(exp, PID)
    flow, holder = task(d, 'inlet_flow_profile'), task(d, 'sample_holder_substrate')
    assert flow['tier'] == 'TEST_CONTENT' and any(f['code'] == 'TEST_LIKE_CONTENT' for f in flow['quality_flags'])
    assert not next(c for c in flow['checks'] if c['code'] == 'DATA_PROVIDED')['done']
    assert {f['code'] for f in holder['quality_flags']} >= {'LEGACY_UNSTRUCTURED', 'DUPLICATE_ACROSS_GAPS'}
    assert holder['tier'] == 'EVIDENCE_SUBMITTED' and not next(c for c in holder['checks'] if c['code'] == 'CONTRACT_COMPLETE')['done']
    assert 'formulário estruturado' in holder['next_step']['text_pt']
    ladder = {x['key']: x['count'] for x in d['summary']['ladder']}
    assert ladder['EVIDENCE_SUBMITTED'] == 2 and d['summary']['gaps_test_content'] == 1
    assert d['history'][-1]['proposal']['details'] == text  # stored events untouched


# ------------------------------------------------------------------ preview, comparison gaps, contracts
def test_preview_is_deterministic_and_does_not_persist(client):
    pid = get(client)['tasks'][IDX['ambient_temperature']]['gap_id']
    def preview(body):
        r = client.post(f'{ROOT}/{pid}/preview', json=body)
        assert r.status_code == 200, r.text
        return r.json()['data']
    p = preview({'action': 'SOURCE', 'proposal': {'structured': {'quantity': {'value': 20, 'unit': 'kg'}}}})
    assert not p['ok'] and any(e['code'] == 'UNIT_DIMENSION' for e in p['errors'])
    p = preview({'action': 'ASSUMPTION', 'proposal': hyp(structured={'quantity': {'value': 25, 'unit': '°C'}})})
    assert p['ok'] and p['conversions'][0]['si'] == '298,15 K' and p['will_be_state'] == 'ASSUMPTION_PROPOSED'
    assert 'Temperatura ambiente' in p['consequences']['requirement_pt'] and 'Não pode ser usado' in p['consequences']['fds_use_pt']
    assert get(client)['revision'] == 0


def test_comparison_gaps_accept_only_non_approved_drafts_and_are_never_fds_inputs(client):
    d = get(client)
    t = task(d, 'measurement_uncertainty')
    assert t['role'] == 'COMPARISON_ONLY' and t['policy']['mode'] == 'DRAFT_ONLY'
    unc = {'uncertainties': [{'quantity': 'flame_spread_rate', 'type': 'standard', 'value': {'value': .005, 'unit': 'mm/s'}, 'method': 'Repetibilidade declarada'}]}
    assert post(client, 'measurement_uncertainty', 'ASSUMPTION', hyp(structured=unc)).status_code == 422
    d = ok(post(client, 'measurement_uncertainty', 'EXPLORATORY_DRAFT', hyp(structured=unc)))
    t = task(d, 'measurement_uncertainty')
    assert t['consequences']['fds_use_pt'].startswith('Não é entrada FDS em nenhum caso')
    assert any(c['code'] == 'COMPARISON_PIPELINE' for c in t['checks'])
    assert 'measurement_uncertainty' not in d['readiness']['pending'] + d['readiness']['satisfied']
    tracking = {'method': 'video_edge', 'observed_quantity': 'front_position', 'criterion': 'Borda luminosa acima do limiar definido',
                'analysis_start': {'value': 60, 'unit': 's'}, 'analysis_end': {'value': 30, 'unit': 's'}, 'calculation': 'linear_fit'}
    r = post(client, 'flame_front_tracking_method', 'EXPLORATORY_DRAFT', hyp(structured=tracking))
    assert r.status_code == 422 and 'posterior ao início' in r.text


def test_every_m1_gap_has_a_typed_contract_and_unknown_gaps_explain_missing_development():
    for param in g.ORDER:
        c = contracts.contract_for(param)
        assert c['kind'] != 'DOCUMENT' and c['fields'] and c['development_needed_pt']
        exported = contracts.export(c)
        for f in exported['fields']:
            if f['type'] == 'quantity':
                assert f['units'] and f['si_unit']
    generic = contracts.contract_for('unknown_thing')
    assert generic['kind'] == 'DOCUMENT' and generic['hypothesis'] == 'NOT_AVAILABLE'
    policy = g._policy(generic, None, True, 'FIDELITY_CONTEXT', bridge.profiles()[1])
    assert policy['mode'] == 'NOT_AVAILABLE' and 'contrato de dados' in policy['development_needed_pt'][0]


def test_new_material_units_convert_and_test_detector_avoids_nasa_test_wording():
    assert units.normalize(1.19, 'g/cm³').value == pytest.approx(1190)
    assert units.normalize(1.5, 'kJ/(kg·K)').value == pytest.approx(1500) and units.normalize(1, 'W/(m·K)').dimension == 'thermal_conductivity'
    assert units.normalize(130, 'kJ/mol').value == pytest.approx(130000) and units.normalize(1e10, 's⁻¹').dimension == 'rate'
    for legit in ('Teste M1 da Tabela 5.1', 'ensaio de teste BASS-II', 'NASA test matrix, test 1'):
        assert not contracts.looks_like_test(legit)
    for fake in ('ambiente de teste', 'Hipótese sintética para teste interno', 'teste', 'asdf', 'Lorem ipsum'):
        assert contracts.looks_like_test(fake)
