# 03 — DEVELOPMENT_BACKLOG

> Plano 0.1 · 14/11/2026 · Mantém os IDs BL-01…BL-11 do DM §13. Subtarefas `BL-xx.yy`. Estado inicial de **todas**: PLANEJADO.
> Testes `T-xx`: [05](05_QUALITY_AND_VALIDATION_PLAN.md). Estimativas em horas-pessoa (h), **ordens de grandeza para planejar**, não compromissos.

## 1. Papéis funcionais (atribuir depois)
| Papel | Sigla | Foco |
|---|---|---|
| Curadoria científica / dados | **DADOS** | PDF, transcrição, conferência, lacunas, trechos |
| Revisão científica | **CIÊNCIA** | Segunda conferência, textos da UI, gates FDS, limites das respostas. Pode ser a mesma pessoa de DADOS, **mas não na conferência do mesmo registro que ela transcreveu** |
| Backend | **BACK** | Store, validadores, API, busca, comparação |
| IA | **IA** | Recuperação, prompt, adaptador, verificador, cache |
| Frontend / UX | **FRONT** | Telas, componentes, gráficos, rótulos |
| Qualidade | **QA** | Testes, checklist de demo, evidências |
| Simulação | **SIM** | F08 (STRETCH), somente fora do caminho crítico |
| Pitch | **PITCH** | Slides, roteiro, matriz 06, capturas |

Equipes pequenas combinam papéis. Uma combinação que funciona: {DADOS+CIÊNCIA}, {BACK+IA}, {FRONT}, {PITCH+QA}. A regra de dupla conferência continua valendo em qualquer combinação.

## 2. Backlog detalhado

### BL-01 · P0 · Repositório, ambiente e escopo (F00)
| ID | Tarefa | Papel | Dep. | h | Aceite / teste |
|---|---|---|---|---|---|
| BL-01.07 | **Auditoria do ambiente atual** (executa primeiro): SO, Python, Node, git, pacotes, FDS, Smokeview, LLM, protótipo, PDF. Cada item marcado VERIFIED/NOT_VERIFIED/ABSENT com comando e saída. Teste FDS do outro computador registrado como histórico | BACK | — | 0,5 | T-00f |
| BL-01.01 | `git init`, `.gitignore`, estrutura de diretórios, remote (D-08) | BACK | 01.07 | 0,25 | repositório com 1º commit |
| BL-01.02 | Backend: venv, `requirements.txt` fixado, `/api/health`, servir `frontend/dist` | BACK | 01.01 | 0,75 | T-00a, T-00b |
| BL-01.03 | Frontend: Vite React-TS + Router + Recharts, placeholder com health e aviso de independência | FRONT | 01.01 | 0,75 | T-00c |
| BL-01.04 | Baixar o PDF NASA/TM-20210011385, `hash_sources.py`, `documents.json` | DADOS | 01.01 | 0,5 | T-00d |
| BL-01.05 | README v0 (escopo MUST, execução, independência NASA) | PITCH | 01.02 | 0,5 | T-00e |
| BL-01.06 | Registrar decisões D-01, D-03, D-07, D-08 em `docs/decisions.md` | Produto/todos | — | 0,25 | decisões com data e responsável |
| BL-01.08 | Se o protótipo de extração for encontrado: copiar para `scripts/legacy_extractor/` + nota de origem, **sem integrar** | DADOS | 01.07 | 0,25 | arquivo + nota, ou registro "ABSENT" |

