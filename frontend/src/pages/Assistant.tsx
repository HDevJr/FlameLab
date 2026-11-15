import { useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type AIAnswer, type RetrievedEvidence } from "../api";
import { Badge, ErrorBox, useReadOnly } from "../components";
import { MODE_TEXT, SUGGESTIONS, answerState } from "../assistant_state";

type Turn = { id: number; question: string; answer?: AIAnswer; error?: ApiError; pending: boolean };

const KIND: Record<RetrievedEvidence["kind"], string> = { RECORD_CARD: "Registro", GAP: "Lacuna (ausente)", PASSAGE: "Trecho do documento" };

function locatorText(l: Record<string, unknown> | null): string {
  if (!l) return "Referência não vinculada";
  const parts = [
    l.page_printed != null ? `p. ${l.page_printed}` : null,
    l.table ? `Tabela ${l.table}` : l.section ? `§${l.section}` : null,
    l.row_label as string | null, l.column_label as string | null,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Referência não vinculada";
}

function AnswerView({ a, onOpenEvidence }: { a: AIAnswer; onOpenEvidence: () => void }) {
  const st = answerState(a);
  const mode = MODE_TEXT[a.mode];
  return (
    <article className={`ai-answer ${st.tone}`} aria-label="Resposta do assistente">
      <div className="ai-head">
        <Badge tone={st.tone}><span aria-hidden>{st.icon}</span> {st.label}</Badge>
        <Badge tone={mode.tone} title={mode.title}>{mode.text}</Badge>
        {a.synthetic_evidence_used && <Badge tone="info" title="Evidência de teste; não é dado da NASA.">Evidência sintética</Badge>}
      </div>
      <p className="ai-explain">{st.explain}</p>
      {a.claims.map((c, i) => (
        <div className="claim" key={i}>
          <span className="lbl">{c.type}</span>
          <div>{c.text_pt}</div>
          <div>{c.evidence_ids.map((id) => <button key={id} className="chip" onClick={onOpenEvidence} title="Abrir evidências">{id}</button>)}</div>
        </div>
      ))}
      {a.blocked_claims.length > 0 && (
        <details open className="blocked">
          <summary>{a.blocked_claims.length} afirmação(ões) bloqueada(s) pelo verificador</summary>
          {a.blocked_claims.map((c, i) => (
            <div className="claim blocked-claim" key={i}><del>{c.text_pt}</del><code>{c.reason}</code></div>
          ))}
        </details>
      )}
      {a.extrapolation_flags.length > 0 && <p className="detail">Extrapolação detectada: {a.extrapolation_flags.join(", ")}. Nenhuma estimativa numérica foi produzida.</p>}
      {a.warnings.map((w, i) => <p className="limit" key={i}>⚠ {w}</p>)}
      <details className="tech"><summary>Detalhes técnicos da resposta</summary>
        <dl className="kv">
          <dt>Modo solicitado</dt><dd>{a.requested_mode}</dd>
          <dt>Provedor / modelo</dt><dd>{a.provider ?? "—"} / {a.model ?? "—"}</dd>
          <dt>Versão do prompt</dt><dd>{a.prompt_version}</dd>
          <dt>Versão do dataset</dt><dd><code>{a.dataset_version ?? "—"}</code></dd>
          <dt>Gerada em</dt><dd>{a.created_at}</dd>
          <dt>Latência</dt><dd>{a.latency_ms} ms</dd>
          {a.provider_error && <><dt>Erro do provedor</dt><dd>{a.provider_error}</dd></>}
        </dl>
      </details>
    </article>
  );
}

function EvidencePanel({ answer, panelRef }: { answer: AIAnswer | undefined; panelRef: React.RefObject<HTMLDetailsElement | null> }) {
  const cited = new Set(answer?.claims.flatMap((c) => c.evidence_ids) ?? []);
  // No celular a lista começa recolhida (a resposta fica à vista); no desktop fica aberta ao lado.
  const wide = typeof window !== "undefined" && window.matchMedia?.("(min-width: 901px)").matches;
  const n = answer?.retrieved.length ?? 0;
  return (
    <details className="card evidence-panel" ref={panelRef as React.RefObject<HTMLDetailsElement>} open={wide} aria-label="Evidências da resposta">
      <summary><h2>Evidências recuperadas{answer ? ` (${n})` : ""}</h2></summary>
      {!answer && <p className="muted">As evidências usadas aparecem aqui depois da primeira pergunta.</p>}
      {answer && n === 0 && <p className="muted">Nenhuma evidência elegível foi recuperada para esta pergunta.</p>}
      {answer?.retrieved.map((r) => (
        <div key={r.id} className={`ev ${cited.has(r.id) ? "cited" : ""}`}>
          <div className="row"><code>{r.id}</code>{cited.has(r.id) && <Badge tone="info">citada</Badge>}</div>
          <div className="detail">{KIND[r.kind]}{r.status ? ` · ${r.status}` : ""}</div>
          <p>{r.value_withheld ? "Valor retido: o dado existe na fonte, mas ainda não foi conferido por uma pessoa." : r.text}</p>
          <div className="detail">{locatorText(r.locator)}{r.document_id ? ` · ${r.document_id}` : ""}</div>
          {r.synthetic && <Badge tone="info">sintética</Badge>}
        </div>
      ))}
    </details>
  );
}

/** S05 — Assistente científico. Chama POST /api/ask; abstenção e indisponibilidade são estados, não erros. */
export default function Assistant() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const readOnly = useReadOnly();
  const panel = useRef<HTMLDetailsElement | null>(null);
  const last = [...turns].reverse().find((t) => t.answer)?.answer;

  async function send(question: string) {
    const q = question.trim();
    if (q.length < 3 || busy) return;
    const id = Date.now();
    setBusy(true); setText("");
    setTurns((t) => [...t, { id, question: q, pending: true }]);
    try {
      const answer = await api.ask(q);
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, answer, pending: false } : x)));
    } catch (e) {
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, error: e as ApiError, pending: false } : x)));
    } finally { setBusy(false); }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); void send(text); };

  return (
    <>
      <div className="crumbs">Assistente científico</div>
      <h1>Assistente científico</h1>
      <p className="muted">Respostas fundamentadas nos registros e documentos do FlameLab. O assistente interpreta evidências; não calcula nem simula o fogo.</p>
      <div className="context-bar"><span>Fonte ativa:</span><code>BASS-II · Ensaio M1 · NASA-TM-20210011385</code><Link to="/experimentos/BASS2-M1">Abrir ficha do M1</Link></div>

      <div className="assist-layout">
        <section className="card chat" aria-label="Conversa" aria-live="polite">
          {turns.length === 0 && (
            <div>
              <p className="muted">Escolha uma pergunta ou escreva a sua. Se a fonte não sustentar a resposta, o assistente se abstém.</p>
              {readOnly && <p className="box info">Na demonstração pública, só as perguntas abaixo têm resposta gravada (respostas reais da IA, verificadas). Uma pergunta nova volta como “sem resposta em cache”.</p>}
              <div className="suggest">{SUGGESTIONS.map((s) => <button key={s.q} onClick={() => void send(s.q)} disabled={busy}>{s.q}<small>{s.hint}</small></button>)}</div>
            </div>
          )}
          {turns.map((t) => (
            <div key={t.id} className="turn">
              <div className="msg-user">{t.question}</div>
              {t.pending && <p className="muted" role="status">Consultando evidências e verificando o suporte da resposta…</p>}
              {t.error && <ErrorBox error={t.error} />}
              {t.answer && <AnswerView a={t.answer} onOpenEvidence={() => { if (panel.current) { panel.current.open = true; panel.current.scrollIntoView({ block: "start" }); } }} />}
            </div>
          ))}
          <form className="composer" onSubmit={submit}>
            <label className="sr-only" htmlFor="ask-input">Pergunta</label>
            <textarea id="ask-input" rows={2} maxLength={1000} value={text} placeholder="Pergunte sobre o ensaio M1…" disabled={busy}
              onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(text); } }} />
            <button className="primary" type="submit" disabled={busy || text.trim().length < 3}>Enviar</button>
          </form>
          <p className="detail">O assistente não substitui a fonte científica nem executa simulações físicas.</p>
        </section>
        <EvidencePanel answer={last} panelRef={panel} />
      </div>
    </>
  );
}
