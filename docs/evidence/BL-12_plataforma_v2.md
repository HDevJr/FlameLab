# Evidências — Plataforma v2 (NASA Enrichment + FDS + Smokeview + protótipo web)

- Data: 14/11/2026 · Branch `feat/arq-v2-nasa-fds-prototipo` (base `feat/bl-02-dataset-cientifico@8937835`; a BL-02 **não** estava na `main`).
- Decisões: [planning/09](../../planning/09_ADR_NASA_ENRICHMENT_FDS_SMOKEVIEW.md). Nada foi enviado (`push`) nem integrado (`merge`).
- Rótulo obrigatório de tudo que veio do FDS: **teste de integração — não é reprodução de experimento NASA.**

## 1. Operações de API realmente executadas
| Fonte | Operação | Modo | Resultado |
|---|---|---|---|
| NTRS | `GET /api/citations/20210011385`; `GET /api/citations/search` (título e texto); `GET /api/openapi/` (UI) + extração do documento OpenAPI do `swagger-ui-init.js` | **online** | 200; sem autenticação |
| NTRS | download de `/api/citations/20210011385/downloads/TM-20210011385.pdf` (49 MB) e do PDF 19980232607 (1,4 MB) só para SHA-256 | **online** | SHA-256 idêntico ao arquivo local nos dois |
| DataCite | `GET /dois/10.60555/4qc4-de67`; `GET /dois?query=publisher:"NASA PSI" AND titles.title:(…)` | **online** | 200; PSI-25 (BASS-II) e PSI-26 (BASS) |
| TechPort | `GET /api/specification`; `GET /api/projects/13543`; `GET /api/projects/search?query=…` | **online** | 200 sem token; 13543 = “Spacecraft Fire Safety Demonstration” (Saffire) |
| PSI | `GET` da página `…/investigations/PSI-25` e do bundle JS público do portal | online | só o casco da aplicação Angular; **sem dados nem API documentada**. O serviço interno encontrado no bundle **não foi sondado** (bloqueado pelo controle de segurança do agente) |
| Testes automáticos | fixtures de respostas reais gravadas em `backend/tests/fixtures/nasa/` | **fixture** | sem rede |
Relatórios: [nasa_enrichment_BASS-II_online_20261114.json](nasa_enrichment_BASS-II_online_20261114.json), [imports_online_20261114.json](imports_online_20261114.json).

## 2. Prova de enriquecimento BASS-II (M1)
1. **PDF NTRS:** TM-20210011385, “Burning and Suppression of Solids–II (BASS-II) Summary Report”, GRC, publicado 2021-10-01, relatório E-19939, palavras-chave Microgravity/Flammability/Flame Spread/ISS/Glovebox. O arquivo local é **byte a byte idêntico** ao do NTRS. O PDF cita o próprio ID NTRS (`MATCH_CONFIRMED`).
2. **PSI-25 (via DataCite):** DOI 10.60555/4qc4-de67, publicador NASA PSI, licença CC0, 5 criadores. **`MATCH_CANDIDATE`**: título e 4 de 5 pessoas coincidem; **o PDF não cita o DOI/PSI e o registro não cita o NTRS**. O PSI-26 (“BASS”) foi descartado (semelhança 0,8). Grafia divergente: “Bhattacharjee” (artigo) × “Bhattachjee” (DataCite).
3. **TechPort:** `NOT_FOUND`. O 13543 (Saffire) **não é equivalente** ao BASS-II e nenhuma relação foi criada.
4. **Informação adicional útil para preparar o experimento:** a descrição do PSI traz objetivos e variáveis primárias (velocidade e direção do fluxo, O₂ por diluição com N₂, geometria da amostra) — **contexto**, sem valores por ensaio.
5. **Lacunas que permanecem:** as 12 de `data/gaps/BASS2-M1.json`; nenhuma foi preenchida por fonte externa (nenhuma fonte consultada expõe valores por ensaio em API documentada).
6. **Divergências:** só de metadados (grafia de autor). Nenhuma divergência de valor foi possível de avaliar. A divergência interna da fonte (largura 1 ou 2 cm × 2,2 cm; DIV-21) segue registrada.
7. **Exige revisão humana:** os 9 registros de M1 (0/9 conferidos), o vínculo PSI-25 (D-13) e qualquer dado complementar. `promoted_records = 0`.