### BL-02 · P0 · Importar e conferir BASS-II Tabela 5.1 (F01 + F02a)
| ID | Tarefa | Papel | Dep. | h | Aceite / teste · status (14/11) |
|---|---|---|---|---|---|
| BL-02.01 | Modelos Pydantic + enums + invariantes ([04](04_SCIENTIFIC_DATA_CONTRACT.md)) | BACK | 01.02 | 1,5 | T-20 | **IMPLEMENTADO_E_TESTADO**: `backend/app/dataset/models.py` (I-1–I-4, I-6, I-8–I-10 por registro) |
| BL-02.02 | `units.py` (mm, cm, m, mm/s, cm/s, m/s, s, min, %, fração) | BACK | 02.01 | 0,5 | T-07 | **IMPLEMENTADO_E_TESTADO**: `backend/app/units.py` (+ alias `vol%` da Tabela 5.1) |
| BL-02.03 | `DatasetStore` (carregar, validar, indexar, `dataset_version`) | BACK | 02.01 | 1 | T-20, servidor recusa dataset inválido | **IMPLEMENTADO_E_TESTADO**: `store.py` (I-5, I-7, referências, versões do documento); servidor não sobe com dataset inválido |
| BL-02.04 | `page_map.py` (página impressa ↔ índice PDF) | DADOS | 01.04 | 0,75 | página de "Table 5.1" identificada nos dois sistemas | **PARCIAL**: capítulo 5 mapeado à mão (Tab. 5.1 = impressa 57 / PDF 65); `page_map.py` genérico não feito |
| BL-02.05 | Ler a Tabela 5.1 e escolher os ensaios do MVP (D-01; recomendado M1 + ≥4 contrastantes, registrar o motivo de cada escolha) | DADOS+CIÊNCIA | 01.04 | 0,5 | lista justificada em `curation_log.md` | PLANEJADO (só M1 nesta etapa) |
| BL-02.06 | Transcrever M1 (9 registros) + evidências literais + localização | DADOS | 02.01, 02.04 | 0,75 | registros `EXTRAIDO_NAO_REVISADO` carregam sem erro | **IMPLEMENTADO_E_TESTADO**: 9 registros + 11 evidências; extração preliminar assistida (não manual) |
| BL-02.07 | Conferência independente de M1 → `CONFERIDO_FONTE` | CIÊNCIA | 02.06 | 0,5 | T-01, T-03, T-19 | **BLOQUEADO — aguarda pessoa da equipe**: 0/9 conferidos. Ferramenta pronta: `scripts/review_record.py` |
| BL-02.08 | Transcrever + conferir os demais ensaios | DADOS → CIÊNCIA | 02.05, 02.07 | 2 | T-21 (M1/M2 não se misturam), T-04 se M2 tiver duas velocidades | PLANEJADO. Atenção: M2–M20 têm várias velocidades por ensaio ("20 and 15"), o que exige um modelo de segmentos (DIV-22) |
| BL-02.09 | Registrar a fonte de "Material = PMMA" e de "microgravidade/ISS" (metadado da investigação) | DADOS | 02.06 | 0,25 | evidência com seção/página | **IMPLEMENTADO** (EXTRAIDO_NAO_REVISADO): material §5.3/§5.1; plataforma ISS/MSG §5.1 |
| BL-02.10 | `gaps.json` a partir do DM §08.2 + campos esperados não encontrados | CIÊNCIA | 02.06 | 0,5 | T-02 | **IMPLEMENTADO_E_TESTADO**: 12 lacunas em `data/gaps/BASS2-M1.json` |
| BL-02.11 | Metadados PSI-25 (`investigations.json`: DOI 10.60555/4qc4-de67, URL) | DADOS | 01.01 | 0,25 | carregado | **IMPLEMENTADO** (DOI/URL copiados do DM, não reconferidos no PSI) |
| BL-02.12 | (SHOULD) `crosscheck_table51.py` com PyMuPDF; reaproveitar o protótipo se ele existir | BACK/DADOS | 02.04, 02.08 | 2 | T-04, T-08, relatório MATCH/MISMATCH | **IMPLEMENTADO_E_TESTADO para M1**: 10/10 MATCH; não generalizado para M2+ |

