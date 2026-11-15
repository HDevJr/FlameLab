# Roteiro de teste manual — jornada S01–S07 (protótipo v2.1)

> **Estado desta validação: `NOT_RUN`.** Nenhuma pessoa abriu estas telas em um navegador durante o desenvolvimento (não havia ferramenta de navegador na sessão). Quem executar este roteiro registra o resultado em [docs/evidence/manual_validation_visual_TEMPLATE.md](evidence/manual_validation_visual_TEMPLATE.md) (copie para `manual_validation_visual_<data>_<nome>.md`). **Não marque PASS por inferência.**

## 0. Preparação (≈ 5 min)
1. Terminal 1 (raiz do repositório): `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000`
2. Terminal 2: `cd frontend; npm install; npm run dev` → abrir <http://localhost:5173>.
3. Tenha à mão o PDF `sources/NASA-TM-1998-207916.pdf` (documento de teste da importação) e o `sources/NASA-TM-20210011385.pdf` (BASS-II).
4. Navegador: Chrome ou Edge atual. Anote versão e tamanho de janela.
5. **Cuidado com a revisão do M1:** confirmar um valor do BASS-II M1 **altera o dataset versionado** (`data/parameters/…`) e o log de curadoria. Só a pessoa escolhida como revisora (D-11) deve fazer isso, e de verdade. Para **testar** a aprovação use os parâmetros do artigo **importado** (ficam em `var/`, fora do Git).

## 1. S01 — Experimentos NASA (`/`)
| # | Ação | Esperado | Resultado |
|---|---|---|---|
| 1.1 | Abrir `/` | Menu com **Experimentos NASA · Importar artigo · Demonstração FDS · Execuções** | |
| 1.2 | Ver o cartão do BASS-II | Selos “Dataset curado” e procedência; “Experimentos (1)”; **0/9 conferidos · 12 lacunas** | |
| 1.3 | Passar o mouse/clicar em “?” de *conferidos* e *lacunas* | Aparece uma explicação em linguagem simples | |
| 1.4 | Clicar “Resumo da análise” | Abre S02b (resumo) | |

## 2. S02 — Importar artigo (`/importar`)
| # | Ação | Esperado | Resultado |
|---|---|---|---|
| 2.1 | Escolher `NASA-TM-1998-207916.pdf` | Lista de etapas: *Arquivo recebido → Identificando o documento → Verificando a origem NASA → Lendo o PDF → Extraindo experimentos e parâmetros → Pesquisando fontes complementares NASA → Comparando informações → Preparando o relatório de análise* | |
| 2.2 | Observar enquanto roda | A etapa atual mostra “em andamento” e **tempo decorrido**; na extração aparece “Lote i de n: páginas a–b”; **não há percentual inventado** | |
| 2.3 | Abrir “Detalhes técnicos” de uma etapa | SHA-256, lotes, tokens e tempos aparecem **somente** ali | |
| 2.4 | Ao terminar | Bloco **“O que o FlameLab encontrou”** com frases curtas: origem verificada, **cobertura das páginas**, experimentos, parâmetros, conferidos × pendentes, fontes NASA, prontidão FDS | |
| 2.5 | Verificar a cobertura | Texto do tipo “A IA leu todas as páginas com texto (1–32)”. Se parcial, mostra páginas lidas e **não lidas** e o motivo | |
| 2.6 | Confirmar a frase sobre origem × revisão | “Procedência verificada não significa números conferidos” aparece no resumo | |
| 2.7 | Tente um arquivo que não é PDF | Mensagem de erro clara; nada é criado | |

## 3. Resumo da análise (`/documentos/<id>/analise`)
| # | Ação | Esperado | Resultado |
|---|---|---|---|
| 3.1 | Abrir o resumo do documento importado | Conclusões no topo; cartões *Origem NASA · Cobertura · Parâmetros · Fontes relacionadas* | |
| 3.2 | Seção “O que ainda não está validado” | 3 avisos (procedência ≠ revisão; fontes não validam números; IA = hipótese) | |
| 3.3 | Abrir “Processamento e tempos (técnico)” | Etapas com duração e tabela de lotes (páginas, tempo, aceitos/descartados, tokens) | |

