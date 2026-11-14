# Evidências — BL-05 Assistente científico (IA)

- Data: 14/11/2026 · Branch: `feat/bl-05-assistente-ia` (base `main@4277987`)
- Máquina: Windows 11, Python 3.12.3 (`.venv`), google-genai 3.3.0, python-dotenv 1.2.4
- **Nenhuma credencial neste arquivo nem nos relatórios JSON** (conferido com busca por prefixo de chave).

## 1. Suíte automatizada (provedor SIMULADO)
Comando: `.\.venv\Scripts\python.exe -m pytest -q backend/tests` → **66 passed** (saída completa em
[test_run_BL-05_20261114.txt](test_run_BL-05_20261114.txt)).

Todos os testes usam `FakeProvider` ou um cliente Gemini falso. **Não comprovam a integração real**; isso é a seção 2.

| Cenário do pedido | Testes | Resultado |
|---|---|---|
| A — extração correta | `test_a_correct_extraction_is_validated`, `test_test_a_valid_observation_passes` | PASS |
| B — abstenção (pressão) | `test_b_missing_pressure_produces_abstention`, `test_b_invented_pressure_is_blocked` | PASS |
| C — número inventado (0,08 vs 0,071) | `test_c_invented_number_blocked_with_reason`, `test_test_c_invented_number_blocked_v2` | PASS |
| D — mistura M1/M2 | `test_d_model_never_receives_out_of_scope_evidence`, `test_d_mixing_tests_blocked`, `test_test_d_*` | PASS |
| E — campo AUSENTE | `test_e_missing_field_never_presumed`, `test_test_e_*` | PASS |
| F — prompt injection | `test_f_prompt_injection_is_data_and_value_not_published`, `test_test_f_injected_number_from_passage_blocked` | PASS |
| G — timeout / 503 | `test_503_*`, `test_timeout_is_mapped_and_retried`, `test_total_budget_limits_attempts`, `test_non_retryable_errors_fail_fast`, `test_g_*` | PASS |
| H — modos LIVE/CACHE/OFF | `test_h_modes_live_cache_off`, `test_h_cache_miss_and_dataset_version_change`, `test_h_live_without_provider_is_unavailable` | PASS |
| I — compatibilidade F00 | `test_health.py` (2 testes) | PASS |
| J — extrapolação (Marte) | `test_j_extrapolation_mars`, `test_v8_extrapolation_restrictions` | PASS |
| API / segurança | `test_assistant_config_api.py` (422 sem ecoar entrada, chave ausente da resposta, dataset vazio ⇒ abstenção) | PASS |

O aviso de depreciação Starlette/httpx registrado na F00 **não apareceu** nesta execução. Nenhuma dependência existente foi atualizada.

## 2. Smoke test REAL do Gemini (evidência SINTÉTICA)
Comando: `.\.venv\Scripts\python.exe scripts\smoke_gemini.py` · modelo `gemini-3.5-flash-lite`.

| Execução (UTC) | Resultado | Relatório |
|---|---|---|
| 18:41:38 | **PROVIDER_ERROR**: HTTP 400 `BAD_REQUEST` nas 3 chamadas | [smoke_gemini_20261114T184138Z.json](smoke_gemini_20261114T184138Z.json) |
| 18:43:09 | **PASS** (3/3) | [smoke_gemini_20261114T184309Z.json](smoke_gemini_20261114T184309Z.json) |

**Diagnóstico da falha 400 (feito com a chave mascarada):** o modelo aceitou `response_mime_type=application/json`
sem schema e com um JSON Schema simples, mas rejeitou ("Request contains an invalid argument") os dois formatos gerados
automaticamente do Pydantic (`response_schema=<modelo>` e `response_json_schema=model_json_schema()`, com `anyOf`/`null`/`$defs`).
**Correção:** `LLM_OUTPUT_PROVIDER_SCHEMA`, declarado à mão em `schemas.py`, é o schema enviado. A validação estrita da resposta
continua sendo feita pelo Pydantic. Um teste unitário garante que o schema enviado não contém `anyOf`/`$defs`.

Resultado da execução PASS (afirmações publicadas após V1–V8):
- **A:** `OBSERVACAO` "No ensaio TEST-01, o material utilizado foi PMMA." [REC-TEST-01.material]; `OBSERVACAO` "...espessura da amostra foi de 1 mm." [REC-TEST-01.thickness], numbers=[1 mm]. 0 bloqueadas.
- **B:** abstenção `MISSING_DATA`; `LIMITACAO` "...a pressão está ausente e não foi informada..." [GAP-TEST-01-pressure]. Nenhum número.
- **J:** abstenção `EXTRAPOLATION`, flag `MARTE`; `LIMITACAO` sem números. **1 afirmação do modelo bloqueada** (`OBSERVACAO` com valores de TEST-01, por `V8_EXTRAPOLATION_CLAIM_TYPE`). O verificador atuou sobre a saída real.

**Escopo da evidência:** prova que o adaptador, o schema, o verificador e os modos funcionam com o provedor real **para evidência sintética**.
**Não** valida conteúdo científico BASS-II/NASA, que ainda não existe no dataset.

## 3. Servidor real (uvicorn), sem chave
`GEMINI_API_KEY=` vazio, modos `off`, `cache` e `live`: `/api/health` 200. `POST /api/ask` com o exemplo do contrato
(PSI-25 / BASS2-M1) devolveu, respectivamente, `UNAVAILABLE/MODE_OFF`, `DETERMINISTIC/NO_ELIGIBLE_EVIDENCE` e
`DETERMINISTIC/NO_ELIGIBLE_EVIDENCE`, com o aviso "Nenhum dataset curado carregado (dependência BL-02 pendente)". `{"question":"x"}` → 422.

## 4. Estado das regras V1–V8
| Regra | Implementada | Testada (simulado) | Exercitada com Gemini real | Limitação conhecida |
|---|---|---|---|---|
| V1 evidência recuperada | sim | PASS | sim (sem violação) | — |
| V2 números | sim | PASS | sim (A: 1 mm aprovado) | números por extenso não são detectados; número sem unidade só casa com grandeza adimensional; números de trechos (PASSAGE) não sustentam afirmações (decisão conservadora, DIV-16) |
| V3 identidade do ensaio | sim | PASS | sim | detecção por rótulos conhecidos + padrão `M<n>`; outras famílias de rótulo dependem do dataset |
| V4 observação conferida | sim | PASS | sim | — |
| V5 ausentes | sim | PASS | sim (B) | por palavras-chave da lacuna; sinônimos não cadastrados escapam (bloqueio parcial, também coberto por V2) |
| V6 causalidade | sim | PASS | não exercitada | lista de expressões PT/EN; paráfrases causais podem escapar |
| V7 explicações sem números | sim | PASS | não exercitada | — |
| V8 extrapolação | sim | PASS | **sim (J: bloqueio real)** | detector por padrões (Marte, Lua, gravidade parcial, outros corpos); outras extrapolações (ex.: pressão) não são detectadas |