### BL-03 · P0 · Ficha M1 (F03 + F04)
| ID | Tarefa | Papel | Dep. | h | Aceite / teste |
|---|---|---|---|---|---|
| BL-03.01 | Rotas de catálogo (`investigations`, `tests`, `tests/{uid}`, `evidence`, `documents`, `passages`) + envelopes e erros | BACK | 02.03 | 1,5 | T-22, T-23 |
| BL-03.02 | Tipos TS e cliente de API | FRONT | 03.01 | 0,5 | `tsc` sem erro |
| BL-03.03 | S01 Home + S02 Explorer (lista simples) | FRONT | 03.02 | 1,5 | navegação até M1 |
| BL-03.04 | S03 Ficha: Condições × Resultados, `StatusChip`, `NatureBadge`, unidades | FRONT | 03.02 | 2 | T-01 (UI) |
| BL-03.05 | `SourcePopover` (documento, página PDF/impressa, tabela/linha/coluna, trecho, link NTRS) | FRONT | 03.04 | 1 | T-24 |
| BL-03.06 | `GapsPanel` "O que não sabemos" | FRONT | 03.04, 02.10 | 0,5 | T-02 (UI) |
| BL-03.07 | Rodapé com `dataset_version` + aviso de independência | FRONT | 03.02 | 0,25 | visível em todas as telas |

### BL-04 · P0 · Busca e classificação (F05)
| ID | Tarefa | Papel | Dep. | h | Aceite / teste |
|---|---|---|---|---|---|
| BL-04.01 | Índice BM25 de `Test` + `Passage` | BACK | 02.03, 05.00 | 0,75 | T-13 |
| BL-04.02 | Filtros exatos/faixa + lista "excluídos por falta de dado" | BACK | 02.03 | 0,75 | T-13 |
| BL-04.03 | Similaridade de condições + `weights.json` + explicação de fonte única | BACK | 02.08 | 1,5 | T-14, T-25 |
| BL-04.04 | `POST /api/search` | BACK | 04.01–03 | 0,5 | teste de API |
| BL-04.05 | UI: busca + filtros na S02, `RankExplanation`, aviso "não é segurança" | FRONT | 04.04, 03.03 | 1,5 | T-14 (UI) |

### BL-05 · P0 · Assistente com citações e abstenção (F06)
| ID | Tarefa | Papel | Dep. | h | Aceite / teste | Status (14/11) |
|---|---|---|---|---|---|---|
| BL-05.00 | (usado também por BL-04) `extract_passages.py`: parágrafos das seções 5.x com página → `passages.jsonl` | DADOS | 02.04 | 1 | trechos com `page_pdf` e seção | PLANEJADO |
| BL-05.01 | Fichas textuais determinísticas por ensaio (a partir dos registros conferidos) | IA | 02.07 | 0,5 | texto gerado contém só valores do registro | **IMPLEMENTADO_E_TESTADO (sintético)**: `assistant/cards.py`. Aguarda os registros reais de BL-02 |
| BL-05.02 | Orquestrador: escopo, recuperação, portão de suficiência, detector de extrapolação | IA | 04.01, 05.01 | 1,5 | T-06 sem chamar LLM | **IMPLEMENTADO_E_TESTADO (sintético)**: `retrieval.py` (BM25 interno, sem dependência) + `service.py` |
| BL-05.03 | **Verificador V1–V8** + `numbers.py` (parse PT/EN de números e unidades) | IA | 02.02 | 2,5 | T-15, T-16, testes unitários com respostas fabricadas | **IMPLEMENTADO_E_TESTADO**: T-15, T-16 PASS; limitações em `docs/evidence/BL-05_assistente_ia.md §4` |
| BL-05.04 | Adaptador LLM (D-03), schema JSON, timeout | IA | D-03 | 1 | chamada real registrada em log (sem chave) | **IMPLEMENTADO_E_TESTADO**: Gemini; smoke real PASS 3/3 (evidência sintética) |
| BL-05.05 | Prompt v1 (dados delimitados, saída JSON, tipos de claim) | IA+CIÊNCIA | 05.04 | 1 | golden set passa | **IMPLEMENTADO_NAO_VALIDADO**: sem revisão de CIÊNCIA; golden set real depende de BL-02 |
| BL-05.06 | Cache verificado + `FLAMELAB_LLM_MODE` | IA | 05.03 | 0,75 | T-09, resposta `mode=CACHE` rotulada | **IMPLEMENTADO_E_TESTADO (simulado)**: cache ainda não gerado para perguntas reais |
| BL-05.07 | `POST /api/ask` + modo UNAVAILABLE | BACK/IA | 05.02–06 | 0,5 | T-09 | **IMPLEMENTADO_E_TESTADO**: servidor real nos 3 modos sem chave; dataset vazio ⇒ abstenção |
| BL-05.08 | UI S05: pergunta, resposta por claim com tipo, citações clicáveis, bloqueadas, banner de modo | FRONT | 05.07 | 2 | T-03, T-06 (UI) | PLANEJADO (fora desta entrega) |
| BL-05.09 | Golden set: 4 perguntas do DM §10.1 + 4 adversariais; gerar o cache das perguntas da demo | IA+CIÊNCIA | 05.05 | 1 | T-26, relatório do golden set | **PARCIAL**: cenários adversariais A–J automatizados com dados sintéticos; **BLOQUEADO** para as perguntas reais (M1/O₂) até BL-02.07 |

