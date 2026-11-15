# BL-17.2 — Formulários científicos estruturados e resolução efetiva de lacunas

## Estado do repositório e preservação

- `main` (`4dbc7a0`) **não contém o código das BL-02…BL-17**: seu último commit ("feat: validação parâmetros") só acrescenta 433 arquivos de `var/` (dados de execução). O código vive em `feat/arq-v2-nasa-fds-prototipo` (`9418e4c`), onde `var/` é ignorado pelo Git.
- Trabalho feito na branch nova **`feat/bl-17-2-formularios-cientificos`**, criada a partir de `9418e4c`. `main` não foi alterada.
- Como `main` versiona `var/` e a branch do protótipo não, o checkout removeria os dados locais do disco. Antes dele, `var/` foi copiado para fora do repositório (433 arquivos) e depois restaurado a partir de `main`. Conferência: `guided_reviews`, `audit`, `cases`, `imports`, `analysis`, `enrichment`, `provenance` e `scenarios` **idênticos** ao backup. Os 9 arquivos diferentes eram logs em `var/runs/` e diferiam só por fim de linha (CRLF).
- Linha de base antes de qualquer edição: backend 378 passed / 2 skipped; frontend 73 passed; typecheck PASS.
- Nenhuma chamada Gemini, nenhum FDS real, nenhum commit, push ou merge.

## Causa raiz dos botões desabilitados

Em `backend/app/guided_review.py` (BL-17):

1. `SCALARS = {"sample_length", "ambient_pressure", "ambient_temperature"}`. A hipótese só era permitida com `req.assumption_allowed and parameter in SCALARS`. Nos outros nove campos o botão era negado **por falta de contrato de dados**, não por uma decisão científica. O próprio perfil PMMA declarava `assumption_allowed=True` para duto, escoamento, suporte e ignição, e a interface contradizia o perfil.
2. Anemômetro, perfil de O₂, incertezas e rastreamento da frente não estão em `profile.requirements`. Por isso `req=None` e esses campos ficavam sempre desabilitados.
3. Todo campo não escalar caía em `kind: DOCUMENT`: texto livre com `physical_validation=REQUIRES_SPECIALIST_SCHEMA`. A mensagem de bloqueio era a mesma para todos os casos e não separava "dado ausente" de "gerador não aprovado".
4. A preparação só contava `RESOLVED_FOR_PROFILE`, estado impossível com o perfil PMMA. Uma proposta enviada não reaparecia **por campo** na preparação.
5. O resumo exibia "12 com registro" contando também rascunhos de formulário.

Dados reais encontrados no `var/` (preservados, sem nenhuma edição): sete registros com "ambiente de teste" gravados como fonte na área científica (3 `SOURCE_SUBMITTED` e 4 rascunhos); duas hipóteses cujo texto declara "hipótese sintética para testes internos"; e suporte e duto com **o mesmo texto livre** em campos diferentes.

## O que foi implementado

### Contratos tipados (`backend/app/gap_contracts.py`)

Um motor genérico de campos, com estes tipos:

- `quantity`: valor e unidade, com dimensão, conversão para SI e limites físicos.
- `enum`
- `text`
- `vector`: x/y/z e unidade.
- `rows`: tabelas com unicidade e tempo estritamente crescente.

Campos condicionais usam `when`. O valor e a unidade enviados são preservados, e o SI é registrado à parte. Os limites aplicados são **apenas os fisicamente necessários** (comprimento > 0, T > 0 K, fração entre 0 e 1). Nenhum domínio de uso foi inventado.

| Lacuna | Tipo | Hipótese neste perfil | Uso |
|---|---|---|---|
| Comprimento, pressão, temperatura | Grandeza | Permitida | Construção |
| Suporte/substrato | Geometria + propriedades térmicas opcionais | Permitida | Construção |
| Duto | Geometria (seção, posição da amostra, sentido do escoamento) | Permitida | Construção |
| Perfil de entrada | Procedimento (perfil espacial, rampa/série temporal) | Permitida | Construção |
| Ignição | Procedimento (tipo, início, duração, posição, grandezas) | Permitida | Construção |
| Pirólise PMMA | Material (modelo + propriedades com fonte e validade) | Só rascunho exploratório não aprovado | Construção |
| Anemômetro | Medição | Só rascunho exploratório | Fidelidade |
| Perfil de O₂ | Procedimento (constante/série) | Só rascunho exploratório | Fidelidade |
| Incertezas | Medição | Só rascunho exploratório | **Só comparação, nunca entrada FDS** |
| Rastreamento da frente | Medição (critério, intervalo, cálculo) | Só rascunho exploratório | **Só comparação, nunca entrada FDS** |
| Parâmetro desconhecido | Documental | Indisponível; explica o desenvolvimento necessário | — |

Material: o contrato lista **nomes** de propriedades exigidas por estrutura de modelo (Arrhenius de uma etapa: 9 propriedades). Não traz valores. O sistema aponta quais propriedades faltam. Nada é deduzido do nome do material.

Coerência com dados publicados (sem alterá-los):

