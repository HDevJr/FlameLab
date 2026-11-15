# FlameLab — NASA Space Apps Challenge 2026

**Status:** planejamento e preparação (F00). **Não há reprodução científica validada de experimentos NASA neste repositório.**

## O que é

FlameLab é um painel de investigação de combustão em microgravidade. O MVP deverá permitir localizar e compreender experimentos reais, consultar parâmetros com origem verificável, comparar ensaios e receber interpretações assistidas por IA **fundamentadas em evidências**. A simulação física usando FDS/Smokeview é uma trilha experimental separada e não bloqueia o MVP.

Desafio: [Flame in Freefall — NASA Space Apps 2026](https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/).

## Documentação oficial do projeto

- [Plano de implementação](planning/01_IMPLEMENTATION_PLAN.md)
- [Arquitetura técnica](planning/02_TECHNICAL_ARCHITECTURE.md)
- [Backlog](planning/03_DEVELOPMENT_BACKLOG.md)
- [Contrato de dados científicos](planning/04_SCIENTIFIC_DATA_CONTRACT.md)
- [Qualidade e validação](planning/05_QUALITY_AND_VALIDATION_PLAN.md)
- [Alinhamento do pitch](planning/06_PITCH_ALIGNMENT_MATRIX.md)
- [Riscos e decisões](planning/07_RISKS_AND_DECISIONS.md)
- [Plano do hackathon](planning/08_HACKATHON_EXECUTION_PLAN.md)

> O documento mestre `.docx` na raiz é a visão do produto. O conteúdo de `planning/` é o plano de execução. Divergências e decisões precisam ser registradas, não resolvidas silenciosamente.

## Estado verificado

- F00: **esqueleto** com endpoint de saúde (`/api/health`) e teste básico.
- BL-05 (assistente de IA, só backend): `POST /api/ask` com adaptador Gemini, verificador determinístico V1–V8, abstenção e modos `live`/`cache`/`off`. **Testado com evidência sintética** (66 testes com provedor simulado + smoke test real do Gemini). Detalhes em [docs/evidence/BL-05_assistente_ia.md](docs/evidence/BL-05_assistente_ia.md).
- BL-02 (dataset científico): `data/` contém o ensaio **BASS-II M1** (9 registros, 11 evidências, 12 lacunas), validado pelo `DatasetStore` (invariantes I-1–I-10). O hash do PDF-fonte confere. **Os 9 registros estão `EXTRAIDO_NAO_REVISADO`: aguardam revisão humana.** Até lá, o assistente informa que o dado "consta na fonte e aguarda revisão" (`PENDING_REVIEW`) e não cita o valor. Detalhes em [docs/evidence/BL-02_dataset_cientifico.md](docs/evidence/BL-02_dataset_cientifico.md) e [docs/curation/BASS2-M1_curation_report.md](docs/curation/BASS2-M1_curation_report.md).
- **Plataforma v2 (ADR-09, protótipo):** importação de artigos NASA em PDF (hash e procedência por comparação com o NTRS), extração assistida por IA com citação literal, enriquecimento NASA (NTRS, PSI via DataCite, TechPort), catálogo genérico, compatibilidade com o FDS, cenários derivados e worker FDS → Smokeview → MP4. Evidências em [docs/evidence/BL-12_plataforma_v2.md](docs/evidence/BL-12_plataforma_v2.md); decisões em [planning/09](planning/09_ADR_NASA_ENRICHMENT_FDS_SMOKEVIEW.md).
- **FDS/Smokeview/FFmpeg: verificados nesta máquina** (FDS 6.11.1, Smokeview 6.11.2, FFmpeg 9.0.2), com um **caso de integração** genérico. **Não há reprodução do BASS-II M1**: depende de revisão humana, lacunas científicas e modelo aprovado.
- **Jornada v2.1 (ADR-09 §11):** importação com etapas legíveis e tempos medidos, leitura do PDF em lotes com **cobertura de páginas** explícita, resumo consolidado (origem NASA ≠ números conferidos), **revisão humana pela interface** (mesma política do script), separação **Experimentos NASA / Demonstração FDS**, hipóteses sobre condições do experimento, vídeo em tempo real (1×) com player completo. Evidências: [docs/evidence/BL-13_jornada_v2_1.md](docs/evidence/BL-13_jornada_v2_1.md).
- Frontend: protótipo navegável (React + TypeScript + Vite) em `frontend/`. **Validação visual: NOT_RUN** — roteiro em [docs/manual_test_roteiro_S01-S07.md](docs/manual_test_roteiro_S01-S07.md); compila, tipa e passa nos testes de componentes (jsdom).
- Busca textual/ranking e comparação lado a lado continuam não implementados.
- Valores BASS-II/M1 citados no planejamento **não são apresentados como conferidos na fonte primária** até dupla revisão do PDF original.

