# 04 — SCIENTIFIC_DATA_CONTRACT

> Plano 0.1 · 14/11/2026 · Contrato v1 a congelar na F02a. Os valores de M1 abaixo vêm do DM §08.1. **Ainda são `EXTRAIDO_NAO_REVISADO`** (DIV-03) até a conferência no PDF original.

## 1. Três eixos independentes

O DM lista seis estados, e dois deles (`INFERIDO`, `CALCULADO`) descrevem **de onde o valor vem**, não **em que ponto da revisão ele está** (DIV-01). Juntar os dois num campo só impede expressar casos reais, como "valor calculado pelo FDS, ainda não revisado". A proposta (D-07) usa três eixos e **mantém os 6 valores do DM** no campo `status`:

| Eixo | Campo | Valores | Pergunta que responde |
|---|---|---|---|
| Papel | `role` | `CONDICAO` · `OBSERVAVEL` · `METADADO` | É entrada do experimento ou resultado medido? |
| Natureza | `nature` | `OBSERVADO` · `CALCULADO` · `INFERIDO` · `CONCEITUAL` | De onde vem (experimento real, modelo, dedução, ilustração)? |
| Revisão/uso | `status` | `EXTRAIDO_NAO_REVISADO` · `CONFERIDO_FONTE` · `INFERIDO` · `AUSENTE` · `APROVADO_MODELO` · `CALCULADO` | Quanto confiamos e para que uso está liberado? |

> `nature=OBSERVADO` cobre tanto condições relatadas (9 cm/s) quanto resultados medidos (0,071 mm/s): os dois vêm do experimento real. O `role` é o que os distingue.

**Invariantes (validadas no carregamento; se uma falha, o servidor não sobe):**
- I-1 `status=AUSENTE` ⇔ `original=null` e `normalized=null`.
- I-2 `status=CALCULADO` ⇒ `nature=CALCULADO` e `sim_run_id` não nulo.
- I-3 `status=INFERIDO` ⇒ `nature=INFERIDO` e `rationale` não vazio.
- I-4 `nature=CALCULADO` ⇒ `status ∈ {CALCULADO}` (um resultado de modelo nunca vira `CONFERIDO_FONTE`).
- I-5 `status=CONFERIDO_FONTE` ⇒ `reviewer`, `reviewed_at`, ≥1 `Evidence` com `locator.precision ∈ {TABLE_CELL, PAGE}` e `page_pdf` não nulo.
- I-6 `status=APROVADO_MODELO` ⇒ previamente `CONFERIDO_FONTE` ou `INFERIDO` revisado, mais `model_review` (quem, domínio de validade). **Nunca para `role=OBSERVAVEL`**: observáveis não são entrada de modelo.
- I-7 Toda `Evidence` de um registro tem o mesmo `test_uid` que o registro (impede misturar M1 e M2).
- I-8 `normalized` = `units.normalize(original)` recalculado no carregamento. Uma divergência maior que a tolerância de arredondamento rejeita o registro.
- I-9 `nature=CONCEITUAL` nunca aparece em `ParameterRecord`. Só em visualizações.
- I-10 `Document.sha256` só pode estar preenchido se `sha256_computed_at` também estiver (o hash só é registrado quando foi calculado de fato).

## 2. Identificadores
| Objeto | Formato | Exemplo |
|---|---|---|
| Document | `<FONTE>-<id>` | `NASA-TM-20210011385` |
| Investigation | id PSI | `PSI-25` (alias `BASS-II`) |
| Test | `<INV_CURTO>-<rótulo>` | `BASS2-M1` |
| ParameterRecord | `<test_uid>.<parameter>` | `BASS2-M1.airflow_velocity` |
| Evidence | `EV-<doc>-<sufixo>` | `EV-TM20210011385-T51-M1-flow` |
| Passage | `PS-<doc>-p<pdf_idx>-<n>` | `PS-TM20210011385-p42-03` *(número ilustrativo de formato, não página real)* |
| Gap | `GAP-<test_uid>-<parameter>` | `GAP-BASS2-M1-duct_geometry` |
| AIAnswer | `ANS-<sha256 curto>` | — |
| SimulationRun | `RUN-<data>-<caso>-<n>` | — |

## 3. Entidades

### 3.1 Document
```json
{
  "document_id": "NASA-TM-20210011385",
  "title": "<título exato conforme o PDF — preencher na F01>",
  "kind": "TECHNICAL_MEMORANDUM",
  "url": "https://ntrs.nasa.gov/citations/20210011385",
  "doi": null,
  "version": "<conforme NTRS>",
  "local_path": "sources/NASA-TM-20210011385.pdf",
  "sha256": null,
  "sha256_computed_at": null,
  "retrieved_at": null,
  "license_note": "<a confirmar: termos NTRS>",
  "lang": "en"
}
```

