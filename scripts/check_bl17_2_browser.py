"""BL-17.2: drive the isolated server (scripts/bl17_browser_server.py) through Chrome DevTools.

Synthetic data is entered ONLY in the interface TEST mode; the scientific-mode step only checks
that test-like text is refused before sending. Never approves anything, never runs FDS.
Requires a Chrome instance with --remote-debugging-port=9227 and a profile inside tmp/.
"""
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence'
BASE = 'http://127.0.0.1:18017'
pages = json.load(urllib.request.urlopen('http://127.0.0.1:9227/json'))
page = next(p for p in pages if p['type'] == 'page')
ws = connect(page['webSocketDebuggerUrl'], max_size=20_000_000)
seq, errors, checks = 0, [], []


def cdp(method, params=None):
    global seq
    seq += 1
    ws.send(json.dumps({'id': seq, 'method': method, 'params': params or {}}))
    while True:
        message = json.loads(ws.recv(timeout=30))
        if message.get('method') == 'Runtime.exceptionThrown':
            errors.append(message['params'])
        if message.get('id') == seq:
            if 'error' in message:
                raise RuntimeError(message['error'])
            return message.get('result', {})


def js(code):
    result = cdp('Runtime.evaluate', {'expression': code, 'returnByValue': True, 'awaitPromise': True})
    if 'exceptionDetails' in result:
        raise RuntimeError(json.dumps(result['exceptionDetails'])[:800])
    return result.get('result', {}).get('value')


def wait(expression, timeout=15):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if js('(()=>{try{return Boolean(' + expression + ')}catch{return false}})()'):
            return
        time.sleep(.15)
    raise AssertionError(expression + ' timed out; ' + str(js('document.body.innerText'))[:1500])


SCOPE = "(document.querySelector('[role=dialog]')||document.body)"


def click(label, scope=SCOPE):
    js(f"(()=>{{const b=[...{scope}.querySelectorAll('button,a')].find(e=>e.textContent.trim()==={json.dumps(label)});if(!b)throw Error('Missing control '+{json.dumps(label)});b.click();}})()")


def fill(prefix, value, scope=SCOPE):
    js(f"""(()=>{{const label=[...{scope}.querySelectorAll('label')].find(e=>e.textContent.trim().startsWith({json.dumps(prefix)}) && e.querySelector('input,textarea,select'));
    const el=label?.querySelector('input,textarea,select');if(!el)throw Error('Missing field '+{json.dumps(prefix)});
    const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:el.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto,'value').set.call(el,{json.dumps(value)});
    el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{{bubbles:true}}));}})()""")


def text(scope=SCOPE):
    return f"{scope}.innerText"


def check(label, expression):
    passed = bool(js(expression))
    checks.append({'check': label, 'result': 'PASS' if passed else 'FAIL'})
    print(('PASS ' if passed else 'FAIL ') + label)
    if not passed:
        raise AssertionError(label)


