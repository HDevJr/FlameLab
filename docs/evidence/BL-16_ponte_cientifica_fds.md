# BL-16 — Ponte científica FDS

## Estado e preservação

Branch `feat/arq-v2-nasa-fds-prototipo`, HEAD `894f939f233e14b89a99d55050bc5fcc49da7612`. A árvore recebida já continha v2.2 e BL-15 sem commit, inclusive revisões humanas BASS-II e novos módulos de integridade. A implementação preservou essas alterações, sem reset, clean, checkout, commit, push ou merge.

Backup local anterior às edições: `tmp/bl16-before.zip` (alterações Git e JSONs locais). Conferência posterior dos 16 arquivos científicos/históricos presentes nesse backup: conteúdo idêntico. Nenhum registro de parâmetro, lacuna ou aprovação científica anterior foi modificado. Não houve processamento de PDF nem chamada Gemini.

Foram consultados os contratos e planos em `planning/`, as evidências/snapshot BL-15 e os módulos de catálogo, revisão, compatibilidade, geração e execução. A referência a um worker separado corresponde, nesta arquitetura, à thread de fila em `SimulationService`; foi reutilizada. A alteração de experimento existente está em `Scenario.tsx`.

## Arquitetura entregue

`Catálogo → resolução científica → perfil versionado → condições/hipóteses → revisão independente → validação → gerador existente → fila existente → FDS → Smokeview → FFmpeg → resultados existentes`.

- **Resolver:** utiliza parâmetros/evidências atuais do catálogo. Separa condições publicadas revisadas, entradas ambíguas e observáveis. Exige natureza observada, evidência, valor, revisão com interpretação e ausência de bloqueios. Não gera FDS nem considera revisão do número como aprovação do modelo.
- **Perfis:** extensão do registro existente, com versão, hash, aprovação técnica, requisitos, unidades, limites, superfícies, reação, saídas e limitações. O perfil técnico usa `fds-integration-simple-fire@1.0.0`. O perfil PMMA permanece sem aprovação/gerador físico.
- **Hipóteses:** contratos Pydantic estritos; origem, fonte, valor/unidade, justificativa, autor, data, versão, campo/variante e limitações. Os cinco tipos de origem são representados. No caso independente, entradas fornecidas pelo cliente aceitam apenas engenharia/literatura externa; `SOFTWARE_DEFAULT` é criado pelo servidor, nunca aceito como alegação arbitrária do cliente. Condições NASA não são transferidas ao caso independente.
- **Versionamento:** cada configuração é imutável; editar cria versão nova. Revisão independente identifica a versão e seu hash. Defaults não são aceitos silenciosamente. Autoria e revisão são declaradas, como na infraestrutura existente; não há autenticação de identidade nesta entrega.
- **Gerador:** reutiliza o template controlado. Valores passam por conversão dimensional, faixas e validação; razão `kg/kg` é tratada localmente como adimensional. Observáveis e parâmetros fora da lista são recusados. O mesmo perfil e os mesmos valores produzem FDS e SHA iguais, inclusive entre casos diferentes. Metadados de data/autoria não alteram o texto numérico.
- **Orquestração:** aceita caso versionado no endpoint de simulações existente. Revalida na submissão e antes de executar. Alteração de perfil, conteúdo ou revisão invalida a execução. O manifesto segue como artefato controlado, disponível também quando uma execução falha depois da preparação. Não foi criado outro worker.

Manifesto: caso/versão, perfil/hash/versão, dados de entrada, fonte e origem das hipóteses, revisão, constantes/defaults do template, SHA do FDS, limitações e contrato de comparação. A execução registra versões dos executáveis, tempos, estados, logs e artefatos pelo mecanismo existente.

Os estados de preparação estão separados dos estados detalhados do worker. `EXPLORATORY_READY` indica configuração técnica preparada, ainda sujeita a revisão/disponibilidade; apenas `EXECUTION_READY` habilita submissão. `reproduction_ready` permanece falso. O diagnóstico M1 informa `MODEL_NOT_APPROVED` e separadamente `MISSING_INPUTS`, sem esconder nenhum desses bloqueios.

## Modelagem e limites

### Caso independente

Combustão prescrita de propano em compartimento. Não prevê propagação em PMMA nem representa gravidade, geometria ou contornos do BASS-II.

Fonte local conferida: `C:/Program Files/firemodels/FDS6/Examples/Fires/simple_test.fds`.