> Dependências mínimas criadas para BL-05: `backend/app/units.py` (subconjunto de BL-02.02, apenas para V2) e a interface `EvidenceSource` (a fonte padrão é vazia até BL-02.03 existir). **Nenhum dado NASA foi criado.**

### BL-06 · P0 · Comparação e gráfico observado (F07)
| ID | Tarefa | Papel | Dep. | h | Aceite / teste |
|---|---|---|---|---|---|
| BL-06.02 | `compare/rules.py` (alinhamento, Δ, contagem de diferenças, avisos) | BACK | 02.08 | 1 | T-05 |
| BL-06.03 | `POST /api/compare` | BACK | 06.02 | 0,25 | teste de API |
| BL-06.04 | `viz` spread-vs-flow (pontos com evidence_ids, `nature=OBSERVADO`) | BACK | 02.08 | 0,5 | T-10b |
| BL-06.05 | UI S04 comparação | FRONT | 06.03 | 1,5 | T-05 (UI) |
| BL-06.06 | `SciFigure` + `SpreadVsFlowChart` com tooltip de fonte | FRONT | 06.04 | 1,5 | T-10b, T-27 |

### BL-07 · P0 · Trilha de demonstração e capturas
| ID | Tarefa | Papel | Dep. | h | Aceite / teste |
|---|---|---|---|---|---|
| BL-07.01 | Roteiro de clique da demo (≤3 min) amarrado às telas reais | PITCH+QA | BL-03…06 | 0,5 | T-12 |
| BL-07.02 | Capturas reais em `docs/evidence/` (S03 com popover, S04, gráfico, S05 citada, S05 abstenção) | PITCH | idem | 0,5 | nomes com data e `dataset_version` |
| BL-07.03 | Vídeo de fallback da trilha | PITCH | 07.01 | 0,5 | arquivo reproduz offline |

### BL-08 · P1 (SHOULD) · Visualização de registros reais ou esquema conceitual
| ID | Tarefa | Papel | Dep. | h | Aceite / teste |
|---|---|---|---|---|---|
| BL-08.01 | `ApparatusSchematic` SVG (duto, fluxo, amostra) com badge CONCEITUAL; dimensões **não** desenhadas em escala, a menos que tenham fonte | FRONT+CIÊNCIA | 03.04 | 1,5 | T-17 |
| BL-08.02 | Localizar imagem/vídeo oficial BASS-II + licença (D-04) | DADOS | — | 1 | `license_note` preenchido |
| BL-08.03 | Exibir mídia com crédito e badge OBSERVADO | FRONT | 08.02 | 0,5 | visual + crédito |
| BL-08.04 | Relatório S07 (export Markdown/JSON com fontes, lacunas, `dataset_version`) | BACK+FRONT | 03.01 | 1,5 | T-18 |
| BL-08.05 | Visualização temporal **somente se** houver série temporal publicada | — | dado | — | dado existe; senão, cancelada e registrada |

