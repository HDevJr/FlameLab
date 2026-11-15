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

// ---------------------------------------------------------------- explicações em linguagem simples
export const GLOSSARY: Record<string, string> = {
  sha256: "Impressão digital do arquivo: dois arquivos idênticos têm o mesmo SHA-256. Serve para saber se o PDF é exatamente o publicado.",
  procedencia: "Resposta a “este arquivo é a publicação da NASA?”. Só é verificada quando o SHA-256 é igual ao do arquivo distribuído pelo NTRS.",
  revisao: "Conferência feita por uma pessoa, que abre o PDF e confirma valor, unidade e página. É diferente da procedência.",
  nao_revisado: "Valor lido do PDF (por IA ou por transcrição) que ainda não foi conferido por uma pessoa. Não deve ser citado como dado da fonte.",
  conferido: "Valor conferido por uma pessoa diferente de quem extraiu, no PDF original cujo hash foi verificado.",
  ntrs: "NASA Technical Reports Server: repositório oficial de relatórios técnicos da NASA.",
  psi: "NASA Physical Sciences Informatics: repositório de investigações e dados de ciências físicas em microgravidade.",
  techport: "Portfólio de projetos de tecnologia da NASA. Um projeto não é o mesmo que um experimento.",
  candidato: "Há semelhança de título e autores, mas nenhum identificador comum prova que são o mesmo trabalho. Precisa de revisão humana.",
  enriquecimento: "Busca de informações complementares em outras fontes NASA. Contextualiza o trabalho; nunca valida nem substitui os números do artigo.",
  lacuna: "Informação necessária (por exemplo, para simular) que não foi encontrada na fonte. Nunca é preenchida com um valor inventado.",
  condicao: "Condição de entrada do experimento (por exemplo, a espessura da amostra).",
  observavel: "Resultado medido no experimento. Serve de referência de comparação; nunca é entrada de uma simulação.",
  cobertura: "Quais páginas do PDF a IA realmente leu. Páginas não lidas podem conter experimentos e parâmetros ainda não encontrados.",
  hipotese: "Cenário que altera um valor para ver o que aconteceria. É uma hipótese computacional, não um dado experimental.",
  fds: "Fire Dynamics Simulator: programa do NIST que simula incêndios e escoamento de fumaça.",
  smokeview: "Programa que desenha os resultados do FDS. Aqui ele gera os quadros do vídeo.",
  demo_fds: "Caso genérico (um queimador em uma sala) que só prova que o pipeline FDS → Smokeview → vídeo funciona. Não pertence a nenhum artigo.",
};

export const REVIEW_ERRORS: Record<string, string> = {
  VALUE_MISMATCH: "O valor ou a unidade que você leu não confere com o registro. Nada foi aprovado. Se o PDF realmente mostra outro valor, use “Registrar divergência”.",
  VALUE_UNREADABLE: "Não foi possível interpretar o valor informado. Digite apenas o número (ou o texto, para materiais).",
  PAGE_MISMATCH: "A página informada não corresponde à evidência deste registro.",
  REVIEWER_NOT_INDEPENDENT: "O revisor precisa ser uma pessoa diferente de quem extraiu o valor.",
  REVIEWER_NOT_HUMAN: "A revisão deve ser feita por uma pessoa da equipe, não por uma IA.",
  REVIEWER_REQUIRED: "Informe o nome de quem está revisando.",
  DECLARATION_REQUIRED: "Marque que você conferiu o PDF original.",
  OBSERVED_REQUIRED: "Informe o valor, a unidade e a página que você leu no PDF.",
  NOTES_REQUIRED: "Descreva o motivo no campo de observações.",
  DOCUMENT_HASH: "O arquivo PDF guardado não tem o hash registrado. A revisão foi bloqueada para proteger a integridade.",
  EVIDENCE_INSUFFICIENT: "Este parâmetro não tem evidência suficiente (página e citação literal) para ser aprovado.",
  WRONG_STATE: "Este registro já foi conferido; não pode ser aprovado de novo.",
};

REVIEW_ERRORS.UNIT_MISSING = "A unidade não foi informada. O número confere, mas a unidade é obrigatória para comparar a grandeza.";
REVIEW_ERRORS.UNIT_INCOMPATIBLE = "A unidade informada mede outra grandeza que a do registro (por exemplo, °C × ângulo em °).";
REVIEW_ERRORS.UNIT_UNSUPPORTED = "Esta unidade não é suportada pela tabela de unidades; a conferência automática não é possível.";
REVIEW_ERRORS.UNIT_UNEXPECTED = "O registro não tem unidade, mas uma unidade foi informada.";
REVIEW_ERRORS.VALUE_AMBIGUOUS = "O valor informado é ambíguo (ex.: “1,234” ou “20 a 80”). Informe um único número sem separador de milhar.";
REVIEW_ERRORS.SEMANTIC_AMBIGUITY = "O número confere, mas o trecho não sustenta a interpretação do parâmetro. Corrija a extração ou mantenha pendente.";
REVIEW_ERRORS.CURATED_READONLY = "Registros do dataset curado são corrigidos pela curadoria, não pela interface.";
REVIEW_ERRORS.NO_CHANGE = "Nenhuma alteração: informe um nome, valor ou unidade diferentes dos atuais.";