SHA-256: `e64834c1f96f3e4cf26f9a05d2bdcff7a5cd01c7ee92e768240c67c91d3505ba`.

Conserva geometria de 3,6 × 2,4 × 2,4 m, malha 36 × 24 × 24, queimador de 0,16 m², reação de propano e abertura controlada. O FlameLab acrescenta dispositivos fixos de temperatura, CHID determinístico e saídas temporais controladas. O exemplo original tem T_END=60 s; o perfil BL-16 restringe a 5–30 s, com default 5 s, explicitamente uma escolha numérica do perfil.

| Entrada | Default | Domínio |
|---|---|---|
| HRRPUA | 1000 kW/m² | 250–2000 kW/m² |
| Rendimento de fuligem | 0,01 kg/kg | 0–0,1 kg/kg |
| Tempo simulado | 5 s | 5–30 s |

Limites: 20.736 células fixas, quatro threads, até 300 quadros configurados e teto de 900 s por execução. Não é apresentada estimativa de custo sem medição. Reutilizam-se diretório isolado, executáveis fixos, ambiente reduzido, ausência de shell e entrega apenas de artefatos cadastrados. O perfil é para a instalação local, em processo único; não introduz autenticação ou isolamento por contêiner.

Gravidade e ambiente padrão do FDS estão identificados como defaults do caso independente, sem equivalência às condições NASA. Os limites de perfis/cenários antigos permanecem preservados; o novo domínio reduzido se aplica à ponte BL-16.

### BASS-II M1

Os nove parâmetros vêm exclusivamente do dataset existente. Os três observáveis permanecem referências, sem alimentar o gerador ou calibrar a saída. Os 12 registros de lacunas existentes são apresentados com categorias de construção, hipótese, fidelidade e comparação.

O alias `material_pyrolysis_properties → pmma_pyrolysis_properties` reconcilia os nomes anteriores sem criar lacuna duplicada. São impeditivos para construção do perfil físico: comprimento, duto, suporte/substrato, pressão, temperatura, perfil de entrada, ignição e propriedades termoquímicas/pirólise. Posição do anemômetro e perfil temporal do O₂ limitam fidelidade; incertezas e rastreamento da frente limitam comparação quantitativa. A classificação não apaga nem fecha lacunas.

Além disso, um perfil físico executável precisará especificar gravidade, reação/degradação térmica, revisão de material/domínio e convergência de malha. Essas exigências são requisitos do modelo, não novas lacunas publicadas. Nenhuma cinética PMMA foi inventada. Nenhum valor da simulação histórica da seção 5.5 foi importado para M1.

O perfil técnico rejeita `experiment_id`. A interface oferece navegação explícita para o caso independente, sem carregar dados M1. Para conectar M1 futuramente, será necessário implementar/aprovar o perfil físico no despacho de geração e seus requisitos; fila, executor, endpoints de execução e player permanecem reutilizáveis.

## API e experiência visual

Endpoints aditivos:

```text
GET  /api/simulation/profiles
GET  /api/experiments/{id}/simulation-preparation
POST /api/cases
GET  /api/cases/{id}?version=1
POST /api/cases/{id}/versions
POST /api/cases/{id}/review?version=1
POST /api/cases/{id}/validate?version=1
POST /api/simulations  {"case_id":"CASE-...","case_version":1}
```

O último também conserva `scenario_id` para consumidores anteriores, exigindo exatamente um alvo. Campos extras, inclusive texto FDS/caminhos, são recusados. A API declara `scientific_cases` e versão `0.5.0-scientific-cases`.

Preparação acessível em `/preparar-simulacao` e `/experimentos/{id}/preparar`, com links nas telas existentes. Quatro etapas: dados disponíveis; informações necessárias; modelo/hipóteses; executar/visualizar. Alterações são progressivas por cartão. Fontes/defaults, autoria, unidades e limitações estão visíveis; revisão e prontidão determinam o botão.

Caso/versão são preservados na URL. A preparação recupera hipóteses salvas e oferece links para execuções anteriores desse caso/versão. Execução, retomada, resultados e vídeo utilizam as páginas existentes. Resultados exibem: **“Comparação quantitativa não disponível para este perfil.”** Nenhuma série FDS é equiparada à propagação M1.

## Arquivos BL-16

