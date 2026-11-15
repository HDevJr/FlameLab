# Continuidade da auditoria de integridade científica — 15/11/2026

O código da auditoria interrompida foi estabilizado, sem alterar o dataset ou os registros locais de revisão. A auditoria científica permanece com **3 registros conferidos com bloqueios** que exigem decisão humana. Passar na suíte não aprova esses registros.

## Estado recebido e preservação

- Branch: `feat/arq-v2-nasa-fds-prototipo`.
- HEAD: `894f939f233e14b89a99d55050bc5fcc49da7612` (documentação/evidências v2.2); referência anterior: `3b311a4`.
- `git status` foi tentado antes de qualquer alteração. O Git recusou a propriedade do diretório no usuário do sandbox; as consultas seguintes usaram `git -c safe.directory=C:/Users/junio/Projetos/FlameLab`, sem alterar a configuração global.
- Não houve checkout, reset, clean, stash, commit, push ou merge.
- Consulta de processos/portas por CIM, com a leitura fora do sandbox após recusa inicial: nenhum processo Python, Node, FDS, Smokeview ou FFmpeg ativo, nem listener nas portas 3000, 5173, 5174, 8000, 8001 ou 8080 naquele momento. Portanto, a divergência histórica entre servidores não foi reproduzida ao vivo nesta retomada.
- Antes das edições: backup de **46 arquivos**, incluindo alterações de código, dados, importações locais/PDFs e auditoria, em `tmp/audit-handoff-20261115/pre-existing-work.zip`; hashes em `manifest.json` no mesmo diretório. São arquivos locais ignorados pelo Git.
- Conferência posterior de SHA-256: **17 arquivos científicos e históricos preservados**, dentre os arquivos cobertos pelo manifesto (`data/`, importações/análises/auditoria em `var/`, log de curadoria). Nenhuma promoção, reabertura, correção de valor ou decisão de lacuna foi aplicada.

Os 22 arquivos já modificados eram:

```text
backend/app/api/platform.py
backend/app/catalog/service.py
backend/app/dataset/review.py
backend/app/ingest/extraction.py
backend/app/main.py
backend/app/review_service.py
backend/app/simulation/compatibility.py
backend/app/simulation/service.py
backend/tests/test_dataset_adapter_review.py
backend/tests/test_review_api.py
backend/tests/test_review_v22.py
data/parameters/BASS2-M1.json
docs/curation/BASS2-M1_curation_log.md
frontend/src/ReviewPanel.tsx
frontend/src/api.ts
frontend/src/components.tsx
frontend/src/lib.ts
frontend/src/main.tsx
frontend/src/pages/Review.tsx
frontend/src/styles.css
frontend/tsconfig.json
scripts/review_record.py
```

Os novos arquivos da implementação interrompida, ainda não rastreados, eram:

```text
backend/app/audit_report.py
backend/app/gap_decisions.py
backend/app/integrity.py
backend/app/readiness.py
backend/app/version.py
backend/tests/test_integrity_v23.py
frontend/src/fixtures/experiment_payload_backend_v2_1.json
frontend/src/pages/Audit.tsx
frontend/src/units_display.test.tsx
```

Documentos consultados: README, CONTRIBUTING, contrato científico (`planning/04`), plano de qualidade (`planning/05`), riscos/decisões (`planning/07`), ADR-09 e adendos v2.1/v2.2, evidências BL-14 e log de curadoria BASS-II. Não foi encontrado `AGENTS.md` aplicável na árvore consultada.

## Causas e correções