## 4. S03 — Fontes NASA (`/documentos/<id>/enriquecimento`)
| # | Ação | Esperado | Resultado |
|---|---|---|---|
| 4.1 | Abrir para o BASS-II → “Consultar fontes NASA” | Faixa amarela **“Enriquecimento não é validação”**; NTRS confirmado; **PSI-25 candidato** (com as razões); TechPort não encontrado | |
| 4.2 | Ver “Operações de API executadas” | Cada chamada com fonte, modo (online/fixture) e HTTP | |
| 4.3 | Verificar que nenhum valor do artigo mudou | Voltar à ficha: estados continuam “Extraído · não revisado” | |

## 5. S04 — Revisão dos parâmetros (`/experimentos/<id>`)
| # | Ação | Esperado | Resultado |
|---|---|---|---|
| 5.1 | Abrir o experimento **importado** | Tabelas *Condições experimentais · Resultados observados · Metadados* e *Campos ausentes* | |
| 5.2 | Clicar “Ver origem e revisar” numa linha | Abre o painel: valor e unidade, experimento, documento, **página e trecho literal**, botão “Abrir o PDF na página N”, dados complementares NASA e trilha de auditoria | |
| 5.3 | Clicar “Abrir o PDF na página N” | O PDF abre na página indicada | |
| 5.4 | Verificar os campos “Valor lido”, “Unidade”, “Página” | Começam **vazios** (de propósito) | |
| 5.5 | Preencher **valor errado** + nome + “Conferi o PDF” → Confirmar | Mensagem “…Nada foi aprovado…”; o estado **não muda**; a tentativa aparece na trilha como *recusada* | |
| 5.6 | Preencher com o **mesmo nome do extrator** (o nome do modelo mostrado em “Extraído por”) | Recusa: revisor precisa ser diferente | |
| 5.7 | Preencher com “Gemini” ou “Claude” | Recusa: revisão por pessoa | |
| 5.8 | Preencher corretamente (valor, unidade, página lidos no PDF) e confirmar | “Conferência registrada”; estado → **Conferido na fonte**; trilha mostra revisor, data e hash | |
| 5.9 | Em outro parâmetro: observações + “Manter pendente (dúvida)” | Continua pendente; dúvida na trilha | |
| 5.10 | Em outro: valor lido diferente + observações + “Registrar divergência” | Continua pendente; **o valor extraído não é alterado**; divergência na trilha | |
| 5.11 | Tentar confirmar de novo um já conferido | O painel não oferece confirmação; se forçar pela API, recusa “WRONG_STATE” | |
| 5.12 | Ver o cartão “Simulação deste experimento” | Selo de prontidão e **motivos**; “Iniciar simulação deste experimento” **desabilitado** quando não há modelo; aviso de que nenhuma simulação genérica é criada no lugar | |

## 6. S05 — Alterar parâmetros do experimento (`/experimentos/<id>/alterar`)
| # | Ação | Esperado | Resultado |
|---|---|---|---|
| 6.1 | Abrir para o BASS-II M1 | Aviso “não pode ser simulado no FDS” com os motivos; lista **só de condições numéricas com unidade** (espessura, largura, velocidade do ar, O₂ inicial) | |
| 6.2 | Procurar resultados observados | **Não** estão na lista de edição; aparecem em “Não editáveis” | |
| 6.3 | Marcar um campo | Mostra origem (tabela/página), unidade, regra, **original × novo** lado a lado e “Restaurar” | |
| 6.4 | Informar valor inválido (0, negativo; O₂ > 100) → Salvar | Mensagem do servidor “fora da faixa” | |
| 6.5 | Informar valor válido → Salvar cenário derivado | Vai para S06 mostrando **“Hipótese sobre …”**, a alteração (valor original riscado → novo) e **“Este cenário não pode ser executado”**; botão Iniciar desabilitado | |
| 6.6 | Voltar à ficha | O valor original continua intacto | |
| 6.7 | Em **nenhum** momento aparecem “queimador”, “HRRPUA” ou “fuligem” nesta jornada | Esses campos só existem em “Demonstração FDS” | |

