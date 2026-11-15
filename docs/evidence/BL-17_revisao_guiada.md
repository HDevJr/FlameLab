# BL-17 — Jornada de revisão guiada e resolução de pendências

## Preservação e escopo

Implementação sobre `feat/arq-v2-nasa-fds-prototipo`, HEAD inicial `894f939f233e14b89a99d55050bc5fcc49da7612`. A árvore recebida continha BL-15 e BL-16 sem commit. Antes das edições, os arquivos modificados/não rastreados e os dados locais foram preservados em `tmp/bl17-before.zip` (482 caminhos); `tmp/bl17-scientific-before.json` registra os hashes de 434 arquivos em `data/`, `var/`, `sources/` e `docs/curation/`.

A conferência posterior encontrou **zero alterações nesses 434 arquivos**. Os nove parâmetros conferidos do M1, as evidências NASA, as 12 lacunas originais e o histórico anterior permanecem intactos. As alterações de código anteriores foram mantidas e estendidas. Não houve reset, clean, troca de branch, commit, push ou merge. O Git exigiu exceção de propriedade; foi usado `git -c safe.directory=...`, sem alterar configuração global.

Foram inspecionados catálogo, importação, análise, revisão, relações entre lacunas/parâmetros, cinco dimensões de prontidão, registro de perfis, ponte de hipóteses/casos BL-16, execução, testes e contratos científicos/ADR-09.

## Problemas e navegação entregue

O diagnóstico anterior distribuía lacunas em tabelas, repetia exigências com nomes técnicos e só destacava o bloqueio do PMMA ao final de uma preparação com quatro etapas. Não havia registro de propostas diretamente a partir de uma lacuna.

O caminho agora é:

`Importar → Resumo da análise → Escolher experimento → Resolver pendências → Preparar modelo → Execução quando autorizada pelo serviço existente → Resultados existentes`.

- **Experimentos NASA:** documento, experimentos, contagem de conferidos, pendências acionáveis, estado físico do modelo e próxima ação.
- **Resumo:** encontrados/conferidos/faltantes, seleção por cartões e botão **Resolver 12 pendências** para M1. O botão abre o assistente no próprio resumo. SHA-256, cobertura, lotes e logs ficam em detalhes secundários.
- **Assistente:** modal amplo, uma lacuna por etapa, título do experimento, posição 1/12, navegação anterior/próxima, salvar rascunho e continuar, voltar, retomada e resumo das decisões. A barra representa requisitos satisfeitos para o perfil, sem aumentar ao visitar telas.
- **Cada etapa:** o que falta, por que é necessário, parâmetros relacionados e links para as páginas do PDF, fontes candidatas existentes, ações de registro/hipótese/não encontrada/adiamento e impacto. Trechos completos e histórico são expansíveis. O formulário abre após escolher a ação.
- **Experimento:** cinco dimensões compactas com ações concretas para revisar parâmetros, abrir o assistente ou entender requisitos do modelo. A antiga reconciliação BL-15 permanece secundária e só lista lacunas com possíveis sobreposições.
- **Preparação NASA:** mostra imediatamente o perfil, a aprovação do gerador, requisitos satisfeitos/pendentes, verificações adicionais e os registros já salvos. Não pede redigitação nem impõe quatro etapas para revelar um bloqueio conhecido. A seleção de perfil recarrega a jornada correspondente; atualmente existe um único perfil físico para esse caminho.
- **Caso independente:** conserva a preparação, hipóteses, revisão, execução e resultados BL-16, sem vínculo ou transferência de dados NASA.

O tema espacial escuro foi aplicado às telas existentes. O modal tem corpo rolável, cabeçalho/rodapé persistentes, indicador de salvamento, Escape, contenção e restauração de foco. O menu passou a quebrar linhas em telas menores, corrigindo o transbordamento encontrado na inspeção do navegador.

## Arquitetura e persistência

O catálogo científico continua sendo somente leitura para esta jornada. `guided_review.py` é uma camada aditiva que usa `bridge.profiles`, `bridge.resolve`, o contrato `bridge.Assumption`, o versionamento de casos e as funções de unidade/escrita atômica existentes. Não foi criado outro executor, gerador, serviço de busca nem worker.

Rotas adicionadas:

```text
GET  /api/experiments/{eid}/guided-review?profile_id=...
POST /api/experiments/{eid}/guided-review/cursor?profile_id=...
POST /api/experiments/{eid}/guided-review/{gap_id}?profile_id=...
```

