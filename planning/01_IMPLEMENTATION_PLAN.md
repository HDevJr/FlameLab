# 01 — IMPLEMENTATION_PLAN — FlameLab (NASA Space Apps 2026)

> Versão do plano: 0.1 (14/11/2026) · Base: `FlameLab_Documento_Mestre_Desenvolvimento_e_Pitch_v1_0.docx` (DM v1.0)
> Situação: **plano para revisão. Nenhum código foi escrito.**
> Documentos irmãos: [02](02_TECHNICAL_ARCHITECTURE.md) · [03](03_DEVELOPMENT_BACKLOG.md) · [04](04_SCIENTIFIC_DATA_CONTRACT.md) · [05](05_QUALITY_AND_VALIDATION_PLAN.md) · [06](06_PITCH_ALIGNMENT_MATRIX.md) · [07](07_RISKS_AND_DECISIONS.md) · [08](08_HACKATHON_EXECUTION_PLAN.md)

---

## Parte 1 — Entendimento do FlameLab

**Problema.** Décadas de resultados de combustão em microgravidade estão espalhados por relatórios (NTRS), repositórios (PSI), tabelas, figuras e vídeos. Para responder a uma pergunta concreta ("o que acontece com a propagação em PMMA fino a 9 cm/s?"), a pessoa precisa achar o ensaio, ler as condições, conferir unidades, comparar com outros ensaios e entender o que *não* foi medido.

**Proposta.** Um painel de investigação que leva a pessoa por **pergunta → experimento → evidência → comparação → interpretação → hipótese**, onde cada número tem origem localizável e cada lacuna aparece como lacuna. A simulação física (FDS) é o diferencial *proposto*, que só pode ser exibido depois de passar por portões científicos.

**Núcleo obrigatório (o que o desafio pede).** Os quatro verbos do desafio: **encontrar, resumir, classificar e interpretar**, num painel interativo com IA. Se a demo não mostrar os quatro com dados reais, o projeto não atende ao desafio, por mais bonita que seja a visualização.

**Escopo do hackathon.** Uma investigação (BASS-II, PSI-25 / NASA/TM-20210011385), um conjunto pequeno e curado de ensaios da Tabela 5.1 (M1 + outros), uma base de trechos do relatório para recuperação e um assistente que só fala com base nesses trechos.

**O que não é.** Não é certificação de segurança, nem previsor de incêndio, nem gerador de experimentos físicos, nem produto da NASA.

---

## Parte 2 — Diagnóstico de viabilidade

### 2.1 Estado comprovado (verificado nesta sessão, 14/11/2026)

| Item | Estado | Evidência |
|---|---|---|
| Repositório | **Não é repositório git.** A pasta `FlameLab/` só contém o DOCX. | `ls` na pasta do projeto |
| Protótipo Python de extração (§6.3 do prompt) | **NOT_VERIFIED / ausente do repositório** | Nenhum `.py` na pasta |
| PDF NASA/TM-20210011385 local | **Ausente** | Nenhum PDF na pasta |
| Python | 3.12.3 instalado | `python --version` |
| Node / npm | v24.19.0 / 11.17.0 | `node --version` |
| git | 2.39.0 | `git --version` |
| PyMuPDF, FastAPI, Pydantic | **Não instalados** no Python global | `ModuleNotFoundError` |
| FDS / Smokeview **neste computador** | **NOT_VERIFIED.** Há diretórios `C:\Program Files\firemodels\FDS6` e `SMV6` no PATH, mas `fds.exe -version` não imprimiu nada no Git Bash (talvez falte o ambiente MPI do `fdsinit.bat`). Versão e execução não estão confirmadas. A auditoria fica na F00 (BL-01.07). | listagem do diretório; saída vazia |
| Teste FDS 6.11.1 / Smokeview 6.11.2 ("STOP: FDS completed successfully") | Realizado **em outro computador** (atualização da equipe, 14/11). Prova só que a equipe consegue rodar um caso básico em algum ambiente. **Não prova nada sobre o ambiente de desenvolvimento** nem sobre BASS-II. Sem log no repositório. | relato da equipe |
| Chave de API de LLM | **Nenhuma** variável `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GEMINI_API_KEY` definida nesta máquina | checagem de variável de ambiente (só presença) |
| Reprodução numérica de BASS-II | **Não existe** | — |

### 2.2 Viabilidade por bloco

| Bloco | Viável no hackathon? | Justificativa |
|---|---|---|
| Catálogo + ficha M1 rastreável | **Sim, alto grau de confiança** | É dado pequeno, transcrito à mão e conferido no PDF. Não depende de parser. |
| Busca + ranking explicável | **Sim** | Corpus minúsculo, então pontuação determinística e transparente basta. Não precisa de vetores. |
| Comparação + gráficos de dados observados | **Sim** | Dados tabulares; uma biblioteca de gráficos. |
| Resumo/interpretação por IA com citações | **Sim, se houver acesso a LLM (D-03)** | Sem chave, cai para respostas pré-geradas em cache ou síntese determinística, sempre rotuladas. |
| Extração automática do PDF completo | **Parcial** | Parser de *uma tabela* conhecida é viável como verificação cruzada. Extração genérica é FUTURO. |
| Vídeo/imagem oficial | **Incerto** | Depende de achar arquivo e licença (D-04). |
| FDS reproduzindo M1 | **Improvável em ~30 h** | Faltam propriedades de pirólise do PMMA, geometria exata, perfil de fluxo e ignição (DM §08.2). A chama em µg na escala de mm exige malha fina, o que dá horas de CPU. O próprio relatório registra discrepâncias com FDS 5.5.3 (DM §08). O realista é chegar a FDS-G1 (geometria justificada) e, no máximo, um escoamento frio exploratório rotulado. |

### 2.3 Desafios técnicos principais
1. **Rastreabilidade fina:** localizar página impressa, índice de página do PDF, tabela, linha e coluna para cada valor. É trabalho manual e exige disciplina.
2. **Verificação determinística da saída da IA:** extrair números da resposta, normalizar unidades e casar com evidências citadas.
3. **Funcionar offline:** a demo não pode depender de internet nem de LLM ao vivo.
4. **Integração de três camadas (dados, API, UI) em menos de 1 dia** sem contratos quebrando. A mitigação é congelar o contrato de dados cedo (F02).

