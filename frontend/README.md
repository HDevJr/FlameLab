# Frontend — protótipo navegável (v2.1)

React 18 + TypeScript + Vite. **Protótipo para validar a jornada**, não o design final.

| Tela | Rota | Função |
|---|---|---|
| S01 Experimentos NASA | `/` | documentos e experimentos do catálogo (curados e importados) |
| S02 Importação | `/importar` | upload de PDF; 8 etapas legíveis com tempo real, limitações e detalhes técnicos; resumo ao final |
| Resumo da análise | `/documentos/:id/analise` | origem NASA × revisão × enriquecimento, cobertura de páginas, prontidão FDS, o que não está validado |
| S03 Fontes NASA | `/documentos/:id/enriquecimento` | NTRS / PSI / TechPort, razões, divergências, operações de API (enriquecimento ≠ validação) |
| S04 Revisão | `/experimentos/:id` | condições × resultados observados; painel de origem e **revisão humana** por parâmetro |
| S05 Alterar parâmetros | `/experimentos/:id/alterar` | hipóteses sobre condições **do experimento** (só numéricas com unidade); original × novo |
| Demonstração FDS | `/demonstracao-fds` | caso genérico **independente de qualquer artigo** |
| S06 Execução | `/simulacao/:scenarioId` | estado real, tempo decorrido, progresso físico do FDS quando informado, tempos medidos |
| S07 Resultado | `/execucoes/:runId` | player (pausa, repetir, 0,25×–2×, linha do tempo, tela cheia), HRR, tempos, proveniência |

Regras de interface: dado real, em revisão, de teste e demonstrativo têm selos distintos; todo resultado de simulação traz o rótulo “teste de integração / hipótese computacional”; nada é animado nem estimado sem corresponder a um estado do backend; termos técnicos têm explicação (“?”).

Comandos: `npm install` · `npm run dev` (backend em `127.0.0.1:8000`) · `npm run typecheck` · `npm test` (vitest + jsdom) · `npm run build`.
Validação visual: **NOT_RUN** até uma pessoa executar `docs/manual_test_roteiro_S01-S07.md`.