### 3.2 Investigation
```json
{
  "investigation_id": "PSI-25",
  "aliases": ["BASS-II", "Burning and Suppression of Solids II"],
  "doi": "10.60555/4qc4-de67",
  "url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
  "platform": { "value": "<ISS/MSG — confirmar na fonte>", "evidence_ids": [] },
  "gravity_environment": { "value": "microgravity", "evidence_ids": ["<preencher>"] },
  "documents": ["NASA-TM-20210011385"],
  "description_pt": "<redigido pela equipe; rotulado como resumo editorial>"
}
```

### 3.3 Test
```json
{
  "test_uid": "BASS2-M1",
  "investigation_id": "PSI-25",
  "label": "M1",
  "source_table": { "document_id": "NASA-TM-20210011385", "table": "5.1" },
  "phenomena": ["flame_spread", "concurrent_or_opposed_flow:<confirmar>"],
  "material_family": "PMMA",
  "tags": ["thin_solid", "one_sided"],
  "selection_reason": "<por que entrou no MVP — BL-02.05>"
}
```

### 3.4 ParameterRecord (núcleo)
```json
{
  "record_id": "BASS2-M1.airflow_velocity",
  "test_uid": "BASS2-M1",
  "investigation_id": "PSI-25",
  "parameter": "airflow_velocity",
  "label_pt": "Velocidade do ar",
  "label_source": "<cabeçalho literal da coluna na Tabela 5.1>",
  "role": "CONDICAO",
  "nature": "OBSERVADO",
  "status": "EXTRAIDO_NAO_REVISADO",
  "original":   { "value": 9, "unit": "cm/s", "raw_text": "9" },
  "normalized": { "value": 0.09, "unit": "m/s" },
  "qualifiers": { "spatial_profile": "AUSENTE", "measurement_point": "AUSENTE" },
  "evidence_ids": ["EV-TM20210011385-T51-M1-flow"],
  "extraction": { "method": "MANUAL_TRANSCRIPTION", "by": "<papel/pessoa>", "at": "<ISO8601>" },
  "review": { "reviewer": null, "reviewed_at": null, "notes": null },
  "model_review": null,
  "rationale": null,
  "sim_run_id": null,
  "caveats_pt": ["Condição tabulada; perfil espacial do escoamento não informado."]
}
```

### 3.5 Evidence
```json
{
  "evidence_id": "EV-TM20210011385-T51-M1-flow",
  "document_id": "NASA-TM-20210011385",
  "test_uid": "BASS2-M1",
  "locator": {
    "section": "5.3",
    "table": "5.1",
    "figure": null,
    "row_label": "M1",
    "column_label": "<literal>",
    "page_printed": null,
    "page_pdf_index": null,
    "bbox": null,
    "precision": "TABLE_CELL"
  },
  "quote": "<texto literal da célula + cabeçalho, em inglês>",
  "quote_lang": "en",
  "method": "MANUAL_TRANSCRIPTION",
  "document_sha256_at_extraction": null
}
```
`precision`: `TABLE_CELL` > `PAGE` > `SECTION` > `DOCUMENT`. `page_pdf_index` começa em 1 (página do visualizador). Isso fica documentado no README para não confundir com o índice 0 do PyMuPDF.

### 3.6 Gap (lacuna)
```json
{
  "gap_id": "GAP-BASS2-M1-pmma_pyrolysis_properties",
  "test_uid": "BASS2-M1",
  "parameter": "pmma_pyrolysis_properties",
  "status": "AUSENTE",
  "purpose_blocked": ["FDS_REPRODUCTION"],
  "searched_in": ["NASA-TM-20210011385 §5.3", "§5.5"],
  "explanation_pt": "Propriedades termoquímicas e de pirólise necessárias ao modelo de material não foram localizadas no corpus curado.",
  "possible_sources_pt": "<referências a investigar; não preencher com valores>"
}
```
> **Extensão aditiva (BL-02, DIV-19, pendente de aprovação):** `label_pt` (obrigatório) e `keywords` (lista), usados pela regra V5 do verificador.

Lista inicial (DM §08.2): comprimento da amostra; posição/apoio metálico; dimensões efetivas do duto; pressão; temperatura; perfil espacial e temporal do fluxo; ponto do anemômetro; procedimento/duração/fonte de ignição; propriedades termoquímicas/pirólise do PMMA; incertezas de medição; método de cálculo do avanço da frente. **Na F01, cada item é verificado no PDF.** Se algum for encontrado, sai de Gap e vira ParameterRecord.