### 2.4 Desafios científicos principais
1. Separar **condição** (9 cm/s) de **resultado observado** (0,071 mm/s) em todas as camadas.
2. O₂ inicial/final **não é concentração constante**. Também é preciso confirmar a base (% vol.) na fonte.
3. A duração (6,4 min) **não implica regime estacionário**.
4. **Comparabilidade:** ensaios que diferem em várias variáveis ao mesmo tempo não autorizam conclusão causal.
5. **Extrapolação** (Marte, Lua, outra pressão): a resposta correta é a abstenção fundamentada.

### 2.5 Dependências externas
NTRS (download do PDF), PSI-25 (metadados/DOI), provedor de LLM (indefinido), mídia NASA (licença), FDS/Smokeview (local), npm/PyPI (instalação, uma vez só, com internet).

### 2.6 Inconsistências e lacunas encontradas
Detalhadas com consequência e recomendação em [07_RISKS_AND_DECISIONS.md §2](07_RISKS_AND_DECISIONS.md). Resumo:
- **DIV-01**: `CALCULADO` e `INFERIDO` aparecem como *estado de revisão* no DM, mas o prompt os trata como *natureza epistêmica*. Proposta: dois eixos ortogonais, mantendo os 6 estados do DM.
- **DIV-02**: "8 campos tabulados" (T-01), mas O₂ inicial/final são 2 valores (9 registros), e *Material* vem do contexto da seção 5, não de uma coluna da tabela.
- **DIV-03**: Os valores atuais de M1 foram "conferidos no texto compartilhado", não no PDF original. Pela política do DM, ainda são `EXTRAIDO_NAO_REVISADO`.
- **DIV-04**: Rota `/api/tests/M1` usa ID não qualificado, que pode colidir entre investigações.
- **DIV-05**: SQLite e JSON aparecem como persistência ao mesmo tempo. Para o tamanho do corpus, JSON versionado basta e SQLite é desnecessário no MVP.
- **DIV-06**: T-04 ("M2 com duas velocidades") e T-05 ("M1 × M14") pressupõem um conteúdo da Tabela 5.1 que **não foi verificado**.
- **DIV-07**: O protótipo de extração citado no prompt não está no repositório.
- **DIV-08**: O cronograma do DM começa em "14/11 manhã". Este plano está sendo feito nessa mesma janela, então o cronograma precisa ser comprimido.
- **DIV-09**: Horário de submissão: 17h local (Rio Verde) ou 23h59 (site geral). Planejar por 17h e confirmar com a organização.
- **DIV-10**: "Ambiente: Microgravidade" aparece no prompt como parâmetro do ensaio. Proposta: tratar como metadado da investigação (ISS), não como linha da Tabela 5.1.
- **DIV-11**: O relatório exportável S07 aparece na jornada, mas não na lista MUST. Classificado como SHOULD.
- **DIV-12**: O título do desafio está escrito "SI-Powered" no DM e no prompt. Conferir a grafia oficial na página antes de usar no slide 03.
- **DIV-13**: O DM §11 sugere que o FDS 6.11.1 está instalado e testado, mas o teste foi feito **em outro computador** (atualização da equipe, 14/11). O FDS no ambiente do projeto fica NOT_VERIFIED até a auditoria F00.A.
- **DIV-14**: O DM §10 prevê "extração por modelo multimodal". Isso é inviável no prazo e fica como FUTURO.

### 2.7 Avaliação da arquitetura proposta (resumo; detalhes em [02](02_TECHNICAL_ARCHITECTURE.md))
| Proposta DM | Veredito | Ajuste recomendado |
|---|---|---|
| React + TS + Vite | Manter | Uma única lib de gráficos (Recharts). Sem state manager global, sem UI kit pesado. |
| Python + FastAPI | Manter | FastAPI também serve o build do frontend: **um processo, uma porta, demo offline**. |
| PyMuPDF + Pydantic + adaptador de tabela | Manter Pydantic (MUST). PyMuPDF só para (a) mapear páginas e extrair trechos para RAG e (b) parser de verificação da Tabela 5.1 | O parser **não fica no caminho crítico**: a fonte da verdade é a transcrição curada e conferida. |
| SQLite + JSON | **Só JSON versionado no git** | SQLite fica para o FUTURO, quando o corpus crescer. Menos código, diffs revisáveis. |
| RAG + LLM | Manter, com **recuperação lexical (BM25)** sobre trechos curados | Embeddings/vetores são desnecessários para cerca de 100 trechos e acrescentam dependência e risco. |
| IA multimodal | **Fora do MVP** | Não se justifica no prazo. |
| FDS/Smokeview | STRETCH isolado, **nunca exposto via API** | Execuções são offline e manuais; os resultados entram como arquivos importados com estado `CALCULADO`. |

### 2.8 O que precisa ser decidido antes de implementar
Ver [07 §3](07_RISKS_AND_DECISIONS.md). Bloqueantes para começar: **D-01** (quantos ensaios), **D-03** (provedor de LLM e chave), **D-07** (eixos de estado), **D-08** (repositório e onde fica o protótipo).

---

## Parte 3 — Escopo final recomendado para o MVP

