/* Componentes reutilizáveis (DESIGN_SYSTEM §9). Cada um devolve HTML (string); sem estado próprio. */
(function () {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const ICONS = {
    layout: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    flask: '<path d="M10 2v7.5L4.5 19a2 2 0 0 0 1.7 3h11.6a2 2 0 0 0 1.7-3L14 9.5V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/>',
    book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
    bot: '<rect x="4" y="8" width="16" height="12" rx="2"/><path d="M12 8V4"/><circle cx="12" cy="3" r="1"/><path d="M9 14h.01M15 14h.01"/>',
    activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.4 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    alert: '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3z"/><path d="M12 9v4M12 17h.01"/>',
    ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
    dashed: '<circle cx="12" cy="12" r="10" stroke-dasharray="3 3"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    ext: '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
    lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    cpu: '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
  };
  const Icon = (n) => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ""}</svg>`;

  /* Valores numéricos: vírgula decimal, algarismos tabulares, sem arredondar o que a fonte trouxe. */
  const fmt = (v) => (typeof v === "number" ? String(v).replace(".", ",") : esc(v));
  const fmtSI = (v) => {
    if (typeof v !== "number") return esc(v);
    if (v !== 0 && Math.abs(v) < 0.001) return v.toExponential(1).replace(".", ",").replace("e-", " × 10⁻").replace(/⁻(\d)/, (_, d) => "⁻" + d.replace(/\d/g, (x) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[x]));
    return String(Number(v.toPrecision(6))).replace(".", ",");
  };
  const UNIT_LABEL = { fraction: "fração", adimensional: "adimensional", "vol%": "vol%" };

  /* StatusBadge — cor + ícone + texto; a cor nunca é o único sinal. */
  const BADGES = {
    CONFERIDO_FONTE: ["ok", "check", "Conferido na fonte"],
    EXTRAIDO_NAO_REVISADO: ["warn", "eye", "Extraído · não revisado"],
    AUSENTE: ["warn", "alert", "AUSENTE NA FONTE"],
    IMPLEMENTADO: ["brand", "cpu", "Implementado"],
    VALIDADO: ["ok", "check", "Validado"],
    DEMONSTRATIVO: ["info", "eye", "Demonstrativo"],
    PENDENTE: ["warn", "clock", "Pendente"],
    BLOQUEADO: ["bad", "ban", "Bloqueado"],
    FUTURO: ["muted", "dashed", "Futuro"],
    VERIFICADO: ["ok", "check", "Verificado"],
    RESPALDADO: ["ok", "check", "RESPALDADO PELA FONTE"],
    DADO_AUSENTE: ["warn", "alert", "DADO AUSENTE"],
    EXTRAPOLACAO: ["bad", "ban", "EXTRAPOLAÇÃO BLOQUEADA"],
    INDISPONIVEL: ["muted", "dashed", "FONTE INDISPONÍVEL"],
    FONTE_CATALOGADA: ["ok", "book", "Fonte catalogada"],
    LACUNAS: ["warn", "alert", "Lacunas identificadas"],
    SIMULACAO_WOKWI: ["info", "cpu", "Simulação Wokwi"],
    GENERICO: ["info", "info", "Ambiente genérico"],
  };
  const StatusBadge = (key, label) => {
    const [tone, icon, text] = BADGES[key] || ["muted", "info", key];
    return `<span class="badge ${tone}">${Icon(icon)}${esc(label || text)}</span>`;
  };

  const PageHeader = ({ crumbs = [], title, lede = "", badges = "", actions = "" }) => `
    ${crumbs.length ? `<nav class="crumbs" aria-label="Trilha">${crumbs.map((c, i) => `${i ? '<span class="sep">/</span>' : ""}<span${i === crumbs.length - 1 ? ' aria-current="page"' : ""}>${esc(c)}</span>`).join("")}</nav>` : ""}
    <header class="page-head"><div><h1>${esc(title)}</h1>${lede ? `<p class="lede">${lede}</p>` : ""}${badges ? `<div class="meta">${badges}</div>` : ""}</div>${actions ? `<div class="actions">${actions}</div>` : ""}</header>`;

  /* EvidenceReference — documento, página/tabela/linha/coluna; abre o trecho literal. Sem dado → "Referência não vinculada". */
  const EvidenceReference = (refs, doc, uid) => {
    if (!refs || !refs.length) return `<span class="ref-loc">Referência não vinculada</span>`;
    const r = refs[0];
    const loc = [r.page != null ? `p. ${r.page}` : null, r.table ? `Tabela ${r.table}` : r.section ? `§${r.section}` : null, r.row, r.column].filter(Boolean).join(" · ");
    const body = refs.map((x) => `
      <div>
        <dl class="ref-grid">
          <dt>Documento</dt><dd>${esc(doc.id)}</dd>
          <dt>Página impressa</dt><dd>${x.page ?? "—"} (índice PDF ${x.pdfIndex ?? "—"})</dd>
          ${x.table ? `<dt>Tabela</dt><dd>${esc(x.table)}</dd>` : ""}
          ${x.section ? `<dt>Seção</dt><dd>§${esc(x.section)}</dd>` : ""}
          ${x.row ? `<dt>Linha</dt><dd>${esc(x.row)}</dd>` : ""}
          ${x.column ? `<dt>Coluna</dt><dd>${esc(x.column)}</dd>` : ""}
          <dt>Precisão</dt><dd>${esc(x.precision)}</dd>
          <dt>Registro</dt><dd>${esc(x.id)}</dd>
        </dl>
        <div class="quote">“${esc(x.quote)}”<small>Trecho literal da fonte (inglês)</small></div>
      </div>`).join("");
    return { loc, body, doc };
  };

  /* ScientificValue — nome, valor, unidade, SI, estado, referência expansível. */
  const ScientificValue = (p, doc, i) => {
    const ref = EvidenceReference(p.refs, doc);
    const isText = typeof p.value === "string";
    const unit = p.unit ? esc(p.unit) : p.key === "burning_faces" ? "adimensional · nº de faces" : "";
    const si = p.si ? `SI: <span class="num">${fmtSI(p.si.value)}</span> ${esc(UNIT_LABEL[p.si.unit] || p.si.unit)}` : "";
    const id = `ref-${i}`;
    return `
    <li class="sv">
      <div class="sv-main">
        <div><div class="sv-label">${esc(p.label)}</div><div class="sv-key">${esc(p.key)}</div></div>
        <div class="sv-value num ${isText ? "text" : ""}">${isText ? esc(p.value) : fmt(p.value)}${unit && !isText ? `<span class="unit">${unit}</span>` : ""}</div>
        ${si ? `<div class="sv-si">${si}</div>` : ""}
      </div>
      <div class="sv-meta">
        ${StatusBadge(p.status)}
        ${typeof ref === "string" ? ref : `
        <button class="ref-toggle" aria-expanded="false" aria-controls="${id}" data-toggle="${id}">${Icon("chevron")}Fonte</button>
        <span class="ref-loc">${esc(ref.loc)}</span>`}
      </div>
      ${typeof ref === "string" ? "" : `<div class="ref-body" id="${id}" hidden>
        ${ref.body}
        ${p.reviewer ? `<div><span class="lbl">Revisão humana</span><div>${esc(p.reviewer)} · ${esc((p.reviewedAt || "").slice(0, 10).split("-").reverse().join("/"))}</div></div>` : ""}
        ${p.caveats.length ? `<div><span class="lbl">Ressalvas registradas</span><ul class="caveats">${p.caveats.map((c) => `<li>${esc(c)}</li>`).join("")}</ul></div>` : ""}
      </div>`}
    </li>`;
  };

  /* DataCategoryPanel — condições, resultados ou lacunas (cada um com cor e papel próprios). */
  const DataCategoryPanel = ({ cls, icon, title, count, note, body }) => `
    <section class="card ${cls}" aria-label="${esc(title)}">
      <div class="panel-head"><h2>${Icon(icon)}${esc(title)}</h2><span class="count">${esc(count)}</span></div>
      ${note ? `<div class="panel-note">${note}</div>` : ""}
      ${body}
    </section>`;

  /* MissingDataNotice — lacuna declarada; nunca preenchida por estimativa. */
  const MissingDataNotice = (g, { key = false, gate = "" } = {}) => `
    <li class="gap ${key ? "key" : ""}">
      <div class="gap-top">
        <div class="gap-title">${Icon("alert")}${esc(g.label)}</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">${gate ? `<span class="badge bad caps">${Icon("ban")}Bloqueia ${esc(gate)}</span>` : ""}${StatusBadge("AUSENTE")}</div>
      </div>
      <p>${esc(g.why)}</p>
      <details><summary>Onde foi procurado</summary>
        <ul class="caveats">${g.searched.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>
        ${g.maybe ? `<p style="margin-top:6px"><b>Pista (não é dado):</b> ${esc(g.maybe)}</p>` : ""}
      </details>
    </li>`;

  /* AssistantMessage — estado, afirmações aprovadas/bloqueadas e evidências. */
  const AssistantMessage = (a) => {
    const [tone] = BADGES[a.state];
    return `
    <article class="msg-ai s-${tone}">
      <div class="msg-head">${StatusBadge(a.state)}<span class="badge muted">${esc(a.mode)}</span>${a.synthetic ? `<span class="badge info caps">Evidência sintética</span>` : ""}</div>
      <div class="msg-body">
        ${a.intro ? `<p>${esc(a.intro)}</p>` : ""}
        ${(a.approved || []).map((c) => `<div class="claim"><span class="lbl">${esc(c.type)}</span><div>${esc(c.text)}</div>${c.evidence.map((e) => `<span class="evidence-chip">${esc(e)}</span>`).join("")}</div>`).join("")}
        ${(a.blocked || []).map((c) => `<div class="claim blocked"><span class="lbl">Bloqueada · ${esc(c.type)}</span><div>${esc(c.text)}</div><span class="why">${esc(c.reason)}</span></div>`).join("")}
        <p class="lbl" style="text-transform:none;letter-spacing:0;font-weight:500">${esc(a.provenance)}</p>
      </div>
    </article>`;
  };

  /* TelemetryTable — só com série real; caso contrário, estado vazio explicativo. */
  const TelemetryTable = (columns, rows) => rows && rows.length
    ? `<div class="table-wrap"><table class="data"><thead><tr>${columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((v) => `<td class="num">${esc(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
    : `<div class="table-wrap"><table class="data"><thead><tr>${columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead></table>
        <div class="empty">${Icon("activity")}<strong>Nenhuma série real carregada</strong><span>Esta tabela só exibe amostras exportadas pelo protótipo. Nenhum valor é simulado aqui para dar aparência de atividade.</span></div></div>`;

  /* ReadinessGate — gate, estado, critério e motivo. */
  const ReadinessGate = (g) => `
    <li class="gate">
      <div class="gate-id">${esc(g.id)}</div>
      <div><h3>${esc(g.name)}</h3><div class="crit"><b>Critério:</b> ${esc(g.criterion)}</div><div class="reason">${g.reason}</div></div>
      <div>${StatusBadge(g.state, g.stateLabel)}</div>
    </li>`;

  const Disclaimer = () => `<strong>Projeto independente</strong>Desenvolvido para o NASA Space Apps Challenge. Não é endossado pela NASA.`;

  const AppShell = ({ route, content, nav }) => `
    <div class="proto-banner" role="note"><b>PROTÓTIPO DE INTERFACE</b> — proposta visual para decisão; dados de BASS2-M1 copiados de <span class="mono">data/</span>; sem backend conectado.</div>
    <div class="topbar"><button id="menu-btn" aria-label="Abrir menu" aria-expanded="false">${Icon("menu")}</button><div class="brand"><span class="brand-mark"><img src="assets/logo-mark.webp" alt="" width="38" height="36" /></span>FlameLab</div></div>
    <div class="shell">
      <aside class="sidebar" id="sidebar" aria-label="Navegação principal">
        <div class="brand"><span class="brand-mark"><img src="assets/logo-mark.webp" alt="" width="38" height="36" /></span><div>FlameLab<small>Painel de combustão em microgravidade</small></div></div>
        <nav class="nav">${nav.map((n) => n.label ? `<div class="nav-label">${esc(n.label)}</div>` : `<a href="#${n.to}" class="${n.sub ? "sub" : ""}" ${n.to === route ? 'aria-current="page"' : ""}>${n.icon ? Icon(n.icon) : ""}${esc(n.text)}</a>`).join("")}</nav>
        <div class="sidebar-foot">${Disclaimer()}</div>
      </aside>
      <main class="main" id="main">${content}<p class="footer-note">Projeto independente desenvolvido para o NASA Space Apps Challenge. Não é endossado pela NASA nem pelo NIST. Valores científicos exibidos vêm do dataset versionado e mantêm a referência à fonte.</p></main>
    </div>`;

  window.FL = { esc, Icon, fmt, StatusBadge, PageHeader, EvidenceReference, ScientificValue, DataCategoryPanel, MissingDataNotice, AssistantMessage, TelemetryTable, ReadinessGate, Disclaimer, AppShell };
})();
