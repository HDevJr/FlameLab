# Curadoria BASS-II · ensaio M1: relatório e pacote de revisão

**Estado em 14/11/2026: 0 de 9 registros conferidos. Todos estão em `EXTRAIDO_NAO_REVISADO`.**
A extração foi feita por assistente de codificação (Claude) sobre a camada de texto do PDF (PyMuPDF) e
**não substitui a revisão humana**. Nenhum valor pode ser apresentado como conferido até que uma pessoa da
equipe execute os passos da seção 3.

## 1. Documento-fonte
| Campo | Valor |
|---|---|
| Documento | NASA/TM-20210011385 — *Burning and Suppression of Solids—II (BASS—II) Summary Report*, out. 2021 |
| URL | https://ntrs.nasa.gov/citations/20210011385 |
| Arquivo local | `sources/NASA-TM-20210011385.pdf` (não versionado; `sources/*.pdf` no `.gitignore`) |
| Tamanho | 48 972 416 bytes · 144 páginas |
| SHA-256 esperado (`data/source_manifest.json` e `data/documents.json`) | `5ffa911fd9b6356f204646003fb9342e341810dcdfdf5cb15756e7f01ec5f770` |
| SHA-256 recalculado (14/11 19:12:55 UTC) | **igual: MATCH** — `docs/evidence/source_hash_check_20261114T191255Z.json` |

Mapa de páginas usado (capítulo 5, Miller & Wichman): §5.1 = impressa 55 / PDF 63 · §5.3 = 56 / 64 ·
**Tabela 5.1 = 57 / 65** · p. 58 / 66 · §5.4–5.5 = 60 / 68 · §5.5–5.6 = 61 / 69 · §5.7 = 63 / 71.
"Página PDF" = numeração do visualizador, começando em 1.

## 2. Registros extraídos (preliminares)
Cabeçalho literal da Tabela 5.1 (p. 57): *TABLE 5.1.—TWENTY BURNING AND SUPPRESSION OF SOLIDS—II (BASS—II) TESTS*.
A verificação cruzada automática (`scripts/crosscheck_table51.py`) deu **MATCH em 10/10 evidências**
(`docs/evidence/crosscheck_*.json`). Ela compara com a camada de texto e **não equivale a conferência**.

| # | Registro | Valor original | SI | Fonte (página impressa / PDF) | Coluna literal | Papel | Estado |
|---|---|---|---|---|---|---|---|
| 1 | `material` | PMMA ("clear cast") | — | §5.3 p. 56 / PDF 64: *"A total of 20 PMMA flat samples were burnt during the BASS-II experimentation (Table 5.1)."* e §5.1 p. 55 / PDF 63 | (texto, **sem coluna**) | METADADO | EXTRAIDO_NAO_REVISADO |
| 2 | `thickness` | 1 mm | 0,001 m | Tab. 5.1, linha M1, p. 57 / PDF 65 | Thickness, mm | CONDICAO | EXTRAIDO_NAO_REVISADO |
| 3 | `width` | 2.2 cm | 0,022 m | idem | Width, cm | CONDICAO | EXTRAIDO_NAO_REVISADO |
| 4 | `burning_faces` | 1 | 1 (adim.) | idem | One or two sides burning | CONDICAO | EXTRAIDO_NAO_REVISADO |
| 5 | `airflow_velocity` | 9 cm/s | 0,09 m/s | idem | Velocity, cm/s | CONDICAO | EXTRAIDO_NAO_REVISADO |
| 6 | `flame_spread_rate` | 0.071 mm/s | 7,1×10⁻⁵ m/s | idem | Spread rate, mm/s | **OBSERVAVEL** | EXTRAIDO_NAO_REVISADO |
| 7 | `burn_duration` | 6.4 min | 384 s | idem | Burn time, min | OBSERVAVEL | EXTRAIDO_NAO_REVISADO |
| 8 | `o2_initial` | 22.2 vol% | 0,222 | idem | Initial O2, vol% | CONDICAO | EXTRAIDO_NAO_REVISADO |
| 9 | `o2_final` | 21.9 vol% | 0,219 | idem | Final O2, vol% | OBSERVAVEL | EXTRAIDO_NAO_REVISADO |

Os valores coincidem com o documento mestre §08.1.