Novos: `backend/app/simulation/bridge.py`, `backend/app/api/cases.py`, `backend/tests/test_bridge.py`, `frontend/src/pages/Prepare.tsx`, `frontend/src/prepare.test.tsx`, `scripts/run_bridge_smoke.py` e este relatório.

Estendidos: contratos/serviço de simulação, API `platform.py`, registro de versão/main, cliente/tipos frontend, capacidades frontend, rotas e páginas Review/DemoFds/Result. O teste anterior que esperava ignorar conteúdo FDS extra agora exige rejeição explícita 422.

## Validação e pendências

| Verificação | Resultado |
|---|---|
| Ponte: resolução M1, separação original, origem, conversão, limites, perfil/versão, revisão independente, hash, determinismo, revalidação na fila | PASS — 18 testes |
| Regressão backend | PASS — 355 testes; dois cenários condicionais antigos skipped |
| Preparação visual | PASS — quatro testes jsdom |
| Regressão frontend | PASS — 64 testes |
| TypeScript e build Vite | PASS |
| Execução controlada de fixture pelo worker e manifesto | PASS — FakeExecutor, sem evidência de fidelidade NASA |
| Executáveis locais FDS/Smokeview/FFmpeg | PASS — disponíveis |
| Template oficial e origem dos defaults | PASS — arquivo local e hash conferidos |
| Preservação científica/histórica e `git diff --check` | PASS |
| FDS real pela nova ponte | NOT_RUN — aguarda declaração humana de revisão dos defaults |
| Smokeview/MP4 reais pela nova ponte | NOT_RUN — dependem da execução autorizada |
| Navegador real | NOT_RUN — sem ferramenta de navegador na sessão |
| Gemini/reprocessamento de PDF | NOT_RUN — desnecessários |

**A validação real de ponta a ponta ainda não está concluída.** Foi preparada a configuração independente `CASE-166dfc63f4b8`, versão 1, de cinco segundos, em `var/cases/`. Não foi registrada aprovação em nome de uma pessoa sem sua declaração. Essa pendência decorre da política de revisão independente escolhida no planejamento, não de uma falha FDS observada. A pergunta de revisão foi apresentada ao usuário durante a implementação.

Não houve falha científica nova nem liberação de M1. As ressalvas históricas DYLCO da BL-15 continuam preservadas. Os dois skips backend são os cenários reais que pressupõem BASS-II ainda não revisado; suas alternativas e os fixtures permanecem testados.

## Executar localmente

Na raiz, PowerShell, iniciar backend:

```powershell
$env:FLAMELAB_LLM_MODE='off'
$env:FLAMELAB_NASA_MODE='fixture'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000
```

Em outro terminal:

```powershell
cd frontend
npm.cmd run dev
```

Abrir `http://localhost:5173/preparar-simulacao`. O caso já preparado pode ser consultado com `?case=CASE-166dfc63f4b8&version=1`. Conferir os defaults e limitações; registrar nome/notas e declaração de revisão independente. Só após `EXECUTION_READY`, executar e acompanhar o player existente.

Também é possível revisar pela API, sempre com identidade e declaração reais:

```powershell
$review = @{reviewer='NOME REAL DO REVISOR'; notes='DECLARAÇÃO REAL SOBRE A CONFIGURAÇÃO'; accepted_defaults=$true} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/cases/CASE-166dfc63f4b8/review?version=1' -ContentType 'application/json' -Body $review
```

Depois de revisado, parar uma eventual instância concorrente do backend e executar na raiz:

```powershell
.\.venv\Scripts\python.exe scripts/run_bridge_smoke.py --case-id CASE-166dfc63f4b8 --version 1
```

O script usa o mesmo worker, aguarda estado terminal e grava `docs/evidence/BL-16_real_RUN-*.json`; falhas retornam código não zero. Sem `--case-id`, apenas prepara um novo caso pendente, sem aprovar nem executar.

Testes:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -ra backend/tests
npm.cmd test --prefix frontend
npm.cmd run typecheck --prefix frontend
npm.cmd run build --prefix frontend
```

Próximos passos: concluir a revisão humana e o ensaio real curto, inspecionar vídeo/logs/manifesto e validar no navegador. Reprodução quantitativa do M1 exige uma etapa científica adicional de modelo físico, dados rastreáveis de material/contorno, domínio aprovado, convergência, método de comparação equivalente e incertezas; esses requisitos permanecem bloqueados nesta entrega.