| Problema reproduzido | Causa | Correção nesta retomada |
|---|---|---|
| TypeScript `TS2741`, `UnitInfo.dimension` | Fixture do painel não acompanhava o contrato da API | Fixture completa, com `dimension: temperature` e estado `PHYSICAL`; contrato continua obrigatório |
| Testes do painel falhavam ao confirmar | A implementação passou a exigir confirmação explícita da interpretação; os testes só declaravam leitura do PDF | Testes exercitam as duas declarações e verificam que só ler o PDF mantém o botão bloqueado |
| Seletores de testes falhavam | Mudança da ficha e nomes repetidos entre rótulo amigável e técnico | Consultas pela ficha acessível e pelo nome técnico em `code` |
| Relatório sintético esperava 4 revisões e recebia 13 | Teste somava os 9 registros reais BASS-II já revisados | Dataset sintético temporário na fixture da suíte de integridade |
| Cinco testes de ingestão/jornada esperavam BASS-II não revisado | Premissa histórica fixa, invalidada pelas revisões humanas recebidas | Comparam estado de entrada/saída e exigem preservação integral pelo enriquecimento e pelas hipóteses |
| Unidade desaparecia com payload antigo | Classificação opcional não existe em servidores antigos | Fallback conserva `original.unit`; ausência de classificação é explícita. Não replica a tabela científica de unidades no frontend |
| Sem unidade virava adimensional para grandeza desconhecida | Ramo `canonical=adimensional` aceitava dimensão esperada desconhecida | Ausência sem dimensão reconhecida gera `MISSING` e atenção `UNIT_UNCLASSIFIED`; adimensional exige nome reconhecido ou declaração explícita. Grandeza física conhecida sem unidade continua bloqueada |
| Condição incorreta eliminava o bloqueio | Bastava existir um objeto `condition` | Condição estruturada deve corresponder ao valor/unidade do trecho; aceita equivalência física (20 °C = 293,15 K), recusa condição divergente ou só texto |
| Revisão antiga podia aparecer completa na interface | Ausência de `review_scope` caía no rótulo de confirmação completa | Só `FULL` exibe interpretação confirmada; bloqueios semânticos também aparecem como inconsistência |
| Versão malformada podia quebrar o aviso | Cliente confiava no JSON de `/api/version` | Validação do formato; versão indisponível/malformada gera aviso. Frontend verifica as dez capacidades usadas pela auditoria; teste cruza a lista real do frontend com a API |
| Duas versões declaradas no backend | Literal no FastAPI e constante em outro módulo | FastAPI/OpenAPI e `/api/version` usam a mesma constante `APP_VERSION` |
| Registro pendente com apenas bloqueio semântico podia receber classificação `OK` | Condicional do relatório só contava sinalizações informativas nesse ramo | Todo achado pendente é exposto como atenção; os bloqueios continuam disponíveis no relatório |

Ambiente verificado: Python 3.12.3 na `.venv`, Node v24.19.0, Vite 5.4.11. `npm.ps1` foi recusado pela política PowerShell; os comandos usaram `npm.cmd`, sem mudar a política. O esbuild dos testes e do build precisou de execução fora do sandbox por acesso negado ao diretório ancestral. Não foram instaladas dependências.

## Evidência e diagnóstico científico

Snapshot estruturado: [BL-15_integrity_snapshot_2026-11-15.json](BL-15_integrity_snapshot_2026-11-15.json). Contém registros, citações, páginas, achados, propostas, relações de lacunas, versões e hashes das fontes. Gerado pela API atual via FastAPI TestClient, com arquivos locais e sem provedores externos.

- **23 registros `CONFERIDO_FONTE`**: 9 BASS-II e 14 DYLCO.
- Classificações exclusivas: **3 `INCONSISTENT_CONFIRMED`, 11 `LEGACY_REVIEW`, 9 `OK`**.
- Os **14 DYLCO** não têm confirmação explícita da interpretação; esse conjunto inclui os 3 inconsistentes.
- Os **9 BASS-II** têm eventos de aprovação com `interpretation_confirmed=true`; valores, estados e revisões foram preservados. `OK` significa ausência de achado pelas regras atuais, não nova aprovação científica.
- Trilha local: 66 eventos, sendo 43 recusas e 23 aprovações; o snapshot registra o SHA-256 da trilha.
- PDFs locais BASS-II e DYLCO: SHA-256 **MATCH** com os hashes esperados, listados integralmente no snapshot. Isso verifica identidade do arquivo local, sem nova consulta de procedência NASA.

