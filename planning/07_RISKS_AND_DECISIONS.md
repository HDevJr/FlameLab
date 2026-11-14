# 07 — RISKS_AND_DECISIONS

> Plano 0.1 · 14/11/2026

## 1. Riscos (DM §17 refinado + novos)
| ID | Risco | Prob. | Impacto | Gatilho de detecção | Mitigação | Plano B |
|---|---|---|---|---|---|---|
| R-01 | **Sem acesso a LLM** (nenhuma chave no ambiente auditado) | Alta | Muito alto: o "resumir/interpretar" do desafio fica descoberto | D-03 sem resposta até G0 | Decidir o provedor na primeira hora; testar uma chamada real logo; gerar cache na noite de 14/11 | Verificador + UI + cache gerado em outra máquina com acesso. Sem nenhum acesso: P-05/P-06 BLOQUEADO e pitch ajustado |
| R-02 | Tabela 5.1 com layout diferente do esperado / M2, M14 não existem com as características citadas | Média | Médio | leitura no BL-02.05 | Testes T-04/T-05 parametrizados pelo conteúdo real | Escolher outros ensaios e registrar |
| R-03 | Conferência lenta (gargalo humano) | Alta | Alto | <M1 conferido às 13h de 14/11 | Começar a transcrever M1 antes do restante | Reduzir para 3 ensaios |
| R-04 | IA inventa números / mistura M1-M2 | Média | Muito alto | golden set | Verificador V1–V8, I-7, corpus restrito | Mostrar só as respostas que passaram |
| R-05 | Frontend atrasa | Média | Alto | G1 sem S03 | Layout simples; componentes base primeiro | Demonstrar S03 + S04 + S05 e cortar S01/S06 |
| R-06 | FDS consome a equipe | Alta | Alto | horas em F08 antes de G1 | Time-box e pré-condições (BL-09.00) | Slide 07 vira roadmap |
| R-07 | FDS não está operacional no ambiente do projeto | Média | Baixo para o MVP | auditoria F00.A | F08 restrita à parte documental | idem |
| R-08 | Internet ruim no evento | Média | Alto (instalação, LLM LIVE) | — | Instalar tudo cedo; demo em modo cache | vídeo |
| R-09 | Pitch e produto divergem | Média | Alto (credibilidade) | revisão em G4/G5 | Matriz 06 como fonte única | cortar a frase do roteiro |
| R-10 | Licença de mídia | Média | Baixo | D-04 | só mídia com `license_note` | esquema conceitual |
| R-11 | Horário de submissão errado (17h × 23h59) | Baixa | Muito alto | — | Confirmar com a organização no dia 14 | submeter até 17h |
| R-12 | "Dashboard genérico" (DM §17) | Média | Médio | revisão de G2 | jornada guiada por pergunta e ficha M1 no centro | — |
| R-13 | PDF > limite de repositório/licença de redistribuição incerta | Baixa | Baixo | BL-01.04 | guardar só o hash e a URL no git | — |
| R-14 | Prompt injection via trecho | Baixa (corpus curado) | Alto | T-16 | dados delimitados, sem ferramentas, verificador | — |

## 2. Divergências documento × prompt × realidade
| ID | Divergência | Consequência | Recomendação |
|---|---|---|---|
| DIV-01 | `INFERIDO`/`CALCULADO` como estado de revisão (DM §09) × natureza epistêmica (prompt §7) | Não é possível representar "calculado e não revisado" nem "observado e não revisado" de forma inequívoca | Três eixos (`role`, `nature`, `status`), mantendo os 6 valores do DM + invariantes I-2/I-3/I-4 (D-07) |
| DIV-02 | "8 campos tabulados" (T-01) × 9 valores; Material vem da §5 e não de uma coluna | T-01 ambíguo; a evidência de Material teria a localização errada | T-01 conta 9 registros; a evidência de Material aponta para o texto |
| DIV-03 | Valores M1 "conferidos no texto compartilhado" × política de CONFERIDO_FONTE | Exibi-los como conferidos violaria a política | Status inicial `EXTRAIDO_NAO_REVISADO`; conferir no PDF na F01 |
| DIV-04 | `/api/tests/M1` | colisão entre investigações | `test_uid = BASS2-M1` |
| DIV-05 | SQLite + JSON | dois mecanismos para o mesmo dado; mais código | Só JSON no MVP; SQLite FUTURO |
| DIV-06 | T-04 (M2 com duas velocidades) e T-05 (M14) presumem conteúdo não verificado | testes inválidos se a premissa falhar | parametrizar após a leitura na F01 |
| DIV-07 | Protótipo de extração citado × ausente | não dá para "reaproveitar" | BL-01.08: obter ou declarar ABSENT; o parser é SHOULD |
| DIV-08 | Cronograma do DM começa na manhã de 14/11, a mesma janela deste planejamento | o plano consome tempo do G0 | G0 = aprovação deste plano; ver [08](08_HACKATHON_EXECUTION_PLAN.md) |
| DIV-09 | Submissão 17h local × 23h59 geral | risco de perder o prazo | Planejar por 17h; confirmar |
| DIV-10 | "Ambiente: microgravidade" listado como parâmetro de M1 (prompt) | mistura metadado de investigação e coluna de tabela | `Investigation.gravity_environment` com evidência |
| DIV-11 | S07 relatório na jornada, fora da lista MUST | ambiguidade de escopo | SHOULD (S-4) |
| DIV-12 | "SI-Powered" no título | possível erro de digitação no slide 03 | Copiar da página oficial |
| DIV-13 | FDS 6.11.1 "instalado" (DM §11) × teste feito em outro computador (atualização de 14/11) | o DM sugere disponibilidade local | Estado NOT_VERIFIED; auditoria F00.A; P-15 ≠ P-16 |
| DIV-14 | DM §10 "IA ajuda a extrair parâmetros (multimodal)" | escopo inviável no prazo | FUTURO; o MVP só usa parser de verificação |

