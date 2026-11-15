import { api, type Experiment } from "./api";

/** Todos os experimentos do catálogo (curados e importados), com parâmetros e lacunas. */
export async function loadAllExperiments(): Promise<Experiment[]> {
  const docs = await api.documents();
  const ids = docs.flatMap((d) => d.experiments.map((e) => e.experiment_id));
  return Promise.all(ids.map((id) => api.experiment(id)));
}
