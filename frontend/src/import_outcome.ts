import type { ImportRecord } from "./api";
import type { Tone } from "./components";

export type OutcomeRow = { key: "READ" | "ORIGIN" | "EXTRACT"; label: string; tone: Tone; status: string; detail: string; action?: string };
export type Outcome = { rows: OutcomeRow[]; warnings: string[]; aiOff: boolean; experiments: number };

const step = (rec: ImportRecord, key: string) => rec.steps.find((s) => s.key === key);

/** Resume o resultado de uma importação em três estados (leitura, origem NASA, extração) e reúne os avisos. Só lê o que o backend enviou. */
export function importOutcome(rec: ImportRecord): Outcome {
  const cov = rec.coverage;
  const total = rec.document.page_count;
  const withText = rec.document.pages_with_text;
  const noText = withText != null ? total - withText : null;

  const read = step(rec, "READ");
  const readRow: OutcomeRow = {
    key: "READ", label: "Leitura do PDF",
    tone: read?.state === "FAILED" ? "bad" : noText ? "warn" : "ok",
    status: read?.state === "FAILED" ? "falhou" : noText ? "lido com lacunas" : "lido",
    detail: withText != null
      ? `${withText} de ${total} páginas com texto${noText ? `; ${noText} sem texto (figuras ou imagens)${cov?.without_text_ranges ? ` — ${cov.without_text_ranges}` : ""}. OCR não está disponível nesta versão.` : "."}`
      : read?.summary_pt ?? `${total} páginas.`,
  };

  const prov = rec.nasa_provenance;
  const originRow: OutcomeRow = !prov
    ? { key: "ORIGIN", label: "Origem NASA", tone: "muted", status: "verificando", detail: "Consulta ao NTRS em andamento." }
    : {
        key: "ORIGIN", label: "Origem NASA",
        tone: prov.state === "VERIFIED" ? "ok" : prov.state === "MISMATCH" ? "bad" : prov.state === "CANDIDATE" ? "warn" : "muted",
        status: prov.label_pt,
        detail: prov.state === "VERIFIED" ? "O arquivo confere com a publicação do NTRS."
          : prov.state === "PENDING"
            ? (rec.document.identifiers && Object.values(rec.document.identifiers).some((v) => v.length)
              ? "Há identificadores no texto, mas a conferência com o NTRS ainda não foi concluída."
              : "O texto não traz identificador NASA e o título não foi reconhecido. O documento não é tratado como publicação NASA validada.")
            : prov.reasons_pt.join(" "),
      };

  const ext = step(rec, "EXTRACT");
  const experiments = rec.experiments.length;
  const reasons = cov?.reasons_pt ?? [];
  const aiOff = ext?.state === "SKIPPED" && (cov?.mode === "NONE" || reasons.some((r) => /IA desligada|não configurada/i.test(r)));
  let extractRow: OutcomeRow;
  if (!ext || ext.state === "PENDING" || ext.state === "RUNNING") {
    extractRow = { key: "EXTRACT", label: "Extração por IA", tone: "muted", status: "em andamento", detail: "Lendo o PDF em lotes de páginas." };
  } else if (ext.state === "SKIPPED") {
    extractRow = {
      key: "EXTRACT", label: "Extração por IA", tone: "warn", status: "não executada",
      detail: aiOff ? "A IA está desligada ou sem chave. Nenhuma página foi lida por IA, então não há experimentos nem parâmetros." : (ext.summary_pt ?? "Etapa não executada."),
      action: aiOff ? "Ative a IA (FLAMELAB_LLM_MODE=live ou cache, com GEMINI_API_KEY no .env), reinicie o backend e use “Reprocessar este PDF”." : undefined,
    };
  } else if (ext.state === "FAILED") {
    extractRow = { key: "EXTRACT", label: "Extração por IA", tone: "bad", status: "falhou", detail: ext.summary_pt ?? "A extração falhou." };
  } else {
    const partial = cov?.mode === "AI_PARTIAL";
    extractRow = {
      key: "EXTRACT", label: "Extração por IA", tone: experiments === 0 || partial ? "warn" : "ok",
      status: experiments === 0 ? "sem resultados" : partial ? "parcial" : "concluída",
      detail: `${experiments} experimento(s) encontrado(s). ${cov?.summary_pt ?? ""}`.trim(),
    };
  }

  const seen = new Set<string>();
  const warnings: string[] = [];
  for (const w of [...rec.warnings_pt, ...rec.steps.map((s) => s.limitation_pt).filter((x): x is string => !!x)]) {
    if (!seen.has(w)) { seen.add(w); warnings.push(w); }
  }
  return { rows: [readRow, originRow, extractRow], warnings, aiOff, experiments };
}