## 3. Importação real de dois artigos (online, Gemini real)
| | BASS-II (referência) | DYLCO — NASA/TM-1998-207916 (generalização) |
|---|---|---|
| Natureza | combustão sólida em microgravidade | líquidos capilares (IML-2) |
| Procedência | `VERIFIED` (hash = NTRS) | `VERIFIED` (hash = NTRS; encontrado por título/autores, sem ID no texto) |
| NTRS / PSI / TechPort | confirmado / **candidato** PSI-25 / não encontrado | candidato (revisão) / não encontrado / não encontrado |
| Extração | já curado → etapa pulada | 1 experimento, 3 parâmetros com citação literal, 1 proposta descartada (citação não literal); **tudo `EXTRAIDO_NAO_REVISADO`** |
| Compatibilidade FDS | `MISSING_PARAMETERS` (BASS2-M1) | **`UNSUPPORTED_PHYSICS`** — explicado na tela; análise e fontes continuam |
A extração do DYLCO leu 14 das 32 páginas (limite da versão; aviso registrado). Os três valores extraídos precisam de revisão humana; não foram conferidos por nós.

## 4. FDS, Smokeview e FFmpeg — execução real
- **Spike manual** (exemplo oficial do FDS, 60 s simulados): [fds_smokeview_spike_20261114.json](fds_smokeview_spike_20261114.json) — `STOP: FDS completed successfully`, 306 s, 100 quadros, MP4 H.264 de 10 s. Descoberta: `RENDERALL` não sobrescreve quadros.
- **Duas execuções reais pelo worker da plataforma** (5 s simulados cada), com artefatos e hashes em `sim_RUN-*/`:

| Execução | Parâmetros | FDS (s) | Quadros | HRR máx. | MP4 |
|---|---|---|---|---|---|
| `RUN-20261114234550-e05b` | caso-base: HRRPUA 1000 kW/m², fuligem 0,01 | 54,2 | 13 | 179,6 kW | `sim_RUN-…e05b/result.mp4` |
| `RUN-20261114234651-a055` | derivado: **HRRPUA 500** (única alteração) | 64,4 | 13 | 82,8 kW | `sim_RUN-…a055/result.mp4` |
Verificação de sanidade (não é validação): a área do queimador é 0,16 m², logo 160 kW (base) e 80 kW (derivado) são as potências nominais; o pico passa desses valores nos primeiros instantes. Versões registradas: FDS-6.11.1-0-gff928db-release, SMV-6.11.2-0-g27cbe59-release, FFmpeg 9.0.2. Todos os artefatos listados responderam 200 na API.
- Bug encontrado e corrigido durante a prova: o quadro-pôster ficava fora do diretório servido (404); agora é copiado para `poster.png` e a execução foi refeita.
- **Não verificado:** execução sem sessão gráfica, Linux/Xvfb, limite de memória.

## 5. Testes
[test_run_plataforma_v2_20261114.txt](test_run_plataforma_v2_20261114.txt): **167 passed, 1 skipped** (backend; os 114 anteriores BL-02/BL-05 preservados, o skip é o mesmo `NOT_RUN` de resposta com evidência real conferida) + `tsc` sem erros + 5 testes `vitest` + `vite build`.

| Resultado | Itens |
|---|---|
| PASS (simulado/fixture) | 53 testes novos: enriquecimento (10), genericidade (1), importação/extração (17), simulação (25) |
| PASS (real, registrado) | FDS+Smokeview+FFmpeg (2 execuções + spike), importações online (2), enriquecimento online, Gemini real (1 extração) |
| NOT_RUN | renderização das telas em navegador; resposta do assistente com registro real **conferido por humano** (depende de D-11); execução sem sessão gráfica |
| FAIL | nenhum no estado final. Falhas intermediárias corrigidas: handle de arquivo no Windows, versão do FDS lida do stderr, pôster fora do diretório, hifenização na citação literal |