**Observações para quem revisar:**
- **Largura (divergência interna da fonte):** o texto das §5.1 e §5.3 diz "1 or 2 cm wide", enquanto a Tabela 5.1 e a p. 58 dizem 1,2 e 2,2 cm. Foi registrado o valor da tabela (2,2 cm). Avalie se isso precisa de nota no pitch.
- **O₂:** a base é volumétrica (vol%), conforme o cabeçalho. A §5.4 diz que o O₂ só foi medido no início e no fim, com perfil linear *assumido*.
- **Escoamento:** sempre oposto (§5.3). O anemômetro mede o ar que entra no duto; o perfil medido é "quite irregular" (§5.5), e os valores do perfil não estão no relatório.
- **Propagação:** obtida por rastreamento de imagens (§5.1, §5.3); incerteza não informada. É **resultado observado**: nunca entrada ou alvo de calibração do FDS.
- A §5.5 descreve a modelagem histórica com **FDS 5.5.3** (DNS 2-D, geometria do duto "approximate", amostra de 3 mm a 10 cm/s, *não* M1). A §5.6 e a §5.7 dizem que o modelo **superestima** a propagação. Nada disso é dado de M1.

Plataforma (nível de investigação, PSI-25): ISS / Microgravity Science Glovebox (§5.1, p. 55), também `EXTRAIDO_NAO_REVISADO`.
DOI e URL do PSI-25 foram copiados do documento mestre e **não foram reconferidos** no portal.

## 3. Como registrar a revisão (pessoa ≠ quem extraiu)
1. Rode `.\.venv\Scripts\python.exe scripts\verify_sources.py` e confirme que o resultado é `MATCH`.
2. Abra o PDF na página indicada e leia o valor e a unidade **sem olhar a tabela acima** (para evitar viés de confirmação).
3. Registre um registro de cada vez, por exemplo:
   ```powershell
   .\.venv\Scripts\python.exe scripts\review_record.py --record BASS2-M1.flame_spread_rate `
     --reviewer "Nome Sobrenome" --observed-value 0.071 --observed-unit mm/s --page-pdf 65 --i-checked-the-pdf
   ```
   Para o material: `--record BASS2-M1.material --observed-value PMMA --page-pdf 64`.
   Para faces: `--observed-value 1` (sem unidade).
4. O script **recusa** a promoção se o valor, a unidade ou a página divergirem, se o hash do PDF não conferir,
   se quem revisa for quem extraiu, ou se o nome indicar uma IA. Quando aceita, grava `CONFERIDO_FONTE`,
   o nome, a data e o hash conferido, valida o dataset inteiro e anexa uma linha ao [log](BASS2-M1_curation_log.md).
5. Faça commit das mudanças em `data/parameters/BASS2-M1.json` e no log, em um PR.

Checklist (o mesmo de `planning/04`, "Curadoria científica — BASS-II"):
- [ ] Identificação M1 correta · [ ] espessura e largura · [ ] faces · [ ] velocidade do ar · [ ] propagação ·
  [ ] duração · [ ] O₂ inicial e final · [ ] unidades originais · [ ] conversões SI · [ ] segunda revisão

## 4. Lacunas registradas (`data/gaps/BASS2-M1.json`, 12 itens, todos AUSENTE)
| Lacuna | Onde foi procurada | O que a fonte diz (sem valores) |
|---|---|---|
| Comprimento da amostra | §5.1–5.7, Tab. 5.1 | §5.1 traz afirmação **geral** sobre o conjunto; não específica de M1 |
| Suporte/substrato metálico | §5.1–5.7 | perda de calor para substrato metálico citada (p. 58), sem dimensões |
| Dimensões do duto | §5.3, §5.5 | "small flow duct"; modelo usou geometria "approximate"; Figs. 5.1/5.6 não analisadas |
| Pressão | §5.1–5.7 | não informada |
| Temperatura | §5.1–5.7 | não informada |
| Perfil do escoamento de entrada | §5.3, §5.5 | medido em vários pontos, "quite irregular"; valores não publicados |
| Posição do anemômetro | §5.3 | "velocity of air entering into the duct"; posição exata não dada |
| Ignição | §5.3, §5.5 | ignitor existe; a duração citada na §5.5 é do **modelo**, não do experimento |
| Propriedades de pirólise do PMMA | §5.1–5.7 | não listadas; autores dizem que precisam ajustar cinética e propriedades |
| Perfil temporal do O₂ | §5.4 | apenas início e fim medidos; perfil linear assumido |
| Incertezas de medição | §5.1–5.7 | não declaradas |
| Método de avanço da frente | §5.1, §5.3 | parcial: rastreamento de imagens + planilha; critério e incerteza não descritos |

Essas lacunas bloqueiam `FDS_REPRODUCTION` e, nos casos indicados, a comparação quantitativa.
