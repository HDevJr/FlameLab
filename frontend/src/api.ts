// Cliente da API do FlameLab. Todas as telas leem dados reais do backend; nada é simulado aqui.

export type Evidence = {
  evidence_id?: string; document_id?: string; page_pdf: number | null; page_printed: number | null;
  column_label?: string | null; quote: string | null; locator_pt: string; literal_check?: string;
};
export type FieldComparison = {
  field: "value" | "unit" | "page"; label_pt: string; expected: string | number | null; received: string | number | null;
  status: "MATCH" | "CONVERTIBLE" | "MISMATCH" | "MISSING" | "INCOMPATIBLE" | "UNSUPPORTED" | "UNEXPECTED" | "UNREADABLE" | "AMBIGUOUS" | "NOT_APPLICABLE";
  detail_pt: string | null; expected_si?: string; received_si?: string; from_value_field?: boolean;
};
export type SemanticFlag = { code: string; severity: "BLOCKING" | "INFO"; title_pt: string; detail_pt: string; terms: string[] };
export type ReviewEvent = {
  at: string; action: "CONFIRM" | "CORRECT" | "DOUBT" | "DIVERGENCE"; outcome: "APPROVED" | "REFUSED" | "RECORDED" | "CORRECTED";
  reviewer: string; notes: string | null; observed_value: string | null; observed_unit: string | null;
  observed_page_pdf: number | null; code?: string; message?: string; comparisons?: FieldComparison[] | null;
  semantic_flags?: SemanticFlag[] | null; prefilled_unchanged?: boolean; before?: Record<string, unknown>; after?: Record<string, unknown>;
};
export type UnitInfo = { raw: string | null; canonical: string | null; display: string | null; dimension_pt: string | null; supported: boolean; has_unit: boolean };
export type Parameter = {
  record_id: string; parameter: string; label_pt: string; role: "CONDICAO" | "OBSERVAVEL" | "METADADO";
  nature: string; status: string; original: { value: number | string | null; unit: string | null; raw_text?: string } | null;
  normalized: { value: number; unit: string } | null; evidence: Evidence[]; caveats_pt: string[];
  extraction?: { method: string; by: string } | null; reviewer?: string | null;
  review?: { reviewer: string; reviewed_at: string | null; notes: string | null; checked_document_sha256: string | null } | null;
  events?: ReviewEvent[];
  technical_name?: string; label_source?: "IA" | "GLOSSARIO" | "HUMANO" | "CURADORIA"; unit_info?: UnitInfo; semantic_flags?: SemanticFlag[];
  original_extraction?: { label_pt: string | null; original: { value: number | string | null; unit: string | null } } | null;
  corrections?: { at: string; by: string; notes: string; before: Record<string, unknown>; after: Record<string, unknown>; reopened: boolean }[];
  review_history?: { reviewer: string; reviewed_at: string | null }[];
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
export type Step = {
  key: string; label_pt: string; state: "PENDING" | "RUNNING" | "DONE" | "FAILED" | "SKIPPED";
  summary_pt: string | null; technical: string[]; limitation_pt: string | null;
  started_at: string | null; finished_at: string | null; duration_ms: number | null;
};
export type Batch = { batch: number; pages: string; chars: number; duration_ms: number; accepted: number; rejected: number; error: string | null; usage?: { total_tokens?: number | null } | null };
export type Coverage = {
  mode: "CURATED" | "AI_FULL" | "AI_PARTIAL" | "NONE"; total_pages: number | null; processed_ranges: string;
  not_processed_ranges: string; without_text_ranges: string; reasons_pt: string[]; summary_pt: string;
  pages_processed: number[]; batches?: Batch[]; limits?: { max_batches: number };
};
export type ImportRecord = {
  import_id: string; filename: string; sha256: string; size_bytes: number; status: string; steps: Step[];
  document: { document_id: string; title: string | null; page_count: number; identifiers: Record<string, string[]> };
  nasa_provenance: Provenance | null; experiments: Experiment[]; warnings_pt: string[]; coverage: Coverage | null;
  extraction: { model: string; rejected: { name: string; reason: string }[]; batches: Batch[]; batches_planned_total: number } | null;
  metrics: { total_ms: number | null; per_step_ms?: Record<string, number | null> };
};
export type Analysis = {
  generated_at: string;
  document: { document_id: string; title: string; origin: string; import_id: string | null; sha256: string | null; pages: number | null; url: string | null };
  provenance: Provenance; coverage: Coverage;
  experiments: { experiment_id: string; label: string; phenomena: string[]; parameters: number; reviewed: number; pending: number; gaps: number;
    fds: { status: string | null; label_pt: string; reasons_pt: string[]; can_simulate: boolean } }[];
  totals: { experiments: number; parameters: number; reviewed: number; pending: number; gaps: number };
  sources: { source: string; state: string; state_pt: string; record_id: string | null; url: string | null; title: string | null }[];
  divergences: { field: string; label_pt: string; divergence_pt: string | null; complementary_source: string | null }[];
  enrichment: { available: boolean; mode: string | null; generated_at: string | null; warnings_pt: string[]; related_count: number };
  conclusions_pt: string[]; not_validated_pt: string[];
  metrics: ImportRecord["metrics"] | null; steps: Step[] | null;
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
export type EditableCondition = { parameter: string; label_pt: string; value: number; unit: string | null; status: string; rule_pt: string; source_pt: string | null };
export type Compatibility = {
  experiment_id: string; status: "COMPATIBLE" | "MISSING_PARAMETERS" | "UNSUPPORTED_PHYSICS" | "REQUIRES_REVIEW";
  reasons_pt: string[]; missing: string[]; unreviewed: string[]; editable_conditions: string[]; editable: EditableCondition[];
  reference_observables: { parameter: string; label_pt: string; status: string }[];
  actions: { analyze: boolean; prepare: boolean; alter: boolean; simulate: boolean }; executor_available: boolean;
};
export type ModelParam = { name: string; label_pt: string; group: string; unit: string; default: number; min: number; max: number; step: number | null; help_pt: string | null };
export type SimModel = { model_id: string; title_pt: string; purpose: string; label_pt: string; description_pt: string; implemented: boolean; parameters: ModelParam[]; required_inputs: string[]; template_source: { origin: string } | null };
export type Change = { name: string; from_value: number; to_value: number; unit: string; label_pt?: string | null; base_status?: string | null };
export type Scenario = {
  scenario_id: string; kind: "BASE" | "DERIVED"; model_id: string | null; experiment_id: string | null; scope: "EXPERIMENT" | "DEMO";
  title_pt: string; hypothesis_pt: string | null; changes: Change[]; values: Record<string, number>; executable: boolean;
  blocked_reasons_pt: string[]; note_pt: string; status: string;
};
export type Artifact = { kind: string; name: string; sha256: string; size_bytes: number; meta: Record<string, unknown> };
export type Run = {
  run_id: string; scenario_id: string; model_id: string; purpose: string; label_pt: string; state: string; demo: boolean; scope: "EXPERIMENT" | "DEMO";
  fds_sha256: string | null; fds_version: string | null; smokeview_version: string | null; ffmpeg_version: string | null;
  parameters: Record<string, number>; changes: Change[]; timestamps: Record<string, string>; failure_reason: string | null;
  artifacts: Artifact[]; timings_ms: Record<string, number | null>;
  progress: { simulated_time_s: number; t_end_s: number; fraction: number; source: string } | null;
  results: { fds_wall_clock_s?: number; frame_count?: number; hrr_series?: { points: [number, number][]; y_unit: string; x_unit: string } };
  log_tail: string[];
};
export type SimStatus = { executor: string; available: boolean; detail: string; demo: boolean; versions: { fds: string | null; smokeview: string | null; ffmpeg: string | null } | null; limits: Record<string, unknown> };
export type ReviewResult = { outcome: "APPROVED" | "RECORDED" | "CORRECTED"; status: string; event: ReviewEvent; reviewed_at?: string; reopened?: boolean };

export type ReviewDetails = { accepted: boolean; code: string; reason_code: string; comparisons: FieldComparison[]; failed_fields: string[]; semantic_flags?: SemanticFlag[] };
export type ReviewPreview = {
  record_id: string; status: string; comparisons: FieldComparison[]; fields_accepted: boolean; field_code: string | null;
  field_message_pt: string | null; failed_fields: string[]; semantic_flags: SemanticFlag[]; blocking_flags: SemanticFlag[];
  reviewer_issue: string | null; accepted: boolean;
};
export type RecordContext = { found: boolean; page: number | null; quote: string | null; before: string; after: string; reason_pt?: string };

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: ReviewDetails) { super(message); }
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
    throw new ApiError(resp.status, e.code ?? "HTTP_ERROR", e.message ?? `Erro ${resp.status}`, e.details);
  }
  return body.data as T;
}

