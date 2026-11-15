"""Drive the isolated BL-17 server through Chrome DevTools; never approves real data."""
import base64
import json
import time
import urllib.request
from pathlib import Path

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence'
pages = json.load(urllib.request.urlopen('http://127.0.0.1:9227/json'))
page = next(p for p in pages if p['type'] == 'page')
ws = connect(page['webSocketDebuggerUrl'], max_size=20_000_000, legacy=True)
seq = 0
errors = []
checks = []


def cdp(method, params=None):
    global seq
    seq += 1
    ws.send(json.dumps({'id':seq,'method':method,'params':params or {}}))
    while True:
        message=json.loads(ws.recv(timeout=20))
        if message.get('method')=='Runtime.exceptionThrown':
            errors.append(message['params'])
        if message.get('id')==seq:
            if 'error' in message:
                raise RuntimeError(message['error'])
            return message.get('result',{})


def js(code):
    result=cdp('Runtime.evaluate',{'expression':code,'returnByValue':True,'awaitPromise':True})
    if 'exceptionDetails' in result:
        raise RuntimeError(result['exceptionDetails'])
    return result.get('result',{}).get('value')


def wait(expression):
    until=time.monotonic()+15
    while time.monotonic()<until:
        if js('(()=>{try{return Boolean('+expression+')}catch{return false}})()'):
            return
        time.sleep(.1)
    raise AssertionError(expression+' timed out; '+str(js('document.body.innerText'))[:1000])


def click(label):
    js(f"(()=>{{const b=[...document.querySelectorAll('button,a')].find(e=>e.textContent.trim()==={json.dumps(label)});if(!b)throw Error('Missing control');b.click();}})()")


def fill(label,value):
    js(f"""(()=>{{const label=[...document.querySelectorAll('label')].find(e=>e.firstChild?.textContent==={json.dumps(label)});
    const el=label?.querySelector('input,textarea');if(!el)throw Error('Missing field');
    const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto,'value').set.call(el,{json.dumps(value)});el.dispatchEvent(new Event('input',{{bubbles:true}}));}})()""")


def check(label,expression):
    passed=bool(js(expression))
    checks.append({'check':label,'result':'PASS' if passed else 'FAIL'})
    if not passed:
        raise AssertionError(label)


def screenshot(name):
    png=cdp('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data']
    (EVIDENCE/name).write_bytes(base64.b64decode(png))


