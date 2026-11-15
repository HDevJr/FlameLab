"""Versão e capacidades da API. O frontend compara com o que precisa e avisa se o servidor está desatualizado
(por exemplo, um backend antigo que não envia `unit_info` — fonte de unidades exibidas como "—" em 15/11)."""

APP_VERSION = "0.6.0-guided-review"
CAPABILITIES = [
    "unit_info", "integrity", "review_preview", "review_scope", "reopen", "gap_decisions", "readiness", "audit_integrity",
    "record_context", "condition", "scientific_cases", "guided_review",
]
