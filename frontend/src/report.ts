import type { Experiment, Parameter } from "./api";
import { valueText } from "./lib";

export type ReportMeta = { datasetVersion: string | null; generatedAt: string };

const ROLE: Record<Parameter["role"], string> = { CONDICAO: "Condições de entrada", OBSERVAVEL: "Resultados observados", METADADO: "Metadados" };
const STATUS: Record<string, string> = { CONFERIDO_FONTE: "conferido na fonte", EXTRAIDO_NAO_REVISADO: "extraído, não revisado" };

const val = (p: Parameter) => `${valueText(p.original?.value) || "—"}${p.original?.unit ? ` ${p.original.unit}` : ""}`;
const si = (p: Parameter) => (p.normalized ? `${valueText(Number(p.normalized.value.toPrecision(8)))} ${p.normalized.unit}` : "");
const cell = (s: string) => s.replace(/\|/g, "\\|").replace(/\n/g, " ");

/** Relatório em Markdown: só o que o backend registrou (valor, unidade, estado, origem, lacunas, ressalvas). Nada é estimado. */
export function experimentMarkdown(e: Experiment, m: ReportMeta): string {
  const out: string[] = [];
  out.push(`# Relatório do experimento — ${e.label}`, "");
  out.push(`- Documento: ${e.document_title ?? e.document_id ?? "—"}${e.document_id ? ` (\`${e.document_id}\`)` : ""}`);
  out.push(`- Versão do dataset: \`${m.datasetVersion ?? "não informada"}\``);
  out.push(`- Gerado em: ${m.generatedAt}`);
  out.push(`- Parâmetros: ${e.parameters.length} · conferidos: ${e.parameters.filter((p) => p.status === "CONFERIDO_FONTE").length} · lacunas: ${e.gaps.length}`, "");
  for (const role of ["CONDICAO", "OBSERVAVEL", "METADADO"] as const) {
    const rows = e.parameters.filter((p) => p.role === role);
    if (!rows.length) continue;
    out.push(`## ${ROLE[role]}`, "", "| Parâmetro | Valor | SI | Estado | Origem |", "|---|---|---|---|---|");
    for (const p of rows) {
      const origin = p.evidence.map((ev) => ev.locator_pt || (ev.page_pdf ? `PDF p. ${ev.page_pdf}` : "")).filter(Boolean).join("; ") || "Referência não vinculada";
      out.push(`| ${cell(p.label_pt)} | ${cell(val(p))} | ${cell(si(p))} | ${STATUS[p.status] ?? p.status} | ${cell(origin)} |`);
    }
    out.push("");
  }
  const cav = e.parameters.filter((p) => (p.caveats_pt?.length ?? 0) > 0);
  if (cav.length) {
    out.push("## Ressalvas da fonte", "");
    for (const p of cav) for (const c of p.caveats_pt) out.push(`- **${p.label_pt}:** ${c}`);
    out.push("");
  }
  out.push("## Lacunas declaradas (AUSENTE NA FONTE)", "");
  if (!e.gaps.length) out.push("Nenhuma lacuna registrada.");
  for (const g of e.gaps) out.push(`- **${g.label_pt}** — ${g.explanation_pt}${g.purpose_blocked.length ? ` _(impede: ${g.purpose_blocked.join(", ")})_` : ""}`);
  out.push("", "---", "Projeto independente desenvolvido para o NASA Space Apps Challenge. Não é endossado pela NASA nem pelo NIST.",
    "Valores “extraídos, não revisados” não são dados conferidos. Lacunas não foram estimadas.", "");
  return out.join("\n");
}

export const experimentJson = (e: Experiment, m: ReportMeta): string =>
  JSON.stringify({ generated_at: m.generatedAt, dataset_version: m.datasetVersion, experiment: e }, null, 2);

/** Baixa um texto como arquivo (sem enviar nada a servidor). */
export function downloadText(filename: string, text: string, mime: string) {
  const url = URL.createObjectURL(new Blob([text], { type: `${mime};charset=utf-8` }));
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