| Registro DYLCO | Evidência local | Diagnóstico e encaminhamento humano |
|---|---|---|
| `initial_temperature = 20 °C` | PDF p. 5 / impressa 3: ciclo de 20 a 80 °C, em incrementos de 20 °C | O número aparece, mas o trecho citado não basta para afirmar condição inicial. Revisar o significado, mantendo a distinção entre temperatura absoluta e incremento |
| `equilibrium_contact_angle = 70 deg` | PDF p. 15 / impressa 13: 70° a 20 °C e 65° a 100 °C | Falta a condição de referência no registro. Registrar o par correto e submeter a revisão independente |
| `contact_angle_accuracy = 2 deg` | PDF p. 15: camada de texto contém `+2*`; a página foi também rasterizada e inspecionada | Símbolo corrompido no texto. O raster mostra a notação angular junto de ±2°, mas isso não constitui confirmação humana; exige a declaração explícita de unidade vista no PDF |
| `test_fluid_code = 50350.0` | PDF p. 5 menciona o código 50350 | Identificador numérico pode perder formato/zeros; deve ser tratado como identificador na revisão, sem interpretar como medição |
| `fluid = Cargille fluid 30350` | Tabela 1, PDF p. 15: 30350; corpo, PDF p. 5: 50350 | Divergência já presente na fonte, confirmada na camada de texto e no raster da tabela. Não escolher automaticamente um código; registrar ressalva e resolver por curadoria |
| `surface_modifier = FC-724` | Evento aprovado submeteu unidade `deg` | Regra antiga ignorava unidade para texto; a aprovação não valida essa unidade. Comparação atual recusa unidade física anexada a valor textual |
| `cell_material` e `fluid` | Eventos aprovaram apenas `quartz` e `30350`, respectivamente | Comparação antiga aceitava fragmentos de texto. O relatório expõe `PARTIAL_TEXT_CONFIRMATION`; reconferir o texto completo |
| `temperature = 40 degC` | Legenda da Figura 3, PDF p. 18: sequência 40, 60, 80, 90 e 95 °C | Valor de uma lista de aquecimento, não temperatura única de todo o experimento; preservar o contexto |
| `dihedral_angle = 65 deg` | Legenda da Figura 3(a), PDF p. 18 / impressa 16: 2α = 65° à esquerda e 60° à direita | Valor com escopo geométrico específico. A lacuna `cell_dihedral_angle` pode estar parcialmente coberta, mas 65° não cobre automaticamente todas as células nem deve ser confundido com α |
| `solid_material = fused silica` | Citação selecionada no título da Tabela 1 menciona líquido com índice de refração casado com sílica | Reavaliar o papel atribuído a esse texto. A fabricação das células em sílica está no corpo da p. 5; o título da tabela isolado tem outro contexto |

No dataset atual, `equilibrium_contact_angle` está em `deg`, **não em °C**. Há tentativa histórica recusada com `70 °C`; o teste de dimensão incompatível cobre a regressão ângulo × temperatura. Não foi reconstruída uma extração original diferente sem artefato que a comprove.

Os rasters e textos locais usados na inspeção estão em `tmp/audit-handoff-20261115/dylco-page-{5,15,18}.*` (rasters apenas de 15 e 18). A verificação é diagnóstico assistido; não substitui o revisor da equipe.

## Política para os achados

