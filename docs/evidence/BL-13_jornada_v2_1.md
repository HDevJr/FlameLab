# Evidências — Jornada v2.1 (correções após o teste manual do protótipo)

- Data: 14–15/11/2026 · Branch `feat/arq-v2-nasa-fds-prototipo` (HEAD inicial `ccc2450`). Nada enviado nem integrado.
- Decisões: [planning/09 §11](../../planning/09_ADR_NASA_ENRICHMENT_FDS_SMOKEVIEW.md). Tudo da simulação continua rotulado **teste de integração — não é reprodução de experimento NASA**.
- **Validação visual por pessoa: NOT_RUN** (roteiro em [manual_test_roteiro_S01-S07.md](../manual_test_roteiro_S01-S07.md); modelo de registro em [manual_validation_visual_TEMPLATE.md](manual_validation_visual_TEMPLATE.md)).

## 1. Problemas do teste manual → o que mudou
| # | Relato | Causa encontrada | Correção | Verificação |
|---|---|---|---|---|
| 1–2 | Upload, leitura, consulta NASA, procedência e extração sem explicação | Etapas técnicas (`HASH`, `NASA_LOOKUP`…) com texto cru | 8 etapas legíveis (recebido → identificando → origem NASA → lendo → extraindo → fontes complementares → comparando → relatório), cada uma com resumo, **limitação**, **detalhes técnicos expansíveis** e **tempo medido** | `test_import_steps_are_readable_and_timed`; execução real |
| 3 | “só 14 de 32 páginas” | Limite fixo da v2 (`MAX_PAGES_SENT = 14`) | **Lotes** (≤ 12 págs./40 mil caracteres), cobertura com páginas lidas/não lidas/sem texto e motivos; DYLCO agora lido **por inteiro (1–32)** | `test_batched_extraction_*`, medição real (§3) |
| 4, 10 | Excesso de informação técnica; não entende o que foi encontrado | Sem síntese | **Resumo da análise**: conclusões em frases + 4 cartões; avisos “o que não está validado”; glossário; logs só em áreas expansíveis | `test_analysis_summary_*` |
| 5 | Muitos “não revisados” sem como revisar | Só havia o script | **Painel de revisão** em cada parâmetro (política única `check_review`) | `test_review_api.py` (20) + componente |
| 6 | Esperas longas | Ver §4 (medições) | Estados reais + tempo decorrido + progresso físico do FDS | `test_running_run_reports_real_fds_progress…` |
| 7–8 | Experimento NASA abria os parâmetros de um queimador | A tela S05 usava o modelo de integração para qualquer experimento | Caminhos separados **Experimentos NASA / Demonstração FDS**; a API **recusa** vincular o caso de integração a experimento; hipóteses só sobre condições do experimento | `test_generic_demo_is_never_linked…`, `pages.test.tsx` |
| 9 | Vídeo curto demais | 13 quadros para 5 s simulados (1 a cada 0,2 s, renderizando 1 em 2) ⇒ ~3,8× mais rápido | `DUMP NFRAMES = 10 × t_end`, todos os quadros renderizados, 10 fps ⇒ **1 s de vídeo = 1 s físico**; player com 0,25×/0,5×/1×/2× | execução real (§2), `test_video_is_real_time…` |

## 2. Execuções FDS reais (via API ao vivo, 10 s simulados)
| Execução | Parâmetros | FDS | Smokeview | MP4 | Total | Quadros | HRR máx. |
|---|---|---|---|---|---|---|---|
| `RUN-20261115010413-afeb` (caso-base) | HRRPUA 1000 | **74,7 s** | 4,6 s | 0,45 s | **80,1 s** | **101** | 185,7 kW |
| `RUN-20261115010534-1313` (derivado) | HRRPUA **500** | 67,0 s | 4,0 s | 0,45 s | 71,5 s | 101 | 86,7 kW |
- Vídeo: 101 quadros a 10 fps = **10,1 s para 10 s simulados** (razão 1,01). **Verificação independente do mapeamento:** o quadro 50 do Smokeview imprime `Time: 5.007` (`poster.png`), isto é, quadro *k* ≈ *k* × 0,1 s. Antes (v2): 13 quadros para 5 s ⇒ 1,3 s de vídeo (3,8× mais rápido).
- Versões: FDS-6.11.1-0-gff928db-release · SMV-6.11.2-0-g27cbe59-release · FFmpeg 9.0.2. Todos os artefatos responderam 200; `Range` retorna **206** (necessário para a linha do tempo).
- **Progresso físico real** (log do FDS): amostras a cada ~2 s em [live_run_samples_base_20261115.json](live_run_samples_base_20261115.json): 0,57 s → 1,34 → 1,60 → 1,90 → … → 8,66 s. O FDS libera o log em blocos (≈ 1 s simulado a cada 4–8 s de relógio), então o valor **avança em degraus** — por isso a interface mostra “tempo físico calculado X de T s” e **não** uma previsão de término.
- Artefatos e hashes: `sim_RUN-20261115010413-afeb/`, `sim_RUN-20261115010534-1313/` (as execuções da v2, de 5 s, ficam como referência histórica em `sim_RUN-2026111423*`).

