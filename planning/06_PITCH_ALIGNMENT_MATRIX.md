# 06 — PITCH_ALIGNMENT_MATRIX

> Fonte única de status para desenvolvimento e pitch. **Atualizar a cada gate (G0–G6)**: quem muda o status anexa a evidência em `docs/evidence/`.
> Estado em 14/11/2026, início do planejamento.

## 1. Estados de comunicação
| Estado | Como falar no pitch |
|---|---|
| **IMPLEMENTADO_E_TESTADO** | Tempo presente: "o FlameLab mostra…". |
| **IMPLEMENTADO_NAO_VALIDADO** | Tempo presente **com a limitação dita junto**: "…em versão exploratória, ainda não validada". |
| **EM_DESENVOLVIMENTO** | Não anunciar como pronto: "estamos construindo…". |
| **PLANEJADO** | "O próximo passo é…". |
| **EVOLUCAO_FUTURA** | Slide de roadmap: "a visão inclui…". |
| **BLOQUEADO** | "Depende de <dado/validação>; por isso não afirmamos <X>". |

**Regra de promoção para IMPLEMENTADO_E_TESTADO:** testes listados em PASS **e** captura real **e** o item aparece na trilha T-12.

## 2. Matriz

| # | Requisito | O que será demonstrado | Status inicial | Evidência necessária | Pode ser "pronto" quando | Captura/gráfico | Se incompleto, dizer | Slides |
|---|---|---|---|---|---|---|---|---|
| P-01 | M-1 Catálogo BASS-II | lista de ensaios da Tabela 5.1 com fonte | **EM_DESENVOLVIMENTO**: dataset com só M1 (backend); catálogo/UI não existem | T-01, T-21, `curation_log` | G1 | S02 com lista | "Começamos pela investigação BASS-II; os dados estão em curadoria." | 04, 05 |
| P-02 | M-2 Ficha M1 rastreável | clicar em 0,071 mm/s e ver Tabela 5.1/linha/página | **BLOQUEADO (revisão humana)**: 9 registros com página/tabela/linha/coluna e trecho, verificação automática 10/10 MATCH, mas **0/9 conferidos**; UI não existe | T-01, T-24, T-19 | G1 | S03 com popover aberto | "Estamos conferindo cada valor no PDF original antes de exibi-lo." | 05, 06 |
| P-03 | M-3 Lacunas | painel "O que não sabemos" | **Backend: IMPLEMENTADO_E_TESTADO** (12 lacunas de M1 com onde foram procuradas); UI PLANEJADO | T-02 | G1 | GapsPanel | "Mapeamos as lacunas do DM; a tela está em construção." | 06 |
| P-04 | M-4/M-5 Busca + ranking explicável | "parecidos com M1" com critérios | PLANEJADO | T-13, T-14, T-25 | G2 | S02 com RankExplanation | "Ranking por critérios explícitos em desenvolvimento." | 05 |
| P-05 | M-6 Assistente citado | pergunta sobre O₂ de M1 → resposta citada | **Backend: IMPLEMENTADO_NAO_VALIDADO** (14/11). Gemini real + verificador V1–V8 PASS **só com evidência sintética**. **Com dados BASS-II: BLOQUEADO** até a curadoria BL-02; UI S05 PLANEJADO | T-03, T-15, T-16, golden set | G2, com o modo dito em voz alta (LIVE ou CACHE) | S05 com citação | Sem LLM: "O assistente está implementado com verificação de citações; nesta demonstração ele opera sem IA ao vivo." **Só se o verificador e a UI estiverem PASS.** | 05, 06 |
| P-06 | M-6 Abstenção | pergunta de Marte → "não há base" | **Backend: IMPLEMENTADO_NAO_VALIDADO** (14/11). Abstenção por extrapolação e por dado ausente funcionou no Gemini real com evidência sintética, incluindo 1 afirmação bloqueada (V8). Falta dataset real + UI | T-06 | G2 | S05 abstenção (até a UI existir: trecho do JSON de `docs/evidence/smoke_gemini_20261114T184309Z.json`, **rotulado "teste com evidência sintética"**) | "O verificador já bloqueia previsões sem base em testes; a tela está em construção." | 06 |
| P-07 | M-7 Comparação | M1 × outro, com aviso de causalidade | PLANEJADO | T-05 | G2 | S04 | "Comparação lado a lado em construção." | 05 |
| P-08 | M-8 Gráfico observado | propagação × fluxo, rotulado NASA | PLANEJADO | T-10b, T-27 | G2 | gráfico com badge | "Gráfico em construção a partir da Tabela 5.1." | 05, 06 |
| P-09 | M-9 Modo offline/degradado | desligar rede/IA e seguir navegando | PLANEJADO | T-09 | G3 | — (pode ir para resposta à banca) | — | Q&A |
| P-10 | M-10 Trilha completa ≤3 min | demo ao vivo ou vídeo | PLANEJADO | T-12 | G3/G4 | vídeo fallback | Usar o vídeo gravado, dizendo que é gravação. | 05 |
| P-11 | S-1 Esquema do aparato | SVG rotulado conceitual | PLANEJADO | T-17 | G3 | SVG com badge | Omitir. | 04 |
| P-12 | S-2 Mídia NASA | imagem/vídeo oficial com crédito | PLANEJADO / depende de D-04 | licença registrada | G3 | mídia + crédito | Omitir; **não substituir por imagem gerada sem rótulo**. | 02, 05 |
| P-13 | S-5 Verificador do PDF | relatório MATCH da Tabela 5.1 | **IMPLEMENTADO_E_TESTADO só para M1** (camada de texto, 10/10 MATCH) | T-04, T-08 | G3 | trecho do relatório | **Não mencionar extração automática.** "Transcrição curada e conferida por duas pessoas." | 06 (opcional) |
| P-14 | Extrator do PDF completo | — | **EVOLUCAO_FUTURA** (protótipo anterior NOT_VERIFIED, ausente do repositório) | — | — | — | "A extração automática de documentos completos faz parte da evolução." | 09 |
| P-15 | FDS no outro computador | caso básico rodou, temperatura no Smokeview | IMPLEMENTADO_E_TESTADO **em outro ambiente** (relato da equipe; precisa de captura/log) | print/log do outro computador | já, **se houver captura** | print Smokeview **rotulado "caso genérico de teste, não BASS-II"** | "Confirmamos que conseguimos operar o FDS num caso básico." | 07 |
| P-16 | FDS no ambiente do projeto | — | **NOT_VERIFIED** → BLOQUEADO até a auditoria | T-00f, auditoria | após F00.A VERIFIED | — | Não mencionar como integrado. | 07 |
| P-17 | X-1 Prontidão FDS (G1) | checklist de gates e lacunas de M1 | PLANEJADO (STRETCH) | gates G1 documentados | G1 científico PASS | S06 | "Mapeamos o que falta para tentar reproduzir M1 em FDS." | 07 |
| P-18 | X-2 Escoamento frio | campo de velocidade em geometria aproximada | PLANEJADO (STRETCH) | T-28, G1+G3 | PASS + revisão CIÊNCIA | gráfico com badge "Simulação exploratória" | Omitir. | 07 |
| P-19 | X-3 Reprodução de M1 | — | **BLOQUEADO** (G2 sem propriedades de PMMA; G4 sem comparação) | G2+G4 | não esperado no hackathon | — | "Ainda não reproduzimos M1. A seção 5.5 do relatório mostra que até a modelagem original teve discrepâncias; tratamos isso como pesquisa." | 07, 09 |
| P-20 | Variação de parâmetro / novos cenários | — | EVOLUCAO_FUTURA | G5 | — | — | Roadmap, sempre como "hipótese computacional". | 09 |
| P-21 | Indicador de segurança de nave | — | **Proibido** | — | nunca | — | "O FlameLab não certifica segurança." | 08, 10 |
| P-22 | Independência da NASA | aviso no app e no slide | PLANEJADO | rodapé visível | G1 | rodapé | — | 10, Q&A |

