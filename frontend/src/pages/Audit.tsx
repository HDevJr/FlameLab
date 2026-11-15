import { Link } from "react-router-dom";
import { api, type AuditRecord } from "../api";
import { Async, Badge, Term, useLoad } from "../components";
import { valueText } from "../lib";

const CLASS: Record<AuditRecord["classification"], { text: string; tone: "ok" | "warn" | "bad" | "info" | "muted" }> = {
  INCONSISTENT_CONFIRMED: { text: "Conferido, mas inconsistente", tone: "bad" },
  LEGACY_REVIEW: { text: "Conferido sem confirmar a interpretação", tone: "warn" },
  ATTENTION: { text: "Ressalvas informativas", tone: "info" },
  OK: { text: "Sem achados", tone: "ok" },
};
const ACTION: Record<string, string> = {
  CORRECT: "Corrigir extração", CORRECT_OR_REOPEN: "Corrigir extração ou reabrir", REOPEN: "Reabrir conferência", REOPEN_THEN_CONFIRM: "Reabrir e reconfirmar",
};

/** Auditoria de integridade (somente leitura): o que foi conferido, o que a fonte sustenta e a correção auditável proposta. */
export default function AuditPage() {
  const report = useLoad(api.auditIntegrity, []);
  return (
    <>
      <h1>Auditoria de integridade científica</h1>
      <p className="muted">Relatório <strong>somente leitura</strong> dos registros já revisados: grandeza, unidade, condição e interpretação sustentadas pela fonte. Nada é alterado aqui; a correção é uma ação humana (Corrigir extração ou Reabrir conferência) que preserva o histórico.</p>
      <Async state={report}>{(r) => (
        <>
          <div className="grid">
            <div className="card"><h3>Registros</h3><p><strong>{r.summary.records}</strong> no total · <strong>{r.summary.confirmed}</strong> <Term k="conferido">conferidos</Term></p></div>
            <div className="card"><h3>Conferidos, mas inconsistentes</h3><p><Badge tone={r.summary.confirmed_with_blocking_inconsistency ? "bad" : "ok"}>{r.summary.confirmed_with_blocking_inconsistency}</Badge></p><p className="detail">Grandeza, unidade ou condição não sustentadas pela fonte.</p></div>
            <div className="card"><h3>Sem confirmação da interpretação</h3><p><Badge tone={r.summary.confirmed_without_interpretation_confirmation ? "warn" : "ok"}>{r.summary.confirmed_without_interpretation_confirmation}</Badge></p><p className="detail">Revisões que compararam número, unidade e página, mas não o significado.</p></div>
          </div>
          <div className="box info">{r.note_pt}</div>
          <table><thead><tr><th>Registro</th><th>Valor / unidade</th><th>Classificação</th><th>Achados</th><th>Correção auditável proposta</th></tr></thead><tbody>
            {r.records.filter((x) => x.classification !== "OK").map((x) => (
              <tr key={x.record_id}>
                <td><strong>{x.label_pt}</strong><div className="detail"><code>{x.parameter}</code> · p. {x.page ?? "—"}</div><Link to={`/experimentos/${x.experiment_id}`}>abrir</Link></td>
                <td>{valueText(x.value)} <small className="muted">{x.unit_raw ?? ""}</small><div className="detail">unidade: {x.unit_state}</div></td>
                <td><Badge tone={CLASS[x.classification].tone}>{CLASS[x.classification].text}</Badge>{x.review?.reviewer && <div className="detail">revisão de {x.review.reviewer} ({x.review.scope === "FULL" ? "completa" : "anterior à interpretação"})</div>}</td>
                <td>{[...x.integrity_findings.filter((f) => f.severity === "BLOCKING"), ...x.semantic_flags.filter((f) => f.severity === "BLOCKING")].map((f) => <div className="detail" key={f.code}>⚠ {f.title_pt}</div>)}
                  {x.audit_anomalies.map((a) => <div className="detail" key={a.code + a.at}>🔎 {a.detail_pt}</div>)}</td>
                <td>{x.proposals.map((p) => <div key={p.finding}><Badge tone="info">{ACTION[p.action] ?? p.action}</Badge><div className="detail">{p.proposal_pt}</div></div>)}</td>
              </tr>
            ))}
          </tbody></table>
        </>
      )}</Async>
    </>
  );
}