| Faixa | Entrega | Critério de "pronto" |
|---|---|---|
| **MUST** | M-1 Catálogo BASS-II com ≥5 ensaios da Tabela 5.1 (M1 + ≥4), valores `CONFERIDO_FONTE` | T-01, T-07 PASS |
| MUST | M-2 Ficha M1: 9 registros (8 campos), estados, origem clicável (página, tabela, linha, coluna, trecho) | T-01, T-03 PASS |
| MUST | M-3 Lacunas: lista de parâmetros `AUSENTE` (DM §08.2) com o motivo e o que bloqueiam | T-02 PASS |
| MUST | M-4 Busca textual + filtros (material, espessura, faces, fluxo, O₂) | T-13 PASS |
| MUST | M-5 Ranking explicável ("por que este registro", com a contribuição de cada critério) | T-14 PASS |
| MUST | M-6 Assistente: resumo e interpretação com citações, verificação determinística de números e abstenção | T-03, T-06, T-15, T-16 PASS |
| MUST | M-7 Comparação lado a lado de ≥2 ensaios, com avisos de não comparabilidade | T-05 PASS |
| MUST | M-8 Gráfico de dados observados (propagação × fluxo, por ensaio) rotulado "Dados experimentais NASA" | T-10b PASS |
| MUST | M-9 Modo degradado: sem LLM, o catálogo, a busca, a comparação e as fontes continuam funcionando | T-09 PASS |
| MUST | M-10 Trilha de demo de 3 min, reproduzível, com o aviso "projeto independente, não endossado pela NASA" | T-12 PASS |
| **SHOULD** | S-1 Esquema conceitual do aparato (SVG) rotulado "Ilustração conceitual" | T-17 |
| SHOULD | S-2 Mídia oficial (imagem/vídeo) com licença registrada | D-04 resolvido |
| SHOULD | S-3 Visualização temporal (só se a fonte tiver série temporal real; caso contrário, não fazer) | dado existe |
| SHOULD | S-4 Relatório/exportação S07 (Markdown/JSON com fontes e versão do dataset) | T-18 |
| SHOULD | S-5 Parser PyMuPDF que reextrai a Tabela 5.1 e confere com a curadoria | T-04, T-08 |
| **STRETCH** | X-1 FDS-G1: geometria e entrada justificadas e documentadas (sem combustão) | Gate G1 |
| STRETCH | X-2 Escoamento frio exploratório em geometria aproximada, pré-executado, com log e versão, rotulado "Simulação numérica exploratória — não é reprodução de M1" | G1 + G3 |
| STRETCH | X-3 Reprodução de M1 com comparação quantitativa (G2–G4) | **Considerado BLOQUEADO até haver propriedades do PMMA com fonte** |
| **FUTURO** | Extração multimodal genérica, múltiplas investigações, IA configuradora de FDS, cenários livres, 3D, colaboração, SQLite/Postgres, embeddings | — |

**Definição de sucesso mínimo (DM §06, mantida):** selecionar M1, ver os parâmetros identificados e os ausentes, abrir o trecho de origem, comparar com outro ensaio, perguntar e receber uma interpretação citada e limitada. **Esse percurso não depende do FDS.**

---

## Parte 4 — Arquitetura recomendada (resumo)

```
┌──────────── Navegador (React + TS + Vite, build estático) ───────────┐
│ S01 Home  S02 Explorer  S03 Ficha  S04 Comparação  S05 Assistente     │
│ S06 Laboratório visual (OBSERVADO | CONCEITUAL | COMPUTACIONAL*)      │
└───────────────▲──────────────────── JSON/HTTP (mesma origem) ─────────┘
                │
┌───────────────┴───────────── FastAPI (1 processo, porta local) ──────┐
│ catalog  search/rank  compare  ask(orchestrator)  viz  health         │
│   │          │           │        │  retrieve(BM25) → LLM adapter     │
│   │          │           │        │  → verifier (determinístico)      │
│   │          │           │        └→ cache de respostas (JSON)        │
│   └──── DatasetStore (carrega + valida Pydantic no startup) ──────────│
└───────────────▲───────────────────────────────────────────────────────┘
                │ leitura
  data/ (git): documents.json · investigations.json · tests/*.json ·
               parameters/*.json · evidence/*.json · passages/*.jsonl ·
               gaps.json · ai_cache/*.json · sim_runs/* (stretch, importado)
  sources/ (fora do git ou LFS): NASA-TM-20210011385.pdf + sha256

  Offline, fora da API: scripts/ (parser de verificação, extração de trechos,
  hash) · fds/ (casos .fds revisados, logs, saídas; execução manual)
```
Detalhamento completo, contratos e APIs: [02_TECHNICAL_ARCHITECTURE.md](02_TECHNICAL_ARCHITECTURE.md) e [04_SCIENTIFIC_DATA_CONTRACT.md](04_SCIENTIFIC_DATA_CONTRACT.md).

**Determinístico × IA**

| Tarefa | Determinístico | IA |
|---|---|---|
| Conversão de unidades, validação de faixas, vínculo ensaio↔valor | ✔ | — |
| Detectar ausência (AUSENTE) | ✔ (lista curada de campos esperados) | — |
| Busca, filtros, ranking e explicação do ranking | ✔ (BM25 + pesos explícitos) | — |
| Comparação e avisos de comparabilidade | ✔ (regras: nº de variáveis diferentes, diferença de faces/espessura) | — |
| Checagem de números, citações e estados na resposta | ✔ (verifier) | — |
| Abstenção por falta de evidência | ✔ (limiar de recuperação + verifier) | a IA também pode se abster |
| Redigir síntese em português a partir de trechos | — | ✔ |
| Interpretar relações entre achados (com cautela causal) | — | ✔ (rotulado OBSERVACAO/ASSOCIACAO/HIPOTESE) |
| Explicar termos técnicos | — | ✔ (rotulado EXPLICACAO, sem números) |
| Extrair parâmetros do PDF | ✔ parser de tabela conhecida | FUTURO (multimodal) |

---

## Parte 5 — Fases de desenvolvimento

### 5.1 Ajustes à sequência proposta, com justificativa
1. **F01 e F02 viram trilhas paralelas, mas o caminho crítico passa pela curadoria manual**, não pelo parser. Motivo: o DM (§17) já prevê "importação curada de fallback". Pôr o parser no caminho crítico arrisca todo o MVP por causa de uma tabela quebrada.
2. **O contrato de dados (F02a) vem antes da transcrição em escala.** Sem schema congelado, o JSON curado precisa ser refeito.
3. **F04–F07 rodam em paralelo** sobre a API de F03 com dados reais, sem mocks. Com dataset real desde o início, o "funciona com mock" não chega a acontecer.
4. **F08 (FDS) é uma trilha separada com time-box**, que só pode consumir horas de quem não está no caminho crítico, e só depois de G1.
5. **F10 (pitch) começa na hora zero** e não é a última fase. Ela avança junto com os gates.

### 5.2 Sequência e dependências

```
F00 Preparação ─┬─> F01 Corpus (PDF, hash, páginas, transcrição) ─┐
                └─> F02a Contrato/validadores ─────────────────────┴─> F03 API+catálogo ─┬─> F04 Interface ─┐
                    F02b Parser verificação (paralelo, SHOULD) ··········(cross-check)·· │                  │
                                                                         ├─> F05 Busca/ranking ─┤
                    F06a Trechos p/ RAG (de F01) ─────────────────────────┼─> F06 Assistente ─────┤
                                                                         └─> F07 Comparação/viz ─┤
                    F08 FDS (STRETCH, time-box, após G1) ········································│
                                                                                                 v
F10 Pitch (contínuo desde F00) ───────────────────────────────────────> F09 Qualidade/demo ─> F10 Entrega
```