## 3. Decisões pendentes
| ID | Decisão | Opções | Recomendação | Prazo | Bloqueia |
|---|---|---|---|---|---|
| D-01 | Quantos ensaios curar | 3 / 5 / tabela inteira | **5** (M1 + 4 contrastantes); expandir só depois de G2 | antes de BL-02.05 | F01 |
| D-02 | Layout e fluxo de 3 min | — | Trilha: S02 busca → S03 M1 (origem + lacunas) → S04 comparação + gráfico → S05 pergunta O₂ + pergunta Marte | G1 | BL-07 |
| D-03 | **Provedor e chave de LLM; política offline** | provedor com chave da equipe / nenhum | Decidir na 1ª hora. Modo `cache` padrão na demo | **imediato** | BL-05.04+ |
| D-04 | Mídia oficial | — | Buscar em PSI-25/NASA; só com licença | G2 | BL-08.02 |
| D-05 | Go/no-go FDS | — | Pré-condição BL-09.00; go/no-go às 09h de 15/11 | 15/11 09h | slide 07 |
| D-06 | Congelamento de escopo e claims | — | G3 (funcionalidades) e G5 (roteiro) | ver 08 | pitch |
| D-07 | Eixos de estado (DIV-01) | campo único DM / três eixos | **Três eixos** | antes de BL-02.01 | contrato |
| D-08 | Repositório (remote, visibilidade) e localização do protótipo | — | GitHub da equipe; pedir o protótipo a quem o escreveu | imediato | F00 |
| D-09 | O PDF entra no git? | sim / só hash | sim, se o tamanho e os termos permitirem | BL-01.04 | — |
| D-10 | Idioma das respostas da IA | PT / PT+citação EN | PT com o trecho citado em EN | BL-05.05 | — |

## 4. Hipóteses assumidas neste plano
- H-1: a Tabela 5.1 do NASA/TM-20210011385 é texto selecionável (não imagem). Verificar no BL-02.04.
- H-2: há pelo menos 4 outros ensaios na Tabela 5.1 com os mesmos campos de M1.
- H-3: a equipe tem pelo menos 2 pessoas capazes de conferir valores no PDF.
- H-4: a máquina de demo é Windows, com Python 3.12 e Node ≥18.
- H-5: a demo pode rodar em `127.0.0.1` sem restrição da rede do evento.

## 5. Critérios para reduzir ou ampliar o escopo
| Situação | Ação |
|---|---|
| G1 não alcançado até o fim da tarde de 14/11 | Cortar BL-08 inteiro e F08; reduzir para 3 ensaios |
| D-03 sem solução até G1 | IA só com cache gerado em outro ambiente; se não houver nenhum, P-05/P-06 BLOQUEADO e o reforço vai para ranking + comparação (os verbos classificar e interpretar via regras) |
| G2 alcançado com folga antes da meia-noite | Liberar BL-08.01 (esquema), BL-02.12 (crosscheck) e, por último, F08 documental |
| FDS VERIFIED + §5.5 com dimensões do duto | Liberar BL-09.04 (escoamento frio) com time-box |
| Qualquer teste MUST falha após G3 | Remover a funcionalidade da trilha e rebaixar o status em 06; não corrigir ao vivo |
