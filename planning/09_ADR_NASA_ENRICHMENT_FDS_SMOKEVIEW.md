# 09 — ADR · FlameLab — NASA Enrichment + FDS Execution + Smokeview Rendering

> 14/11/2026 · Revisa a política de FDS dos documentos 02 (§1.5, §4, §11), 03 (BL-09/BL-10) e 05 (§6) **sem apagar o histórico**: os textos anteriores continuam válidos como registro da decisão original (ADR-01) e passam a constar como “substituída por ADR-09”.
> Estado de cada componente: `IMPLEMENTADO_E_TESTADO`, `IMPLEMENTADO_NAO_VALIDADO`, `PROTOTIPO`, `BLOQUEADO`, `NAO_INICIADO`.

## 1. Contexto e decisão
A equipe redefiniu o produto: o FlameLab recebe **artigos NASA**, extrai parâmetros com IA, enriquece com fontes NASA, prepara um pacote experimental e — quando há modelo compatível — executa o FDS em infraestrutura própria, renderiza com o Smokeview e entrega um vídeo no navegador.

Princípio: **BASS-II é o primeiro exemplo; artigos NASA são o domínio do MVP; o FDS é o primeiro motor científico, não uma capacidade universal.**

### ADR-09.1 — Política de execução (substitui 02 §1.5 e §11)
| | Antes (ADR-01) | Agora (ADR-09) |
|---|---|---|
| Quem executa FDS | ninguém na aplicação; execução manual fora dela | **somente o worker isolado** do FlameLab |
| Que `.fds` pode rodar | escrito/revisado por humano | **somente** arquivos produzidos pelo `FDS Case Builder` a partir de parâmetros numéricos validados de um **modelo aprovado** |
| `POST /api/simulations` | sempre 423 | 202 para cenário executável; `BLOCKED` (com motivo) quando não há modelo/gerador/executor |
| Texto FDS do usuário ou da IA | nunca executado | **continua nunca executado**: a API não aceita FDS, caminhos, executáveis nem argumentos |

Impacto: a hipótese de “demo offline sem solver” permanece válida (o executor é opcional: sem ele, a API devolve `BLOCKED`). O requisito de que o servidor web não calcule continua: o cálculo roda em **thread de worker** que lança processos filhos.

## 2. Arquitetura

```
React/Vite ──► FastAPI ──► Catalog ◄── DatasetStore (data/, curado, invariantes I-1..I-10)
                │  │                       ▲
                │  ├─ /imports ─► Ingest ──┘ (var/imports) ──► PDF (hash, texto) ─► Gemini (propõe) ─► verificador literal
                │  ├─ /documents/{id}/enrichment ─► nasa/ (clients · matching · enrichment · provenance)
                │  └─ /scenarios, /simulations ─► Compatibility ─► Case Builder ─► Fila ─► Worker
                │                                                                          │
                │                                       FDS ─► Smokeview (.ssf) ─► PNG ─► FFmpeg ─► MP4
                └─ /simulations/{id}/artifacts/{nome}  (só artefatos listados da execução COMPLETED)
```

| Módulo | Responsabilidade | Estado |
|---|---|---|
| `backend/app/nasa/clients` | NTRS, DataCite (registro de DOIs do PSI), TechPort; só GET/HTTPS/lista de hosts; registra cada operação | IMPLEMENTADO_E_TESTADO (fixtures) + execução online registrada |
| `nasa/matching` | similaridade de título (Jaccard), sobrenomes de autores, grafias quase iguais | IMPLEMENTADO_E_TESTADO |
| `nasa/enrichment` | descoberta por identificadores e metadados; estados de correspondência; `promoted_records = 0` | IMPLEMENTADO_E_TESTADO |
| `ingest` | upload, SHA-256, leitura de texto, identificação, procedência por comparação de hash com o NTRS, extração assistida | IMPLEMENTADO_E_TESTADO (IA simulada) + 1 execução real com Gemini |
| `catalog` | documentos e experimentos (`Test` do contrato v1 = `Experiment` da API), curados e importados | IMPLEMENTADO_E_TESTADO |
| `simulation/compatibility` | `COMPATIBLE / MISSING_PARAMETERS / UNSUPPORTED_PHYSICS / REQUIRES_REVIEW` | IMPLEMENTADO_E_TESTADO |
| `simulation/case_builder` | gerador determinístico, faixas por parâmetro | IMPLEMENTADO_E_TESTADO (só modelo de integração) |
| `simulation/service + executor` | fila, estados, limites, executor local Windows | IMPLEMENTADO_E_TESTADO (executor simulado) + 2 execuções reais |
| Modelo de **reprodução** de propagação de chama | gerador do caso | **BLOQUEADO / NAO_INICIADO** (lacunas científicas, G2/G4) |
| Frontend S01–S07 | telas navegáveis | PROTOTIPO |
| Outros motores além do FDS | — | NAO_INICIADO (`SimulationModel.engine` já é um campo) |

