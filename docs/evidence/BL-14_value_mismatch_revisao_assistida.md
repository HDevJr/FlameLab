# Evidências — Correção do `VALUE_MISMATCH` e revisão científica assistida (v2.2)

- Data: 15/11/2026 · Branch `feat/arq-v2-nasa-fds-prototipo` (HEAD inicial `4204c93`). Nada enviado nem integrado.
- Validação visual por pessoa: **NOT_RUN** (roteiro atualizado em [manual_test_roteiro_S01-S07.md](../manual_test_roteiro_S01-S07.md) §5).

## 1. Causa raiz (demonstrada, não deduzida da mensagem)
Fonte primária: a trilha de auditoria real (`var/audit/review_events.jsonl`) e o registro real `DOC-…-E1.initial_temperature` = `{value: 20.0, unit: "°C", raw_text: "20"}`, evidência p. 5. Reproduzido com o código **anterior** (`backend/app/dataset/review.py` v2.1):

| # | Entrada do revisor | Resultado anterior | Por quê (rastreado no código) |
|---|---|---|---|
| A | valor `"20.0 °C"`, unidade **vazia** (o relato) | `VALUE_MISMATCH` | `_parse_observed` usava `extract_numbers`, cujo casamento **inclui a unidade** (`raw="20.0 °C"`); devolvia 20.0 e **descartava o "°C"**. A unidade vazia virava `canonical_unit(None) = "adimensional"`; °C não existia na tabela (`normalize` → `None`); o ramo "as duas desconhecidas" exigia ambas `None`; caía em `same = a is not None and b is not None` → **falso** |
| B | valor `20.0`, unidade vazia | `VALUE_MISMATCH` | mesma causa: **unidade ausente** era reportada como **valor divergente** |
| C | `20,0` + `°C` digitados em campos separados | aceito | só porque as **duas** unidades eram "desconhecidas" e caíam numa **comparação de texto** — exatamente o que não deve decidir igualdade física |
| D | `20.0` + `℃` (U+2103) | `VALUE_MISMATCH` | sem normalização Unicode |
| E | `293.15` + `K` | impossível | °C e K não existiam na tabela; sem deslocamento de temperatura |
| F | `19` + `°C` num registro de ângulo (`19.0 °`) | `VALUE_MISMATCH` | grandezas incompatíveis (temperatura × ângulo) reportadas como "valor diferente" |

**Por que a interface parecia mostrar valores iguais:** a mensagem era montada como `valor lido ({valor} {unidade_recebida}) diverge do registro ({valor} {unidade_do_registro})`. Com a unidade recebida vazia, ficava `20.0 °C ` (com espaço sobrando) × `20.0 °C`: **visualmente idênticos**, embora o campo comparado (unidade) fosse `None` × `°C`. O histórico mostra o mesmo padrão em `peak_temperature` (`95 ` × `95.0 °C`) e em `uncoated_cells_contact_angle` (`19 °C` × `19.0 °`).

## 2. O que mudou (código)
| Arquivo | Mudança |
|---|---|
| `backend/app/units.py` | Tabela **v1.1** (aditiva, DIV-33): temperatura °C/K/°F **com deslocamento**, ângulo, pressão, volume, massa, área, frequência, potência, µm/ms/h etc. Normalização Unicode **antes** do NFKC (`℃`, `º`, `˚`, `µ`, NBSP/espaços finos, `° C`). "none"/"n/a"/vazio = sem unidade |
| `backend/app/quantities.py` (novo) | `parse_value_input` (separa número e unidade; `20`, `20.0`, `20,0` equivalentes; `1,234`, `1.234,5`, `20 to 80`, `20-80` **ambíguos**, nunca adivinhados) e `compare_fields` (valor × unidade × página, **estruturado**) |
| `backend/app/dataset/review.py` | `check_review` passou a chamar `compare_fields`; removido o `_parse_observed` e a comparação de texto de unidade. `ReviewRejected` carrega `details` |
| `backend/app/semantic.py` (novo) | Verificação **semântica** (ver §4) |
| `backend/app/labels.py` (novo) | Nome amigável em português (glossário determinístico) |
| `backend/app/review_service.py` | Prévia (`/review/preview`), bloqueio semântico, ação **CORRECT** (preserva o original, reabre a revisão), `prefilled_unchanged`, comparações na trilha |
| `backend/app/catalog/service.py` | `technical_name`, rótulo amigável, `unit_info` (unidade separada), `semantic_flags`, contexto da página |
| `backend/app/ingest/extraction.py` | A IA agora sugere `label_pt` (prompt `ext-v3`); `technical_name` preservado |
| `frontend/src/ReviewPanel.tsx` | Painel reescrito (A extração · B evidência · C conferência lado a lado · D ações) |