**Caminho crítico:** F00 → F01 (M1 + 4 ensaios conferidos) → F02a → F03 → F04 (ficha) → F07 (comparação) → F09 → F10.
**Caminho de maior risco (paralelo):** D-03 → F06 (assistente). Se travar, M-9 (modo degradado) garante a demo, e o pitch rebaixa a IA conforme [06](06_PITCH_ALIGNMENT_MATRIX.md).

### 5.3 Detalhamento de cada fase (Bloco D)

Cada fase usa os 15 itens pedidos. Testes `T-xx` estão em [05](05_QUALITY_AND_VALIDATION_PLAN.md) e subtarefas `BL-xx.yy` em [03](03_DEVELOPMENT_BACKLOG.md).

---

#### F00 — Preparação do projeto
1. **ID:** F00 · 2. **Nome:** Preparação · 4. **Prioridade:** MUST
3. **Objetivo:** saber com evidência o que existe no ambiente atual. Depois disso, ter repositório, ambiente reproduzível e esqueleto que sobe com um comando, além do PDF-fonte baixado com hash.
5. **Pré-requisitos:** D-08 (repositório/remote), internet para instalar dependências.
6. **Tarefas — F00.A Auditoria do ambiente (primeiro passo, antes de instalar qualquer coisa):** inventário de cada máquina que será usada (dev e demo) em `docs/environment_audit.md`, com o comando exato e a saída de cada item: SO; Python; Node/npm; git; pacotes Python (PyMuPDF, FastAPI, Pydantic); presença e versão do FDS (`fds` em "CMD with FDS"/`fdsinit.bat`); Smokeview; execução de um caso mínimo do FDS *nesta máquina* (opcional, só se F08 for tentada); acesso a LLM (D-03: chave/provedor, sem registrar o valor); presença do protótipo de extração (D-08); presença do PDF-fonte. Cada item recebe `VERIFIED` / `NOT_VERIFIED` / `ABSENT`. O teste FDS feito no outro computador fica registrado como histórico, **não** como estado deste ambiente. Saída: lista de dependências a instalar.
   **F00.B Estrutura:** `git init` + `.gitignore` · README inicial com escopo e aviso de independência da NASA · `backend/` com venv, `requirements.txt` fixado (fastapi, uvicorn, pydantic, pymupdf, rank-bm25, pytest, httpx) · `frontend/` via Vite React-TS + Recharts · endpoint `/api/health` · FastAPI servindo `frontend/dist` · baixar NASA/TM-20210011385 para `sources/`, calcular sha256, registrar a data do download · registrar as versões das ferramentas (`fds` via `fdsinit`/CMD) em `docs/environment.md` · importar o protótipo de extração, se for fornecido (D-08).
7. **Arquivos:** `README.md`, `.gitignore`, `backend/app/main.py`, `backend/requirements.txt`, `frontend/*`, `sources/README.md`, `data/documents.json`, `docs/environment_audit.md`, `scripts/hash_sources.py`.
8. **Contratos:** `Document` (sha256, retrieved_at). Ver [04 §3.1](04_SCIENTIFIC_DATA_CONTRACT.md).
9. **Testes:** T-00a (instalação limpa), T-00b (`/api/health` 200), T-00c (`npm run build` ok e servido pelo FastAPI), T-00d (sha256 recomputado = registrado).
10. **Aceite:** outra pessoa clona, segue o README e vê a página-placeholder servida pelo backend em ≤10 min. O sha256 do PDF está em `documents.json`.
11. **Evidências:** commit hash, print do health, sha256 no JSON, saída do `fds` com a versão.
12. **Riscos:** internet instável no evento; versão de Node/Python divergente entre máquinas.
13. **Plano B:** instalar dependências logo no início do dia, enquanto há internet. Uma máquina "de demo" única.
14. **Impacto na demo:** nenhum visível; é a base.
15. **Pitch:** "Executamos um caso básico de FDS 6.11.1 + Smokeview 6.11.2" pode ser dito como **viabilidade do ambiente**, desde que exista uma captura ou log do outro computador. Sem isso, a frase sai. Afirmar que o FDS está integrado ao FlameLab exige a auditoria `VERIFIED` na máquina do projeto **e** a F08.

---

#### F01 — Base científica (corpus curado)
1. F01 · 2. Base científica · 4. **MUST**
3. **Objetivo:** ter os valores da Tabela 5.1 de M1 e ≥4 outros ensaios, conferidos no PDF original com localização exata, e os trechos do relatório que vão alimentar o RAG.
5. **Pré-requisitos:** F00 (PDF + hash), F02a pelo menos em rascunho (schema dos registros), D-01.
6. **Tarefas:**
   - Mapear página impressa ↔ índice de página do PDF para as seções 5.3, 5.5, 5.6 e a Tabela 5.1.
   - Transcrever as linhas de M1 e de ≥4 ensaios, escolhidos para criar contrastes úteis (mesma espessura com fluxo diferente; faces diferentes; O₂ diferente; o M2 se tiver as "duas velocidades" do T-04; o M14 se existir).
   - Para cada valor: texto literal da célula, unidade original, cabeçalho da coluna e rótulo da linha.
   - **Segunda pessoa confere** cada valor contra o PDF. Só depois disso o estado vira `CONFERIDO_FONTE`.
   - Registrar a origem do "Material = PMMA" (seção/página do texto, não a tabela).
   - Criar `gaps.json` com os parâmetros AUSENTES do DM §08.2 e o motivo de cada um.
   - Extrair os trechos (parágrafos com página) das seções 5.x para `passages.jsonl`. Ver F06a.