## 3. Modelo de entidades (reuso do contrato v1)
`Document`, `Investigation`, `Experiment` (= `Test`), `Parameter` (= `ParameterRecord`), `Evidence` já existem (04). Novos, **somente na camada de plataforma** (não alteram o contrato v1): `SourceMatch`, `EnrichmentRecord`, `SimulationModel`, `Scenario`, `SimulationRun`, `RenderedArtifact`. Documentos importados vivem em `var/` (não versionado) com o mesmo formato de parâmetro e `extraction.method = "LLM"`; **nenhum chega a `CONFERIDO_FONTE` sem revisão humana** (fluxo `scripts/review_record.py`, inalterado).

## 4. Fluxo de dados e política científica
1. **Importação:** o PDF é conteúdo não confiável. Só o texto é lido; nome de arquivo nunca vira caminho; limite de 120 MB/800 páginas; sem execução de conteúdo.
2. **Procedência NASA** (`VERIFIED / CANDIDATE / MISMATCH / PENDING`): o texto ou a aparência do PDF **nunca bastam**. `VERIFIED` exige (a) um registro NTRS correspondente e (b) **SHA-256 do arquivo idêntico ao distribuído pelo NTRS**. Sem NTRS ou sem comparação, o documento fica `PENDING`/`CANDIDATE`, “não tratado como publicação NASA validada”.
3. **Extração (Gemini propõe, o código dispõe):** cada parâmetro precisa de página e citação **literal**, e o valor precisa estar dentro da citação (normalização simétrica de espaços e hifenização de fim de linha). O que falha é descartado e listado em `extraction.rejected`. O que passa entra `EXTRAIDO_NAO_REVISADO`. Lacunas sugeridas pela IA ficam marcadas `SUGERIDA_POR_IA`.
4. **Enriquecimento (opcional):** NTRS (identificador forte ou busca por título), PSI via registro de DOI no DataCite, TechPort por busca textual. Resultado por campo com `original`, `complementar`, fonte, tipo de correspondência, divergência e `curation_decision = PENDENTE`. **Nunca substitui** o valor do artigo. Correspondência de projeto ≠ concordância de medição.
5. **Compatibilidade:** avaliada separadamente; não bloqueia análise, comparação nem exportação.
6. **Resultados observados nunca são entradas** (BASS-II M1: `flame_spread_rate` é referência de comparação).

## 5. Provedores NASA (o que foi verificado em 14/11/2026)
| Fonte | O que existe | Acesso | Uso no FlameLab |
|---|---|---|---|
| **NTRS** | API REST pública, OpenAPI em `https://ntrs.nasa.gov/api/openapi/` (UI Swagger; o documento JSON está embutido em `swagger-ui-init.js`). Operações: `GET/POST /citations/search`, `GET /citations/{id}`, `/citations/{id}/downloads[/{filename}]`, `/export*`, `/pubspace/search`, `/health`. | sem autenticação nas operações usadas; respostas JSON | metadados (título, autores, números de relatório, palavras-chave, categorias, links de download); comparação de hash do PDF |
| **PSI** | Portal Angular (`/physci/repo`). O código do portal chama um serviço interno (`/geode-py/ws/...`) **sem documentação pública**; a sondagem direta desse serviço foi **bloqueada pelo controle de segurança do agente e não foi feita**. | sem API documentada | **não consultado diretamente.** A descoberta usa o **DataCite** (API pública documentada): os DOIs `10.60555/…` têm publicador “NASA PSI” e `url` apontando para a investigação (`PSI-25`, `PSI-26`). Dados de arquivos da investigação = consulta manual ao portal. |
| **TechPort** | `GET https://techport.nasa.gov/api/specification` (OpenAPI 3, v4.5.3); `GET /api/projects/{id}`, `/api/projects/search?query=`. A especificação declara `bearerAuth` (JWT) mas **nenhuma operação o exige**; as leituras funcionaram sem token. | sem token (observado); pode mudar | busca textual por título; candidato só com semelhança ≥ 0,85. 401/403 → `SOURCE_UNAVAILABLE`. Nenhum token de sessão é guardado. |
| **DataCite** | `GET https://api.datacite.org/dois/{doi}` e `/dois?query=` | público | registro do DOI da investigação PSI; metadados e licença (CC0) |

Achados para BASS-II (execução **online** em 14/11): NTRS 20210011385 → `MATCH_CONFIRMED` (ID presente no PDF e no registro); PSI-25 → `MATCH_CANDIDATE` (título e 4 de 5 criadores em comum; **os dois registros não se citam por identificador**; PSI-26 “BASS” descartado, semelhança 0,8); TechPort → `NOT_FOUND`. **O projeto TechPort 13543 é “Spacecraft Fire Safety Demonstration” (Saffire)** — foi consultado e **não é equivalente**; nenhuma relação foi criada.