def screenshot(name):
    png = cdp('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})['data']
    (EVIDENCE / name).write_bytes(base64.b64decode(png))


status = 'PASS'
try:
    cdp('Runtime.enable'); cdp('Page.enable')
    cdp('Emulation.setDeviceMetricsOverride', {'width': 1280, 'height': 960, 'deviceScaleFactor': 1, 'mobile': False})
    cdp('Page.navigate', {'url': BASE + '/experimentos/BASS2-M1/preparar'})
    js("localStorage.clear()")
    cdp('Page.reload')
    wait(f"{text('document.body')}.includes('Requisitos do perfil, campo a campo')")
    check('Preparação mostra requisitos campo a campo e a escada dos 5 estágios',
          "['Preparação documental','Construção de hipóteses','Validação do modelo de material','Validação do gerador FDS','Autorização de execução'].every(t=>document.body.innerText.includes(t))")
    check('Execução do experimento bloqueada com motivo explícito',
          "[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Executar simulação deste experimento')?.disabled===true && document.body.innerText.includes('Nenhuma combustão prescrita de propano')")
    screenshot('BL-17_2_preparacao_desktop.png')

    # Scientific mode refuses test-like content before sending.
    click('Abrir requisito: Comprimento da amostra', 'document.body')
    wait(f"{text()}.includes('Pendência 1/12')")
    click('Registrar evidência científica')
    fill('Comprimento da amostra', '15'); fill('Unidade (comprimento)', 'cm')
    fill('Fonte científica ou referência bibliográfica', 'ambiente de teste da interface')
    fill('Página ou localização', 'p. 1'); fill('Evidência da fonte', 'ambiente de teste da interface')
    wait(f"{text()}.includes('parece conteúdo de teste')")
    check('Modo científico: “ambiente de teste” recusado antes do envio, com conversão 15 cm = 0,15 m visível',
          f"{text()}.includes('0,15 m') && [...document.querySelectorAll('[role=dialog] button.primary')].find(b=>b.textContent.includes('Enviar evidência'))?.disabled===true")
    js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))")  # sem autor: nada vai ao servidor
    wait("!document.querySelector('[role=dialog]')")

    # Interface TEST mode.
    js("[...document.querySelectorAll('label')].find(l=>l.textContent.includes('Modo de teste da interface')).querySelector('input').click()")
    wait(f"{text('document.body')}.includes('MODO DE TESTE')")
    check('Modo de teste identificado na página', f"{text('document.body')}.includes('Nada registrado aqui vira dado NASA')")
    click('Abrir requisito: Suporte/substrato da amostra', 'document.body') if js(
        "[...document.querySelectorAll('button')].some(b=>b.textContent.trim()==='Abrir requisito: Suporte/substrato da amostra')") else js(
        "[...document.querySelectorAll('button')].find(b=>b.textContent.startsWith('Abrir requisito: ') && /suporte|substrato/i.test(b.textContent)).click()")
    wait(f"{text()}.includes('Pendência 2/12')")
    click('Preparar hipótese exploratória')
    wait(f"{text()}.includes('Forma geométrica do suporte')")
    click('Preencher com valores sintéticos (TESTE)')
    wait(f"{text()}.includes('Pronto para enviar')")
    check('Geometria estruturada: posição x/y/z, sistema de coordenadas e consequência para o FDS visíveis',
          f"{text()}.includes('Sistema de coordenadas') && {text()}.includes('Uso no FDS') && {text()}.includes('Não pode ser usado como entrada FDS')")
    screenshot('BL-17_2_wizard_geometria_desktop.png')
    click('Enviar proposta de hipótese')
    wait(f"{text()}.includes('Registro salvo no servidor como')")
    check('Hipótese de geometria salva no modo TESTE, sem resolução automática',
          f"{text()}.includes('Registro atual') && {text()}.includes('TESTE') && document.querySelector('[role=dialog] progress').value===0")

    # Pyrolysis: exploratory draft, missing properties identified.
    click('Consultar resumo das decisões')
    wait(f"{text()}.includes('Decisões registradas')")
    js("[...document.querySelectorAll('[role=dialog] button')].find(b=>/pirólise/i.test(b.textContent) && !b.textContent.startsWith('Abrir requisito'))?.click()")
    wait(f"{text()}.includes('Pendência 9/12')")
    click('Preparar hipótese exploratória')
    wait(f"{text()}.includes('Salvar rascunho exploratório não aprovado')")
    click('Preencher com valores sintéticos (TESTE)')
    wait(f"{text()}.includes('Propriedades ainda ausentes')")
    check('Pirólise: ausência de propriedades identificada e rascunho explicitamente não aprovado',
          f"{text()}.includes('Energia de ativação') && {text()}.includes('NÃO APROVADO')")
    click('Salvar rascunho exploratório não aprovado')
    wait(f"{text()}.includes('Registro salvo no servidor como')")

    # Reload: persisted and shown in preparation; edit with history.
    click('Voltar ao resumo')
    wait("!document.querySelector('[role=dialog]')")
    cdp('Page.reload')
    wait(f"{text('document.body')}.includes('Requisitos do perfil, campo a campo') && {text('document.body')}.includes('MODO DE TESTE')")
    check('Propostas recuperadas após recarregar e exibidas na preparação (origem, conteúdo, autor)',
          f"{text('document.body')}.includes('Hipótese proposta') && {text('document.body')}.includes('Rascunho exploratório') && {text('document.body')}.includes('Pessoa de teste')")
    js("[...document.querySelectorAll('button')].find(b=>b.textContent.startsWith('Abrir requisito: ') && /suporte|substrato/i.test(b.textContent)).click()")
    wait(f"{text()}.includes('Editar proposta')")
    click('Editar proposta')
    wait(f"{text()}.includes('Motivo da alteração')")
    fill('Comprimento do suporte', '7')
    fill('Motivo da alteração', 'TESTE — alteração sintética do comprimento')
    wait(f"{text()}.includes('campo(s) alterado(s)') && {text()}.includes('Pronto para enviar')")
    click('Enviar proposta de hipótese')
    wait(f"{text()}.includes('Registro salvo no servidor como')")
    check('Edição auditável: motivo e diferença registrados no histórico',
          "(()=>{const d=document.querySelector('[role=dialog] details.tech');d.open=true;return d.innerText.includes('Motivo da alteração') && d.innerText.includes('→')})()")

    # Mobile viewport.
    cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(.4)
    check('Viewport móvel 390 px: sem rolagem horizontal da página do assistente',
          "document.querySelector('.guided-modal').scrollWidth<=document.querySelector('.guided-modal').clientWidth+1")
    screenshot('BL-17_2_wizard_mobile.png')
    check('Sem exceções JavaScript durante o roteiro', 'true' if not errors else 'false')
except Exception as exc:  # registra a falha com a etapa
    status = 'FAIL'
    checks.append({'check': 'roteiro', 'result': 'FAIL', 'detail': str(exc)[:1500]})
    print('FAIL', str(exc)[:1500])
finally:
    (EVIDENCE / 'BL-17_2_browser_checks.json').write_text(json.dumps(
        {'status': status, 'mode': 'isolated server + interface TEST mode', 'checks': checks, 'js_exceptions': len(errors)},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
sys.exit(0 if status == 'PASS' else 1)