## 7. Demonstração FDS (`/demonstracao-fds`)
| # | Ação | Esperado | Resultado |
|---|---|---|---|
| 7.1 | Abrir | Faixa **“Isto não é um experimento NASA”**; selo “Teste de integração” | |
| 7.2 | Marcar “Potência por área do queimador”, informar 500 | Original 1000 → novo 500, faixa 250–2000 | |
| 7.3 | “Salvar cenário derivado da demonstração” | Vai para S06 com a faixa “Demonstração FDS” | |

## 8. S06 — Execução (`/simulacao/<scenarioId>`)
| # | Ação | Esperado | Resultado |
|---|---|---|---|
| 8.1 | “Iniciar simulação” | Linha *Na fila → Validando → Executando FDS → Processando → Renderizando → Concluído* | |
| 8.2 | Enquanto o FDS roda | Mensagem **“O FDS está executando o cálculo”**, **tempo decorrido** e, se o log informar, **tempo físico calculado “X s de T s”** (sem previsão de término). Caso não haja informação: barra indeterminada + só tempo decorrido | |
| 8.3 | Sair da tela e voltar (ou abrir “Execuções”) | A execução continua e é reencontrada | |
| 8.4 | Ao final | Tabela **“Tempos medidos”** (fila, preparação, FDS, processamento, Smokeview, MP4, total) e botão “Ver resultado e vídeo” | |

## 9. S07 — Resultado (`/execucoes/<runId>`)
| # | Ação | Esperado | Resultado |
|---|---|---|---|
| 9.1 | Abrir | Faixa “Demonstração FDS, independente de qualquer artigo… hipótese computacional” | |
| 9.2 | Player | Botões **Reproduzir/Pausar, Reproduzir novamente, 0,25× 0,5× 1× 2×, Repetir automaticamente, Tela cheia** e linha do tempo | |
| 9.3 | Reproduzir; mudar a velocidade; arrastar a linha do tempo | Velocidade muda; o vídeo busca o instante (suporta Range) | |
| 9.4 | Marcar/desmarcar “Repetir automaticamente”; recarregar a página | A escolha é lembrada | |
| 9.5 | Tela cheia e sair | Funciona | |
| 9.6 | Ler o texto abaixo do player | Duração do vídeo; tempo físico simulado ≈ X s; “1 s de vídeo = 1 s de tempo físico simulado” (execuções novas) | |
| 9.7 | Fechar a aba, reabrir `/execucoes` e abrir a execução | **O vídeo continua disponível** | |
| 9.8 | Gráfico de HRR; com a execução derivada, ver a curva tracejada do caso-base | Curvas coerentes: o derivado (500) fica abaixo do base (1000) | |
| 9.9 | “Proveniência e artefatos (técnico)” | Hash do .fds, versões, lista de artefatos clicáveis | |

## 10. Critérios de aceite (marque ao final)
Compreendi o resultado da importação · A cobertura parcial/total do PDF está visível · Consigo consultar a origem de cada parâmetro · Consigo revisar na interface e as recusas fazem sentido · Enriquecimento está separado da validação · A demonstração FDS não se confunde com o artigo · Vejo tempos medidos · Fica claro quando o FDS está executando · O vídeo continua disponível · Consigo pausar, repetir e mudar a velocidade · O que não foi verificado continua marcado como pendente.

**Observações de usabilidade** (o que confundiu, o que faltou): _preencher no modelo de registro._