### BL-09 · Stretch · Prontidão FDS e baseline (F08)
| ID | Tarefa | Papel | Dep. | h | Aceite / teste |
|---|---|---|---|---|---|
| BL-09.00 | **Pré-condição:** FDS VERIFIED (BL-01.07) em máquina com acesso ao repositório; caso contrário, só .01–.03 | SIM | 01.07 | — | registro na auditoria |
| BL-09.01 | Ler a §5.5 (FDS 5.5.3): geometria, malha, propriedades, discrepâncias; transformar em registros/evidências ou AUSENTE | SIM+CIÊNCIA | 02.04 | 1,5 | registros com evidência |
| BL-09.02 | `fds_readiness/BASS2-M1.json` com gates G1–G5 e motivos | SIM | 09.01 | 0,5 | JSON valida |
| BL-09.03 | S06 "Prontidão para simulação" (somente leitura) | FRONT | 09.02 | 1 | T-11 |
| BL-09.04 | (só com dimensões com fonte) caso de escoamento frio revisado, executado manualmente, log guardado | SIM | 09.00, 09.01 | 2–3 | T-28, G3 |

> **Atualização 14/11/2026 (ADR-09):** BL-09.00 e a regra “execução manual” foram **superadas**: o FDS/Smokeview/FFmpeg foram verificados nesta máquina e o worker isolado foi implementado e provado com um caso de integração. BL-09.01/.02 (leitura da §5.5 e gates do M1) **continuam abertos** e bloqueiam qualquer reprodução do BASS-II.

### BL-12 · Plataforma v2 — importação, enriquecimento NASA, simulação e protótipo web (ADR-09)
| ID | Tarefa | Estado |
|---|---|---|
| BL-12.01 | Clientes NTRS/DataCite(PSI)/TechPort + registro de operações | IMPLEMENTADO_E_TESTADO |
| BL-12.02 | Comparador de fontes e relatório de enriquecimento (`SourceMatch`, `EnrichmentRecord`) | IMPLEMENTADO_E_TESTADO |
| BL-12.03 | Importação de PDF (hash, identificação, procedência por hash NTRS) | IMPLEMENTADO_E_TESTADO |
| BL-12.04 | Extração assistida por Gemini com citação literal verificada | IMPLEMENTADO_E_TESTADO (IA simulada) · 1 execução real |
| BL-12.05 | Catálogo genérico (documentos/experimentos, curados e importados) | IMPLEMENTADO_E_TESTADO |
| BL-12.06 | Compatibilidade de simulação (`COMPATIBLE/MISSING_PARAMETERS/UNSUPPORTED_PHYSICS/REQUIRES_REVIEW`) | IMPLEMENTADO_E_TESTADO |
| BL-12.07 | FDS Case Builder + cenários derivados | IMPLEMENTADO_E_TESTADO (modelo de integração) |
| BL-12.08 | Worker, fila e executor local FDS→Smokeview→FFmpeg | IMPLEMENTADO_E_TESTADO (simulado) · execução real registrada |
| BL-12.09 | Telas S01–S07 | PROTOTIPO |
| BL-12.10 | Modelo de **reprodução** de propagação de chama (gerador) | BLOQUEADO (G1/G2, revisão humana de M1, DIV-22) |
| BL-12.11 | Contêiner/limite de memória, Linux/Xvfb, autenticação, fila durável | NAO_INICIADO |
| BL-12.12 | Revisão de parâmetros importados na UI (promoção a `CONFERIDO_FONTE`) | NAO_INICIADO (hoje só por `scripts/review_record.py` no dataset curado) |