`GET simulation-preparation` também expõe a jornada já persistida. A API anuncia `0.6.0-guided-review` e a capacidade `guided_review`; o frontend detecta servidor anterior.

Contrato de decisão:

```json
{
  "expected_revision": 0,
  "action": "SOURCE",
  "author": "Pessoa responsável",
  "proposal": {
    "value": 15.0,
    "unit": "cm",
    "details": "",
    "source": "Referência científica completa",
    "location": "página ou seção",
    "evidence": "Trecho a ser conferido por pessoa independente",
    "author": "Pessoa responsável",
    "justification": "",
    "limitations": ""
  }
}
```

O exemplo é apenas formato de API, **não é valor científico para M1**. O parâmetro é obtido da lacuna no servidor; o cliente não pode atribuir um estado de aprovação.

Cada experimento/perfil tem `var/guided_reviews/{eid}/{profile_id}.json`. O documento contém eventos sequenciais com revisão, ação, autoria, data UTC, estado, proposta/rascunho, normalização, hash do perfil, versão do perfil e hash do catálogo consultado. Eventos encadeiam o hash anterior. Uma revisão esperada desatualizada retorna 409; a interface mantém os campos e apresenta o motivo. Escrita é atômica e serializada pelo mesmo bloqueio reentrante da BL-16.

Cada decisão cria uma **versão imutável de caso BL-16** com `content.guided_review`, hash do conteúdo e indicação `DOCUMENTATION_ONLY_NOT_GENERATOR_INPUT`. Hipóteses numéricas reutilizam a validação `bridge.Assumption`. Propostas documentais ficam no snapshot e **não** são inseridas em `content.values` ou nas hipóteses executáveis do PMMA. Eventos registram caso, versão e hash; leituras verificam cadeia, conteúdo do caso e correspondência exata com a decisão capturada.

Navegação registra somente cursor; não muda a resolução. Rascunhos incompletos são identificados como `DRAFT_UNVALIDATED`; não passam por entradas científicas. Formulários editados ficam também em armazenamento local, com chave por experimento/perfil/lacuna. Ao navegar ou fechar com autoria informada, são salvos no servidor; sem autor, podem ser fechados mantendo apenas a cópia local. Depois de enviado, o cache local é removido e o registro do servidor é a referência.

## Estados e revisão

| Ação/condição | Estado resultante |
|---|---|
| Nenhuma decisão / adiar | `OPEN` |
| Salvar rascunho / solicitar correções | `IN_PROGRESS` |
| Enviar fonte complementar | `SOURCE_SUBMITTED` |
| Propor hipótese permitida | `ASSUMPTION_PROPOSED` |
| Solicitar revisão | `UNDER_REVIEW` |
| Informação não encontrada, com justificativa | `BLOCKED` |
| Parecer independente favorável + contrato físico executável satisfeito | `RESOLVED_FOR_PROFILE` |

Um parecer favorável no PMMA permanece `UNDER_REVIEW`, com `review_state=ACCEPTED`: a evidência pode ter parecer registrado, mas não satisfaz um perfil sem implementação/aprovação. Autorrevisão é recusada. Solicitar revisão e registrar parecer são ações explícitas, preservadas no histórico. Campos extras, inclusive tentativas de enviar `state`, são recusados.

A elegibilidade exige revisão favorável, gerador implementado/aprovado, perfil e catálogo ainda correspondentes aos hashes, parâmetro explicitamente aceito, dimensão compatível, domínio definido pelo perfil e permissão para hipótese, quando aplicável. Alterações posteriores de perfil/catálogo invalidam a elegibilidade derivada, preservando o evento histórico.

## M1: 12 lacunas, requisitos e bloqueios distintos

A ordem é estável e usa os IDs existentes: comprimento; suporte/substrato; duto; pressão; temperatura; perfil de entrada; anemômetro; ignição; pirólise PMMA; perfil temporal do oxigênio; incertezas; rastreamento da frente. Lacunas importadas desconhecidas recebem ordenação determinística por parâmetro/ID.

Os dados atuais satisfazem cinco dos 13 requisitos documentais do perfil; oito faltam. Os nove parâmetros conferidos incluem observáveis, que continuam referências de comparação. O painel separa esses requisitos da implementação/aprovação do gerador e das verificações de gravidade, reação, material e convergência de malha.

