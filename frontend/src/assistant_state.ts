import type { AIAnswer } from "./api";
import type { Tone } from "./components";

export type AnswerStateKey = "SUPPORTED" | "MISSING" | "PENDING_REVIEW" | "EXTRAPOLATION" | "VERIFIER_BLOCKED" | "MODEL_ABSTAINED" | "UNAVAILABLE";

export type AnswerState = { key: AnswerStateKey; tone: Tone; icon: string; label: string; explain: string };

/**
 * Estado da resposta para a interface. Deriva só dos campos que o backend envia
 * (nunca infere "conferido" a partir da existência de uma citação).
 */
export function answerState(a: AIAnswer): AnswerState {
  if (a.mode === "UNAVAILABLE") {
    const why = { MODE_OFF: "o modo da IA está desligado (off)", CACHE_MISS: "não há resposta em cache para esta pergunta", PROVIDER_NOT_CONFIGURED: "o provedor de IA não está configurado", PROVIDER_ERROR: "o provedor de IA falhou" } as const;
    return { key: "UNAVAILABLE", tone: "muted", icon: "○", label: "FONTE INDISPONÍVEL", explain: `Nenhuma resposta gerada: ${a.unavailable_reason ? why[a.unavailable_reason] : "IA indisponível"}. As evidências recuperadas ficam no painel de evidências.` };
  }
  if (!a.abstained) {
    return { key: "SUPPORTED", tone: "ok", icon: "✔", label: "RESPALDADO PELA FONTE", explain: "Cada afirmação passou pelo verificador determinístico e cita evidência recuperada." };
  }
  switch (a.abstain_reason) {
    case "EXTRAPOLATION":
      return { key: "EXTRAPOLATION", tone: "bad", icon: "⛔", label: "EXTRAPOLAÇÃO BLOQUEADA", explain: "A pergunta exige inferência ou número fora do que a fonte sustenta. O FlameLab não estima esse valor." };
    case "PENDING_REVIEW":
      return { key: "PENDING_REVIEW", tone: "warn", icon: "⚠", label: "VALOR RETIDO · AGUARDA REVISÃO", explain: "O dado consta na fonte, mas ainda não foi conferido por uma pessoa; o número não é liberado." };
    case "VERIFICATION_FAILED":
      return { key: "VERIFIER_BLOCKED", tone: "bad", icon: "⛔", label: "VERIFICADOR BLOQUEOU A RESPOSTA", explain: "As afirmações geradas não passaram na verificação. Nada foi publicado como fato." };
    case "MODEL_ABSTAINED":
      return { key: "MODEL_ABSTAINED", tone: "warn", icon: "⚠", label: "ABSTENÇÃO FUNDAMENTADA", explain: "O modelo declarou não haver base suficiente nas evidências recuperadas." };
    default:
      return { key: "MISSING", tone: "warn", icon: "⚠", label: "DADO AUSENTE", explain: "A fonte consultada não informa o dado solicitado. O FlameLab não o estima." };
  }
}

export const MODE_TEXT: Record<AIAnswer["mode"], { tone: Tone; text: string; title: string }> = {
  LIVE: { tone: "info", text: "Modo: ao vivo", title: "Gerada pelo provedor nesta requisição e aprovada pelo verificador." },
  CACHE: { tone: "warn", text: "Modo: cache", title: "Resposta gerada e verificada antes, reverificada contra o dataset atual. Não é uma consulta ao vivo." },
  DETERMINISTIC: { tone: "muted", text: "Modo: regra determinística", title: "Abstenção decidida em código, sem chamar a IA." },
  UNAVAILABLE: { tone: "muted", text: "Modo: IA indisponível", title: "A IA não foi utilizada nesta resposta." },
};

/** Perguntas de partida (todas sobre o M1). Cada uma tem resposta real gravada no cache, para funcionar na demonstração pública. */
export const SUGGESTIONS = [
  { q: "Qual era a pressão no ensaio M1?", hint: "dado ausente na fonte" },
  { q: "Qual foi a velocidade de propagação da chama no ensaio M1?", hint: "resultado observado" },
  { q: "Qual seria a propagação da chama na atmosfera de Marte?", hint: "extrapolação — deve ser bloqueada" },
  { q: "Qual foi a concentração inicial de oxigênio no M1?", hint: "condição de entrada" },
  { q: "Qual era a largura da amostra no ensaio M1?", hint: "valor com ressalva na fonte" },
  { q: "Qual era a velocidade do ar no ensaio M1?", hint: "condição de entrada" },
  { q: "Quais valores do M1 são condições de entrada e quais são resultados observados?", hint: "entrada × resultado" },
  { q: "O que a fonte não informa sobre o ensaio M1?", hint: "lacunas" },
  { q: "Qual era a geometria do duto no ensaio M1?", hint: "dado ausente na fonte" },
  { q: "Qual seria a velocidade de propagação da chama com 30% de oxigênio?", hint: "extrapolação numérica" },
  { q: "Como a chama se comportaria na Estação Espacial Internacional com outra pressão?", hint: "extrapolação" },
  { q: "Esse material seria seguro para uma nave espacial?", hint: "fora do escopo" },
];