7. **Arquivos:** `data/investigations.json`, `data/tests/BASS2-*.json`, `data/parameters/BASS2-*.json`, `data/evidence/*.json`, `data/gaps.json`, `data/passages/NASA-TM-20210011385.jsonl`, `docs/curation_log.md`.
8. **Contratos:** `Investigation`, `Test`, `ParameterRecord`, `Evidence`, `Gap`, `Passage`.
9. **Testes:** T-01, T-02, T-03, T-07, T-19 (dupla conferência registrada).
10. **Aceite (resultado esperado):** a linha **M1** está identificada e os **9 registros** (material, espessura 1 mm, largura 2,2 cm, faces 1, fluxo 9 cm/s, propagação 0,071 mm/s, duração 6,4 min, O₂ inicial 22,2 %, O₂ final 21,9 %) têm unidade original e valor normalizado SI (0,001 m; 0,022 m; 0,09 m/s; 7,1×10⁻⁵ m/s; 384 s; 0,222 e 0,219 em fração). Cada um traz `table="5.1"`, `row="M1"`, coluna, página PDF e página impressa. Nenhum valor de M2 aparece em M1. Os parâmetros da §08.2 aparecem como `AUSENTE` e `value=null`. Todos os registros exibidos na demo estão em `CONFERIDO_FONTE`, com o nome de quem conferiu.
11. **Evidências:** `curation_log.md` com quem transcreveu, quem conferiu e quando; diff dos JSONs; prints das páginas do PDF.
12. **Riscos:** a Tabela 5.1 não ter o layout esperado; M2/M14 não terem as características dos testes do DM; a base do O₂ não estar declarada.
13. **Plano B:** se M14 não existir, escolher outro ensaio com várias diferenças em relação a M1 e atualizar o T-05. Se a base do O₂ não estiver declarada, `unit_original="%"` e `basis=AUSENTE`, com a lacuna exibida.
14. **Impacto na demo:** é a matéria-prima de tudo. Sem F01, não há demo.
15. **Pitch:** "Cada número da ficha M1 tem página, tabela e linha conferidos no relatório NASA/TM-20210011385".

---

#### F02 — Extração e rastreabilidade
Duas subfases.

**F02a — Contrato e validadores (MUST, caminho crítico)**
3. **Objetivo:** ter um schema Pydantic congelado e validadores determinísticos que *recusam* dados inconsistentes no carregamento.
6. **Tarefas:** modelos Pydantic de [04](04_SCIENTIFIC_DATA_CONTRACT.md) · tabela de unidades (mm, cm, m, cm/s, mm/s, m/s, s, min, %) com conversões · invariantes (AUSENTE ⇒ value null; CONFERIDO_FONTE ⇒ evidence com página e reviewer; role=OBSERVAVEL nunca é marcado como entrada de modelo; o `test_id` da evidência é igual ao `test_id` do registro; CALCULADO ⇒ `sim_run_id`) · `DatasetStore` que carrega, valida e falha alto (fail-fast) · `dataset_version` = hash do conteúdo de `data/`.
7. **Arquivos:** `backend/app/models/*.py`, `backend/app/units.py`, `backend/app/store.py`, `backend/tests/test_contract.py`, `backend/tests/test_units.py`.
9. **Testes:** T-07, T-20 (invariantes rejeitam JSON inválido), T-21 (M1/M2 não se misturam).
10. **Aceite:** carregar o dataset real passa; cada um dos 6 JSONs propositalmente inválidos em `tests/fixtures/invalid/` é rejeitado com uma mensagem que nomeia o campo.

**F02b — Parser de verificação da Tabela 5.1 (SHOULD, fora do caminho crítico)**
3. **Objetivo:** confirmar automaticamente que a transcrição curada bate com o texto do PDF e localizar as páginas. Ele **não substitui** a curadoria.
6. **Tarefas:** usar PyMuPDF para achar a página da "Table 5.1" · extrair as palavras com coordenadas · reconstruir as linhas por rótulo (M1, M2…) · comparar célula a célula com a curadoria · gerar `reports/table51_crosscheck.md` · reaproveitar o protótipo existente, se D-08 o trouxer.
9. **Testes:** T-04, T-08.
10. **Aceite:** o relatório mostra para cada célula curada MATCH/MISMATCH/NOT_FOUND. Um MISMATCH bloqueia o `CONFERIDO_FONTE` até revisão humana. Um trecho malformado (T-08) gera NOT_FOUND e nunca um palpite.
12. **Riscos:** tabela renderizada como imagem ou com colunas mescladas. **Plano B:** abandonar o F02b e registrar no pitch que a extração automática "não foi homologada".
15. **Pitch (só se PASS):** "Um verificador automático confere a transcrição da tabela contra o PDF." Sem PASS, o pitch não menciona extração automática.

---

#### F03 — API e catálogo
1. F03 · 4. **MUST**
3. **Objetivo:** expor o dataset validado em endpoints estáveis, consumidos por todas as telas.
5. **Pré-requisitos:** F02a, e F01 com pelo menos M1.
6. **Tarefas:** endpoints de leitura de [02 §4](02_TECHNICAL_ARCHITECTURE.md) · envelope de resposta padrão (`data`, `dataset_version`, `warnings`) · erros padronizados · CORS desligado em produção (mesma origem) · tipos TS gerados ou escritos a partir do OpenAPI (`openapi-typescript`, opcional).
7. **Arquivos:** `backend/app/api/catalog.py`, `backend/app/api/errors.py`, `backend/tests/test_api_catalog.py`, `frontend/src/api/client.ts`, `frontend/src/api/types.ts`.
9. **Testes:** T-01 via API, T-02 via API, T-22 (404 claro para ensaio inexistente), T-23 (contrato: todo número na resposta vem com unidade e evidence_id).
10. **Aceite:** `GET /api/tests/BASS2-M1` retorna 9 registros, cada um com `status`, `role`, `evidence[]`, e uma lista `gaps[]` não vazia. `GET /api/tests/BASS2-M1/evidence` retorna a localização de cada campo. Os testes de API passam no pytest.
13. **Plano B:** se o frontend atrasar, a API + Swagger (`/docs`) servem para o print de evidência, mas **não** contam como demo.
15. **Pitch:** nenhum enunciado próprio; habilita F04–F07.

---