### BL-13 · Jornada v2.1 — correções após o teste manual (ADR-09 §11)
| ID | Tarefa | Estado |
|---|---|---|
| BL-13.01 | Etapas legíveis da importação com resumo, limitação, detalhes técnicos e **tempo real medido** | IMPLEMENTADO_E_TESTADO |
| BL-13.02 | Leitura do PDF em lotes com cobertura de páginas explícita, tokens e espera por cota | IMPLEMENTADO_E_TESTADO (IA simulada) · medição real (DYLCO, BASS-II) |
| BL-13.03 | Resumo consolidado da análise (procedência × revisão × enriquecimento) | IMPLEMENTADO_E_TESTADO (API) · PROTOTIPO (tela) |
| BL-13.04 | Revisão humana na interface com a política única do script | IMPLEMENTADO_E_TESTADO (API e componente) · **tela não inspecionada em navegador** |
| BL-13.05 | Separação **Experimentos NASA / Demonstração FDS**; cenário de hipótese do experimento | IMPLEMENTADO_E_TESTADO |
| BL-13.06 | Tempos e progresso físico real da execução | IMPLEMENTADO_E_TESTADO · execução real medida |
| BL-13.07 | Player (pausa, repetição, 0,25×–2×, linha do tempo, tela cheia) e vídeo em tempo real | IMPLEMENTADO_E_TESTADO (componente) · NOT_RUN visual |
| BL-13.08 | Validação visual S01–S07 por pessoa da equipe | **NOT_RUN** (roteiro: `docs/manual_test_roteiro_S01-S07.md`) |
| BL-13.09 | Autenticação/lista de revisores, ritmo entre lotes, OCR | NAO_INICIADO |

### BL-14 · Correção do VALUE_MISMATCH e revisão científica assistida (ADR-09 §12)
| ID | Tarefa | Estado |
|---|---|---|
| BL-14.01 | Causa raiz do `VALUE_MISMATCH` (reprodução com o registro real) | CONCLUÍDO (`docs/evidence/BL-14_…`) |
| BL-14.02 | Parsing seguro (número × unidade) e comparação estruturada por campo; tabela de unidades v1.1 com °C/K | IMPLEMENTADO_E_TESTADO |
| BL-14.03 | Diagnóstico por campo na API, na prévia e na trilha | IMPLEMENTADO_E_TESTADO |
| BL-14.04 | Verificação semântica (intervalo, incremento, lista) com bloqueio de confirmação | IMPLEMENTADO_E_TESTADO (heurística) |
| BL-14.05 | Ação “Corrigir extração” preservando o original | IMPLEMENTADO_E_TESTADO |
| BL-14.06 | Painel de revisão assistida (A–D), nome amigável e contexto da página | IMPLEMENTADO_E_TESTADO (componente) · **visual NOT_RUN** |
| BL-14.07 | Validação em navegador por pessoa da equipe | **NOT_RUN** |
| BL-14.08 | Autenticação de revisores; ampliar regras semânticas; ΔT como grandeza | NAO_INICIADO |

### BL-17.2 · Formulários científicos estruturados e resolução de lacunas (`docs/evidence/BL-17_2_formularios_estruturados.md`)
| ID | Tarefa | Estado |
|---|---|---|
| BL-17.2.01 | Diagnóstico: causa raiz dos botões desabilitados e da descontinuidade revisão→preparação | CONCLUÍDO |
| BL-17.2.02 | Contratos tipados por lacuna (grandeza, geometria, material, procedimento, medição) e unidades v1.2 | IMPLEMENTADO_E_TESTADO |
| BL-17.2.03 | Três caminhos, rascunho exploratório não aprovado, pré-visualização determinística, edição com motivo/diff | IMPLEMENTADO_E_TESTADO |
| BL-17.2.04 | Requisitos campo a campo na preparação, escada de maturidade e cinco estágios PMMA | IMPLEMENTADO_E_TESTADO |
| BL-17.2.05 | Modo de teste isolado (`var/test_mode/`) e recusa de conteúdo de teste no modo científico | IMPLEMENTADO_E_TESTADO · navegador PASS (área descartável) |
| BL-17.2.06 | Gerador PMMA, modelo de material revisado, comparação quantitativa | BLOQUEADO (modelo físico) |
| BL-17.2.07 | Validação com pesquisador humano e leitor de tela | NOT_RUN |

### BL-10 · Stretch · Visualizar resultado FDS e comparar
| ID | Tarefa | Papel | Dep. | h | Aceite / teste |
|---|---|---|---|---|---|
| BL-10.01 | `import_sim_run.py` → `SimulationRun` + registros CALCULADO | SIM/BACK | 09.04 | 1 | T-28 |
| BL-10.02 | Gráfico CALCULADO com badge e metadados de motor/versão | FRONT | 10.01 | 1 | T-10 |
| BL-10.03 | Comparação quantitativa com observável NASA (G4) | SIM+CIÊNCIA | G2 | — | **BLOQUEADO no hackathon** (sem propriedades de PMMA com fonte) |

