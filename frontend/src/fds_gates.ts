import type { Experiment, Gap, Run, SimStatus } from "./api";
import { GATE_OF } from "./gap_themes";
import type { Tone } from "./components";

export type GateView = { id: string; name: string; criterion: string; tone: Tone; state: string; reason: string; gaps: Gap[] };

const open = (g: Gap) => !["COBERTA", "DISTINTA"].includes(g.coverage_state ?? "ABERTA");

/**
 * G0–G5 (planning/05 §6). Estado derivado de dados reais: status do executor, lacunas abertas e execuções registradas.
 * Aprovação de G1/G2/G4 é CIÊNCIA: sem lacunas abertas o gate fica "aguardando aprovação", nunca "liberado" automaticamente.
 */
export function fdsGates(exp: Experiment | undefined, status: SimStatus | undefined, runs: Run[]): GateView[] {
  const gaps = exp?.gaps ?? [];
  const by = (g: "G1" | "G2" | "G4") => gaps.filter((x) => GATE_OF[x.parameter] === g && open(x));
  const scienceGate = (id: "G1" | "G2" | "G4", name: string, criterion: string, extra?: string): GateView => {
    const g = by(id);
    return g.length
      ? { id, name, criterion, tone: "bad", state: "BLOQUEADO", reason: `${g.length} lacuna(s) aberta(s): ${g.map((x) => x.label_pt).join("; ")}.${extra ?? ""}`, gaps: g }
      : { id, name, criterion, tone: "warn", state: "AGUARDANDO APROVAÇÃO CIENTÍFICA", reason: "Sem lacunas abertas para este gate; a aprovação é decisão humana e ainda não foi registrada.", gaps: [] };
  };
  const g2open = by("G2").length > 0;
  const generic = runs.filter((r) => r.scope === "DEMO" && r.state === "DONE");
  const mine = runs.filter((r) => r.scope === "EXPERIMENT" && r.state === "DONE");
  return [
    {
      id: "G0-env", name: "Ambiente", criterion: "FDS verificado em máquina com acesso ao repositório.", gaps: [],
      ...(status?.available
        ? { tone: "ok" as Tone, state: "VERIFICADO", reason: `Executor disponível${status.versions ? ` (FDS ${status.versions.fds ?? "?"}, Smokeview ${status.versions.smokeview ?? "?"}, FFmpeg ${status.versions.ffmpeg ?? "?"})` : ""}.` }
        : { tone: "muted" as Tone, state: "INDISPONÍVEL", reason: status ? status.detail : "Status do executor não obtido." }),
    },
    scienceGate("G1", "Geometria e condições", "Cada dimensão/condição do caso com evidência ou hipótese justificada."),
    scienceGate("G2", "Material", "Propriedades de pirólise/ignição do PMMA com fonte e revisão."),
    {
      id: "G3", name: "Execução", criterion: ".fds, versão, log completo e saídas guardadas.", gaps: [],
      ...(mine.length
        ? { tone: "ok" as Tone, state: "EXECUTADO NO EXPERIMENTO", reason: `${mine.length} execução(ões) concluída(s) para este experimento.` }
        : generic.length
          ? { tone: "info" as Tone, state: "SÓ CASO GENÉRICO", reason: `${generic.length} execução(ões) do caso genérico (não representa o ensaio). Nenhuma para este experimento.` }
          : { tone: "muted" as Tone, state: "SEM EXECUÇÃO", reason: "Nenhuma execução registrada." }),
    },
    scienceGate("G4", "Comparação", "Observável calculado comparável ao da NASA, com erro, incerteza e método documentados.", g2open ? " Depende também de G2." : ""),
    { id: "G5", name: "Alteração", criterion: "Uma variável alterada com rastreabilidade.", tone: "muted", state: "FUTURO", reason: "Não disponível nesta versão.", gaps: [] },
  ];
}

export const blockedForReproduction = (gates: GateView[]) => gates.some((g) => g.tone === "bad") || gates.every((g) => g.id === "G0-env" || g.tone !== "ok");