#### F04 — Interface científica
1. F04 · 4. **MUST** (S01–S03), S06 parcial SHOULD
3. **Objetivo:** permitir que uma pessoa sem ajuda encontre M1, entenda condições × resultados, clique na origem de cada valor e veja as lacunas.
5. **Pré-requisitos:** F03.
6. **Tarefas:** S01 Home (o que é, busca, BASS-II, "como funciona", aviso de independência) · S02 Explorer (lista + filtros; o resultado vem de F05) · S03 Ficha: blocos "Condições do ensaio" e "Resultados observados" separados visualmente; chip de estado por valor; popover de origem (documento, página PDF/impressa, tabela, linha/coluna, trecho literal em inglês, link NTRS); painel "O que não sabemos" (gaps); botões "Comparar" e "Perguntar à IA" · componente `NatureBadge` (OBSERVADO/CALCULADO/INFERIDO/CONCEITUAL) obrigatório em toda visualização · rótulos em PT com o termo original em inglês entre parênteses · acessibilidade básica (contraste, estado não só por cor).
7. **Arquivos:** `frontend/src/pages/{Home,Explorer,TestDetail}.tsx`, `frontend/src/components/{ParameterTable,SourcePopover,StatusChip,NatureBadge,GapsPanel,IndependenceNotice}.tsx`.
9. **Testes:** T-01 (UI), T-02 (UI), T-17 (rótulos), T-24 (pessoa externa encontra a origem do valor 0,071 mm/s em ≤30 s sem ajuda).
10. **Aceite:** na S03, todos os 9 valores aparecem com unidade e chip. Clicar em 0,071 mm/s mostra "Tabela 5.1, linha M1, coluna …, p. PDF n / impressa m" e o trecho. O painel de lacunas lista ≥6 itens do §08.2. Nenhum valor aparece sem unidade.
12. **Riscos:** gastar tempo em estética antes do fluxo. **Plano B:** layout simples, e o polimento visual fica para depois do G2.
15. **Pitch:** print da S03 com o popover de origem aberto, no slide 05/06.

---

#### F05 — Busca e classificação
1. F05 · 4. **MUST**
3. **Objetivo:** dada uma pergunta ou um conjunto de condições, ordenar os ensaios e trechos e **explicar** cada posição.
5. **Pré-requisitos:** F03, e ≥5 ensaios em F01.
6. **Tarefas:** BM25 sobre `Test` (descrição + tags) e `Passage` · filtros exatos e por faixa · escore de similaridade de condições com pesos explícitos (material, espessura, faces, fluxo, O₂), cada critério devolvendo `{criterio, valor_consulta, valor_registro, contribuicao, explicacao}` · ensaio de referência (ex.: "parecidos com M1") · aviso fixo "Relevância para a pergunta, não indicador de segurança" · ignorar campos AUSENTES no escore e dizer que foram ignorados.
7. **Arquivos:** `backend/app/search/{bm25.py,rank.py,weights.json}`, `backend/app/api/search.py`, `backend/tests/test_rank.py`, `frontend/src/components/RankExplanation.tsx`.
9. **Testes:** T-13 (busca "PMMA one-sided" retorna M1), T-14 (explicação soma ao escore; o aviso aparece), T-25 (determinismo: mesma consulta, mesma ordem).
10. **Aceite:** "parecidos com M1" devolve uma ordem estável, e cada item lista ≥3 critérios com a contribuição numérica. A soma das contribuições é igual ao escore exibido (±1e-9). Os pesos estão versionados em `weights.json`.
13. **Plano B:** se o escore por condições confundir mais do que ajudar, ficar só com BM25 + filtros, com a explicação "termos encontrados".
15. **Pitch:** "O ranking mostra por que cada ensaio aparece. Não é um score de segurança."

---

#### F06 — Assistente científico
1. F06 · 4. **MUST**
3. **Objetivo:** responder perguntas com síntese em português **limitada às evidências recuperadas**, citações verificáveis e abstenção quando falta base.
5. **Pré-requisitos:** F01 (trechos), F03, F05 (recuperação), **D-03** (LLM).
6. **Tarefas:**
   - **F06a** Trechos: parágrafos das seções 5.x com página, mais "fichas sintéticas" geradas *deterministicamente* a partir dos registros conferidos (ex.: "Ensaio M1: velocidade de propagação observada 0,071 mm/s [Tabela 5.1]").
   - **F06b** Orquestrador: escopo → recuperação (top-k BM25 + registros do ensaio em foco) → limiar mínimo; abaixo dele, abstém sem chamar o LLM.
   - **F06c** Adaptador LLM agnóstico de provedor (interface `generate(prompt, schema) -> json`), timeout de 20 s, sem ferramentas (*tools*) e sem acesso à rede além do provedor.
   - **F06d** Prompt de sistema: os trechos chegam dentro de delimitadores como **dados não confiáveis**; a saída é JSON com `claims[]`, e cada claim tem `type` (OBSERVACAO/ASSOCIACAO/HIPOTESE/EXPLICACAO/LIMITACAO), `evidence_ids[]` e `numbers[]`.
   - **F06e** Verificador determinístico: (1) todo `evidence_id` existe e foi recuperado; (2) todo número no texto aparece em `numbers[]` e casa, após normalização de unidade, com um valor da evidência citada; (3) o `test_id` mencionado é igual ao da evidência; (4) uma claim OBSERVACAO exige evidência OBSERVADO; (5) nenhuma claim pode citar registro `AUSENTE` com número; (6) causalidade ("causa", "devido a") só é aceita em HIPOTESE. Uma claim que falha é removida e listada em "afirmações bloqueadas". Se sobrar zero claims, a resposta é abstenção.
   - **F06f** Cache: respostas verificadas das perguntas da demo salvas em `data/ai_cache/` com provedor, modelo, prompt_version, dataset_version e timestamp. A UI mostra "Resposta gerada por IA em <data>, reproduzida do cache".
   - **F06g** Modo sem LLM: a UI mostra "IA indisponível" e oferece os trechos recuperados + a ficha. **Não** gera um texto que pareça de IA.
7. **Arquivos:** `backend/app/assistant/{retrieve.py,orchestrator.py,llm_adapter.py,prompts/v1.md,verifier.py,numbers.py,cache.py}`, `backend/app/api/ask.py`, `backend/tests/test_verifier.py`, `backend/tests/test_ask_golden.py`, `frontend/src/pages/Assistant.tsx`.
9. **Testes:** T-03, T-06, T-09, T-15 (número inventado é bloqueado), T-16 (injeção de prompt em trecho é ignorada), T-26 (pergunta "A NASA validou nosso FDS?" recebe "Não").
10. **Aceite:** as 4 perguntas do DM §10.1 + 4 perguntas adversariais passam: a resposta tem ≥1 citação clicável que abre o trecho; nenhum número sem evidência. A pergunta de Marte devolve abstenção listando as diferenças. Com o LLM desligado, o `/api/ask` responde `mode="UNAVAILABLE"` em <1 s e a UI continua usável. O verificador tem testes unitários com respostas fabricadas (sem LLM), o que permite testá-lo mesmo antes de D-03.
12. **Riscos:** não haver chave de API (hoje não há nesta máquina); latência alta; o LLM ignorar o schema.
13. **Plano B:** (1) cache das perguntas da demo gerado na noite de 14/11; (2) sem nenhum acesso a LLM, a funcionalidade fica **BLOQUEADA** e o pitch diz "assistente implementado, demonstrado sem IA ao vivo", conforme [06](06_PITCH_ALIGNMENT_MATRIX.md). Nesse caso o núcleo do desafio fica descoberto, por isso D-03 é a decisão de maior prioridade.
14. **Impacto na demo:** é o "resumir/interpretar" do desafio, um dos 4 verbos.
15. **Pitch:** "A IA responde com citações. Quando não há evidência, ela diz que não há." Mostrar a resposta de Marte (abstenção) como prova de confiança.