Anemômetro e perfil temporal de oxigênio limitam fidelidade. Incertezas e método de rastreamento limitam comparação quantitativa. Nenhuma dessas quatro lacunas é automaticamente tratada como entrada exigida pelo gerador. `compatibility.py` e `readiness.py` agora consultam os requisitos do perfil, reconciliam o alias antigo de pirólise e evitam repetir a mesma informação como nome amigável e identificador técnico. Uma lacuna aberta de construção continua bloqueante.

Mensagem do painel PMMA:

> Os dados podem ser preparados, mas este modelo ainda não pode ser executado. É necessária a implementação e aprovação do perfil físico.

Não há substituição pelo propano. O perfil físico desta jornada continua conservadoramente sem liberação de execução; a liberação de um perfil futuro precisa também ser conectada à avaliação completa do motor/worker BL-16. O caso independente já utiliza as verificações de execução existentes.

## Validação de propostas e limites científicos

Comprimento, pressão e temperatura aceitam números finitos, com unidade e dimensão verificadas pelo serviço existente. A normalização preserva valor/unidade enviados e registra SI separadamente. Pressão/comprimento devem ser positivos; temperatura deve superar o zero absoluto. Comprimento não pode ser menor ou igual à espessura documentada. Domínios de uso adicionais pertencem ao perfil físico, não são inventados pela interface.

Hipóteses escalares exigem referência identificável, localização, evidência, autoria, justificativa e limites de validade; começam sem aprovação e ficam vinculadas ao perfil/versão. A interface informa a restrição antes de abrir o formulário. Pirólise e campos sem contrato numérico não aceitam hipótese escalar.

**Limitação explícita:** duto, suporte, perfis espaciais/temporais, ignição, propriedades de material e métodos de comparação ainda não possuem schemas físicos especializados implementados. O registro desses campos aceita documentação estruturada por fonte/localização/evidência e descrição, com `physical_validation=REQUIRES_SPECIALIST_SCHEMA`; recusa usá-la como escalar arbitrário ou como entrada FDS. Não equivale à validação física de uma geometria, série temporal ou conjunto de propriedades. Esses schemas e o perfil PMMA executável continuam necessários para uso numérico futuro.

## Arquivos e componentes

Novos: `backend/app/guided_review.py`, `backend/app/api/guided_review.py`, `backend/tests/test_guided_review.py`, `frontend/src/GuidedReview.tsx`, `frontend/src/guided_review.test.tsx`, fixture `guided_review_m1.json`, servidor e roteiro de navegador em `scripts/bl17_browser_server.py` e `scripts/check_bl17_browser.py`.

Estendidos: `catalog/service.py`, `simulation/bridge.py`, `simulation/compatibility.py`, `readiness.py`, `api/cases.py`, `main.py`, `version.py`; cliente/tipos/capacidades frontend, `components.tsx`, `Analysis.tsx`, `Library.tsx`, `Review.tsx`, `Prepare.tsx`, estilos e teste de preparação. O fluxo de importação reutiliza `AnalysisSummary`, passando a oferecer a mesma ação guiada. Executor e player permanecem os existentes.

## Testes e evidências

| Verificação | Resultado |
|---|---|
| Regressão backend | **PASS — 378 testes**, dois skips históricos de registros BASS-II já conferidos |
| Contratos BL-17 backend | **PASS — 23 testes**, incluídos na regressão |
| Regressão frontend | **PASS — 73 testes**, incluindo nove novos cenários do assistente |
| TypeScript | **PASS** |
| Build de produção Vite | **PASS** |
| Contrato fixture frontend × resposta real backend | **PASS**, incluído nos 23 testes |
| Navegador Chrome real, API e build de produção | **PASS — 14 verificações**, desktop 1280×960 e móvel emulado 390×844 |
| Inspeção visual das capturas desktop/móvel | **PASS** |
| Snapshot científico e histórico | **PASS — 434 arquivos idênticos** |
| `git diff --check` | **PASS** |
| Estudo de usabilidade com pesquisador humano novo | **NOT_RUN** |
| Dispositivo móvel físico / teclado virtual / leitor de tela | **NOT_RUN** |
| FDS real / Smokeview real / Gemini | **NOT_RUN — não necessários para esta entrega** |

Os testes cobrem ordenação, drafts/decisões, cursor, retomada, concorrência otimista, conversões cm→m e °C→K, tipo/domínio/dimensão, referência insuficiente, fonte sem promoção, autorrevisão recusada, requisitos de perfil, invalidação por mudança de perfil/catálogo, lacunas bloqueantes/não bloqueantes, PMMA sem aprovação, DYLCO sem física FDS, caso independente e adulteração de eventos/casos.