## Executar localmente (Windows / PowerShell)

Requisitos: Python 3.12+, Git. Para F00, Node não é necessário.

```powershell
git clone https://github.com/HDevJr/FlameLab.git
cd FlameLab
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Em outro terminal, dentro da raiz:

```powershell
.\.venv\Scripts\python.exe -m pytest -q backend/tests
```

Verificação: abrir <http://127.0.0.1:8000/api/health>; resposta esperada `{"status":"ok","stage":"F00"}`. Isso atesta apenas a API mínima, não as integrações científicas.

### Frontend (protótipo v2)
```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxy de /api para 127.0.0.1:8000)
npm run typecheck; npm test; npm run build
```
Variáveis úteis do backend: `FLAMELAB_NASA_MODE=online|fixture` (padrão `online`; `fixture` usa respostas gravadas, sem rede) e `FLAMELAB_VAR_DIR` (área de trabalho local; padrão `var/`, não versionada). O executor FDS usa `C:/Program Files/firemodels`; se ausente, simulações ficam `BLOCKED` com o motivo. Importações usam o Gemini quando `FLAMELAB_LLM_MODE=live` (um PDF = uma chamada real **por lote de páginas**; `FLAMELAB_EXTRACT_MAX_BATCHES`, padrão 8).

## Assistente científico (IA)

### Variáveis de ambiente (`.env` na raiz, nunca versionado)

| Variável | Padrão | Uso |
|---|---|---|
| `FLAMELAB_LLM_MODE` | `off` | `live`, `cache` ou `off` |
| `FLAMELAB_LLM_PROVIDER` | `none` | `gemini` (único implementado) |
| `FLAMELAB_LLM_MODEL` | — | ex.: `gemini-3.5-flash-lite` (modelo testado pela equipe) |
| `GEMINI_API_KEY` | — | só no `.env` local; nunca é registrada, impressa ou devolvida |
| `FLAMELAB_LLM_TIMEOUT_S` | `20` | timeout por chamada |
| `FLAMELAB_LLM_MAX_ATTEMPTS` | `2` | 1–3; retry só para 5xx/timeout, com espera progressiva |
| `FLAMELAB_LLM_TOTAL_BUDGET_S` | `45` | limite total de tempo, somando as tentativas |
| `FLAMELAB_AI_CACHE_DIR` | `data/ai_cache` | diretório do cache de respostas |
| `FLAMELAB_AI_CACHE_WRITE` | `true` | grava respostas LIVE no cache |

O `.env` é lido **pelo caminho explícito da raiz do repositório**, o que funciona tanto em `uvicorn` quanto em `python scripts\...`. Variáveis do ambiente têm precedência sobre o `.env`. Sem chave, os modos `off` e `cache` funcionam normalmente.

### Modos
- `off`: nenhuma chamada à IA. `/api/ask` responde `mode=UNAVAILABLE` (`MODE_OFF`) com as evidências recuperadas.
- `cache`: serve respostas geradas antes pela IA, **reverificadas** contra o dataset atual e rotuladas `mode=CACHE`. `created_at` mostra quando foram geradas. Sem entrada no cache → `UNAVAILABLE` (`CACHE_MISS`). Nunca chama o provedor.
- `live`: chama o Gemini, e toda resposta passa pelo verificador antes de ser publicada como `mode=LIVE`. Se o provedor falhar (timeout, 503, cota, autenticação), usa o cache como fallback (`mode=CACHE` com `provider_error`); se não houver cache, responde `UNAVAILABLE`. Nenhum outro provedor é acionado.
- Sem evidência elegível, a abstenção é decidida em código, sem chamar a IA: `mode=DETERMINISTIC`.

### Endpoint
`POST /api/ask` com `{"question": "...", "scope": {"investigation_id": "PSI-25", "test_uids": ["BASS2-M1"]}, "lang": "pt"}`.
Responde `{"data": AIAnswer, "dataset_version": ..., "warnings": [...]}` (contrato em `planning/04 §3.9`). Abstenção e indisponibilidade são **estados com HTTP 200**; entrada inválida devolve **422** `{"error": {...}}`.

### Testes
```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q backend/tests          # sem rede; provedor simulado
.\.venv\Scripts\python.exe scripts\smoke_gemini.py             # REAL, explícito; usa evidência sintética
```
O smoke test grava o relatório em `docs/evidence/smoke_gemini_<UTC>.json`, sem credenciais. Sem chave, o resultado é `NOT_RUN`. Ele **não valida** conteúdo BASS-II.

### Limitações atuais
- O dataset tem só o ensaio M1, ainda sem revisão humana: o assistente não afirma valores experimentais da NASA (ver "Dataset científico" abaixo).
- Números só são aceitos quando vêm de fichas de registros `CONFERIDO_FONTE`. Trechos de documento sustentam apenas afirmações qualitativas.
- O verificador não detecta números por extenso. Paráfrases causais e extrapolações fora da lista (Marte, Lua, gravidade parcial e outros corpos celestes) podem escapar das regras V6/V8.
- O prompt v1 ainda não teve revisão científica. O golden set real depende da curadoria.

## Dataset científico (BL-02)

- Layout: `data/documents.json`, `data/investigations.json`, `data/tests/`, `data/parameters/`, `data/evidence/`, `data/gaps/`, cada um no envelope `{"contract_version": "1.0", "items": [...]}` (contrato em `planning/04`). Na inicialização, o servidor valida tudo e **não sobe** se o dataset for inválido.
- O PDF-fonte fica em `sources/NASA-TM-20210011385.pdf` e **não é versionado**. Baixe-o em <https://ntrs.nasa.gov/citations/20210011385> e confira:
  ```powershell
  .\.venv\Scripts\python.exe scripts\verify_sources.py        # SHA-256 → MATCH esperado
  .\.venv\Scripts\python.exe scripts\crosscheck_table51.py    # curadoria × texto do PDF (automático)
  ```
- **Revisão humana** (somente pessoa da equipe, diferente de quem extraiu): `scripts\review_record.py`. Ela exige o valor, a unidade e a página lidos no PDF e recusa qualquer divergência. Passo a passo em [docs/curation/BASS2-M1_curation_report.md](docs/curation/BASS2-M1_curation_report.md).
- Registros não conferidos chegam ao assistente como **valor retido**: o modelo sabe que o dado existe e onde está, mas não recebe o número.
- Smoke real sobre o dataset real (explícito): `.\.venv\Scripts\python.exe scripts\smoke_gemini_real_dataset.py`.

## Organização e colaboração

- `planning/` — escopo e critérios de aceite; **não sobrescrever** sem revisão.
- `docs/` — decisões, auditoria e evidências.
- `sources/` — documentos científicos locais; PDFs grandes/externos não são adicionados por padrão ao Git.
- `data/` — dados estruturados versionados, quando validados.
- `backend/` — API e testes.
- `frontend/` — reservado à experiência visual do MVP.
- `scripts/` — tarefas de preparação/validação.
- `fds/` — trilha experimental isolada; não execute entradas arbitrárias por rota web.

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para branches, PRs, segurança e atualização do pitch.

## Fonte científica inicial

NASA/TM-20210011385 — [BASS-II Summary Report](https://ntrs.nasa.gov/citations/20210011385). A conferência na fonte primária é necessária antes de marcar parâmetros como revisados.

O FlameLab não é produto oficial, homologado ou endossado pela NASA ou pelo NIST.