## 3. Frases permitidas e proibidas (até nova evidência)
| ✅ Permitido hoje | ❌ Proibido sem evidência |
|---|---|
| "Selecionamos BASS-II e o ensaio M1 da Tabela 5.1 do NASA/TM-20210011385." | "Reproduzimos o experimento M1." |
| "Conseguimos executar um caso básico de FDS + Smokeview." (com print) | "O FDS está integrado ao FlameLab." |
| "O FlameLab foi projetado para não inventar números." (intenção) | "Nossa IA nunca erra." / "100 % preciso." (o valor de 100 % é **meta**, DM §18) |
| "Projeto independente, criado para o NASA Space Apps." | "Ferramenta da NASA" / "validado pela NASA". |
| — | "Extraímos automaticamente os dados do PDF." (até T-04/T-08 PASS **e** isso estar no fluxo) |

## 4. Slides × dependência técnica
| Slide (DM §19.1) | Pode ser feito já? | Depende de |
|---|---|---|
| 01 Hook | Sim. Imagem conceitual **rotulada** | — |
| 02 Problema | Sim | links PSI/NTRS |
| 03 Desafio | Sim. Conferir a grafia oficial do título (DIV-12) | — |
| 04 Solução | Sim. Diagrama de fluxo (não é print) | — |
| 05 Demonstração | **Não** | P-01, P-02, P-04, P-05, P-07, P-08 em IMPLEMENTADO_E_TESTADO (G2/G3) |
| 06 Confiança | **Não** | P-03, P-06 (G2) |
| 07 Diferencial | Rascunho em duas versões (A: com P-17/P-18; B: roadmap) | decisão go/no-go FDS (08: 15/11 09h) |
| 08 Impacto | Sim, sem números de impacto inventados | — |
| 09 Evolução | Sim | — |
| 10 Encerramento | Sim | — |

