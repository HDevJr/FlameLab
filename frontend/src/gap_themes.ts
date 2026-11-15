import type { Gap } from "./api";

/** Agrupa lacunas por tema para leitura. O nome e a explicação de cada lacuna vêm do dataset; só o agrupamento é daqui. */
const THEME_OF: Record<string, string> = {
  sample_length: "Geometria e montagem", duct_geometry: "Geometria e montagem", sample_holder_substrate: "Geometria e montagem",
  ambient_pressure: "Condições ambientais e escoamento", ambient_temperature: "Condições ambientais e escoamento",
  inlet_flow_profile: "Condições ambientais e escoamento", anemometer_location: "Condições ambientais e escoamento",
  ignition_procedure: "Combustão e material", pmma_pyrolysis_properties: "Combustão e material",
  o2_time_profile: "Medição e incerteza", measurement_uncertainty: "Medição e incerteza", flame_front_tracking_method: "Medição e incerteza",
};
export const THEME_ORDER = ["Geometria e montagem", "Condições ambientais e escoamento", "Combustão e material", "Medição e incerteza", "Outras lacunas"];

export function groupGaps(gaps: Gap[]): [string, Gap[]][] {
  const by = new Map<string, Gap[]>();
  for (const g of gaps) { const t = THEME_OF[g.parameter] ?? "Outras lacunas"; by.set(t, [...(by.get(t) ?? []), g]); }
  return THEME_ORDER.filter((t) => by.has(t)).map((t) => [t, by.get(t)!]);
}

/** Gate FDS (planning/05 §6) que cada lacuna impede. G1 geometria/condições, G2 material, G4 comparação. */
export const GATE_OF: Record<string, "G1" | "G2" | "G4"> = {
  sample_length: "G1", duct_geometry: "G1", sample_holder_substrate: "G1", inlet_flow_profile: "G1", anemometer_location: "G1",
  ambient_pressure: "G1", ambient_temperature: "G1", ignition_procedure: "G1",
  pmma_pyrolysis_properties: "G2", measurement_uncertainty: "G4", flame_front_tracking_method: "G4",
};
