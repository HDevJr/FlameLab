import type { Experiment } from "./api";
import { valueText } from "./lib";

export type Hit = { id: string; experimentId: string; experiment: string; kind: "Parâmetro" | "Lacuna"; title: string; snippet: string; score: number; why: string[]; to: string };

const norm = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const tokens = (s: string) => norm(s).split(/[^a-z0-9.]+/).filter((t) => t.length > 1);

/** Busca textual simples. A pontuação soma pesos por campo; "why" lista exatamente o que casou (fonte única do score). */
export function searchExperiments(exps: Experiment[], query: string): Hit[] {
  const q = [...new Set(tokens(query))];
  if (!q.length) return [];
  const hits: Hit[] = [];
  for (const e of exps) {
    const base = { experimentId: e.experiment_id, experiment: e.label };
    for (const p of e.parameters) {
      const fields: [string, string, number][] = [
        ["nome", p.label_pt, 3], ["nome técnico", p.parameter, 3], ["valor", `${valueText(p.original?.value)} ${p.original?.unit ?? ""}`, 2],
        ["citação da fonte", p.evidence.map((x) => x.quote ?? "").join(" "), 1], ["ressalva", (p.caveats_pt ?? []).join(" "), 1],
      ];
      const h = score(q, fields);
      if (h) hits.push({ ...base, id: p.record_id, kind: "Parâmetro", title: p.label_pt, score: h.score, why: h.why, to: `/experimentos/${e.experiment_id}`,
        snippet: `${valueText(p.original?.value) || "—"} ${p.original?.unit ?? ""} · ${p.status === "CONFERIDO_FONTE" ? "conferido" : "não revisado"}` });
    }
    for (const g of e.gaps) {
      const h = score(q, [["nome", g.label_pt, 3], ["nome técnico", g.parameter, 3], ["explicação", g.explanation_pt, 1]]);
      if (h) hits.push({ ...base, id: g.gap_id, kind: "Lacuna", title: g.label_pt, score: h.score, why: h.why, to: `/experimentos/${e.experiment_id}#lacunas`, snippet: "AUSENTE NA FONTE" });
    }
  }
  return hits.sort((a, b) => b.score - a.score || a.title.localeCompare(b.title, "pt"));
}

function score(q: string[], fields: [string, string, number][]): { score: number; why: string[] } | null {
  let s = 0; const why: string[] = [];
  for (const [name, text, w] of fields) {
    const t = new Set(tokens(text)); const joined = norm(text);
    const matched = q.filter((x) => t.has(x) || joined.includes(x));
    if (matched.length) { s += w * matched.length; why.push(`${name}: ${matched.join(", ")} (+${w * matched.length})`); }
  }
  return s ? { score: s, why } : null;
}