O navegador importou o **PDF local real**, reutilizou a curadoria existente sem Gemini e percorreu resumo, 1/12, proposta, 2/12, retorno, fechamento, recarga, retomada, resumo das decisões e preparação ainda bloqueada. Os registros de proposta do teste são sintéticos, explicitamente rotulados, e ficam somente em `tmp/bl17-browser-workspace-*`. Não foram gravados na área real `var/`.

Evidências: [resultados do navegador](BL-17_browser_checks.json), [preservação](BL-17_preservacao.json), [resumo desktop](BL-17_resumo_desktop.png), [assistente desktop](BL-17_wizard_desktop.png), [assistente móvel](BL-17_wizard_mobile.png).

O primeiro ensaio móvel encontrou transbordamento do menu: **FAIL inicial, corrigido e retestado PASS**. O sandbox também bloqueou esbuild em algumas execuções; testes/build foram repetidos com a permissão necessária e concluíram. Avisos de migração futura do React Router permanecem informativos.

## Riscos e limitações operacionais

- Identidade continua declarada, sem autenticação: a comparação de autor/revisor impede autorrevisão nominal, não prova identidade. Não há aprovação automática de ciência.
- Persistência JSON e bloqueio em processo único, conforme BL-16. Não é uma solução transacional entre múltiplos servidores. Uma interrupção entre gravar o caso e o evento pode deixar uma versão documental órfã; ela nunca habilita execução.
- A cadeia detecta alteração de eventos e casos vinculados, mas não substitui assinatura, armazenamento imutável externo ou proteção contra administrador que reescreva todo o histórico. Backup da área `var/` continua necessário.
- Hash do catálogo/perfil é conservador: mudanças exigem nova avaliação da elegibilidade.
- Rascunho local sem autoria depende do navegador e não é uma submissão científica nem uma cópia compartilhada.
- Apenas o perfil PMMA documental está disponível no caminho NASA; DYLCO é mostrado como incompatível com esse perfil. Novos perfis precisam de contratos explícitos e conexão às verificações do motor.

## Reproduzir os testes

Na raiz:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -ra backend/tests
npm.cmd test --prefix frontend
npm.cmd run typecheck --prefix frontend
npm.cmd run build --prefix frontend
git -c safe.directory=C:/Users/junio/Projetos/FlameLab diff --check
```

Para inspeção manual com dados isolados, após o build:

```powershell
$env:PYTHONPATH=(Get-Location).Path
.\.venv\Scripts\python.exe scripts/bl17_browser_server.py
```

Abrir `http://127.0.0.1:18017/`. O servidor cria uma nova área temporária por inicialização, usa fontes NASA de fixture, provedor IA desligado e FakeExecutor. Não usar o servidor de teste para ciência ou execução real.

1. Importar `sources/NASA-TM-20210011385.pdf`, ou abrir o resumo do artigo existente. Confirmar nove parâmetros conferidos e 12 pendências.
2. Selecionar M1 e clicar **Resolver 12 pendências**. Conferir 1/12, explicação, fontes/evidências, ações e impacto.
3. Abrir **Registrar informação científica**. Somente na área isolada, preencher uma proposta rotulada como teste e enviar; conferir **Evidência enviada**, sem aumentar os requisitos satisfeitos.
4. Avançar, voltar e verificar os dados. Editar um rascunho com autoria, salvar/continuar e conferir o indicador.
5. Voltar ao resumo, recarregar e usar **Retomar revisão**; conferir cursor e conteúdo.
6. Consultar decisões, histórico e versão do caso. Solicitar revisão; tentar parecer do próprio autor (deve recusar). Registrar parecer de pessoa independente apenas se ela realmente realizou a revisão.
7. Abrir a preparação e conferir os dados reaproveitados, requisitos físicos e bloqueio PMMA desde o início. Não deve aparecer uma execução M1 baseada em propano.
8. Percorrer as 12 posições sem decisões: a barra não deve aumentar. Conferir a distinção das lacunas de comparação e as hipóteses indisponíveis de pirólise.
9. Repetir em viewport de 390 px: corpo rola e navegação permanece acessível. Conferir teclado, Escape e retorno de foco.

Para repetir o roteiro automatizado de Chrome, iniciar uma instância de teste com depuração local na porta 9227 e perfil dentro de `tmp/`, depois executar `python scripts/check_bl17_browser.py` usando a `.venv`. O roteiro pressupõe área isolada nova e PDF local disponível; grava apenas capturas/checks e propostas sintéticas nessa área.
