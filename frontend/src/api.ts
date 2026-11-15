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
  at: string; action: "CONFIRM" | "CORRECT" | "REOPEN" | "DOUBT" | "DIVERGENCE"; outcome: "APPROVED" | "REFUSED" | "RECORDED" | "CORRECTED" | "REOPENED";
  reviewer: string; notes: string | null; observed_value: string | null; observed_unit: string | null;
  observed_page_pdf: number | null; code?: string; message?: string; comparisons?: FieldComparison[] | null;
  semantic_flags?: SemanticFlag[] | null; prefilled_unchanged?: boolean; before?: Record<string, unknown>; after?: Record<string, unknown>;
};
export type UnitState = "PHYSICAL" | "UNSUPPORTED" | "DIMENSIONLESS" | "MISSING" | "NOT_APPLICABLE";
export type UnitInfo = {
  raw: string | null; canonical: string | null; display: string | null; dimension: string | null; dimension_pt: string | null; supported: boolean; has_unit: boolean;
  state?: UnitState; expected_dimension?: string | null; expected_dimension_pt?: string | null;
};
export type IntegrityFinding = { code: string; severity: "BLOCKING" | "ATTENTION"; field: string; title_pt: string; detail_pt: string; terms: string[] };
export type Integrity = {
  status: "OK" | "ATTENTION" | "INCONSISTENT"; findings: IntegrityFinding[]; pdf_value: { found: boolean | null; literal: string | null };
  unit_source?: "QUOTE" | "SYMBOL_UNREADABLE" | "NOT_FOUND" | "NOT_CHECKED"; condition_candidates: { text: string; value: number; unit: string | null; dimension: string | null }[];
};
export type Condition = { text: string; value: number | null; unit: string | null; source: "IA" | "HUMANO"; by?: string };
export type ReviewComponents = { number: boolean; unit: boolean; interpretation: boolean; condition: boolean | null; unit_verified_in_pdf: boolean; prefilled_unchanged: boolean };
export type Parameter = {
  record_id: string; parameter: string; label_pt: string; role: "CONDICAO" | "OBSERVAVEL" | "METADADO";
  nature: string; status: string; original: { value: number | string | null; unit: string | null; raw_text?: string } | null;
  normalized: { value: number; unit: string } | null; evidence: Evidence[]; caveats_pt: string[];
  extraction?: { method: string; by: string } | null; reviewer?: string | null;
  review?: { reviewer: string; reviewed_at: string | null; notes: string | null; checked_document_sha256: string | null; components?: ReviewComponents } | null;
  events?: ReviewEvent[];
  integrity?: Integrity; review_scope?: "FULL" | "LEGACY" | null; condition?: Condition | null;
  technical_name?: string; label_source?: "IA" | "GLOSSARIO" | "HUMANO" | "CURADORIA"; unit_info?: UnitInfo; semantic_flags?: SemanticFlag[];
  original_extraction?: { label_pt: string | null; original: { value: number | string | null; unit: string | null } } | null;
  corrections?: { at: string; by: string; notes: string; before: Record<string, unknown>; after: Record<string, unknown>; reopened: boolean }[];
  review_history?: { reviewer: string; reviewed_at: string | null; reopen_reason?: string }[];
};
export type GapRelation = { record_id: string; label_pt: string | null; value: number | string | null; unit: string | null; page: number | null; relation: string; scope_differs: boolean; explanation_pt: string };
export type GapDecision = { at: string; gap_id: string; decision: "COVERED" | "PARTIAL" | "DISTINCT"; reviewer: string; notes: string; record_id: string | null };
export type Gap = {
  gap_id: string; parameter: string; label_pt: string; explanation_pt: string; purpose_blocked: string[]; origin: string;
  related_parameters?: GapRelation[]; decision?: GapDecision | null; coverage_state?: "ABERTA" | "POSSIVEL_SOBREPOSICAO" | "PARCIALMENTE_COBERTA" | "COBERTA" | "DISTINTA";
};
export type Review = { total: number; reviewed: number; pending: number; gaps: number };
export type Experiment = {
  experiment_id: string; label: string; origin: string; document_id: string | null; document_title: string | null;
  description: string | null; phenomena: string[]; parameters: Parameter[]; gaps: Gap[]; review: Review;
};
export type ExperimentSummary = { experiment_id: string; label: string; phenomena: string[]; review: Review; model_state_pt?:string };
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
  readiness?: Readiness;
};
export type ReadinessDimension = { key: string; label_pt: string; status: string; tone: "ok" | "warn" | "bad" | "muted"; summary_pt: string; items: string[] };
export type Readiness = { dimensions: ReadinessDimension[]; can_simulate: boolean };
export type AuditRecord = {
  record_id: string; document_id: string; experiment_id: string; parameter: string; label_pt: string; status: string; value: number | string | null; unit_raw: string | null;
  unit_state: string | null; page: number | null; quote: string | null; classification: "INCONSISTENT_CONFIRMED" | "LEGACY_REVIEW" | "ATTENTION" | "OK";
  review: { reviewer: string | null; reviewed_at: string | null; scope: string | null } | null; integrity_findings: IntegrityFinding[]; semantic_flags: SemanticFlag[];
  audit_anomalies: { code: string; at: string; detail_pt: string }[]; proposals: { finding: string; action: string; proposal_pt: string }[];
};
export type AuditReport = {
  generated_at: string; read_only: boolean; note_pt: string; records: AuditRecord[];
  summary: { records: number; confirmed: number; by_classification: Record<string, number>; confirmed_with_blocking_inconsistency: number; confirmed_without_interpretation_confirmation: number };
};
export type VersionInfo = { app_version: string; capabilities: string[] };
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
  case_id?: string | null; case_version?: number | null;
  run_id: string; scenario_id: string; model_id: string; purpose: string; label_pt: string; state: string; demo: boolean; scope: "EXPERIMENT" | "DEMO";
  fds_sha256: string | null; fds_version: string | null; smokeview_version: string | null; ffmpeg_version: string | null;
  parameters: Record<string, number>; changes: Change[]; timestamps: Record<string, string>; failure_reason: string | null;
  artifacts: Artifact[]; timings_ms: Record<string, number | null>;
  progress: { simulated_time_s: number; t_end_s: number; fraction: number; source: string } | null;
  results: { fds_wall_clock_s?: number; frame_count?: number; hrr_series?: { points: [number, number][]; y_unit: string; x_unit: string } };
  log_tail: string[];
};
export type SimStatus = { executor: string; available: boolean; detail: string; demo: boolean; versions: { fds: string | null; smokeview: string | null; ffmpeg: string | null } | null; limits: Record<string, unknown> };
export type ReviewResult = { outcome: "APPROVED" | "RECORDED" | "CORRECTED" | "REOPENED"; status: string; event: ReviewEvent; reviewed_at?: string; reopened?: boolean };