- comprimento > espessura;
- seção do duto ≥ largura da amostra;
- aviso quando a velocidade ou o O₂ inicial difere do valor publicado.

As unidades de densidade, calor específico, condutividade, energia específica/molar, taxa, atenuação e W/m² foram acrescentadas a `units.py` (extensão aditiva v1.2).

### Fluxo de resolução

Três caminhos em cada pendência:

1. **Registrar evidência científica** (`SOURCE`).
2. **Preparar hipótese exploratória**: `ASSUMPTION`, ou `EXPLORATORY_DRAFT`, um estado novo e explicitamente não aprovado que nunca vira entrada FDS.
3. **Manter pendência em aberto** (`NOT_FOUND` / `DEFER`).

Cada caminho desabilitado mostra o motivo específico e o que falta desenvolver.

Cada registro tem um conjunto de verificações separado em três grupos:

- **Dados** (resolvíveis na revisão): informação registrada; contrato completo e com unidades.
- **Revisão** (outra pessoa): parecer favorável.
- **Modelo físico** (fora da tela): o perfil define o uso do campo; gerador implementado e aprovado. Para lacunas de comparação ou fidelidade: pipeline de comparação ou consumo pelo perfil.

`_eligible` continua sendo a única regra para `RESOLVED_FOR_PROFILE`. O modo TESTE nunca resolve requisitos.

Pré-visualização determinística: `POST …/guided-review/{gap}/preview`. Usa a mesma função do envio e não grava nada. Devolve erros por campo, conversões, propriedades ausentes, o diff de uma edição e as consequências: o que será salvo, que requisito pode atender e por que (não) é entrada FDS.

Edição auditável: alterar uma proposta existente exige `change_reason`. O evento novo guarda `revises_revision` e o `diff` campo a campo, e o parecer volta a `PENDING`. A cadeia de hash e os eventos anteriores ficam intactos.

### Continuidade revisão → preparação (integração BL-16)

A visão inclui `requirements`: 13 requisitos de dados mais 4 verificações físicas. Para cada um:

- original publicado (valor, unidade, localizador) ou "ausente na fonte";
- nova proposta (origem, resumo estruturado, autor, data, modo, fonte);
- nível e se satisfaz o perfil;
- verificações e motivo;
- próximo passo e `gap_id`.

`GET /simulation-preparation` devolve o mesmo. A tela **Preparar modelo** mostra essa tabela, com o botão **Abrir requisito** para cada campo, e um botão de execução **desabilitado com o motivo**.

Cada decisão continua criando uma versão imutável de caso BL-16 (`DOCUMENTATION_ONLY_NOT_GENERATOR_INPUT`). Nada entra em `content.values`.

### Resumo sem progresso artificial

O resumo apresenta uma escada de seis níveis, que correspondem às seis categorias do enunciado:

1. publicados conferidos;
2. evidência submetida;
3. hipóteses e rascunhos exploratórios;
4. revisados;
5. requisitos satisfeitos;
6. modelo aprovado.

Mostra também os cinco estágios do PMMA: preparação documental, construção de hipóteses, validação do modelo de material, validação do gerador e autorização de execução.

"Pendências tratadas" (X/12) aparece separado de "requisitos satisfeitos" (Y/13). Registros com conteúdo de teste na área científica são **sinalizados e não contam**. Textos livres anteriores à BL-17.2 recebem o aviso "reenvie pelo formulário estruturado". Textos idênticos em lacunas diferentes são apontados.

### Modo científico × modo de teste

- `?mode=TEST` em todas as rotas da revisão guiada. `workspace.use_mode` (contextvar por requisição) redireciona **apenas** `guided_reviews` e `cases` para `var/test_mode/`. O catálogo e as importações são só lidos.
- Casos de teste não são encontrados por `/api/cases` nem por `/api/simulations`. Seu snapshot leva `TEST_ONLY_SYNTHETIC_NOT_SCIENTIFIC`.
- No modo de teste, tipos, unidades e limites continuam valendo. Há um botão para preencher valores sintéticos rotulados "TESTE".
- No modo científico, textos típicos de teste ("ambiente de teste", "sintético", "teste interno", "lorem ipsum"…) são recusados com orientação para usar o modo de teste. O detector é conservador: "Teste M1" e "NASA test matrix" não disparam.

### PMMA

O perfil continua `approved=False`, `implemented=False`. `can_execute` continua sempre falso, sem nenhuma substituição por propano. Um parecer favorável sobre uma hipótese aparece como "Revisada por pessoa independente" e não como requisito satisfeito.

## Lacunas ainda sem esquema físico validado

Todos os contratos são **contratos de dados** (`DATA_CONTRACT_ONLY` ou `DATA_CONTRACT_AND_DOMAIN_CHECKS`). Para uso numérico ainda falta:

- gerador do perfil PMMA, que mapeie comprimento, duto, suporte, entrada e ignição para MESH/OBST/VENT/SURF;
- modelo de material MATL/REAC revisado por especialista, com verificação da cinética;
- gravidade/microgravidade, convergência de malha e modelo de reação;
- pós-processamento da frente de chama e comparação quantitativa com incertezas;
- condição de contorno de O₂ variável no tempo.