## 3. Antes × depois (registro real `20.0 °C`, p. 5) — saída em [test_run_review_v2_2_20261115.txt](test_run_review_v2_2_20261115.txt)
| Entrada | Antes | Depois |
|---|---|---|
| A) `"20.0 °C"`, unidade vazia | `VALUE_MISMATCH` | **aceito** — número e unidade separados explicitamente; a unidade aparece como "lida do campo de valor" |
| B) `20.0`, unidade vazia | `VALUE_MISMATCH` | **`UNIT_MISSING`** — `valor: Confere · unidade: Falta · página: Confere` |
| C) `20,0` + `°C` | aceito (por texto) | aceito (por dimensão e conversão) |
| D) `℃` | `VALUE_MISMATCH` | aceito |
| E) `293.15` + `K` | impossível | aceito (`Confere após conversão`: 293,15 K × 293,15 K) |
| F) `20` + `K` | impossível | `VALUE_MISMATCH` (20 K = −253,15 °C) |
| `19` + `°C` num ângulo `19 °` | `VALUE_MISMATCH` | **`UNIT_INCOMPATIBLE`** — "°C é temperatura; ° é ângulo" |

## 4. Revisão semântica — "temperatura inicial" × ciclo de 20 a 80 °C
Trecho: *"The temperature was then cycled from 20 to 80 °C in increments of 20 °C."* O número 20 **está** no texto, mas como **início de um intervalo** e como **incremento**; o texto **não afirma** que 20 °C foi a temperatura inicial. Regras determinísticas (sem IA, sem inventar contexto):

| Sinalização | Gravidade | Exemplo |
|---|---|---|
| `INITIAL_FROM_RANGE`, `FINAL_FROM_RANGE`, `ENDPOINT_MISMATCH` | **BLOQUEIA** a confirmação | rótulo "inicial" + valor é o limite inferior de "from 20 to 80", sem palavra "initial/started" no trecho |
| `INCREMENT_AS_ABSOLUTE` | **BLOQUEIA** | 20 °C é "steps of 20 °C" (diferença), rotulado como temperatura |
| `VALUE_ALSO_INCREMENT`, `VALUE_FROM_LIST`, `MULTIPLE_VALUES_IN_QUOTE`, `APPROXIMATE_VALUE` | informativa | "up to 40, 60, 80, 90 and even 95 °C"; "70 ° at 20 °C and 65 ° at 100 °C" |

Para `initial_temperature = 20 °C` o servidor responde **`SEMANTIC_AMBIGUITY`** mesmo com valor/unidade/página corretos (teste `test_numerically_correct_confirmation_is_still_blocked…`). A saída é **corrigir a extração** (por exemplo, "Temperatura mínima do ciclo"): o original da IA é preservado em `original_extraction`, a correção entra em `corrections`, a conferência fica pendente e **outra pessoa** precisa confirmá-la.

### Estado real dos dados do usuário (somente leitura, sem alterar nada)
Entre as sessões o revisor já conferiu os 14 registros do DYLCO. Com as regras novas, **apenas `initial_temperature` tem bloqueio semântico**; está `CONFERIDO_FONTE` (decisão humana anterior) e **não foi alterado**: o painel mostra o aviso e oferece "Corrigir extração (reabre a conferência)". `temperature = 40 °C` (lista) e os ângulos/temperaturas com vários números têm sinalizações **informativas**. A trilha de auditoria ficou **byte a byte inalterada** durante a verificação.