export type ReviewDetails = { accepted: boolean; code: string; reason_code: string; comparisons: FieldComparison[]; failed_fields: string[]; semantic_flags?: SemanticFlag[]; integrity_findings?: IntegrityFinding[] };
export type ReviewPreview = {
  record_id: string; status: string; comparisons: FieldComparison[]; fields_accepted: boolean; field_code: string | null;
  field_message_pt: string | null; failed_fields: string[]; semantic_flags: SemanticFlag[]; blocking_flags: SemanticFlag[];
  reviewer_issue: string | null; accepted: boolean; integrity_findings?: IntegrityFinding[]; blocking_integrity?: IntegrityFinding[];
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
  action: "CONFIRM" | "CORRECT" | "REOPEN" | "DOUBT" | "DIVERGENCE"; reviewer: string; observed_value?: string | null; observed_unit?: string | null;
  observed_page_pdf?: number | null; notes?: string | null; checked_pdf?: boolean; prefilled_unchanged?: boolean;
  corrected_label_pt?: string | null; corrected_value?: string | null; corrected_unit?: string | null;
  corrected_condition_text?: string | null; corrected_condition_value?: string | null; corrected_condition_unit?: string | null;
  interpretation_confirmed?: boolean; unit_verified_in_pdf?: boolean;
};