## Antes × depois

| Antes (BL-17) | Depois (BL-17.2) |
|---|---|
| Hipótese só em 3 de 12 lacunas; mensagem genérica | Hipótese em 7; rascunho exploratório não aprovado em 5; motivo e desenvolvimento necessário por campo |
| Texto livre para geometria/material/procedimento | Formulários tipados com unidades, conversão para SI, campos condicionais e tabelas |
| Sem validação antes do envio | Pré-visualização ao vivo, erros no campo, envio desabilitado com explicação |
| Proposta não reaparecia por campo | Tabela de requisitos na preparação, com "Abrir requisito" |
| "12 com registro" (incluía rascunhos) | Pendências tratadas × requisitos satisfeitos × escada × cinco estágios |
| "Ambiente de teste" aceito como fonte | Recusado no modo científico; legado sinalizado e fora das contagens; modo de teste isolado |
| Reenvio sem motivo | Edição com motivo e diff obrigatórios; parecer reiniciado |

## Testes

| Verificação | Resultado |
|---|---|
| Regressão backend | **PASS — 394 passed, 2 skipped** (os mesmos skips históricos) |
| Aceitação BL-17.2 (`test_structured_gaps.py`, 16 testes: itens 1–10 + modo TESTE, legado, preview, comparação, contratos, unidades) | **PASS** |
| Frontend (vitest) | **PASS — 81** (eram 73) |
| TypeScript | **PASS** |
| Build Vite | **PASS** |
| Fixture frontend × resposta real (regenerada com `scripts/export_guided_fixture.py`) | **PASS** |
| Chrome real, UI de produção + API real, área descartável, modo TESTE (`scripts/check_bl17_2_browser.py`) | **PASS — 11/11**, sem exceções JS ([checks](BL-17_2_browser_checks.json)) |
| Isolamento em disco após o navegador: 0 registros científicos, 4 eventos `mode=TEST`; `var/` real idêntico ao backup | **PASS** |
| `git diff --check` | **PASS** |
| Pesquisador humano / leitor de tela / dispositivo físico | **NOT_RUN** |
| FDS, Smokeview, Gemini | **NOT_RUN** (não necessários) |

Mudança intencional de comportamento: o teste BL-17 que aceitava texto livre para o duto passou a exigir o formulário estruturado (`test_complex_value_requires_structured_contract_never_scalar_or_free_text`).

Capturas: [preparação](BL-17_2_preparacao_desktop.png), [geometria](BL-17_2_wizard_geometria_desktop.png), [móvel](BL-17_2_wizard_mobile.png). Saída completa: [test_run_BL-17_2_20261115.txt](test_run_BL-17_2_20261115.txt).

## Roteiro de teste manual

```powershell
npm.cmd run build --prefix frontend
$env:PYTHONPATH=(Get-Location).Path
.\.venv\Scripts\python.exe scripts/bl17_browser_server.py   # área descartável em tmp/, http://127.0.0.1:18017
```

1. Abrir `/experimentos/BASS2-M1/preparar`. Conferir a tabela "Requisitos do perfil, campo a campo", os cinco estágios e o botão de execução desabilitado com o motivo.
2. **Modo científico:** clicar em "Abrir requisito: Comprimento da amostra", depois em "Registrar evidência científica". Informar 15 cm. Ver "15 cm = 0,15 m". Digitar "ambiente de teste" como fonte: o envio fica bloqueado com orientação. Fechar com Esc sem informar autor (nada é enviado).
3. Selecionar **Modo de teste da interface** e conferir o aviso vermelho.
4. Comprimento 12 cm como hipótese de engenharia → "Hipótese computacional proposta", ainda pendente na tabela.
5. Pressão 1 atm → 101325 Pa. Temperatura 20 °C → 293,15 K.
6. Suporte: "Preparar hipótese", escolher "Placa plana" (os campos aparecem), posição x/y/z, normal e contato. Enviar.
7. Escoamento: uniforme, 10 cm/s → aviso de diferença em relação aos 9 cm/s publicados. Testar uma série com tempos decrescentes → recusada.
8. Pirólise: "Preparar hipótese" vira "Salvar rascunho exploratório não aprovado". Adicionar só a densidade → a lista mostra 8 propriedades ausentes.
9. Recarregar a página: as propostas reaparecem na preparação. Clicar em "Editar proposta": o motivo é obrigatório e o histórico mostra o diff.
10. Solicitar revisão e registrar parecer com **outro nome** → "Revisada por pessoa independente". Os requisitos satisfeitos não mudam e a execução continua bloqueada.
11. Voltar ao modo científico: nada do modo de teste aparece.

Não usar o servidor de teste para ciência. No `var/` real, use o modo científico só com fontes verdadeiras.

## Pendências para decisão da equipe

- Os sete registros "ambiente de teste" e as duas hipóteses "sintéticas" continuam no histórico científico real. Ficam sinalizados e fora das contagens. Removê-los exigiria reescrever uma cadeia de hash, o que não foi feito. A saída recomendada é editar cada um com motivo, pela interface.
- `main` contém um commit só com `var/`, aparentemente acidental. Não foi alterado.