### 3.7 Passage (para recuperação)
```json
{ "passage_id": "PS-…", "document_id": "NASA-TM-20210011385", "section": "5.5",
  "page_pdf_index": null, "page_printed": null, "text": "<literal>", "lang": "en",
  "kind": "BODY_TEXT" }
```
`kind` ∈ `BODY_TEXT` · `TABLE_CAPTION` · `FIGURE_CAPTION` · `SYNTHETIC_TEST_CARD` (cartão gerado deterministicamente dos registros conferidos, com `source_record_ids`).

### 3.8 M1: registros esperados (resultado de aceite da F01)
| parameter | role | original | normalized (SI) | Observações |
|---|---|---|---|---|
| `material` | METADADO | "PMMA" | — | fonte: texto da §5 (não é coluna da Tabela 5.1), DIV-02 |
| `thickness` | CONDICAO | 1 mm | 0.001 m | Tabela 5.1 |
| `width` | CONDICAO | 2.2 cm | 0.022 m | Tabela 5.1 |
| `burning_faces` | CONDICAO | 1 ("one-sided") | 1 (adimensional) | Tabela 5.1 |
| `airflow_velocity` | CONDICAO | 9 cm/s | 0.09 m/s | perfil AUSENTE |
| `flame_spread_rate` | **OBSERVAVEL** | 0.071 mm/s | 7.1e-5 m/s | **nunca** entrada de modelo |
| `burn_duration` | OBSERVAVEL | 6.4 min | 384 s | não implica regime estacionário |
| `o2_initial` | CONDICAO | 22.2 % | 0.222 (fração) | base (vol./molar) a confirmar |
| `o2_final` | OBSERVAVEL | 21.9 % | 0.219 (fração) | não é concentração constante |

Total: **9 registros = os "8 campos" do DM** (O₂ inicial e final contam como um campo). T-01 conta registros, não campos.

### 3.9 AIAnswer
```json
{
  "answer_id": "ANS-…",
  "question": "Qual a velocidade de propagação em M1?",
  "scope": { "investigation_id": "PSI-25", "test_uids": ["BASS2-M1"] },
  "mode": "LIVE | CACHE | UNAVAILABLE",
  "abstained": false,
  "abstain_reason": null,
  "extrapolation_flags": [],
  "claims": [
    { "type": "OBSERVACAO", "text_pt": "…0,071 mm/s…", "evidence_ids": ["EV-…"],
      "numbers": [{ "value": 0.071, "unit": "mm/s" }], "verification": "PASS" }
  ],
  "blocked_claims": [ { "text_pt": "…", "reason": "V2_NUMBER_NOT_IN_EVIDENCE" } ],
  "retrieved": [ { "id": "EV-…", "score": 0.0 } ],
  "provider": "<D-03>", "model": "<D-03>", "prompt_version": "v1",
  "dataset_version": "sha256:…", "created_at": "…", "latency_ms": 0
}
```
`type`: `OBSERVACAO` (dado observado citado), `ASSOCIACAO` (relação entre observações, sem causa), `HIPOTESE` (interpretação, explicitamente marcada), `EXPLICACAO` (conceito geral, **sem números do experimento**), `LIMITACAO` (o que não se pode afirmar).

> **Extensão aditiva implementada em BL-05 (14/11), pendente de aprovação: DIV-15 em [07](07_RISKS_AND_DECISIONS.md).** Nenhum campo acima foi removido ou renomeado.
> - `mode` ganha `DETERMINISTIC`: abstenção decidida em código, sem chamar a IA (ex.: nenhum dado curado elegível).
> - Novos campos: `requested_mode` (live/cache/off configurado), `unavailable_reason` (MODE_OFF, CACHE_MISS, PROVIDER_NOT_CONFIGURED, PROVIDER_ERROR), `provider_error` (somente o tipo: AUTH, QUOTA, TIMEOUT, UNAVAILABLE, BAD_REQUEST, INVALID_RESPONSE, CONFIG), `warnings`, `synthetic_evidence_used`, `served_at` (em CACHE, `created_at` é o momento original da geração).
> - `blocked_claims[]` ganha `type` e `reasons[]` (todas as violações); `retrieved[]` ganha `kind`, `test_uid`, `status`, `nature`, `text`, `locator`, `document_id`, `synthetic`.
> - `abstain_reason`: NO_ELIGIBLE_EVIDENCE, INSUFFICIENT_EVIDENCE, MISSING_DATA, EXTRAPOLATION, MODEL_ABSTAINED, VERIFICATION_FAILED.
> - IDs de evidência no assistente: fichas `REC-<record_id>`, lacunas `GAP-…`, trechos `PS-…`.
> - **BL-02 (DIV-20):** `abstain_reason` ganha `PENDING_REVIEW`; `retrieved[]` ganha `value_withheld` (registro não conferido: existe na fonte, valor não liberado).

