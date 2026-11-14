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

- Este pacote F00 adiciona um **esqueleto** com endpoint de saúde (`/api/health`) e teste básico. Não implementa dados NASA, busca, IA nem integração com FDS.
- Teste simples do FDS/Smokeview aconteceu em **outro computador**; a máquina atual ainda precisa de auditoria.
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

## Modos de IA previstos

- `off` — padrão local, nenhum serviço externo; recursos de IA não disponíveis.
- `live` — integração futura com provedor escolhido pela equipe (preferência inicial a investigar: API Gemini em modalidade gratuita elegível).
- `cache` — respostas já geradas e verificadas, **claramente identificadas como cache**, para apresentação sem rede.

Nenhuma dessas integrações de IA está implementada por este pacote. Nunca adicione chaves ao Git. Use `.env` local (ignorado) ou secrets do ambiente.

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
