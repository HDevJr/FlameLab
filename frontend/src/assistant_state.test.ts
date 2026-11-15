import { describe, expect, it } from "vitest";
import type { AIAnswer } from "./api";
import { answerState } from "./assistant_state";

const base: AIAnswer = {
  answer_id: "A", question: "q", scope: {}, mode: "LIVE", requested_mode: "live", abstained: false, abstain_reason: null,
  unavailable_reason: null, provider_error: null, extrapolation_flags: [], claims: [], blocked_claims: [], retrieved: [], warnings: [],
  synthetic_evidence_used: false, provider: "gemini", model: "m", prompt_version: "v2", dataset_version: "sha256:x",
  created_at: "2026-11-15T00:00:00Z", served_at: "2026-11-15T00:00:00Z", latency_ms: 1,
};
const st = (o: Partial<AIAnswer>) => answerState({ ...base, ...o });

describe("estado da resposta do assistente", () => {
  it("resposta com suporte → respaldada", () => expect(st({}).key).toBe("SUPPORTED"));
  it("extrapolação → bloqueada, em vermelho, sem número", () => {
    const s = st({ abstained: true, abstain_reason: "EXTRAPOLATION" });
    expect(s.key).toBe("EXTRAPOLATION"); expect(s.tone).toBe("bad"); expect(s.label).toMatch(/BLOQUEADA/);
  });
  it("dado ausente e valor retido são estados distintos", () => {
    expect(st({ abstained: true, abstain_reason: "MISSING_DATA" }).key).toBe("MISSING");
    expect(st({ abstained: true, abstain_reason: "PENDING_REVIEW" }).key).toBe("PENDING_REVIEW");
  });
  it("IA desligada ou sem cache → fonte indisponível, nunca 'respaldado'", () => {
    const s = st({ mode: "UNAVAILABLE", abstained: true, unavailable_reason: "MODE_OFF" });
    expect(s.key).toBe("UNAVAILABLE"); expect(s.explain).toMatch(/off/);
  });
  it("verificador bloqueou tudo → não é abstenção do modelo", () => {
    expect(st({ abstained: true, abstain_reason: "VERIFICATION_FAILED" }).key).toBe("VERIFIER_BLOCKED");
  });
});