### BL-11 · P0 · Testes finais, documentação, licenças, vídeo, submissão (F09 + F10)
| ID | Tarefa | Papel | Dep. | h | Aceite / teste |
|---|---|---|---|---|---|
| BL-11.01 | Suíte pytest completa + relatório em `docs/evidence/test_run_*.md` | QA | todas | 0,5 | 100 % MUST PASS |
| BL-11.02 | Checklist manual T-12 duas vezes, offline e com LLM off | QA | 07.01 | 1 | T-09, T-12 |
| BL-11.03 | Varredura de linguagem proibida na UI e nos slides ("validado", "prevê", "seguro", "oficial NASA") | CIÊNCIA+PITCH | — | 0,5 | 0 ocorrências indevidas |
| BL-11.04 | README final (instalação, execução, escopo, limitações, dados, créditos, licenças) | PITCH+BACK | — | 1 | T-00e repetido em máquina limpa |
| BL-11.05 | Tag `demo-v1` + congelamento do dataset | BACK | G3 | 0,1 | tag existe |
| BL-11.06 | Submissão: confirmar horário/link com a organização (DIV-09), enviar, conferir link | PITCH | 11.04 | 0,5 | link abre |

## 3. Dependências e caminho crítico

```
BL-01.07 → BL-01.01 → BL-01.02 → BL-02.01 → BL-02.03 ─┐
                       BL-01.04 → BL-02.04 → BL-02.06 → BL-02.07 → BL-02.08 ─┤
                                                                            ▼
                                        BL-03.01 → BL-03.04 → BL-03.05 → BL-06.05 → BL-07.01 → BL-11.02 → BL-11.06
                                                                                    ▲
                                        BL-04.03 → BL-04.05 ────────────────────────┤
                                        BL-05.03 → BL-05.07 → BL-05.08 → BL-05.09 ──┘
```
**Caminho crítico (sequência mínima, ~13–15 h corridas com 3–4 pessoas):**
BL-01.07 → 01.01 → 01.02 → 02.01 → 02.03 → (02.04 → 02.06 → 02.07 → 02.08 em paralelo, por DADOS) → 03.01 → 03.04 → 03.05 → 06.05 → 07.01 → 11.02 → 11.06.

**Gargalo humano:** BL-02.07/02.08 (conferência). É a única tarefa que não se paraleliza além do número de pessoas qualificadas para conferir.

## 4. Paralelismo sem espera
| Trilha | Pode começar quando | Trabalha contra |
|---|---|---|
| DADOS: PDF, page_map, transcrição | BL-01.01 | schema rascunho (BL-02.01 pode estar em andamento: combinar campos no início) |
| BACK: modelos, store, API | BL-01.02 | fixtures com o **registro M1 do DM** marcado `EXTRAIDO_NAO_REVISADO` (é dado real ainda não conferido, não mock) |
| IA: verificador, `numbers.py` | BL-02.02 | respostas fabricadas em teste unitário (sem LLM; não é uma integração) |
| FRONT: layout, componentes | BL-03.01 publicar o contrato (antes mesmo dos dados completos) | API real servindo M1 |
| PITCH: slides 1–4, README v0 | imediatamente | DM + este plano |
| SIM: leitura da §5.5 | após G1 | PDF |

## 5. Ordem de corte (se o prazo apertar)
1. BL-10 inteiro → 2. BL-09.04 → 3. BL-08.05, 08.02/03 → 4. BL-08.04 → 5. BL-02.12 → 6. BL-09.01–03 → 7. BL-08.01 → 8. reduzir os ensaios curados de 5 para 3 (o mínimo para ranking não trivial).
**Não cortáveis:** BL-02.07 (conferência), BL-03.04/05/06, BL-04.03 (explicação), BL-05.03 (verificador), BL-06.02/06, BL-07, BL-11.02.