export const reviewErrorMessage = (code: string, fallback: string) => REVIEW_ERRORS[code] ?? fallback;

// ---------------------------------------------------------------- tempos
export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1).replace(".", ",")} s`;
  const m = Math.floor(s / 60);
  return `${m} min ${String(Math.round(s - m * 60)).padStart(2, "0")} s`;
}

export function elapsedMs(startIso: string | null | undefined, nowMs: number): number | null {
  if (!startIso) return null;
  const t = Date.parse(startIso);
  return Number.isNaN(t) ? null : Math.max(0, nowMs - t);
}

export function formatClock(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00.0";
  const m = Math.floor(seconds / 60);
  return `${m}:${(seconds - m * 60).toFixed(1).padStart(4, "0")}`;
}

/** Tempo físico simulado correspondente a um instante do vídeo (quadros em intervalos iguais de tempo simulado). */
export function simulatedTimeAt(videoTime: number, videoDuration: number, simulatedTotal: number | null | undefined): number | null {
  if (!simulatedTotal || !videoDuration || videoDuration <= 0) return null;
  return Math.min(simulatedTotal, Math.max(0, (videoTime / videoDuration) * simulatedTotal));
}

/** Segundos simulados por segundo de vídeo (1 = tempo real; >1 = vídeo mais rápido que o fenômeno). */
export function playbackRatio(videoDuration: number | null | undefined, simulatedTotal: number | null | undefined): number | null {
  if (!videoDuration || !simulatedTotal) return null;
  return simulatedTotal / videoDuration;
}

export const SPEEDS = [0.25, 0.5, 1, 2] as const;
export const speedLabel = (s: number) => `${String(s).replace(".", ",")}×`;

// ---------------------------------------------------------------- revisão assistida
export const FIELD_STATUS: Record<string, { text: string; tone: "ok" | "warn" | "bad" | "info" | "muted" }> = {
  MATCH: { text: "Confere", tone: "ok" }, CONVERTIBLE: { text: "Confere após conversão", tone: "ok" },
  MISMATCH: { text: "Diverge", tone: "bad" }, MISSING: { text: "Falta", tone: "bad" }, INCOMPATIBLE: { text: "Incompatível", tone: "bad" },
  UNSUPPORTED: { text: "Unidade não suportada", tone: "bad" }, UNEXPECTED: { text: "Inesperada", tone: "bad" },
  UNREADABLE: { text: "Ilegível", tone: "bad" }, AMBIGUOUS: { text: "Ambíguo", tone: "bad" }, NOT_APPLICABLE: { text: "—", tone: "muted" },
};
export const FIELD_OK = new Set(["MATCH", "CONVERTIBLE", "NOT_APPLICABLE"]);
export const failedFields = (c: { field: string; status: string }[] | null | undefined) => (c ?? []).filter((x) => !FIELD_OK.has(x.status)).map((x) => x.field);

export const LABEL_SOURCE: Record<string, string> = { IA: "nome sugerido pela IA", GLOSSARIO: "nome traduzido pelo glossário", HUMANO: "nome definido por uma pessoa", CURADORIA: "nome da curadoria" };

/** Divide `text` em trechos, marcando os que coincidem (sem distinguir maiúsculas) com algum dos `terms`. */
export function highlightSegments(text: string, terms: string[]): { text: string; hit: boolean }[] {
  const clean = [...new Set(terms.map((t) => t.trim()).filter((t) => t.length > 0))].sort((a, b) => b.length - a.length);
  if (!text || clean.length === 0) return [{ text, hit: false }];
  const re = new RegExp(clean.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "gi");
  const out: { text: string; hit: boolean }[] = [];
  let last = 0;
  for (const m of text.matchAll(re)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ text: text.slice(last, at), hit: false });
    out.push({ text: m[0], hit: true });
    last = at + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last), hit: false });
  return out;
}

/** Valor extraído como texto de campo (sem unidade): 20.0 → "20". */
export const valueText = (v: number | string | null | undefined): string => (v == null ? "" : typeof v === "number" ? String(Number.isInteger(v) ? v : Number(v.toPrecision(12))) : v);
