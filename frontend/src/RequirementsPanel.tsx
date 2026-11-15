// BL-17.2: o que foi registrado, que requisito pode atender e por que (ainda) não vira entrada FDS.
import type { Check, GuidedJourney, JourneySummary, QualityFlag, RequirementRow, Tier } from "./api";
import { Badge, type Tone } from "./components";

export const TIER_TONE: Record<Tier, Tone> = {
  OPEN: "muted", DRAFT: "muted", NOT_FOUND: "bad", CORRECTIONS_REQUESTED: "warn", TEST_CONTENT: "bad", EVIDENCE_SUBMITTED: "info",
  HYPOTHESIS_PROPOSED: "info", EXPLORATORY_DRAFT: "warn", REVIEWED: "info", REQUIREMENT_SATISFIED: "ok", PUBLISHED_VERIFIED: "ok",
  MISSING: "bad", MODEL_DEVELOPMENT: "bad",
};
const CATEGORY_PT: Record<Check["category"], string> = {
  DATA: "Falta informação — pode ser resolvido nesta revisão",
  REVIEW: "Falta revisão — outra pessoa precisa conferir",
  PHYSICS: "Falta modelo físico — desenvolvimento fora desta tela",
};
const STAGE_TONE: Record<string, Tone> = { NOT_STARTED: "muted", IN_PROGRESS: "warn", COMPLETE: "ok", BLOCKED: "bad", NOT_IMPLEMENTED: "bad" };
const STAGE_PT: Record<string, string> = { NOT_STARTED: "Não iniciada", IN_PROGRESS: "Em andamento", COMPLETE: "Concluída", BLOCKED: "Bloqueada", NOT_IMPLEMENTED: "Não implementada" };

export function Flags({ flags }: { flags?: QualityFlag[] }) {
  if (!flags?.length) return null;
  return <ul className="flags">{flags.map((f) => <li key={f.code} className={`box ${f.severity === "warning" ? "warn" : "info"}`}>{f.message_pt}</li>)}</ul>;
}

/** Verificações agrupadas: separa dado ausente, revisão pendente e modelo físico não aprovado. */
export function ChecksList({ checks, title = "Verificações" }: { checks: Check[]; title?: string }) {
  if (!checks.length) return null;
  const groups = (["DATA", "REVIEW", "PHYSICS"] as const).map((c) => [c, checks.filter((x) => x.category === c)] as const).filter(([, l]) => l.length);
  return <div className="checks" aria-label={title}>
    {groups.map(([cat, list]) => <div key={cat}><p className="check-cat">{CATEGORY_PT[cat]}</p>
      <ul>{list.map((c) => <li key={c.code} className={c.done ? "done" : "pending"}>
        <span aria-hidden="true">{c.done ? "✓" : "○"}</span> <strong>{c.label_pt}</strong>{c.done ? "" : " — pendente"}<br /><small>{c.detail_pt}</small></li>)}</ul></div>)}
  </div>;
}

export function MaturityLadder({ summary }: { summary: JourneySummary }) {
  return <section className="card ladder" aria-label="Escada de maturidade dos dados">
    <h3>Onde cada informação está</h3>
    <p className="detail">Cada nível é independente; um nível alto não é alcançado por visitar telas nem por concluir a revisão documental.</p>
    <ol>{summary.ladder.map((s) => <li key={s.key}><span className="ladder-count">{s.count}<small>/{s.of}</small></span> {s.label_pt} <small className="muted">({s.unit_pt})</small></li>)}</ol>
  </section>;
}

export function Stages({ summary }: { summary: JourneySummary }) {
  return <section className="card" aria-label="Etapas até a execução">
    <h3>Etapas até a execução</h3>
    <ol className="stages">{summary.stages.map((s) => <li key={s.key}><Badge tone={STAGE_TONE[s.status]}>{STAGE_PT[s.status]}</Badge> <strong>{s.label_pt}</strong><br /><small>{s.detail_pt}</small></li>)}</ol>
  </section>;
}

function Original({ r }: { r: RequirementRow }) {
  if (r.original) return <>{String(r.original.value ?? "—")} {r.original.unit ?? ""} <small className="muted">({r.original.locator_pt || "fonte conferida"})</small></>;
  return <span className="muted">Ausente na fonte publicada</span>;
}

function Proposal({ r }: { r: RequirementRow }) {
  const p = r.proposal;
  if (!p) return <span className="muted">Nenhuma proposta</span>;
  return <>{p.mode === "TEST" && <Badge tone="bad">TESTE</Badge>} <strong>{p.origin_pt}</strong>: {p.summary_pt || "—"}
    <br /><small>{p.author ? `por ${p.author}` : ""}{p.at ? ` · ${new Date(p.at).toLocaleString("pt-BR")}` : ""}{p.source ? ` · fonte: ${p.source}` : ""}</small></>;
}

export function RequirementsTable({ journey, onOpen }: { journey: GuidedJourney; onOpen?: (gapId: string) => void }) {
  const data = journey.requirements.filter((r) => r.category === "DATA_INPUT");
  const model = journey.requirements.filter((r) => r.category === "MODEL_DEVELOPMENT");
  if (!journey.requirements.length) return <p className="detail">Este perfil não define requisitos para a física deste experimento.</p>;
  return <section className="card requirements" aria-label="Requisitos do perfil por campo">
    <h3>Requisitos do perfil, campo a campo</h3>
    <p>{journey.summary.requirements_satisfied} de {journey.summary.requirements_total} requisitos de dados satisfeitos · {model.length} verificações físicas dependem de desenvolvimento do modelo.</p>
    <div className="req-list">{data.map((r) => <article key={r.parameter} className="req">
      <div className="row"><h4 className="grow">{r.label_pt}</h4><Badge tone={TIER_TONE[r.tier]}>{r.tier_pt}</Badge></div>
      <dl className="kv">
        <dt>Valor ou descrição original</dt><dd><Original r={r} /></dd>
        <dt>Nova proposta</dt><dd><Proposal r={r} /></dd>
        <dt>Estado</dt><dd>{r.satisfied ? "Satisfaz o perfil" : "Não satisfaz o perfil"}</dd>
        {!r.satisfied && <><dt>Por que ainda não</dt><dd>{r.reason_pt}</dd></>}
        {r.next_step_pt && <><dt>Próximo passo</dt><dd>{r.next_step_pt}</dd></>}
      </dl>
      <Flags flags={r.quality_flags} />
      {r.checks.length > 0 && <details><summary>Verificações deste requisito ({r.checks.filter((c) => !c.done).length} pendentes)</summary><ChecksList checks={r.checks} /></details>}
      {r.gap_id && onOpen && <button onClick={() => onOpen(r.gap_id!)}>Abrir requisito: {r.label_pt}</button>}
    </article>)}</div>
    <h4>Verificações físicas do modelo (sem lacuna de dados)</h4>
    <ul>{model.map((r) => <li key={r.parameter}><strong>{r.label_pt}</strong> — {r.reason_pt}</li>)}</ul>
  </section>;
}