## 5. Registro de mudanças de status
| Data/hora | Item | De → Para | Evidência | Quem |
|---|---|---|---|---|
| 14/11 | P-15 | — → IMPLEMENTADO_E_TESTADO (outro ambiente) | relato da equipe; captura pendente | equipe |
| 14/11 | P-16 | — → NOT_VERIFIED | binários FDS6/SMV6 presentes nesta máquina; `fds -version` sem saída no Git Bash | planejamento |
| 14/11 | P-14 | — → EVOLUCAO_FUTURA | protótipo ausente do repositório | planejamento |
| 14/11 | P-05, P-06 | PLANEJADO → IMPLEMENTADO_NAO_VALIDADO (backend, evidência sintética) | `docs/evidence/BL-05_assistente_ia.md`; 66 testes PASS (simulado); smoke Gemini real PASS 3/3 (sintético) | BL-05 |
| 14/11 | P-02 | PLANEJADO → BLOQUEADO (revisão humana) | `docs/curation/BASS2-M1_curation_report.md`; crosscheck 10/10 MATCH; 0/9 CONFERIDO_FONTE | BL-02 |
| 14/11 | P-03 | PLANEJADO → backend IMPLEMENTADO_E_TESTADO | `data/gaps/BASS2-M1.json` (12 lacunas) | BL-02 |
| 14/11 | P-05/P-06 | backend agora lê o dataset real; abstém-se com `PENDING_REVIEW` / `MISSING_DATA` (Gemini real) | `docs/evidence/smoke_real_dataset_20261114T191858Z.json` | BL-02 |

> **Frase permitida a partir de 14/11 (P-05/P-06):** "Nosso assistente usa o Gemini, mas toda resposta passa por um verificador automático que bloqueia números sem evidência, mistura de ensaios e previsões fora dos dados. Já testamos isso com dados de teste." **Proibido:** dizer que a IA já responde sobre o BASS-II ou o M1, ou mostrar o JSON sintético como se fosse dado da NASA.

## 6. Para o pitch: o que está verificado e o que está pendente (14/11, BL-02)
| Informação | Situação | Pode ser dito? |
|---|---|---|
| O PDF usado é o NASA/TM-20210011385, com hash conferido | **VERIFICADO** (SHA-256 recalculado = registrado) | Sim: "trabalhamos sobre o arquivo original, com integridade verificada por hash" |
| Tabela 5.1 = p. 57 impressa / p. 65 do PDF; M1 com os 8 campos do DM | Extraído e verificado **automaticamente** contra o texto do PDF; **não conferido por pessoa** | Só como "extraído, em revisão". Não diga "conferido" |
| Valores de M1 (1 mm; 2,2 cm; 1 face; 9 cm/s; 0,071 mm/s; 6,4 min; 22,2 → 21,9 vol%) | EXTRAIDO_NAO_REVISADO | **Não apresentar como dado conferido.** Pode aparecer como "valor extraído da Tabela 5.1, aguardando revisão" |
| Material PMMA | EXTRAIDO_NAO_REVISADO (texto §5.3/§5.1, não coluna da tabela) | Idem |
| Experimento na ISS / MSG, em microgravidade | EXTRAIDO_NAO_REVISADO (§5.1) | Contexto geral ok, com a fonte |
| 12 lacunas para reprodução no FDS (pressão, temperatura, duto, pirólise…) | Registradas, com onde foram procuradas | **Sim**: "mapeamos o que falta para reproduzir M1" |
| A IA lê o dataset real e não inventa | Gemini real: pressão → "ausente"; propagação → "consta na fonte, aguarda revisão", sem número | Sim, descrevendo **exatamente** isso |
| Divergência interna da fonte (largura "1 or 2 cm" no texto × 2,2 cm na tabela) | Registrada como ressalva | Opcional, como exemplo de rigor |

> **Frase permitida (BL-02):** "Carregamos o relatório BASS-II original, verificamos sua integridade e estruturamos o ensaio M1 com página, tabela e coluna de cada valor. Antes de qualquer número ser usado, ele passa por revisão humana; enquanto isso não acontece, o assistente diz que o dado existe e está em revisão, sem citá-lo."
> **Proibido até a revisão:** "dados conferidos", "valores validados", ou mostrar 0,071 mm/s como resposta da IA.