---

#### F07 — Comparação e visualização
1. F07 · 4. **MUST** (comparação + gráfico observado); SHOULD (temporal, mídia, esquema)
3. **Objetivo:** comparar ensaios lado a lado e visualizar dados observados reais com rótulo de natureza.
5. **Pré-requisitos:** F03, ≥2 ensaios conferidos.
6. **Tarefas:** `POST /api/compare` com alinhamento por parâmetro, diferenças absolutas e relativas, contagem de variáveis diferentes e avisos ("M1 e Mx diferem em 3 condições; a diferença de propagação não pode ser atribuída a uma única variável") · S04 tabela + destaque das diferenças · gráfico M-8: propagação observada × velocidade do fluxo, um ponto por ensaio, com a forma do marcador por faces/espessura e o tooltip com a fonte · badge "Dados experimentais NASA — Tabela 5.1" · (SHOULD) SVG conceitual do duto com a direção do fluxo, badge "Ilustração conceitual — não é dado medido" · (SHOULD) mídia oficial com licença.
7. **Arquivos:** `backend/app/api/compare.py`, `backend/app/compare/rules.py`, `backend/app/api/viz.py`, `frontend/src/pages/Compare.tsx`, `frontend/src/components/{SpreadVsFlowChart,ApparatusSchematic}.tsx`.
9. **Testes:** T-05, T-10b (gráfico observado rotulado, pontos iguais aos registros), T-17 (esquema rotulado), T-27 (gráfico não interpola nem desenha linha de tendência sem rótulo de natureza).
10. **Aceite:** comparar M1 × outro mostra ≥3 linhas com diferença destacada e o aviso de causalidade quando houver ≥2 diferenças. O gráfico tem N pontos = N ensaios conferidos e cada tooltip mostra a fonte. Não há curva ajustada, a menos que esteja rotulada "ajuste INFERIDO" (recomendação: não fazer).
15. **Pitch:** print do gráfico e da comparação com o aviso, nos slides 05/06.

---

#### F08 — Integração experimental FDS (STRETCH, gated)
1. F08 · 4. **STRETCH** · time-box: **máx. 4 h-pessoa no dia 14 + 2 h no dia 15, até as 09h**. Depois disso, go/no-go.
3. **Objetivo:** demonstrar, de forma honesta, até onde a ponte documento → modelo chega: no mínimo um checklist FDS-G1 preenchido a partir da ficha, com as lacunas bloqueantes visíveis.
5. **Pré-requisitos:** G1 do hackathon alcançado (fluxo mínimo sem IA); pessoa fora do caminho crítico; leitura da §5.5 do relatório; **FDS `VERIFIED` na auditoria F00.A em alguma máquina da equipe com acesso ao repositório**. Sem isso, só X-1 (documental) é possível.
6. **Tarefas:**
   - X-1: ler a §5.5 (FDS 5.5.3: geometria do duto, malha, propriedades usadas, discrepâncias) e registrar cada item como `ParameterRecord` com evidência, ou como AUSENTE.
   - Montar o checklist G1–G5 em `data/fds_readiness/BASS2-M1.json` (estado de cada gate e o motivo).
   - Tela S06 "Prontidão para simulação": gates, o que falta e de onde viria.
   - (X-2, só se as dimensões do duto tiverem fonte) caso de **escoamento frio** a 0,09 m/s em geometria aproximada, revisado por humano, executado **manualmente** fora da API. Guardar o `.fds`, o log completo, a versão e um perfil de velocidade. Importar como `SimulationRun` CALCULADO, com o badge "Simulação numérica exploratória — sem combustão — não é reprodução de M1".
   - Verificar diferenças de sintaxe/namelist entre FDS 5.5.3 e 6.x **no Guia do Usuário do FDS 6** antes de reaproveitar qualquer parâmetro histórico.
7. **Arquivos:** `fds/cases/BASS2-M1-coldflow/{case.fds,README.md}`, `fds/runs/<run_id>/{log.txt,*.csv}`, `data/fds_readiness/BASS2-M1.json`, `data/sim_runs/<run_id>.json`, `frontend/src/pages/SimulationReadiness.tsx`.
9. **Testes:** T-10 (rótulo de simulação), T-11 (execução via app bloqueada), T-28 (run importado tem versão, hash do .fds e log).
10. **Aceite:** G1 PASS = cada dimensão e condição de entrada do caso tem evidência ou é uma hipótese declarada `INFERIDO` com justificativa revisada. G3 PASS = log termina em "STOP: FDS completed successfully", com os arquivos guardados. **G2 e G4 ficam fora do alcance esperado** e não podem ser declarados sem propriedades do PMMA com fonte e sem comparação quantitativa documentada.
12. **Riscos:** tempo de CPU; sintaxe 5.5.3 incompatível; tentação de "calibrar" a propagação até 0,071 mm/s (proibido: é observável).
13. **Plano B:** S06 mostra só o checklist e as lacunas. O slide 07 vira roadmap.
14. **Impacto na demo:** opcional. Nunca pode atrasar G2/G3.
15. **Pitch:** com G1 só: "mapeamos o que falta para reproduzir M1 em FDS". Com G1+G3 (frio): "executamos um escoamento exploratório na geometria aproximada; ainda não é uma reprodução". **"Reproduzimos M1" nunca é permitido sem G4.**

---

