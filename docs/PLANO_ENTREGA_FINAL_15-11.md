# Plano até a entrega final — 15/11/2026

> Escrito às ~10h15 de 15/11. Complementa `planning/08_HACKATHON_EXECUTION_PLAN.md` (não o substitui) com o estado real de hoje. **Horários oficiais (pré-apresentação 15h30, submissão local 17h, prazo geral 23h59) são do planejamento e precisam ser confirmados com a organização (DIV-09).** Os demais horários são propostas. Responsáveis por trilha: a atribuir.

## 1. Onde estamos (verificado no repositório)

| Camada | Estado | Fonte |
|---|---|---|
| Dataset M1 | 9 registros `CONFERIDO_FONTE` (revisor registrado), 12 lacunas, evidências com página/tabela/linha | `data/` |
| Backend | API, assistente com verificador V1–V8, importação, enriquecimento NASA, worker FDS; testes automatizados | `backend/`, README |
| Assistente com dados reais | Smoke real feito em 14/11 **antes** da revisão (9 valores retidos). **Cache e golden set reais ainda não gerados** com os registros agora conferidos | `docs/evidence/BL-05_assistente_ia.md`, BL-05.06/.09 |
| Frontend real | Protótipo React navegável; **validação visual NOT_RUN** | `frontend/README.md` |
| Protótipo de design | HTML em `prototypes/` com ficha M1, assistente, FDS; não ligado à API | `prototypes/` |
| Telemetria / Wokwi | **Nenhum CSV nem arquivo Wokwi no repositório** | busca no repo |
| FDS | Caso genérico verificado; **reprodução do M1 bloqueada** (G1, G2, G4) | `fds/README.md`, `planning/05 §6` |
| Não implementado | busca/ranking, comparação lado a lado, relatório S07, vídeo de fallback | README, backlog |
| Auditoria de integridade | 14 registros DYLCO com revisão legada, 3 com bloqueios; nada promovido automaticamente | `docs/evidence/BL-15_*` |

## 2. Decisões que precisam ser tomadas agora (≤ 10 min)

1. **FDS: NO-GO para reprodução do M1.** O go/no-go das 09h já passou e as lacunas G1/G2 seguem abertas. Mostrar apenas o checklist de prontidão e, se houver, o caso genérico rotulado "ambiente genérico". Sem alegar reprodução.
2. **Interface da demo.** Recomendado: levar tokens e a ficha M1 do protótipo para o frontend real, com limite de 90 min. Se não estiver pronto às 12h30, demonstrar o frontend atual e apresentar o protótipo como "proposta de interface" rotulada.
3. **Telemetria.** Confirmar se o projeto Wokwi existe fora do repositório. Se existir, exportar um CSV real e versionar em `docs/evidence/` com o código e o diagrama. Se não, a telemetria entra no pitch como **pendente**, sem gráficos fabricados.

## 3. Cronograma

| Quando | Marco | O que precisa estar pronto (critério verificável) |
|---|---|---|
| 10h15–10h30 | Decisões da §2 | Registradas em `docs/decisions.md` ou neste arquivo |
| 10h30–12h30 | **Trilhas em paralelo** (ver §4) | Cada trilha entrega sua evidência |
| **12h30** | **G3 — congelamento** | Tag `demo-v1`; `pytest -q backend/tests` e `npm run typecheck && npm test && npm run build` passam; `dataset_version` anotado. Depois disso, só correção crítica (crash, dado errado, texto proibido) |
| 12h30–13h30 | QA e evidências | T-12 (roteiro de clique) executado 2×, por quem não desenvolveu; capturas definitivas |
| **13h30** | **G4 — demo pronta** | Vídeo de fallback gravado e reproduz offline; README final; capturas em `docs/evidence/` |
| **14h30** | **G5 — roteiro congelado** | Revisão cruzada roteiro × `planning/06` por pessoa que não escreveu o roteiro |
| 14h30–15h30 | Ensaio | Pitch cronometrado, com plano B testado (modo `cache`, depois `off`, depois vídeo) |
| **15h30** | Pré-apresentação | — |
| **antes das 17h** | **G6 — submissão local** | Enviada; link conferido; print da submissão |
| 23h59 | Prazo geral | Só correção de submissão, se necessário |