const json = (method: string, data: unknown): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

export type ReviewBody = {
  action: "CONFIRM" | "CORRECT" | "DOUBT" | "DIVERGENCE"; reviewer: string; observed_value?: string | null; observed_unit?: string | null;
  observed_page_pdf?: number | null; notes?: string | null; checked_pdf?: boolean; prefilled_unchanged?: boolean;
  corrected_label_pt?: string | null; corrected_value?: string | null; corrected_unit?: string | null;
};

export const api = {
  documents: () => call<DocumentItem[]>("/api/documents"),
  document: (id: string) => call<DocumentItem>(`/api/documents/${id}`),
  analysis: (id: string) => call<Analysis>(`/api/documents/${id}/analysis`),
  experiment: (id: string) => call<Experiment>(`/api/experiments/${id}`),
  compatibility: (id: string) => call<Compatibility>(`/api/experiments/${id}/compatibility`),
  enrichment: (id: string) => call<Enrichment>(`/api/documents/${id}/enrichment`),
  runEnrichment: (id: string) => call<Enrichment>(`/api/documents/${id}/enrichment`, { method: "POST" }),
  upload: (file: File) => { const f = new FormData(); f.append("file", file); return call<ImportRecord>("/api/imports", { method: "POST", body: f }); },
  importRecord: (id: string) => call<ImportRecord>(`/api/imports/${id}`),
  review: (recordId: string, body: ReviewBody) => call<ReviewResult>(`/api/records/${recordId}/review`, json("POST", body)),
  reviewPreview: (recordId: string, body: { reviewer?: string | null; observed_value?: string | null; observed_unit?: string | null; observed_page_pdf?: number | null }) =>
    call<ReviewPreview>(`/api/records/${recordId}/review/preview`, json("POST", body)),
  recordContext: (recordId: string, evidence = 0) => call<RecordContext>(`/api/records/${recordId}/context?evidence=${evidence}`),
  simStatus: () => call<SimStatus>("/api/simulation/status"),
  models: () => call<SimModel[]>("/api/simulation/models"),
  createScenario: (d: { model_id: string; values: Record<string, number>; title?: string }) => call<Scenario>("/api/scenarios", json("POST", d)),
  createExperimentScenario: (experimentId: string, d: { changes: { parameter: string; value: number }[]; title?: string; hypothesis?: string }) =>
    call<Scenario>(`/api/experiments/${experimentId}/scenarios`, json("POST", d)),
  scenario: (id: string) => call<Scenario>(`/api/scenarios/${id}`),
  submit: (scenario_id: string) => call<Run>("/api/simulations", json("POST", { scenario_id })),
  runs: () => call<Run[]>("/api/simulations"),
  run: (id: string) => call<Run>(`/api/simulations/${id}`),
};

export const artifactUrl = (runId: string, name: string) => `/api/simulations/${runId}/artifacts/${name}`;
export const documentFileUrl = (documentId: string, page?: number | null) =>
  `/api/documents/${documentId}/file${page ? `#page=${page}` : ""}`;