export const api = {
  guidedReview: (id: string, profile?: string) => call<GuidedJourney>(`/api/experiments/${id}/guided-review${profile ? `?profile_id=${encodeURIComponent(profile)}` : ""}`),
  guidedDecision: (id: string, gap: string, body: GuidedDecision, profile: string) => call<GuidedJourney>(`/api/experiments/${id}/guided-review/${gap}?profile_id=${encodeURIComponent(profile)}`, json("POST", body)),
  guidedCursor: (id: string, gap_id: string, expected_revision: number, profile: string) => call<GuidedJourney>(`/api/experiments/${id}/guided-review/cursor?profile_id=${encodeURIComponent(profile)}`, json("POST", {gap_id,expected_revision})),
  profiles: () => call<CaseProfile[]>("/api/simulation/profiles"),
  preparation: (id: string) => call<Preparation>(`/api/experiments/${id}/simulation-preparation`),
  createCase: (body: CaseRequest) => call<ScientificCase>("/api/cases", json("POST", body)),
  case: (id: string, version = 1) => call<CaseDiagnostic>(`/api/cases/${id}?version=${version}`),
  caseVersion: (id: string, body: CaseRequest) => call<ScientificCase>(`/api/cases/${id}/versions`, json("POST", body)),
  reviewCase: (id: string, version: number, reviewer: string, notes: string) => call<unknown>(`/api/cases/${id}/review?version=${version}`, json("POST", { reviewer, notes, accepted_defaults: true })),
  validateCase: (id: string, version: number) => call<CaseDiagnostic>(`/api/cases/${id}/validate?version=${version}`, json("POST", {})),
  submitCase: (id: string, version: number) => call<Run>("/api/simulations", json("POST", {case_id:id, case_version:version})),
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
  version: async (): Promise<VersionInfo | null> => {
    try {
      const response = await fetch("/api/version");
      if (!response.ok) return null;
      const value: unknown = await response.json();
      if (!value || typeof value !== "object" || !("app_version" in value) || typeof value.app_version !== "string"
        || !("capabilities" in value) || !Array.isArray(value.capabilities) || !value.capabilities.every((c: unknown) => typeof c === "string")) return null;
      return { app_version: value.app_version, capabilities: value.capabilities };
    } catch { return null; }
  },
  auditIntegrity: () => call<AuditReport>("/api/audit/integrity"),
  gapDecision: (gapId: string, body: { decision: "COVERED" | "PARTIAL" | "DISTINCT"; reviewer: string; notes: string; record_id?: string | null }) =>
    call<GapDecision>(`/api/gaps/${gapId}/decision`, json("POST", body)),
  reviewPreview: (recordId: string, body: { reviewer?: string | null; observed_value?: string | null; observed_unit?: string | null; observed_page_pdf?: number | null; unit_verified_in_pdf?: boolean }) =>
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

export type CaseProfile = { model_id: string; version: string; title_pt: string; approved: boolean; independent_only: boolean; parameters: {name:string;label_pt:string;unit:string;default:number;min:number;max:number}[]; limitations:string[] };
export type CaseAssumption = { parameter:string; value:number; unit:string; source:string; source_type:string; justification:string; author:string; limitations:string };
export type CaseRequest = { profile_id:string;profile_version:string;experiment_id?:string;title:string;assumptions:CaseAssumption[] };
export type ScientificCase = { content_sha256:string;content:CaseRequest & {case_id:string;version:number;values:Record<string,number>;label_pt:string} };
export type CaseDiagnostic = { state:string;blockers:string[];case:ScientificCase;approval:unknown;fds_sha256?:string };
export type Preparation = { state:string;conditions:Parameter[];ambiguous:Parameter[];observables:Parameter[];gaps:(Gap & {required:boolean;assumption_allowed:boolean;impact_pt:string;categories:string[]})[];blockers:string[] };

export type ResolutionState = "OPEN" | "IN_PROGRESS" | "SOURCE_SUBMITTED" | "ASSUMPTION_PROPOSED" | "UNDER_REVIEW" | "RESOLVED_FOR_PROFILE" | "BLOCKED";
export type GuidedProposal = {value:number|null;unit:string;details:string;source:string;location:string;evidence:string;author:string;justification:string;limitations:string};
export type GuidedAction = "DRAFT" | "SOURCE" | "ASSUMPTION" | "NOT_FOUND" | "DEFER" | "REQUEST_REVIEW" | "ACCEPT" | "REJECT";
export type GuidedEvent = {revision:number;at:string;action:GuidedAction|"NAVIGATE";author?:string;notes?:string;state:ResolutionState;review_state?:string;proposal?:GuidedProposal;draft?:Record<string,string>;case_id?:string;case_version?:number;sha256:string};
export type GuidedTask = Gap & {why_pt:string;impact_pt:string;required:boolean;state:ResolutionState;current:GuidedEvent|null;assumption_allowed:boolean;assumption_reason_pt:string;schema:{kind:"SCALAR"|"DOCUMENT";unit:string};known:Parameter[];history:GuidedEvent[];searched_in?:string[];possible_sources_pt?:string|null};
export type GuidedJourney = {experiment_id:string;title:string;profile:CaseProfile & {implemented:boolean;requirements?:{parameter:string;unit:string|null}[];additional_requirements?:string[]};revision:number;tasks:GuidedTask[];cursor:string|null;recorded:number;resolved:number;history:GuidedEvent[];readiness:{supported:boolean;generator_approved:boolean;satisfied:string[];pending:string[];additional:string[];can_execute:boolean;message_pt:string}};
export type GuidedDecision = {expected_revision:number;action:GuidedAction;author:string;notes?:string;draft?:Record<string,string>;proposal?:GuidedProposal;next_gap_id?:string};
