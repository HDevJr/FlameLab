"""BL-05.02/05.06 — orquestrador do assistente científico.

Fluxo (planning/02 §8):
  pergunta → análise de extrapolação → recuperação no escopo → [off] UNAVAILABLE
  → portão de suficiência (sem evidência ⇒ abstenção DETERMINISTIC, sem chamar a IA)
  → [cache] entrada reverificada ou UNAVAILABLE(CACHE_MISS)
  → [live] provedor → verificador V1–V8 → resposta LIVE → grava cache
           falha do provedor ⇒ cache reverificado (mode=CACHE) ou UNAVAILABLE(PROVIDER_ERROR)

Nenhum outro provedor é acionado automaticamente.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Callable

from backend.app.assistant.cache import AnswerCache, CacheEntry, cache_key
from backend.app.assistant.config import AssistantSettings
from backend.app.assistant.prompts import build_user_prompt, system_prompt
from backend.app.assistant.provider import LLMProvider, ProviderError
from backend.app.assistant.retrieval import EvidenceSource, RetrievalResult, detect_extrapolation, retrieve
from backend.app.assistant.schemas import (
    PROMPT_VERSION,
    AbstainReason,
    AIAnswer,
    AnswerMode,
    AskRequest,
    LLMOutput,
    RetrievedEvidence,
    UnavailableReason,
)
from backend.app.assistant.verifier import has_substantive, verify_output

log = logging.getLogger("flamelab.assistant")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AssistantService:
    def __init__(
        self,
        settings: AssistantSettings,
        source: EvidenceSource,
        provider: LLMProvider | None = None,
        cache: AnswerCache | None = None,
        clock: Callable[[], datetime] = _now,
    ):
        self.settings = settings
        self.source = source
        self.provider = provider
        self.cache = cache if cache is not None else AnswerCache(settings.cache_dir)
        self._clock = clock

    # ------------------------------------------------------------ helpers
    def _base(self, req: AskRequest, ctx: RetrievalResult, flags: list[str], t0: float, **kw) -> AIAnswer:
        now = self._clock()
        created = kw.pop("created_at", now)
        seed = f"{req.question}|{req.scope.model_dump_json()}|{created.isoformat()}|{kw.get('mode')}"
        retrieved = [
            RetrievedEvidence(
                id=i.evidence_id, score=ctx.scores.get(i.evidence_id, 0.0), kind=i.kind, test_uid=i.test_uid,
                status=i.status, nature=i.nature, text=i.text, locator=i.locator,
                document_id=i.document_id, synthetic=i.synthetic,
            )
            for i in ctx.items
        ]
        warnings = list(ctx.warnings) + list(self.settings.config_warnings) + kw.pop("extra_warnings", [])
        return AIAnswer(
            answer_id="ANS-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16],
            question=req.question,
            scope=req.scope,
            requested_mode=self.settings.mode,
            extrapolation_flags=flags,
            retrieved=retrieved,
            warnings=warnings,
            synthetic_evidence_used=any(i.synthetic for i in ctx.items),
            prompt_version=PROMPT_VERSION,
            dataset_version=self.source.dataset_version,
            created_at=created,
            served_at=now,
            latency_ms=int((time.monotonic() - t0) * 1000),
            **kw,
        )

    def _unavailable(self, req, ctx, flags, t0, reason: UnavailableReason, provider_error: str | None = None):
        return self._base(
            req, ctx, flags, t0, mode=AnswerMode.UNAVAILABLE, abstained=False,
            unavailable_reason=reason, provider_error=provider_error,
            provider=self.provider.name if self.provider else None,
            model=self.provider.model if self.provider else None,
        )

    def _from_output(self, req, ctx, flags, t0, output: LLMOutput, mode: AnswerMode, provider: str,
                     model: str, created_at: datetime | None = None, provider_error: str | None = None,
                     extra_warnings: list[str] | None = None) -> AIAnswer:
        result = verify_output(output, ctx.by_id(), req.scope, flags, self.source.known_tests())
        substantive = has_substantive(result.approved)
        reason: AbstainReason | None = None
        if not substantive:
            if flags:
                reason = AbstainReason.EXTRAPOLATION
            elif result.cited_gap:
                reason = AbstainReason.MISSING_DATA
            elif output.abstain:
                reason = AbstainReason.MODEL_ABSTAINED
            elif result.blocked:
                reason = AbstainReason.VERIFICATION_FAILED
            else:
                reason = AbstainReason.MODEL_ABSTAINED
        kwargs = dict(
            mode=mode, abstained=not substantive, abstain_reason=reason, claims=result.approved,
            blocked_claims=result.blocked, provider=provider, model=model, provider_error=provider_error,
            extra_warnings=extra_warnings or [],
        )
        if created_at is not None:
            kwargs["created_at"] = created_at
        return self._base(req, ctx, flags, t0, **kwargs)

    def _serve_cache(self, req, ctx, flags, t0, key: str, provider_error: str | None = None) -> AIAnswer | None:
        entry = self.cache.get(key)
        if entry is None or entry.dataset_version != self.source.dataset_version:
            return None
        warns = ["Resposta reproduzida do cache: gerada pela IA em "
                 f"{entry.created_at.isoformat()} e reverificada contra o dataset atual."]
        if provider_error:
            warns.append("Chamada ao provedor falhou; servindo cache como fallback.")
        return self._from_output(req, ctx, flags, t0, entry.output, AnswerMode.CACHE, entry.provider,
                                 entry.model, created_at=entry.created_at, provider_error=provider_error,
                                 extra_warnings=warns)

    # ------------------------------------------------------------ API pública
    def ask(self, req: AskRequest) -> AIAnswer:
        t0 = time.monotonic()
        flags = detect_extrapolation(req.question)
        ctx = retrieve(self.source, req.question, req.scope)
        mode = self.settings.mode

        if mode == "off":
            return self._unavailable(req, ctx, flags, t0, UnavailableReason.MODE_OFF)

        if not ctx.sufficient:
            return self._base(
                req, ctx, flags, t0, mode=AnswerMode.DETERMINISTIC, abstained=True,
                abstain_reason=AbstainReason(ctx.reason or "INSUFFICIENT_EVIDENCE"),
            )

        key = cache_key(req.question, req.scope, self.source.dataset_version, PROMPT_VERSION)
        if mode == "cache":
            return self._serve_cache(req, ctx, flags, t0, key) or self._unavailable(
                req, ctx, flags, t0, UnavailableReason.CACHE_MISS)

        # live
        if self.provider is None:
            return self._serve_cache(req, ctx, flags, t0, key, provider_error="CONFIG") or self._unavailable(
                req, ctx, flags, t0, UnavailableReason.PROVIDER_NOT_CONFIGURED, provider_error="CONFIG")
        try:
            output = self.provider.generate_json(
                system_prompt(),
                build_user_prompt(req.question, req.scope, ctx.items, flags),
                LLMOutput,
                self.settings.timeout_s,
            )
        except ProviderError as err:
            log.warning("provider failure kind=%s attempts=%s", err.kind.value, err.attempts)
            return self._serve_cache(req, ctx, flags, t0, key, provider_error=err.kind.value) or self._unavailable(
                req, ctx, flags, t0, UnavailableReason.PROVIDER_ERROR, provider_error=err.kind.value)

        created = self._clock()
        answer = self._from_output(req, ctx, flags, t0, output, AnswerMode.LIVE, self.provider.name,
                                   self.provider.model, created_at=created)
        if self.settings.cache_write:
            self.cache.put(CacheEntry(
                key=key, question=req.question, scope=req.scope, dataset_version=self.source.dataset_version,
                prompt_version=PROMPT_VERSION, provider=self.provider.name, model=self.provider.model,
                created_at=created, output=output,
            ))
        log.info("ask mode=LIVE approved=%d blocked=%d latency_ms=%d",
                 len(answer.claims), len(answer.blocked_claims), answer.latency_ms)
        return answer


def build_provider(settings: AssistantSettings) -> LLMProvider | None:
    """Cria o provedor somente em modo live com configuração completa; senão None."""
    if settings.mode != "live" or not settings.live_ready:
        return None
    from backend.app.assistant.gemini_provider import GeminiProvider

    try:
        return GeminiProvider(
            api_key=settings.gemini_api_key.get_secret_value(),  # type: ignore[union-attr]
            model=settings.model or "",
            max_attempts=settings.max_attempts,
            total_budget_s=settings.total_budget_s,
        )
    except ProviderError:
        return None
