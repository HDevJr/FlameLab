import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Async, Badge, ErrorBox, useLoad } from "../components";
import { blockedForReproduction, fdsGates } from "../fds_gates";

/** Validação física: gates G0–G5 derivados de dados reais. Não existe botão de execução do experimento enquanto houver bloqueio. */
export default function FdsGates() {
  const { id = "BASS2-M1" } = useParams();
  const exp = useLoad(() => api.experiment(id), [id]);
  const status = useLoad(api.simStatus, []);
  const runs = useLoad(api.runs, []);
  const ready = !exp.loading && !status.loading && !runs.loading;
  return (
    <>
      <div className="crumbs">Validação física (FDS)</div>
      <h1>Validação física — FDS / Smokeview</h1>
      <p className="muted">A física é calculada pelo FDS. O assistente não substitui o solver.</p>
      {exp.error && <ErrorBox error={exp.error} onRetry={exp.reload} />}
      <Async state={exp}>{(e) => {
        const gates = fdsGates(e, status.data ?? undefined, runs.data ?? []);
        const blocked = blockedForReproduction(gates);
        return (
          <>
            <div className={`box ${blocked ? "bad" : "info"}`} role="status">
              <strong>{blocked ? `Reprodução do ensaio ${e.label} bloqueada` : "Gates sem bloqueio aberto"}</strong>
              <p>{blocked
                ? "Faltam informações críticas de geometria e propriedades do material, e a comparação com os resultados de referência ainda não está estabelecida. O FlameLab não completa esses dados por estimativa."
                : "A liberação continua dependendo de aprovação científica registrada."}</p>
              <button disabled aria-disabled="true">Executar simulação do experimento (indisponível)</button>
            </div>
            <ol className="gates" aria-label="Gates de validação">
              {gates.map((g) => (
                <li key={g.id} className={g.tone}>
                  <div className="row"><code>{g.id}</code><strong className="grow">{g.name}</strong><Badge tone={g.tone}>{g.state}</Badge></div>
                  <div className="detail"><strong>Critério:</strong> {g.criterion}</div>
                  <div>{g.reason}</div>
                </li>
              ))}
            </ol>
            <div className="card generic-label">
              <Badge tone="info">CASO GENÉRICO — NÃO REPRESENTA A REPRODUÇÃO DO ENSAIO {e.label}</Badge>
              <p className="detail">Qualquer resultado de FDS/Smokeview exibido em “Demonstração FDS” e “Execuções” vem de um caso de integração independente do experimento.</p>
              <Link className="btn" to="/demonstracao-fds">Demonstração FDS</Link> <Link className="btn" to={`/experimentos/${id}`}>Ficha do experimento</Link>
            </div>
            {ready && status.error && <p className="detail">Status do executor indisponível: {status.error.message}</p>}
          </>
        );
      }}</Async>
    </>
  );
}