1. Relatório, classificação e proposta são derivados em leitura; não alteram `status`, valor, unidade, condição ou lacuna.
2. Para importados: uma pessoa identifica a evidência, registra motivo e usa `REOPEN` ou `CORRECT`. Correção preserva a extração original e reabre a conferência existente. Outra pessoa, independente de quem extraiu/corrigiu, confirma valor, unidade, página e interpretação; condições são comparadas ao trecho.
3. Registros curados continuam com alteração pela curadoria dos arquivos, conforme contrato, com evidência/log e revisão independente. A interface recusa correção/reabertura de curados.
4. Unidade fora da tabela bloqueia confirmação automática. Símbolo ilegível exige verificação explícita no PDF; unidade ausente não é inventada.
5. Lacuna sobreposta requer decisão humana `COVERED`, `PARTIAL` ou `DISTINCT`, com responsável, motivo e vínculo ao parâmetro. Identidade lexical/grandeza não prova identidade de escopo. Nenhuma decisão foi registrada nesta sessão.
6. Revisão legada é preservada como histórica; não recebe interpretação confirmada por inferência. As cinco dimensões da prontidão distinguem integridade, revisão, cobertura, compatibilidade FDS e execução. Não há liberação automática de simulação por contagem de aprovações.

## Validação

| Verificação | Resultado |
|---|---|
| Backend direcionado: integridade v2.3, revisão v2.2/API e adaptador | **PASS — 154 testes** |
| Backend direcionado: ingestão e jornada após corrigir premissas históricas | **PASS — 48 testes** |
| Frontend direcionado: unidades, versões e painel de revisão | **PASS — 34 testes** |
| `npm.cmd run typecheck` | **PASS** |
| `npm.cmd run build` (TypeScript + Vite) | **PASS** |
| Regressão completa backend, `pytest -q -ra backend/tests` | **PASS — 337 passaram, 2 skipped** |
| Regressão completa frontend, `npm.cmd test` | **PASS — 60 testes, 5 arquivos** |
| API atual: versão = OpenAPI, metadados de integridade/unidade/escopo em todos os parâmetros, relatório somente leitura | **PASS — TestClient** |
| Hash dos 2 PDFs e preservação dos 17 arquivos científicos/históricos do manifesto | **PASS** |
| `git diff --check` | **PASS** |
| Integridade científica dos 3 registros DYLCO identificados | **FAIL — achados preservados; requer revisão humana** |
| Dois cenários da suíte real que pressupõem BASS-II ainda pendente | **NOT_RUN / skipped — BASS-II já conferido; caminho revisado e fixtures sintéticos cobertos** |
| Navegador real / validação visual S01–S07 | **NOT_RUN** |
| Gemini real, rede NASA, FDS, Smokeview e FFmpeg reais | **NOT_RUN — desnecessários nesta auditoria** |

As falhas iniciais estão registradas nos logs locais do backup: TS2741; 1 falha em 149 testes direcionados backend; 8 falhas em 22 testes frontend; depois, 5 falhas em 339 testes backend na primeira regressão completa. São distintas dos três achados científicos ainda existentes. Avisos de migração futura do React Router não impediram os testes.

Reprodução (na raiz, PowerShell):

```powershell
$env:FLAMELAB_LLM_MODE = 'off'
$env:FLAMELAB_NASA_MODE = 'fixture'
.\.venv\Scripts\python.exe -m pytest -q -ra backend/tests
npm.cmd test --prefix frontend
npm.cmd run typecheck --prefix frontend
npm.cmd run build --prefix frontend
```

Para consultar o diagnóstico atual, iniciar o backend local com esses modos e ler `GET /api/version` e `GET /api/audit/integrity`. A interface `/auditoria` usa esse relatório. Os testes usam área `var/` temporária, transportes/provedores simulados e executor simulado. Nenhuma chamada Gemini ou execução FDS real foi feita.

Pendências: decisões humanas sobre os três bloqueios DYLCO; revisão do contexto dos demais registros legados, dos códigos divergentes e do ângulo diedral; eventual segunda revisão do BASS-II conforme o plano de curadoria; teste visual no navegador. Os documentos históricos que descrevem BASS-II como inteiramente pendente refletem o estado anterior às aprovações preservadas nesta retomada; o estado efetivo está nos dados, na trilha e no snapshot acima.