### 3.10 Comparison (saída)
```json
{ "test_uids": ["BASS2-M1","BASS2-Mx"],
  "rows": [ { "parameter": "thickness", "role": "CONDICAO",
              "values": { "BASS2-M1": {"value":0.001,"unit":"m","status":"CONFERIDO_FONTE"},
                          "BASS2-Mx": {"value":null,"status":"AUSENTE"} },
              "differs": null, "comparable": false } ],
  "differing_conditions": 3,
  "warnings": ["Os ensaios diferem em 3 condições; diferenças nos resultados não podem ser atribuídas a uma variável isolada."] }
```
Regra: `AUSENTE` em qualquer lado → `differs=null`, `comparable=false`. **Nunca imputar.**

### 3.11 SimulationRun (STRETCH)
```json
{ "run_id": "RUN-…", "engine": "FDS", "engine_version": "<lido do log>",
  "case_file": "fds/cases/…/case.fds", "case_sha256": "…",
  "machine_audit_ref": "docs/environment_audit.md#…",
  "purpose": "COLD_FLOW_EXPLORATORY | REPRODUCTION_ATTEMPT",
  "source_test_uid": "BASS2-M1",
  "assumptions": [ { "text_pt": "…", "status": "INFERIDO", "rationale": "…" } ],
  "gates": { "G1": "PASS|FAIL|NOT_RUN", "G2": "…", "G3": "…", "G4": "…", "G5": "…" },
  "log_path": "fds/runs/…/log.txt", "completed": true, "wall_time_s": 0,
  "outputs": [ { "name": "…", "path": "…csv", "unit": "…" } ],
  "validity_label_pt": "Simulação numérica exploratória — não é reprodução de M1" }
```

### 3.12 Scenario (FUTURO): só a declaração
`{scenario_id, base_test_uid, changed_parameters:[{parameter, from, to}], hypothesis_pt, status: "HIPOTESE_COMPUTACIONAL", sim_run_ids}`. **Não implementado no MVP.**

## 4. Unidades (tabela v1)
| Grandeza | Aceitas | SI |
|---|---|---|
| comprimento | mm, cm, m | m |
| velocidade | mm/s, cm/s, m/s | m/s |
| tempo | s, min | s |
| fração | %, fração | fração (0–1) |
| contagem | adimensional | adimensional |
Unidades fora da tabela → o registro é rejeitado no carregamento (não há conversão "aproximada").

> **Extensão aditiva v1.1 (15/11/2026, DIV-33):** a tabela passou a incluir temperatura (°C, K, °F, com **deslocamento**: K = °C + 273,15), ângulo (°, rad), pressão (Pa…atm, psi), volume, massa, área, frequência, potência/fluxo de calor, µm/ms/h e ppm, além de normalização Unicode das grafias (`℃`, `º`, `˚`, `µ`, espaços finos). Nada que era aceito deixou de ser. **Igualdade física é decidida por dimensão + conversão; texto de unidade nunca decide.** Unidade fora da tabela continua sem conversão e a revisão a trata como `UNIT_UNSUPPORTED`. A diferença de temperatura (ΔT) **não** é uma unidade desta tabela.

## 5. Versionamento
- `contract_version: "1.0"` em cada arquivo JSON.
- `dataset_version` = sha256 do JSON canônico (chaves ordenadas) de todos os arquivos em `data/`, exceto `ai_cache/`.
- Mudar o contrato depois da F02a exige atualizar este documento, os fixtures e um teste de regressão.


# Curadoria científica — BASS-II

## Fonte
- Documento: NASA/TM-20210011385
- Investigação: BASS-II
- SHA-256: consultar data/source_manifest.json

## Experimento M1
- Seção: 5.3
- Tabela: 5.1
- Página impressa: 57
- Página do PDF: 65 (impressa 57) — identificada na extração preliminar (BL-02, 14/11)
- Material: texto da §5.3 (p. 56 / PDF 64) e §5.1 (p. 55 / PDF 63), não coluna da tabela
- Extração preliminar: claude-code (camada de texto PyMuPDF), verificação cruzada 10/10 MATCH
- Revisor 1: PENDENTE (pessoa da equipe; `scripts/review_record.py`)
- Revisor 2: PENDENTE
- Estado: EXTRAIDO_NAO_REVISADO (9/9)
- Relatório: `docs/curation/BASS2-M1_curation_report.md`

## Conferência
- [ ] Identificação M1 correta
- [ ] Espessura e largura verificadas
- [ ] Número de faces verificado
- [ ] Velocidade do ar verificada
- [ ] Propagação observada verificada
- [ ] Duração verificada
- [ ] Oxigênio inicial e final verificados
- [ ] Unidades originais preservadas
- [ ] Conversões para SI verificadas
- [ ] Segunda revisão concluída

## Resultado
PENDENTE DE VALIDAÇÃO