## 3. Leitura do PDF em lotes — custo e viabilidade (Gemini real, `gemini-3.5-flash-lite`)
Medição **sem gravar nada** no dataset ([extraction_batches_*.json](.)); as propostas não foram conferidas por humano.
| Documento | Páginas (com texto) | Lotes | Tempo | Tokens (informados pelo SDK) | Aceitos / descartados | Cobertura |
|---|---|---|---|---|---|---|
| DYLCO (1998) | 32 (32) | 3 | **6,4 s** | 23 311 | 9 / 2 (duplicados) | **1–32 completa** |
| BASS-II (2021) | 144 (137) | 12 planejados | 34,0 s até o lote 10 | 106 354 | 63 / 26 | **parcial**: lidas 1–7, 9–109, 111–117; **QUOTA (429) no lote 11**; não lidas 118–141 |
- **Viável**: 1,6–4,8 s por lote de 21–36 mil caracteres (medido); o documento mais longo cabe em ~12 chamadas. Não se assume que uma única chamada baste.
- **Limite real encontrado:** o 429 apareceu no 11º lote. Depois dessa medição foi implementado **espera de 30 s + nova tentativa do mesmo lote**, com o tempo registrado; a segunda falha interrompe e marca as páginas restantes como **não lidas** (`test_quota_*`). **Não foi refeita a medição do BASS-II depois dessa mudança.**
- Custo em dinheiro **não é estimado** (a tarifa do plano não é conhecida por este código); só tokens.
- As referências de página são sempre as do PDF (`<page n>` real de cada lote); a citação de outra página/lote é descartada (`test_citation_from_another_batch_is_rejected`).

## 4. Importação real e operações bloqueantes (online + Gemini real)
| Documento | Total | RECEBIDO | IDENTIF. | ORIGEM | LENDO | EXTRAINDO | FONTES | COMPARANDO | RELATÓRIO |
|---|---|---|---|---|---|---|---|---|---|
| DYLCO (1,4 MB) | **15,1 s** | 16 ms | 202 ms | 4,2 s | 46 ms | 7,5 s | 3,1 s | 14 ms | 62 ms |
| BASS-II (49 MB, curado → IA pulada) | 12,6 s | 62 ms | 171 ms | **8,5 s** | 438 ms | — | 3,3 s | 31 ms | 31 ms |
- A etapa “origem” é dominada pelo **download do PDF do NTRS para comparar o hash** (49 MB ≈ 8 s).
- Corrigido durante a medição: o cronômetro da etapa era **reiniciado** a cada atualização “lote i de n” (extração aparecia com 1,4 s); agora conta do início ao fim (`test_step_timer_is_not_reset…`).
- **HTTP bloqueante?** `POST /api/imports` retorna em 0,7–1,2 s (grava, calcula hash, abre o PDF) e o resto roda em thread; `POST /api/simulations` retorna na hora (fila); leituras do catálogo 7–50 ms. **Exceção:** `POST /api/documents/{id}/enrichment` é **síncrono**: 4,4 s (BASS-II) e 5,9 s (DYLCO) online — no pior caso, a soma dos timeouts por fonte. A tela mostra “Consultando…”, mas a requisição fica aberta. Registrado como limitação (virar tarefa em segundo plano é a correção).
- **No navegador:** a importação consulta o servidor a cada 1 s; a execução, a cada 1 s; o vídeo carrega com `preload="auto"` e segue por `Range`. Não foram observados bloqueios, mas **a inspeção no navegador não foi feita (NOT_RUN)**.

## 5. Revisão humana — política e estado do M1
- Mesma função (`check_review`) para script, dataset curado e importado. Recusas testadas: valor/unidade/página divergentes, revisor = extrator, nome de IA, revisor vazio, hash do PDF diferente, evidência sem página/citação, estado diferente de “não revisado”, ausência da declaração de conferência.
- Regra nova (DIV-30): unidade **fora da tabela v1** (ex.: “degrees C”) exige valor igual **e o mesmo texto de unidade**.
- Dúvida/divergência **não alteram o dado**. Trilha em `var/audit/review_events.jsonl` (aprovadas, recusadas, dúvidas, divergências).
- **Estado do BASS-II M1: 0/9 conferidos** (`git status data/` sem alterações). Nenhum registro foi promovido nesta etapa.
- **Limitação (R-22):** o nome do revisor é digitado; não há autenticação.

## 6. Testes
[test_run_jornada_v2_1_20261115.txt](test_run_jornada_v2_1_20261115.txt): backend **218 passed, 1 skipped** (os 167 da v2 preservados + 51 novos; o skip é o mesmo `NOT_RUN` do assistente com registro real conferido por humano) · frontend **31 passed** (`lib`, componentes e telas com jsdom) · `tsc` sem erros · `vite build`.
| Resultado | Itens |
|---|---|
| PASS (simulado/fixture/jsdom) | revisão (20), jornada v2.1 (31), importação (17), simulação (25), enriquecimento (10), genericidade (1); player, painel de revisão, etapas, menu, estados longos, separação artigo × demonstração, vídeo persistente (31 no frontend) |
| PASS (real, registrado) | 2 execuções FDS→Smokeview→MP4, 2 importações online, 2 medições de leitura em lotes, tempos de endpoints |
| NOT_RUN | **validação visual das telas por pessoa**; medição do BASS-II completo após a espera por cota; resposta do assistente com registro real conferido por humano |
| FAIL | nenhum no estado final. Corrigidos no caminho: cronômetro reiniciado, 30 s de espera real em teste (agora injetável), seletores ambíguos em teste |
