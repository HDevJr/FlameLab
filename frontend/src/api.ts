// Cliente da API do FlameLab. Todas as telas leem dados reais do backend; nada é simulado aqui.

export type Evidence = {
  evidence_id?: string; document_id?: string; page_pdf: number | null; page_printed: number | null;
  column_label?: string | null; quote: string | null; locator_pt: string;
};
export type Parameter = {
  record_id: string; parameter: string; label_pt: string; role: "CONDICAO" | "OBSERVAVEL" | "METADADO";
  nature: string; status: string; original: { value: number | string | null; unit: string | null; raw_text?: string } | null;
  normalized: { value: number; unit: string } | null; evidence: Evidence[]; caveats_pt: string[];
  extraction?: { method: string; by: string } | null; reviewer?: string | null;
};
export type Gap = { gap_id: string; parameter: string; label_pt: string; explanation_pt: string; purpose_blocked: string[]; origin: string };
export type Review = { total: number; reviewed: number; pending: number; gaps: number };
export type Experiment = {
  experiment_id: string; label: string; origin: string; document_id: string | null; document_title: string | null;
  description: string | null; phenomena: string[]; parameters: Parameter[]; gaps: Gap[]; review: Review;
};
export type ExperimentSummary = { experiment_id: string; label: string; phenomena: string[]; review: Review };
export type Provenance = { state: "VERIFIED" | "CANDIDATE" | "MISMATCH" | "PENDING"; label_pt: string; reasons_pt: string[]; ntrs_id: string | null };
export type DocumentItem = {
  document_id: string; title: string; origin: "CURATED" | "IMPORTED"; url: string | null; sha256: string | null;
  size_bytes: number | null; nasa_provenance: Provenance; import_id: string | null; experiments: ExperimentSummary[];
};
export type Step = { key: string; label_pt: string; state: "PENDING" | "RUNNING" | "DONE" | "FAILED" | "SKIPPED"; detail_pt: string | null };
export type ImportRecord = {
  import_id: string; filename: string; sha256: string; size_bytes: number; status: string; steps: Step[];
  document: { document_id: string; title: string | null; page_count: number; identifiers: Record<string, string[]> };
  nasa_provenance: Provenance | null; experiments: Experiment[]; warnings_pt: string[];
  extraction: { model: string; rejected: { name: string; reason: string }[] } | null;
};
export type Match = {
  source: string; state: string; match_type: string; source_record_id: string | null; source_url: string | null;
  title: string | null; score: number | null; reasons_pt: string[]; note_pt: string | null;
  rejected_candidates: { id: string | number; title: string; score: number }[];
};
export type EnrichRecord = {
  field: string; label_pt: string; scope: string; original_value: unknown; original_source: string | null;
  complementary_value: unknown; complementary_source: string | null; complementary_source_id: string | null;
  state: string; divergence_pt: string | null; curation_decision: string; review_status: string;
};
export type Enrichment = {
  document_id: string; generated_at: string; mode: string; matches: Match[]; records: EnrichRecord[];
  related_documents: { ntrs_id: string; title: string; url: string; note_pt: string }[];
  operations: { source: string; url: string; mode: string; http_status: number | null; ok: boolean; error: string | null }[];
  warnings_pt: string[]; promoted_records: number;
};
export type Compatibility = {
  experiment_id: string; status: "COMPATIBLE" | "MISSING_PARAMETERS" | "UNSUPPORTED_PHYSICS" | "REQUIRES_REVIEW";
  reasons_pt: string[]; missing: string[]; unreviewed: string[]; editable_conditions: string[];
  reference_observables: { parameter: string; label_pt: string; status: string }[];
  actions: { analyze: boolean; prepare: boolean; alter: boolean; simulate: boolean }; executor_available: boolean;
};
export type ModelParam = { name: string; label_pt: string; group: string; unit: string; default: number; min: number; max: number; step: number | null; help_pt: string | null };
export type SimModel = { model_id: string; title_pt: string; purpose: string; label_pt: string; description_pt: string; implemented: boolean; parameters: ModelParam[]; required_inputs: string[]; template_source: { origin: string } | null };
export type Change = { name: string; from_value: number; to_value: number; unit: string };
export type Scenario = {
  scenario_id: string; kind: "BASE" | "DERIVED"; model_id: string; experiment_id: string | null; title_pt: string;
  changes: Change[]; values: Record<string, number>; executable: boolean; blocked_reasons_pt: string[]; note_pt: string; status: string;
};
export type Artifact = { kind: string; name: string; sha256: string; size_bytes: number; meta: Record<string, unknown> };
export type Run = {
  run_id: string; scenario_id: string; model_id: string; purpose: string; label_pt: string; state: string; demo: boolean;
  fds_sha256: string | null; fds_version: string | null; smokeview_version: string | null; ffmpeg_version: string | null;
  parameters: Record<string, number>; changes: Change[]; timestamps: Record<string, string>; failure_reason: string | null;
  artifacts: Artifact[]; results: { fds_wall_clock_s?: number; frame_count?: number; hrr_series?: { points: [number, number][]; y_unit: string; x_unit: string };
    devc_series?: { series: Record<string, [number, number][]>; unit: Record<string, string> } }; log_tail: string[];
};
export type SimStatus = { executor: string; available: boolean; detail: string; demo: boolean; versions: { fds: string | null; smokeview: string | null; ffmpeg: string | null } | null; limits: Record<string, unknown> };

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(path, init);
  } catch {
    throw new ApiError(0, "BACKEND_UNREACHABLE", "Servidor local não encontrado. Inicie o backend (uvicorn) na porta 8000.");
  }
  const body = await resp.json().catch(() => null);
  if (!resp.ok) {
    const e = body?.error ?? {};
    throw new ApiError(resp.status, e.code ?? "HTTP_ERROR", e.message ?? `Erro ${resp.status}`);
  }
  return body.data as T;
}

const json = (method: string, data: unknown): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

export const api = {
  documents: () => call<DocumentItem[]>("/api/documents"),
  document: (id: string) => call<DocumentItem>(`/api/documents/${id}`),
  experiment: (id: string) => call<Experiment>(`/api/experiments/${id}`),
  compatibility: (id: string) => call<Compatibility>(`/api/experiments/${id}/compatibility`),
  enrichment: (id: string) => call<Enrichment>(`/api/documents/${id}/enrichment`),
  runEnrichment: (id: string) => call<Enrichment>(`/api/documents/${id}/enrichment`, { method: "POST" }),
  upload: (file: File) => { const f = new FormData(); f.append("file", file); return call<ImportRecord>("/api/imports", { method: "POST", body: f }); },
  importRecord: (id: string) => call<ImportRecord>(`/api/imports/${id}`),
  simStatus: () => call<SimStatus>("/api/simulation/status"),
  models: () => call<SimModel[]>("/api/simulation/models"),
  createScenario: (d: { model_id: string; values: Record<string, number>; title?: string; experiment_id?: string }) => call<Scenario>("/api/scenarios", json("POST", d)),
  scenario: (id: string) => call<Scenario>(`/api/scenarios/${id}`),
  submit: (scenario_id: string) => call<Run>("/api/simulations", json("POST", { scenario_id })),
  runs: () => call<Run[]>("/api/simulations"),
  run: (id: string) => call<Run>(`/api/simulations/${id}`),
};

export const artifactUrl = (runId: string, name: string) => `/api/simulations/${runId}/artifacts/${name}`;
