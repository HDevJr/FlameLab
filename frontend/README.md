# Frontend — protótipo navegável (v2)

React 18 + TypeScript + Vite. **Protótipo para validar a jornada**, não o design final.

| Tela | Rota | Função |
|---|---|---|
| S01 Biblioteca | `/` | documentos e experimentos do catálogo (curados e importados) |
| S02 Importação | `/importar` | upload de PDF; estados reais de cada etapa |
| S03 Enriquecimento | `/documentos/:id/enriquecimento` | NTRS / PSI / TechPort, razões, divergências, operações de API |
| S04 Revisão | `/experimentos/:id` | condições × resultados observados, estado de revisão, lacunas, prontidão FDS |
| S05 Alteração | `/experimentos/:id/alterar` | formulário gerado do modelo; original × novo; cenário derivado |
| S06 Execução | `/simulacao/:scenarioId` | estado real da tarefa (fila → FDS → renderização) |
| S07 Resultado | `/execucoes/:runId` | vídeo MP4, HRR, parâmetros alterados, proveniência |

Regras de interface: dado real, em revisão, de teste e demonstrativo têm selos distintos; todo resultado de simulação traz o rótulo “teste de integração / hipótese computacional”; nada é animado sem corresponder a um estado do backend. Não há modo demonstrativo no frontend (testes usam executor simulado no backend).

`npm install` · `npm run dev` (backend em `127.0.0.1:8000`) · `npm run typecheck` · `npm test` · `npm run build`.
