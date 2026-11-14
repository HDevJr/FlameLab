# FDS — worker isolado e casos aprovados

**Política vigente: [planning/09](../planning/09_ADR_NASA_ENRICHMENT_FDS_SMOKEVIEW.md) (substitui a execução manual da F00).**

- O servidor web **não calcula**. Um worker (thread + processos filhos) executa FDS → Smokeview → FFmpeg para arquivos gerados pelo `FDS Case Builder` (`backend/app/simulation/case_builder.py`) a partir de parâmetros numéricos validados.
- A aplicação **não aceita** FDS, caminhos, executáveis nem argumentos do usuário ou da IA.
- Modelo executável hoje: `fds-integration-simple-fire`, **teste de integração** derivado do exemplo oficial `Examples/Fires/simple_test.fds` do FDS 6.11.1 (queimador de propano em sala). **Não é reprodução de nenhum experimento NASA.**
- Modelo de reprodução de propagação de chama (BASS-II): **BLOQUEADO** (lacunas científicas, revisão humana pendente).
- Execuções ficam em `var/runs/<RUN-id>/` (não versionado). Evidências curadas: `docs/evidence/sim_RUN-*/`.
