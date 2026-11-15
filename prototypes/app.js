/* Telas do protótipo. Roteamento por hash; dados reais de BASS2-M1 em window.FL_DATA. */
(function () {
  const { esc, Icon, StatusBadge, PageHeader, ScientificValue, DataCategoryPanel, MissingDataNotice, AssistantMessage, TelemetryTable, ReadinessGate, AppShell } = window.FL;
  const D = window.FL_DATA;
  const NAV = [
    { to: "/", text: "Visão geral", icon: "layout" },
    { label: "Biblioteca científica" },
    { to: "/biblioteca", text: "BASS-II", icon: "book" },
    { to: "/ensaio/m1", text: "Ensaio M1", sub: true },
    { label: "Ferramentas" },
    { to: "/assistente", text: "Assistente científico", icon: "bot" },
    { to: "/telemetria", text: "Telemetria", icon: "activity" },
    { to: "/fds", text: "Validação física (FDS)", icon: "flame" },
    { to: "/fontes", text: "Fontes e metodologia", icon: "info" },
  ];
  const link = (to, text, cls = "btn") => `<a class="${cls}" href="#${to}">${text}</a>`;
  const ntrs = D.doc.url;

  /* ---------- Visão geral ---------- */
  function overview() {
    const conf = D.params.filter((p) => p.status === "CONFERIDO_FONTE").length;
    const layers = [
      { icon: "book", t: "Dados científicos", s: "IMPLEMENTADO", txt: `<b>${conf} de ${D.params.length}</b> registros de M1 conferidos na fonte · <b>${D.gaps.length}</b> lacunas declaradas · evidências com página e tabela.`, to: "/ensaio/m1", cta: "Abrir ficha M1" },
      { icon: "bot", t: "Assistente científico", s: "IMPLEMENTADO", txt: "Backend com verificador determinístico (V1–V8), abstenção e modos live/cache/off. Testado com provedor simulado e smoke real do Gemini.", to: "/assistente", cta: "Ver respostas gravadas" },
      { icon: "activity", t: "Telemetria (protótipo físico)", s: "PENDENTE", txt: "Arduino Uno + BMP180 + 2 potenciômetros no Wokwi. <b>Nenhum CSV real</b> no repositório até agora.", to: "/telemetria", cta: "Ver estrutura" },
      { icon: "flame", t: "Validação física (FDS)", s: "BLOQUEADO", txt: "FDS/Smokeview verificados em <b>caso genérico</b>. Reprodução do M1 bloqueada por lacunas e gates G1, G2 e G4.", to: "/fds", cta: "Ver prontidão" },
    ];
    return `
      ${PageHeader({ title: "Visão geral", lede: "Estado real das quatro camadas do FlameLab e o caminho até o ensaio M1. Cada selo reflete o que existe hoje no projeto, não o que está planejado." })}
      <div class="grid cols-4">${layers.map((l) => `
        <article class="card layer-card"><h3>${Icon(l.icon)}${l.t}</h3>${StatusBadge(l.s)}<p class="stat">${l.txt}</p>${link(l.to, l.cta)}</article>`).join("")}
      </div>
      <h2 style="margin:28px 0 12px;font-size:16px">Caminho até o ensaio M1</h2>
      <ol class="path" style="padding:0;margin:0">
        <li>1 · Fonte catalogada<br><span class="num" style="font-size:12px">${esc(D.doc.id)}</span><br>${StatusBadge("FONTE_CATALOGADA")}</li>
        <li>2 · Parâmetros conferidos<br>${conf} de ${D.params.length} · revisão humana<br>${StatusBadge("VALIDADO", "Conferidos")}</li>
        <li>3 · Lacunas resolvidas<br>${D.gaps.length} abertas<br>${StatusBadge("PENDENTE")}</li>
        <li>4 · Modelo físico aprovado<br>Nenhum para BASS-II<br>${StatusBadge("BLOQUEADO")}</li>
        <li>5 · Comparação com o observado<br>Depende do passo 4<br>${StatusBadge("BLOQUEADO")}</li>
      </ol>
      <div class="cta-card" style="margin-top:24px"><div><h2>BASS-II · Ensaio M1</h2><p>Condições de entrada, resultados observados e lacunas declaradas, cada valor com a página e a tabela de origem.</p></div>${link("/ensaio/m1", "Abrir ficha do ensaio", "btn primary")}</div>`;
  }

  /* ---------- Biblioteca (mínima: só um ensaio real) ---------- */
  function library() {
    return `
      ${PageHeader({ crumbs: ["Biblioteca científica", "BASS-II"], title: "BASS-II — Biblioteca científica", lede: "Investigação PSI-25. Por enquanto, apenas o ensaio M1 foi curado; busca textual e comparação lado a lado ainda não existem." })}
      <article class="card card-pad" style="display:flex;flex-wrap:wrap;gap:14px;justify-content:space-between;align-items:center">
        <div><h2 style="font-size:16px">Ensaio M1 · PMMA · fluxo oposto</h2><p class="ref-loc" style="margin-top:4px">${esc(D.doc.id)} · Tabela 5.1</p><div class="meta" style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">${StatusBadge("FONTE_CATALOGADA")}${StatusBadge("LACUNAS")}</div></div>
        ${link("/ensaio/m1", "Abrir ficha", "btn primary")}
      </article>`;
  }

  /* ---------- Ficha M1 (tela prioritária) ---------- */
  function m1() {
    const cond = D.params.filter((p) => p.role !== "OBSERVAVEL");
    const res = D.params.filter((p) => p.role === "OBSERVAVEL");
    const keyGap = { duct_geometry: "G1", pmma_pyrolysis_properties: "G2" };
    const gaps = [...D.gaps].sort((a, b) => (keyGap[b.key] ? 1 : 0) - (keyGap[a.key] ? 1 : 0));
    const idx = (list) => list.map((p) => D.params.indexOf(p));
    return `
      ${PageHeader({
        crumbs: ["Biblioteca científica", "BASS-II", "Ensaio M1"],
        title: "BASS-II — Ensaio M1",
        lede: `Referência: <span class="num">${esc(D.doc.id)} · Tabela 5.1</span>. Os valores abaixo foram copiados do dataset versionado; abra “Fonte” para ver o trecho literal.`,
        badges: `${StatusBadge("FONTE_CATALOGADA")}${StatusBadge("LACUNAS")}<a class="ref-toggle" href="${esc(ntrs)}" target="_blank" rel="noopener">Fonte original (NTRS)${Icon("ext")}</a>`,
        actions: link("/assistente", `${Icon("bot")}Consultar no assistente`, "btn primary"),
      })}
      <div class="m1-layout">
        ${DataCategoryPanel({ cls: "panel-conditions", icon: "flask", title: "A. Condições de entrada", count: `${cond.length} registros`, note: "Condições do ensaio como informadas na fonte. Não são resultados.", body: `<ul class="sv-list">${cond.map((p) => ScientificValue(p, D.doc, D.params.indexOf(p))).join("")}</ul>` })}
        ${DataCategoryPanel({ cls: "panel-results", icon: "eye", title: "B. Resultados observados", count: `${res.length} registros`, note: "Resultados medidos pela NASA. <b>Nunca</b> servem de entrada ou alvo de calibração de modelo.", body: `<ul class="sv-list">${res.map((p) => ScientificValue(p, D.doc, D.params.indexOf(p))).join("")}</ul>` })}
        <div class="full">${DataCategoryPanel({
          cls: "panel-gaps", icon: "alert", title: "C. Lacunas declaradas", count: `${D.gaps.length} lacunas · todas impedem a reprodução no FDS`,
          note: "Dados procurados e <b>ausentes na fonte</b>. Permanecem como lacuna; não há estimativa nem preenchimento silencioso.",
          body: `<ul class="gap-list">${gaps.map((g) => MissingDataNotice(g, { key: !!keyGap[g.key], gate: keyGap[g.key] || "" })).join("")}</ul>` })}</div>
      </div>`;
  }

  /* ---------- Assistente ---------- */
  const ANSWERS = [
    {
      id: "pressao", q: "Qual era a pressão no ensaio M1?", hint: "Dado ausente · execução real 14/11",
      a: { state: "DADO_AUSENTE", mode: "LIVE", intro: "", approved: [{ type: "LIMITACAO", text: "A pressão no ensaio M1 está ausente no corpus curado e não é informada no capítulo 5 para o ensaio BASS2-M1.", evidence: ["GAP-BASS2-M1-ambient_pressure"] }], blocked: [], provenance: "Execução real (Gemini, modo LIVE) sobre o dataset real em 14/11/2026 — docs/evidence/smoke_real_dataset_20261114T191858Z.json. Nenhum número publicado." },
    },
    {
      id: "marte", q: "Qual seria a propagação da chama na atmosfera de Marte?", hint: "Extrapolação bloqueada · evidência sintética",
      a: { state: "EXTRAPOLACAO", mode: "LIVE", synthetic: true, approved: [{ type: "LIMITACAO", text: "As evidências do ensaio TEST-01 não incluem condições de atmosfera de Marte, limitando previsões numéricas para esse cenário.", evidence: ["REC-TEST-01.material"] }], blocked: [{ type: "OBSERVACAO", text: "No ensaio TEST-01, o material utilizado foi PMMA.", reason: "V8_EXTRAPOLATION_CLAIM_TYPE" }, { type: "OBSERVACAO", text: "No ensaio TEST-01, a velocidade do ar foi de 9 cm/s.", reason: "V8_EXTRAPOLATION_CLAIM_TYPE" }], provenance: "Execução real (Gemini) sobre evidência SINTÉTICA TEST-01 — docs/evidence/smoke_gemini_20261114T191825Z.json. Não valida conteúdo BASS-II. Nenhuma estimativa numérica para Marte foi produzida." },
    },
    {
      id: "material", q: "Qual material foi utilizado e qual sua espessura?", hint: "Respaldado · evidência sintética",
      a: { state: "RESPALDADO", mode: "LIVE", synthetic: true, approved: [{ type: "OBSERVACAO", text: "No ensaio TEST-01, o material utilizado foi PMMA.", evidence: ["REC-TEST-01.material"] }, { type: "OBSERVACAO", text: "No ensaio TEST-01, a espessura da amostra foi de 1 mm.", evidence: ["REC-TEST-01.thickness"] }], blocked: [], provenance: "Execução real (Gemini) sobre evidência SINTÉTICA TEST-01 — mesmo arquivo de smoke. Serve para mostrar o estado “respaldado”; não é resposta sobre M1." },
    },
  ];
  function assistant(sel = "pressao") {
    const cur = ANSWERS.find((x) => x.id === sel) || ANSWERS[0];
    return `
      ${PageHeader({ crumbs: ["Assistente científico"], title: "Assistente científico", lede: "Responde só com trechos delimitados da fonte; um verificador determinístico bloqueia o que não tem suporte. A IA interpreta, não simula o fogo." })}
      <div class="context-bar">${Icon("book")}<span>Fonte ativa:</span><span class="mono">BASS-II · Ensaio M1 · ${esc(D.doc.id)}</span><span style="margin-left:auto">${StatusBadge("DEMONSTRATIVO", "Respostas gravadas")}</span></div>
      <div class="assist-layout">
        <section class="card" aria-label="Conversa">
          <div class="chat" id="chat" aria-live="polite">
            <div class="msg-user">${esc(cur.q)}</div>
            ${AssistantMessage(cur.a)}
          </div>
          <div class="composer"><input disabled aria-label="Pergunta" placeholder="Ligar ao POST /api/ask na implementação real" /><button class="btn" disabled>${Icon("send")}Enviar</button></div>
        </section>
        <aside style="display:grid;gap:18px">
          <section class="card"><div class="panel-head"><h2>Consultas gravadas</h2></div><div class="suggest">${ANSWERS.map((x) => `<button data-ask="${x.id}" aria-pressed="${x.id === cur.id}">${esc(x.q)}<small>${esc(x.hint)}</small></button>`).join("")}</div></section>
          <section class="card"><div class="panel-head"><h2>Estados da resposta</h2></div><div class="state-legend">
            <div>${StatusBadge("RESPALDADO")}<br>Suporte documental e citação.</div>
            <div>${StatusBadge("DADO_AUSENTE")}<br>A fonte não informa o dado.</div>
            <div>${StatusBadge("EXTRAPOLACAO")}<br>Exige inferência ou número sem suporte.</div>
            <div>${StatusBadge("INDISPONIVEL")}<br>Fonte não consultada (modo off/cache sem entrada). Sem execução gravada.</div>
          </div></section>
        </aside>
      </div>`;
  }

  /* ---------- Telemetria ---------- */
  function telemetry() {
    const cols = ["TEMPO_S", "PRESSAO_KPA", "TEMP_C", "O2_PCT", "FLUXO_CMS"];
    return `
      ${PageHeader({ crumbs: ["Telemetria"], title: "Telemetria do protótipo", lede: "Ponte entre o protótipo físico/virtual e os dados exportados. Não indica que o sensor mede propriedades que ele não mede.", badges: `${StatusBadge("SIMULACAO_WOKWI")}${StatusBadge("PENDENTE", "Sem série carregada")}` })}
      <div class="grid cols-2">
        <section class="card"><div class="panel-head"><h2>${Icon("cpu")}Protótipo</h2></div><div class="card-pad"><dl class="kv">
          <dt>Hardware</dt><dd>Arduino Uno + BMP180 + 2 potenciômetros</dd>
          <dt>Ambiente</dt><dd>Simulação Wokwi</dd>
          <dt>Sensor</dt><dd>BMP180 mede pressão e temperatura. Os demais canais vêm dos potenciômetros (entradas ajustáveis, não sensores de O₂ ou de fluxo).</dd>
          <dt>Código e ligações</dt><dd>Referência ainda não vinculada neste protótipo</dd>
        </dl></div></section>
        <section class="card"><div class="panel-head"><h2>Estrutura do CSV</h2></div><div class="card-pad" style="display:grid;gap:10px"><div class="csv-head">${cols.join(",")}</div><p style="font-size:13.5px;color:var(--text-secondary)">Uma linha por amostra. O arquivo é gerado pelo Wokwi; a tela só exibe linhas realmente exportadas.</p></div></section>
        <section class="card" style="grid-column:1/-1"><div class="panel-head"><h2>Amostras exportadas</h2><span class="count">0 linhas</span></div><div class="card-pad">${TelemetryTable(cols, [])}</div></section>
      </div>`;
  }

  /* ---------- Prontidão FDS ---------- */
  function fds() {
    const by = (keys) => D.gaps.filter((g) => keys.includes(g.key)).map((g) => esc(g.label)).join("; ");
    const gates = [
      { id: "G0-env", name: "Ambiente", state: "VERIFICADO", criterion: "FDS verificado em máquina com acesso ao repositório.", reason: "FDS 6.11.1, Smokeview 6.11.2 e FFmpeg 9.0.2 executados nesta máquina (registro no README e em docs/evidence)." },
      { id: "G1", name: "Geometria e condições", state: "BLOQUEADO", criterion: "Cada dimensão/condição do caso com evidência ou hipótese justificada.", reason: `Ausentes na fonte: ${by(["duct_geometry", "sample_length", "sample_holder_substrate", "inlet_flow_profile", "anemometer_location", "ambient_pressure", "ambient_temperature", "ignition_procedure"])}.` },
      { id: "G2", name: "Material", state: "BLOQUEADO", criterion: "Propriedades de pirólise/ignição do PMMA com fonte e revisão.", reason: `Ausente na fonte: ${by(["pmma_pyrolysis_properties"])}.` },
      { id: "G3", name: "Execução", state: "DEMONSTRATIVO", stateLabel: "Só caso genérico", criterion: ".fds, versão, log completo e saídas guardadas.", reason: "Há execuções reais do caso de integração genérico (queimador de propano em sala). Nenhuma do M1." },
      { id: "G4", name: "Comparação", state: "BLOQUEADO", criterion: "Observável calculado comparável ao da NASA, com erro, incerteza e método documentados.", reason: `Depende de G2. Ausentes: ${by(["measurement_uncertainty", "flame_front_tracking_method"])}.` },
      { id: "G5", name: "Alteração", state: "FUTURO", criterion: "Uma variável alterada com rastreabilidade.", reason: "Não iniciado." },
    ];
    const blocks = D.gaps.filter((g) => g.blocks.includes("FDS_REPRODUCTION"));
    return `
      ${PageHeader({ crumbs: ["Validação física (FDS)"], title: "Prontidão para simulação FDS", lede: "O FDS calcula o comportamento físico. A IA não substitui o modelo físico." })}
      <div class="verdict" role="status">${Icon("ban")}<div><h2>Não pronto para reprodução fiel do ensaio M1</h2><p>Parâmetros críticos continuam ausentes na fonte. A execução está desabilitada para o M1.</p></div><div style="margin-left:auto"><button class="btn" disabled aria-disabled="true">${Icon("lock")}Executar simulação (indisponível)</button></div></div>
      <div class="m1-layout">
        <section class="card"><div class="panel-head"><h2>Gates</h2></div><ol class="sv-list" style="padding:0;margin:0">${gates.map(ReadinessGate).join("")}</ol></section>
        <section class="card panel-gaps"><div class="panel-head"><h2>${Icon("alert")}Bloqueios identificados</h2><span class="count">${blocks.length}</span></div><ul class="gap-list">${blocks.map((g) => `<li class="gap"><div class="gap-title">${Icon("alert")}${esc(g.label)}</div><p>${esc(g.why)}</p></li>`).join("")}</ul></section>
        <section class="proof full"><div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:6px">${StatusBadge("GENERICO", "Prova de conceito em ambiente genérico")}</div><p><b>Não representa reprodução do ensaio M1.</b> Qualquer visualização do Smokeview mostrada aqui vem do caso de integração <span class="mono">fds-integration-simple-fire</span> (evidências em <span class="mono">docs/evidence/sim_RUN-*</span>). Nenhuma imagem é incluída neste protótipo.</p></section>
      </div>`;
  }

  /* ---------- Fontes e metodologia ---------- */
  function sources() {
    return `
      ${PageHeader({ crumbs: ["Fontes e metodologia"], title: "Fontes e metodologia" })}
      <div class="grid cols-2">
        <section class="card card-pad"><h2 style="font-size:15px;margin-bottom:10px">Documento-fonte</h2><dl class="kv"><dt>Título</dt><dd>${esc(D.doc.title)}</dd><dt>Identificador</dt><dd class="mono">${esc(D.doc.id)}</dd><dt>Versão</dt><dd>${esc(D.doc.version)}</dd><dt>SHA-256</dt><dd class="mono" style="word-break:break-all;font-size:12px">${esc(D.doc.sha256)}</dd><dt>Link</dt><dd><a href="${esc(ntrs)}" target="_blank" rel="noopener">NTRS${Icon("ext")}</a></dd></dl></section>
        <section class="card card-pad prose"><h2 style="margin-top:0">Como ler os dados</h2><ul><li><b>Conferido na fonte:</b> uma pessoa comparou valor, unidade e página no PDF.</li><li><b>Ausente na fonte:</b> o dado foi procurado e não consta; permanece como lacuna.</li><li><b>Observado ≠ calculado:</b> resultados da NASA nunca alimentam um modelo como entrada.</li><li><b>IA:</b> interpreta trechos delimitados; não calcula nem simula.</li></ul><p style="margin-top:12px;font-size:13px;color:var(--text-secondary)">O FlameLab não é produto oficial, homologado ou endossado pela NASA ou pelo NIST.</p></section>
      </div>`;
  }

  /* ---------- Router ---------- */
  const ROUTES = { "/": overview, "/biblioteca": library, "/ensaio/m1": m1, "/assistente": () => assistant(window.__ask), "/telemetria": telemetry, "/fds": fds, "/fontes": sources };
  function render() {
    const route = (location.hash.slice(1) || "/");
    const view = ROUTES[route] || overview;
    document.getElementById("app").innerHTML = AppShell({ route: ROUTES[route] ? route : "/", content: view(), nav: NAV });
    document.title = "FlameLab · protótipo";
    window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", () => { document.body.classList.remove("nav-open"); window.__ask = undefined; render(); });
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-toggle]");
    if (t) {
      const body = document.getElementById(t.dataset.toggle);
      const open = t.getAttribute("aria-expanded") === "true";
      t.setAttribute("aria-expanded", String(!open));
      body.hidden = open;
      return;
    }
    const ask = e.target.closest("[data-ask]");
    if (ask) { window.__ask = ask.dataset.ask; const y = window.scrollY; render(); window.scrollTo(0, y); return; }
    if (e.target.closest("#menu-btn")) { const o = document.body.classList.toggle("nav-open"); document.getElementById("menu-btn").setAttribute("aria-expanded", String(o)); }
    else if (document.body.classList.contains("nav-open") && !e.target.closest("#sidebar")) document.body.classList.remove("nav-open");
  });
  render();
})();