try:
    cdp('Runtime.enable');cdp('Page.enable')
    cdp('Emulation.setDeviceMetricsOverride',{'width':1280,'height':960,'deviceScaleFactor':1,'mobile':False})
    cdp('Page.navigate',{'url':'http://127.0.0.1:18017/importar'})
    wait("document.querySelector('input[type=file]')")
    root=cdp('DOM.getDocument')['root']['nodeId']
    node=cdp('DOM.querySelector',{'nodeId':root,'selector':'input[type=file]'})['nodeId']
    cdp('DOM.setFileInputFiles',{'nodeId':node,'files':[str(ROOT/'sources/NASA-TM-20210011385.pdf')]})
    wait("document.body.innerText.includes('Abrir resumo completo')")
    check('Importação real do PDF local sem Gemini, preservando nove conferidos',"document.body.innerText.includes('9 parâmetros conferidos')")
    cdp('Page.navigate',{'url':'http://127.0.0.1:18017/documentos/NASA-TM-20210011385/analise'})
    wait("document.body.innerText.includes('Resolver 12 pendências') && document.body.innerText.includes('Gerador sem aprovação')")
    check('Resumo: nove conferidos e bloqueio físico antes de iniciar',"document.body.innerText.includes('9 parâmetros conferidos') && document.body.innerText.includes('Execução bloqueada')")
    screenshot('BL-17_resumo_desktop.png')
    click('Resolver 12 pendências')
    wait("document.querySelector('[role=dialog]')?.innerText.includes('Pendência 1/12')")
    check('Uma pendência principal com cinco explicações',"document.querySelectorAll('.task-title').length===1 && ['A. O que','B. Por que','C. O que','D. Como','E. Qual'].every(t=>document.querySelector('[role=dialog]').innerText.includes(t))")
    screenshot('BL-17_wizard_desktop.png')
    click('Registrar informação científica')
    fill('Responsável pelo registro','TESTE ISOLADO BL-17')
    fill('Valor','15');fill('Unidade','cm')
    fill('Fonte científica ou referência bibliográfica','FIXTURE DE INTERFACE — SEM VALIDADE CIENTÍFICA')
    fill('Página ou localização','fixture p. 55')
    fill('Evidência da fonte','Dado sintético exclusivo para testar persistência; não usar como evidência científica.')
    click('Enviar evidência complementar')
    wait("document.querySelector('[role=dialog]').innerText.includes('Evidência enviada') && document.querySelector('[role=dialog]').innerText.includes('Registro salvo no servidor')")
    check('Proposta registrada sem resolução automática',"document.querySelector('progress').value===0 && document.querySelector('[role=dialog]').innerText.includes('Registro salvo no servidor')")
    click('Próxima');wait("document.querySelector('[role=dialog]').innerText.includes('Pendência 2/12')")
    click('Anterior');wait("document.querySelector('[role=dialog]').innerText.includes('Pendência 1/12')")
    click('Registrar informação científica')
    check('Resposta preservada ao retornar',"[...document.querySelectorAll('label')].find(e=>e.firstChild?.textContent==='Valor').querySelector('input').value==='15'")
    click('Próxima');wait("document.querySelector('[role=dialog]').innerText.includes('Pendência 2/12')")
    click('Voltar ao resumo');wait("!document.querySelector('[role=dialog]')")
    cdp('Page.reload');wait("document.body.innerText.includes('Retomar revisão')")
    click('Retomar revisão');wait("document.querySelector('[role=dialog]')?.innerText.includes('Pendência 2/12')")
    check('Retomada do servidor após recarregar a página',"document.querySelector('[role=dialog]').innerText.includes('Pendência 2/12')")
    cdp('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
    wait("innerWidth===390")
    check('Modal móvel sem transbordamento horizontal',"document.querySelector('.guided-modal').getBoundingClientRect().width<=390 && document.documentElement.scrollWidth<=390")
    check('Navegação móvel permanece visível',"(()=>{const r=document.querySelector('.guided-footer').getBoundingClientRect();return r.top>=0 && r.bottom<=844;})()")
    screenshot('BL-17_wizard_mobile.png')
    click('Consultar resumo das decisões')
    wait("document.querySelector('[role=dialog]').innerText.includes('Decisões registradas')")
    check('Resumo das decisões mantém PMMA bloqueado',"document.querySelector('[role=dialog]').innerText.includes('Gerador sem aprovação') && document.querySelector('[role=dialog]').innerText.includes('Execução bloqueada')")
    click('Voltar ao resumo');wait("!document.querySelector('[role=dialog]')")
    cdp('Page.navigate',{'url':'http://127.0.0.1:18017/experimentos/BASS2-M1/preparar'})
    wait("document.body.innerText.includes('Retomar revisão') && document.body.innerText.includes('Gerador sem aprovação')")
    check('Preparação consome decisões sem quatro etapas nem novo formulário',"!document.querySelector('nav[aria-label=\"Etapas de preparação\"]') && !document.querySelector('input') && document.body.innerText.includes('1 de 12 com registro')")
    check('M1 nunca oferece executar propano como seu modelo',"![...document.querySelectorAll('button')].some(b=>b.innerText.includes('Executar'))")
    cdp('Emulation.setDeviceMetricsOverride',{'width':1280,'height':960,'deviceScaleFactor':1,'mobile':False})
    cdp('Page.navigate',{'url':'http://127.0.0.1:18017/experimentos/BASS2-M1'})
    wait("document.querySelectorAll('.readiness > li').length===5")
    check('Cinco dimensões compactas com ação para cada bloqueio',"[...document.querySelectorAll('.readiness > li.warn,.readiness > li.bad')].every(li=>li.querySelector('button,a'))")
    click('Resolver pendências');wait("document.querySelector('[role=dialog]')")
    check('Ação de cobertura abre diretamente a revisão guiada',"document.querySelector('[role=dialog]').innerText.includes('Pendência 2/12')")
    check('Sem exceção JavaScript no navegador',json.dumps(not errors))
finally:
    (EVIDENCE/'BL-17_browser_checks.json').write_text(json.dumps({'checks':checks,'javascript_errors':errors,'workspace':'tmp/bl17-browser-workspace-* (isolated)','scientific_validity':'SYNTHETIC_UI_TEST_ONLY'},ensure_ascii=False,indent=2),encoding='utf-8')
    ws.close()
print(json.dumps(checks,ensure_ascii=True,indent=2))
