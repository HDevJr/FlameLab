# Evidências — BL-02 Dataset científico BASS-II/M1 e integração com o assistente

- Data: 14/11/2026 · Branch: `feat/bl-02-dataset-cientifico` (base `main@a8bda1b`, que inclui o PR #2 da BL-05)
- Nenhuma credencial neste arquivo ou nos relatórios (busca por prefixo de chave: 0 ocorrências).

## 1. Documento NASA
`scripts/verify_sources.py` → **MATCH** ([source_hash_check_20261114T191255Z.json](source_hash_check_20261114T191255Z.json)).
O SHA-256 recalculado é `5ffa911fd9b6356f204646003fb9342e341810dcdfdf5cb15756e7f01ec5f770`, igual a `data/source_manifest.json`
(da equipe) e a `data/documents.json`. Tamanho: 48 972 416 bytes, igual ao manifesto. O PDF **não** foi adicionado ao Git.

## 2. Curadoria M1
Relatório completo e pacote de revisão: [docs/curation/BASS2-M1_curation_report.md](../curation/BASS2-M1_curation_report.md).
- 9 registros (8 campos do DM) e 11 evidências (9 células da Tabela 5.1 + 2 trechos para o material).
  Mais 1 evidência de nível de investigação (plataforma ISS/MSG) e 12 lacunas.
- **Estado: 0/9 `CONFERIDO_FONTE`.** Todos estão `EXTRAIDO_NAO_REVISADO`; a revisão humana está pendente.
- Verificação cruzada automática com a camada de texto: **10/10 MATCH** ([crosscheck_20261114T191949Z.json](crosscheck_20261114T191949Z.json)). Não equivale a conferência.

## 3. Testes (provedor SIMULADO)
`python -m pytest -q backend/tests` → **114 passed, 1 skipped** ([test_run_BL-02_20261114.txt](test_run_BL-02_20261114.txt)).

| Cenário pedido | Teste(s) | Resultado |
|---|---|---|
| Hash correspondente | `test_hash_match`, `test_real_pdf_hash_matches_if_present` | PASS |
| Hash divergente | `test_hash_mismatch_is_reported_not_rewritten`, `test_hash_mismatch_omits_records`, `test_review_refused_when_hash_mismatch` | PASS |
| Registro válido | `test_valid_record_loads_and_version_is_stable`, `test_real_dataset_loads_with_nine_m1_records` | PASS |
| Registro sem fonte | `test_record_without_source_rejected`, `test_record_with_unknown_evidence_rejected` | PASS |
| Campo ausente | `test_i1_missing_field_must_be_null`, `test_gap_loads_as_absent`, `test_gaps_registered_without_values` | PASS |
| Conversão de unidades | `test_i8_unit_conversion_checked` + T-07 (BL-05) | PASS |
| Evidência de outro ensaio | `test_i7_evidence_from_other_test_rejected` | PASS |
| Revisão incompleta | `test_incomplete_review_rejected`, `test_i5_conferido_requires_page`, `test_review_rejections_leave_file_unchanged` (6 casos) | PASS |
| Dataset inválido | `test_invalid_json_and_contract_version`, `test_duplicate_ids_and_unknown_test`, `test_server_refuses_to_start_with_invalid_dataset` | PASS |
| Integração com o adaptador | `test_adapter_preserves_ids_and_links`, `test_reviewed_record_supports_validated_answer`, `test_unreviewed_records_never_support_observations` | PASS |
| Pergunta sem evidência elegível | `test_question_without_eligible_evidence_abstains` | PASS |
| Pergunta com evidência real conferida | `test_answer_with_human_reviewed_real_evidence` | **NOT_RUN** (pulado: nenhum registro real conferido por humano) |
| Preservação da BL-05 | os 66 testes anteriores (5 atualizados para o comportamento DIV-20, sem afrouxar asserções) | PASS |

## 4. Gemini REAL
| Execução (UTC) | Escopo | Resultado |
|---|---|---|
| 19:15:36 | dataset real, prompt v1 | Rotulado PASS pelo script, mas **reprovado na análise humana**: o Gemini disse que a propagação de M1 "está ausente no relatório" (citando a lacuna errada) e o verificador aprovou. Isso motivou a DIV-20. [smoke_real_dataset_20261114T191536Z.json](smoke_real_dataset_20261114T191536Z.json) |
| 19:18:25 | sintético (BL-05), prompt v2 | PASS 3/3 (regressão do BL-05) — [smoke_gemini_20261114T191825Z.json](smoke_gemini_20261114T191825Z.json) |
| 19:18:58 | dataset real, prompt v2 | **PASS**: pressão → `MISSING_DATA` citando `GAP-BASS2-M1-ambient_pressure`; propagação → `PENDING_REVIEW`: "consta na fonte, mas … aguarda revisão humana", citando `REC-BASS2-M1.flame_spread_rate`, **sem número** — [smoke_real_dataset_20261114T191858Z.json](smoke_real_dataset_20261114T191858Z.json) |

## 5. Correção de integridade (DIV-20)
Registros não conferidos chegavam ao modelo apenas como ausência, e o modelo os descrevia como "ausentes".
Agora:
1. Eles entram como **VALOR RETIDO**: o modelo sabe que o dado existe e onde está, mas não recebe o valor, as ressalvas nem o trecho. Há teste confirmando que "0,071" não aparece no prompt.
2. **V5b:** uma afirmação que cita uma lacuna precisa falar daquele parâmetro.
3. **V5c:** um registro pendente não pode ser descrito como ausente.
4. Novo motivo de abstenção `PENDING_REVIEW`. Prompt passou a v2, o que invalida caches v1.
