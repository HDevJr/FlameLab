import type { Experiment, Parameter } from "./api";

export type Cell = { text: string; si: number | null; siUnit: string | null; status: string; page: string | null } | null;
export type CompareRow = { key: string; label: string; role: Parameter["role"]; a: Cell; b: Cell; differs: boolean; note: string | null };
export type Comparison = { rows: CompareRow[]; differing: number; onlyA: number; onlyB: number; warnings: string[] };

const cellOf = (p: Parameter | undefined): Cell => !p ? null : {
  text: `${p.original?.value ?? "—"}${p.original?.unit ? ` ${p.original.unit}` : ""}`,
  si: p.normalized ? p.normalized.value : null, siUnit: p.normalized ? p.normalized.unit : null, status: p.status,
  page: p.evidence[0]?.locator_pt || (p.evidence[0]?.page_pdf ? `PDF p. ${p.evidence[0].page_pdf}` : null),
};

/** Alinha os parâmetros por nome técnico. Compara em SI quando ambos têm a mesma unidade normalizada; caso contrário não decide. */
export function compareExperiments(a: Experiment, b: Experiment): Comparison {
  const A = new Map(a.parameters.map((p) => [p.parameter, p]));
  const B = new Map(b.parameters.map((p) => [p.parameter, p]));
  const keys = [...new Set([...A.keys(), ...B.keys()])];
  const rows: CompareRow[] = keys.map((key) => {
    const pa = A.get(key), pb = B.get(key);
    const ca = cellOf(pa), cb = cellOf(pb);
    let differs = false, note: string | null = null;
    if (ca && cb) {
      if (ca.si != null && cb.si != null && ca.siUnit === cb.siUnit) {
        const scale = Math.max(Math.abs(ca.si), Math.abs(cb.si), 1e-12);
        differs = Math.abs(ca.si - cb.si) / scale > 1e-9;
      } else if (ca.si != null && cb.si != null) { note = "Unidades normalizadas diferentes: comparação numérica não é possível."; differs = true; }
      else { differs = ca.text !== cb.text; note = differs ? null : null; }
      if (pa && pb && pa.role !== pb.role) note = "O papel do parâmetro difere entre os experimentos.";
    } else note = ca ? "Ausente no segundo experimento." : "Ausente no primeiro experimento.";
    return { key, label: (pa ?? pb)!.label_pt, role: (pa ?? pb)!.role, a: ca, b: cb, differs: differs || !(ca && cb), note };
  }).sort((x, y) => x.role.localeCompare(y.role) || x.label.localeCompare(y.label, "pt"));
  const warnings: string[] = [];
  if (a.document_id !== b.document_id) warnings.push("Os experimentos vêm de documentos diferentes; as condições de contorno podem não ser comparáveis.");
  const unrev = [a, b].filter((e) => e.parameters.some((p) => p.status !== "CONFERIDO_FONTE")).length;
  if (unrev) warnings.push("Há valores não conferidos por uma pessoa em pelo menos um dos experimentos.");
  warnings.push("Comparação de valores registrados; não é avaliação de risco, segurança ou desempenho.");
  return { rows, differing: rows.filter((r) => r.differs && r.a && r.b).length, onlyA: rows.filter((r) => r.a && !r.b).length, onlyB: rows.filter((r) => !r.a && r.b).length, warnings };
}
