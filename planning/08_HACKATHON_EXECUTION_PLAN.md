# 08 — HACKATHON_EXECUTION_PLAN

> Plano 0.1 · 14/11/2026 · NASA Space Apps 2026, Rio Verde-GO, 14–15/11.
> **Horários:** os marcos fixos vêm do DM §14 (pré-apresentações a partir de 15h30 de 15/11; submissão local às 17h; prazo geral 23h59). **Todos a confirmar com a organização (DIV-09).** Os demais horários são **propostas de planejamento** e não refletem a agenda real da equipe.
> Este plano está sendo escrito na janela "14/11 manhã" do DM, portanto o G0 = aprovação deste plano + decisões D-01/D-03/D-07/D-08.

## 1. Menor caminho até um MVP utilizável
`auditoria → repositório/esqueleto → schema → M1 conferido → API → ficha S03 com origem e lacunas → +4 ensaios → comparação + gráfico → busca/ranking → assistente (cache/live) → trilha T-12`

## 2. Marcos (gates)

| Gate | Quando (proposta) | Critério de passagem (verificável) | Evidência | Pitch libera |
|---|---|---|---|---|
| **G0** Escopo | 14/11 até ~11h | plano aprovado; D-01, D-03, D-07, D-08 decididos; auditoria F00.A feita | `docs/decisions.md`, `environment_audit.md` | slides 01–04 e 08–10 |
| **G0.5** Esqueleto | 14/11 ~13h | T-00a–f PASS; PDF + hash | prints, commit | — |
| **G1** Fluxo mínimo sem IA | 14/11 ~19h | M1 + ≥2 ensaios CONFERIDO_FONTE; S03 com origem e lacunas; T-01, T-02, T-07, T-20, T-21, T-24 PASS | `test_run_G1.md`, print S03 | P-01, P-02, P-03 → IMPLEMENTADO_E_TESTADO |
| **G2** Ponta a ponta | 14/11 ~01h | 5 ensaios; busca/ranking; comparação + gráfico; assistente em LIVE ou CACHE; golden set PASS; T-03, T-05, T-06, T-10b, T-13–T-16, T-26 PASS | `golden_*.md`, prints | P-04 a P-08 |
| **FDS go/no-go** | 15/11 09h | BL-09.00 + G1/G3 científicos ou não | `fds_readiness` | slide 07 versão A ou B |
| **G3** Congelamento de funcionalidades | 15/11 ~11h | T-09, T-12 (2×) PASS; tag `demo-v1`; dataset congelado | tag, `test_run_G3.md` | P-09, P-10 |
| **G4** Demo pronta | 15/11 ~13h30 | vídeo fallback; README final; T-29 PASS; capturas definitivas | vídeo, README | slides 05–07 com prints reais |
| **G5** Roteiro congelado | 15/11 ~14h30 (antes de 15h30) | revisão cruzada roteiro × matriz 06 | checklist assinado | — |
| **G6** Entrega local | 15/11 antes de 17h | submissão enviada, link conferido | print da submissão | — |

Depois do **G3, só correções críticas** (crash, dado errado, texto proibido). Nenhuma funcionalidade nova.

## 3. Cronograma por trilha (propostas)

| Janela | DADOS/CIÊNCIA | BACK | IA | FRONT | PITCH/QA | SIM |
|---|---|---|---|---|---|---|
| 14/11 manhã (até G0/G0.5) | baixar PDF, hash, page_map; ler a Tab. 5.1 e propor ensaios (D-01) | auditoria, repositório, venv, health | **D-03**: provedor, chave, 1ª chamada | Vite + layout base | slides 01–04; README v0 | — |
| 14/11 tarde (até G1) | transcrever + conferir M1, depois 2 ensaios; gaps.json | schema, units, store, rotas de catálogo | `numbers.py` + verificador (testes com respostas fabricadas) | S02/S03, popover, lacunas | roteiro v0 com marcadores [EVIDÊNCIA] | — |
| 14/11 noite (até G2) | +2 ensaios conferidos; extract_passages; revisar textos da UI | busca/ranking, comparação, viz | orquestrador, adaptador, prompt, cache, golden set | S04, gráfico, S05 | capturas G1; slides 05–07 rascunho A/B | (só se G1 passou) ler §5.5, readiness G1, time-box 4 h |
| 15/11 manhã (até G3) | revisão científica final; T-29 | testes, correções | gerar/verificar o cache das perguntas da demo | polimento; esquema SVG (SHOULD) | T-12 2×; T-09 offline | go/no-go às 09h; se GO: só importar o run já feito |
| 15/11 início da tarde (até G4/G5) | — | tag `demo-v1`, README | — | correções críticas | vídeo, prints finais, ensaio do pitch | — |
| 15/11 até 17h | — | — | — | — | pre-pitch 15h30; submissão (G6) | — |

## 4. Paralelismo
Do G0.5 em diante, quatro trilhas independentes (DADOS, BACK, IA, FRONT). O ponto de sincronização é o **contrato v1** (04), congelado no início da tarde de 14/11. O FRONT trabalha contra a API real servindo M1 em `EXTRAIDO_NAO_REVISADO` até a conferência terminar. Isso não é mock: é o dado real com o status real.

## 5. O que pode impedir a demo, e a resposta
| Ameaça | Resposta imediata |
|---|---|
| LLM indisponível na hora | `FLAMELAB_LLM_MODE=cache` (já é o padrão); dizer em voz alta "resposta gerada pela IA e verificada, reproduzida do cache" |
| Cache também falha | modo `off`: mostrar recuperação + ficha; dizer "IA indisponível neste momento"; seguir |
| Notebook trava | vídeo fallback (G4) |
| Dado errado descoberto após o G3 | remover o ensaio do dataset, regenerar, rodar T-01/T-21; se não der tempo, retirar da trilha |
| FDS falha | não está na trilha principal; o slide 07 versão B já está pronto |

## 6. Ordem de eliminação de escopo
Igual a [03 §5](03_DEVELOPMENT_BACKLOG.md): FDS → mídia/temporal → relatório S07 → crosscheck → esquema → reduzir ensaios para 3. **Nunca:** conferência, origem, lacunas, explicação do ranking, verificador, comparação com aviso, T-12.

## 7. Contingência: IA ou FDS não funcionam na apresentação
- **IA:** a demo foi desenhada para mostrar o *verificador* e a *abstenção* como valor, e não a fluência do texto. Mesmo em cache, a mensagem central ("cita, verifica e se abstém") se mantém e pode ser comprovada.
- **FDS:** nunca está na trilha ao vivo. No máximo um print rotulado de um run pré-executado (P-18), ou o checklist (P-17), ou nada (versão B).

## 8. Rotina de sincronização desenvolvimento × pitch
- Em cada gate: o responsável técnico registra a evidência e atualiza [06](06_PITCH_ALIGNMENT_MATRIX.md) (seção 5).
- PITCH só passa uma frase para o tempo presente depois de o item estar IMPLEMENTADO_E_TESTADO na matriz.
- Revisão cruzada roteiro × produto: em G4, G5 e imediatamente antes de G6, feita por uma pessoa que não escreveu o roteiro.

## 9. Critério de congelamento do MVP (G3)
1. Todos os T-xx MUST em PASS, com registro.
2. T-12 executado 2× seguidas por quem não desenvolveu.
3. Tag `demo-v1` criada e `dataset_version` anotado no slide 05 e no README.
4. Matriz 06 atualizada, sem item na trilha em estado inferior a IMPLEMENTADO_E_TESTADO (exceto se for dito explicitamente como IMPLEMENTADO_NAO_VALIDADO).