## 4. Trilhas entre 10h30 e 12h30

### A. Dados e ciência
- Revisar os 9 registros M1 contra as ressalvas já registradas (largura 1 ou 2 cm no texto × 1,2 e 2,2 cm na tabela; O₂ só no início e no fim). Não promover nem rebaixar nada sem decisão humana.
- Atualizar o texto do README: ainda diz "9 registros aguardam revisão", o que já não é verdade.
- Fora do pitch: DYLCO e os 3 registros com bloqueio (ver BL-15).

### B. Assistente (precisa de `GEMINI_API_KEY` local, nunca em chat nem no Git)
- Gerar o cache e o golden set com os registros agora conferidos: 4 perguntas do documento mestre §10.1 + 4 adversariais, incluindo Marte.
- Rodar `scripts/smoke_gemini_real_dataset.py` e guardar o relatório em `docs/evidence/`.
- Definir `FLAMELAB_LLM_MODE=cache` como padrão da demo e testar também `off`.
- Estado do prompt v1 permanece **IMPLEMENTADO_NAO_VALIDADO** até revisão científica; dizer isso, se perguntado.

### C. Frontend
- P0: tokens, `AppShell`, ficha M1 com condições, resultados, lacunas e referência por parâmetro (usar `prototypes/styles.css` e `components.js` como base; reaproveitar `frontend/src/pages/Review.tsx`).
- P0: aviso de independência visível; layout legível em celular.
- P1: tela do assistente com resposta respaldada e abstenção; tela de prontidão FDS sem botão de execução ativo.
- Executar `docs/manual_test_roteiro_S01-S07.md` e registrar o resultado (troca o `NOT_RUN`).

### D. Pitch e QA
- Atualizar `planning/06_PITCH_ALIGNMENT_MATRIX.md`: cada frase só no presente se o item estiver IMPLEMENTADO_E_TESTADO.
- Roteiro de demo ≤ 3 min: lista de experimentos → ficha M1 → "Fonte" de um valor → lacunas → assistente respaldado → abstenção (Marte) → prontidão FDS bloqueada.
- Capturas reais e vídeo de fallback.

## 5. O que pode e o que não pode ser dito

| Pode (com evidência) | Não pode |
|---|---|
| Ficha do M1 com valores conferidos e página/tabela de origem | "Reprodução fiel do ensaio M1" |
| Lacunas declaradas como `AUSENTE` | Preencher lacuna com estimativa |
| Assistente cita, verifica e se abstém (resposta gravada/em cache, dita como tal) | "A IA prevê incêndios" ou "simula o fogo" |
| FDS/Smokeview verificados em caso **genérico** | Vídeo FDS como se fosse do M1 |
| Protótipo de interface, identificado como proposta | Telemetria ou gráfico sem dado real |
| "Projeto independente, não endossado pela NASA" | "Aprovado pela NASA", "simulação oficial" |

## 6. Ordem de corte se o tempo apertar
1. Tela de telemetria (mostrar só a estrutura do CSV, rotulada pendente).
2. Port do design para o frontend real (usar o protótipo como proposta).
3. Tela de prontidão FDS vira slide.
4. Assistente ao vivo vira cache/gravado.

**Nunca cortar:** conferência e origem dos valores, lacunas visíveis, verificador/abstenção, aviso de independência, plano B de demo (cache → off → vídeo).

## 7. Riscos de hoje
| Risco | Resposta |
|---|---|
| Gemini indisponível ou cota | modo `cache` (padrão), depois `off`; dizer em voz alta que a resposta é reproduzida do cache |
| Dado errado descoberto após 12h30 | remover da trilha e regenerar; rodar testes; não "corrigir" número sem revisão humana |
| Notebook trava | vídeo de fallback |
| Rede da sede | `FLAMELAB_NASA_MODE=fixture`; nada na demo depende de internet em `cache`/`off` |
| Segredo vazado | `.env` e chaves nunca no Git nem no chat da equipe |