## 5. Contratos
- **Dataset v1:** entidades inalteradas. Extensão **aditiva** da tabela de unidades (04 §4) — DIV-33.
- **API de revisão (aditiva):** `error.details = {accepted:false, code:"REVIEW_MISMATCH", reason_code, comparisons:[{field,label_pt,expected,received,status,detail_pt,…}], failed_fields, semantic_flags}`. Códigos novos: `UNIT_MISSING`, `UNIT_INCOMPATIBLE`, `UNIT_UNSUPPORTED`, `UNIT_UNEXPECTED`, `VALUE_AMBIGUOUS`, `SEMANTIC_AMBIGUITY`, `NO_CHANGE`, `CURATED_READONLY`. `VALUE_MISMATCH` agora significa **só** divergência numérica real. Rotas novas: `POST /api/records/{id}/review/preview` (não grava nem audita), `GET /api/records/{id}/context`. Ação nova `CORRECT`; campos `prefilled_unchanged`, `corrected_label_pt/value/unit`. — DIV-34.
- **Parâmetros importados (`var/`, não versionado):** `technical_name`, `label_source`, `original_extraction`, `corrections`, `review_history`, `extraction.corrected_by`.
- A trilha de auditoria anterior é preservada; novos eventos incluem `comparisons`, `semantic_flags` e `prefilled_unchanged`.

## 6. Testes
[test_run_review_v2_2_20261115.txt](test_run_review_v2_2_20261115.txt): backend **295 passed, 1 skipped** (os 218 anteriores preservados + 77 novos em `test_review_v22.py`; dois testes antigos foram atualizados porque assumiam °C/kPa "desconhecidos") · frontend **44 passed** (31 anteriores + 13 do painel) · `tsc` sem erros · `vite build`.
Cobertos: `20`×`20.0`×`20,0`; `20 °C` separado; unidade não informada; espaços/símbolos Unicode; °C×K×°F; unidade incompatível/não suportada; página divergente; revisor = extrator (inclusive quem corrigiu); intervalo ≠ valor inicial; incremento ≠ absoluto; lista; diagnóstico por campo na API e na trilha; confirmação com auditoria (`prefilled_unchanged`); preservação do original e reabertura; registro curado não corrigível pela interface; `/preview` sem efeitos; contexto da página.
| NOT_RUN | **inspeção do painel em navegador por pessoa da equipe**; resposta do assistente com registro real conferido (depende da revisão do M1) |

## 7. Limitações restantes
1. **Pré-preenchimento × leitura independente.** Atendendo ao pedido de não exigir redigitação, os campos vêm preenchidos com a extração; a salvaguarda passa a ser a declaração "verifiquei a evidência", a comparação por campo e o registro `prefilled_unchanged` na trilha. **O servidor não consegue provar que a pessoa leu o PDF** (R-25).
2. **Semântica é heurística**, cobre intervalos, incrementos, extremidades e listas; não é compreensão geral de texto. Há falsos negativos (outras ambiguidades) e pode haver bloqueios discutíveis; a saída é corrigir (renomear) e **outra pessoa** confirmar.
3. **Unidades:** a tabela cresceu, mas é finita; unidade fora dela ⇒ `UNIT_UNSUPPORTED` (a confirmação é bloqueada, por desenho). "C" sozinho **não** é aceito como °C. **ΔT** (diferença de temperatura) não é modelado como unidade: só é tratado semanticamente.
4. `1.234` (um ponto) é lido como decimal inglês; `1,234` é ambíguo e recusado.
5. O contexto da página usa a camada de texto do PDF; tabelas e figuras podem não casar literalmente.
6. Identidade do revisor continua **declarada, não autenticada** (R-22).
7. Registro já conferido com bloqueio semântico (`initial_temperature`) **não é reaberto automaticamente**: a decisão é humana.
