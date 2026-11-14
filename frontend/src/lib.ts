// Funções puras de apresentação (testadas em lib.test.ts).
import type { Parameter } from "./api";

export const STATUS_LABEL: Record<string, { text: string; tone: "ok" | "warn" | "bad" | "info" | "muted" }> = {
  CONFERIDO_FONTE: { text: "Conferido na fonte", tone: "ok" },
  APROVADO_MODELO: { text: "Aprovado p/ modelo", tone: "ok" },
  EXTRAIDO_NAO_REVISADO: { text: "Extraído · não revisado", tone: "warn" },
  INFERIDO: { text: "Inferido", tone: "info" },
  CALCULADO: { text: "Calculado", tone: "info" },
  AUSENTE: { text: "Ausente", tone: "bad" },
};

export const COMPAT_LABEL: Record<string, { text: string; tone: "ok" | "warn" | "bad" | "info" }> = {
  COMPATIBLE: { text: "Compatível com FDS", tone: "ok" },
  MISSING_PARAMETERS: { text: "Faltam parâmetros", tone: "warn" },
  UNSUPPORTED_PHYSICS: { text: "Física não suportada", tone: "bad" },
  REQUIRES_REVIEW: { text: "Requer revisão", tone: "info" },
};

export const MATCH_LABEL: Record<string, { text: string; tone: "ok" | "warn" | "bad" | "info" | "muted" }> = {
  MATCH_CONFIRMED: { text: "Correspondência confirmada", tone: "ok" },
  MATCH_CANDIDATE: { text: "Candidato (revisão humana)", tone: "warn" },
  NOT_FOUND: { text: "Não encontrado", tone: "muted" },
  CONFLICT: { text: "Conflito", tone: "bad" },
  SOURCE_UNAVAILABLE: { text: "Fonte indisponível", tone: "bad" },
  ADDITIONAL_DATA_FOUND: { text: "Dado adicional", tone: "info" },
  NOT_QUERIED: { text: "Não consultado", tone: "muted" },
};

export const RUN_STEPS = ["QUEUED", "VALIDATING", "RUNNING_FDS", "PROCESSING_RESULTS", "RENDERING", "COMPLETED"] as const;
export const RUN_STEP_LABEL: Record<string, string> = {
  QUEUED: "Na fila", VALIDATING: "Validando", RUNNING_FDS: "Executando FDS",
  PROCESSING_RESULTS: "Processando resultados", RENDERING: "Renderizando", COMPLETED: "Concluído",
  FAILED: "Falhou", BLOCKED: "Bloqueado",
};
export const isTerminal = (s: string) => s === "COMPLETED" || s === "FAILED" || s === "BLOCKED";

export function formatValue(p: Parameter): string {
  const o = p.original;
  if (!o || o.value === null || o.value === undefined) return "—";
  return o.unit ? `${o.value} ${o.unit}` : String(o.value);
}

export function groupByRole(params: Parameter[]) {
  return {
    conditions: params.filter((p) => p.role === "CONDICAO"),
    observed: params.filter((p) => p.role === "OBSERVAVEL"),
    metadata: params.filter((p) => p.role === "METADADO"),
  };
}

export const fmtBytes = (n: number | null | undefined) =>
  n == null ? "—" : n > 1e6 ? `${(n / 1e6).toFixed(1)} MB` : n > 1e3 ? `${(n / 1e3).toFixed(1)} kB` : `${n} B`;

export function render(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.map(render).join("; ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** Valida o valor digitado contra a faixa do modelo. Devolve a mensagem de erro ou null. */
export function validateChange(value: number, min: number, max: number, unit: string): string | null {
  if (!Number.isFinite(value)) return "Informe um número.";
  if (value < min || value > max) return `Fora da faixa permitida: ${min} a ${max} ${unit}.`;
  return null;
}

export function pathPoints(points: [number, number][], w: number, h: number, xmax: number, ymax: number): string {
  if (!points.length || xmax <= 0 || ymax <= 0) return "";
  return points.map(([x, y], i) => `${i ? "L" : "M"}${((x / xmax) * w).toFixed(1)},${(h - (y / ymax) * h).toFixed(1)}`).join(" ");
}