#### F09 — Qualidade e demonstração
1. F09 · 4. **MUST**
3. **Objetivo:** mostrar que o fluxo inteiro funciona na máquina de demo, offline, e que todos os testes críticos passam.
5. **Pré-requisitos:** F04–F07 (e F06 em algum modo).
6. **Tarefas:** rodar o pytest completo · executar o checklist manual T-12 · teste offline (Wi-Fi desligado) · teste com LLM desligado · revisão científica de cada texto da UI (busca por "validado", "prevê", "seguro", "NASA aprova") · gravar o vídeo de fallback da demo · congelar `dataset_version` e a tag git `demo-v1`.
9. **Testes:** todos os T-xx MUST. Matriz em [05](05_QUALITY_AND_VALIDATION_PLAN.md).
10. **Aceite:** 100 % dos testes MUST em PASS registrados em `docs/evidence/test_run_<data>.md`; demo de ≤3 min executada 2× seguidas sem intervenção de dev; vídeo gravado.
13. **Plano B:** se algum MUST falhar, remover a funcionalidade da trilha da demo e rebaixar o status na matriz do pitch. Não se "conserta ao vivo".
15. **Pitch:** a lista de entregas comprovadas para a pergunta da banca "O que o time fez no evento?".

---

#### F10 — Entrega e pitch (contínua)
1. F10 · 4. **MUST**
3. **Objetivo:** fazer com que submissão, README, slides e roteiro reflitam exatamente a tag `demo-v1`.
6. **Tarefas:** README final (instalação, execução, escopo, limitações, dados, créditos, independência da NASA) · `docs/evidence/` com prints e logs · atualizar [06](06_PITCH_ALIGNMENT_MATRIX.md) em cada gate · trocar placeholders por prints reais · revisão cruzada roteiro × produto antes do pre-pitch e antes da submissão · confirmar horário e link de submissão (DIV-09).
10. **Aceite:** cada frase do roteiro em tempo presente corresponde a uma linha `IMPLEMENTADO_E_TESTADO` na matriz, e cada imagem de slide tem rótulo de natureza.
15. **Pitch:** é o próprio pitch.

---

## Parte 6 — Backlog e critérios de aceite
Ver [03_DEVELOPMENT_BACKLOG.md](03_DEVELOPMENT_BACKLOG.md): BL-01…BL-11 decompostos em subtarefas BL-xx.yy, com dependências, papel, teste e aceite.

## Parte 7 — Cronograma integrado ao pitch
Ver [08_HACKATHON_EXECUTION_PLAN.md](08_HACKATHON_EXECUTION_PLAN.md) e [06_PITCH_ALIGNMENT_MATRIX.md](06_PITCH_ALIGNMENT_MATRIX.md).

## Parte 8 — Riscos, bloqueios e decisões
Ver [07_RISKS_AND_DECISIONS.md](07_RISKS_AND_DECISIONS.md).

## Parte 9 — Primeira fase recomendada: F00 (+ início de F01 e F02a)

**Escopo exato autorizável agora:**
0. **Auditoria do ambiente (F00.A / BL-01.07):** gerar `docs/environment_audit.md` com cada dependência marcada `VERIFIED`/`NOT_VERIFIED`/`ABSENT` e o comando + saída. Os itens abaixo dependem dela (ex.: instalar PyMuPDF/FastAPI só depois de confirmado que estão ausentes).
1. `git init` na pasta `FlameLab/`. O DOCX permanece onde está, e `planning/` passa a ser versionado.
2. Estrutura de pastas: `backend/`, `frontend/`, `data/`, `sources/`, `scripts/`, `docs/`, `fds/`, `planning/`.
3. Backend: venv, `requirements.txt` com versões fixadas, `app/main.py` com `GET /api/health` → `{status, dataset_version: null, llm: "unconfigured"|"configured", independence_notice}`, e servindo `frontend/dist` em `/`.
4. Frontend: Vite React-TS, uma página placeholder que chama `/api/health` e mostra o aviso de independência.
5. `sources/`: baixar o PDF de NASA/TM-20210011385 (via NTRS), calcular o sha256 com `scripts/hash_sources.py` e registrar em `data/documents.json`, com `retrieved_at` e URL. Decidir se o PDF entra no git (recomendação: sim, se ≤ ~20 MB e redistribuível; caso contrário, fica só local + hash).
6. (incluído no item 0) A versão do FDS é verificada a partir de um "CMD with FDS" / `fdsinit.bat`. Se não responder, o FDS fica `NOT_VERIFIED`, e a F08 fica restrita à parte documental.
7. README v0: o que é, como rodar, escopo MUST, aviso "projeto independente, não endossado pela NASA".
8. Se o protótipo de extração for localizado: copiar para `scripts/legacy_extractor/` sem integrar, com uma nota de origem.

**Pré-requisitos:** D-08 (onde fica o repositório/remote); internet.
**Fora do escopo da F00:** modelos Pydantic completos (F02a), transcrição (F01), qualquer UI real.

**Testes de aceite da F00:**
| Teste | Procedimento | PASS se |
|---|---|---|
| T-00a | Em terminal novo: criar venv, `pip install -r backend/requirements.txt`, `npm ci` em `frontend/` | sem erro |
| T-00b | `uvicorn app.main:app` e `GET /api/health` | HTTP 200 com os 4 campos |
| T-00c | `npm run build` e abrir `http://localhost:<porta>/` servido pelo FastAPI | placeholder com aviso de independência visível |
| T-00d | `python scripts/hash_sources.py --verify` | sha256 recomputado = valor em `documents.json` |
| T-00e | Outra pessoa segue só o README | consegue o T-00c em ≤10 min |
| T-00f | Abrir `docs/environment_audit.md` | todo item tem estado + comando + saída; FDS e protótipo não aparecem como `VERIFIED` sem saída correspondente |

**Saída para o pitch após F00:** nada novo em tempo presente, exceto a verificação documentada da versão do FDS.

## Parte 10 — Artefatos
Os oito arquivos desta pasta `planning/`. A fonte de verdade de status é [06_PITCH_ALIGNMENT_MATRIX.md](06_PITCH_ALIGNMENT_MATRIX.md), atualizada a cada gate.

---

## Padrão de execução por fase (após aprovação)
Para cada fase: revisar requisitos → inspecionar arquivos → definir alterações → implementar só o escopo autorizado → executar testes → checar regressões → registrar resultados em `docs/evidence/` → atualizar [06](06_PITCH_ALIGNMENT_MATRIX.md) → informar o impacto no pitch → recomendar a próxima fase. Nenhum PASS sem execução; nenhum "integrado" com mock.