## 6. Segurança do executor
- Executáveis em lista fixa (`fds.exe`, `smokeview.exe`, `ffmpeg`), `shell=False`, ambiente mínimo, `stdin` fechado.
- Diretório por execução (`var/runs/<RUN-id>/`); nome do caso (`CHID`) gerado pelo servidor.
- Limites: 900 s no total por execução; 300 quadros; `t_end` ≤ 60 s; threads = 4. Estouro → `FAILED` com motivo, processo interrompido.
- `.fds` apenas pelo Case Builder; valores numéricos finitos dentro da faixa do modelo; a API rejeita campos desconhecidos.
- Download só de artefatos listados da execução `COMPLETED`; nomes validados.
- Reinício do servidor marca execuções interrompidas como `FAILED`.
- **Limitação:** isolamento é por processo/diretório, **não por contêiner nem por limite de memória** (Windows). CPU limitada por threads, memória não. Registrado como risco R-15.

## 7. Renderização no backend (provado)
`RENDERDIR frames` → `LOAD3DSMOKE SOOT DENSITY` + `LOAD3DSMOKE HRRPUV` → `RENDERALL 2 frame` → `EXIT`, executado com `smokeview.exe -runscript <caso>` **sem sessão interativa** (a janela OpenGL é criada e fechada pelo próprio Smokeview; foi funcional neste Windows 11 com o usuário logado — **não foi testado em servidor sem sessão gráfica/Linux/Xvfb**). `RENDERALL` **não sobrescreve** quadros existentes (por isso cada execução usa um diretório novo). Quadros `frame_0000…` são validados em sequência; sem quadros → `FAILED`. FFmpeg 9.0.2 (pacote `imageio-ffmpeg`) gera H.264/yuv420p com `+faststart`.

## 8. Contratos de API (novos)
| Rota | Função |
|---|---|
| `GET /api/documents`, `/api/documents/{id}`, `/api/documents/{id}/file` | catálogo e PDF local (caminho decidido pelo servidor) |
| `GET /api/experiments/{id}`, `/api/experiments/{id}/compatibility` | ficha e prontidão |
| `POST /api/imports` (multipart), `GET /api/imports[/{id}]` | importação com estado por etapa |
| `GET/POST /api/documents/{id}/enrichment` | relatório de enriquecimento (opcional, repetível, sempre 200 com avisos) |
| `GET /api/simulation/status`, `/api/simulation/models` | executor, versões, limites, modelos e faixas |
| `POST /api/scenarios`, `GET /api/scenarios/{id}` | cenário base ou derivado (só alterações registradas) |
| `POST /api/simulations` (202), `GET /api/simulations[/{id}]`, `GET /api/simulations/{id}/artifacts/{nome}` | fila, estado, resultados e vídeo |
Envelope: `{"data": …, "dataset_version": …}`; erros `{"error": {"code","message"}}`. Estados: `QUEUED, VALIDATING, RUNNING_FDS, PROCESSING_RESULTS, RENDERING, COMPLETED, FAILED, BLOCKED`.

## 9. Fases e critérios de conclusão
| Fase | Escopo | Estado |
|---|---|---|
| 1 Auditoria e desenho | Git, FDS/Smokeview/FFmpeg/Node, ADR | concluída |
| 2 Enriquecimento NASA | APIs, adaptadores, comparador, relatório BASS-II | concluída |
| 3 Protótipo S01–S07 | telas navegáveis integradas aos endpoints | concluída (PROTOTIPO) |
| 4 Prova FDS/Smokeview | caso de integração → quadros → MP4 → player | concluída (2 execuções reais) |
| 5 Preparação | contratos, riscos, plano de produção | este documento + `07` |
| **Produção** (fora desta entrega) | revisão humana de M1, DIV-22, modelo de reprodução, contêiner/Linux, filas, autenticação | NAO_INICIADO |

Critérios para chamar algo de **reprodução** do BASS-II M1: parâmetros relevantes `CONFERIDO_FONTE`; lacunas G1/G2 resolvidas; modelo de reprodução aprovado por CIÊNCIA; saída comparável com o observável e erro documentado (G4). **Nenhum desses critérios está satisfeito.**

## 10. Riscos novos (também em `07`)
R-15 isolamento sem contêiner/memória; R-16 Smokeview depende de contexto gráfico; R-17 TechPort pode passar a exigir token; R-18 PSI sem API documentada; R-19 vídeo de teste confundido com resultado BASS-II (mitigado por rótulos obrigatórios em API e UI); R-20 extração por IA lê só 14 páginas por artigo.
