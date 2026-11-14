# Dados científicos

Formato e invariantes: `planning/04_SCIENTIFIC_DATA_CONTRACT.md` (contrato v1). Carregamento e validação: `backend/app/dataset/store.py`.

| Caminho | Conteúdo |
|---|---|
| `documents.json` | documentos-fonte (URL, SHA-256 calculado, tamanho) |
| `investigations.json` | investigações (PSI-25 / BASS-II) |
| `tests/` | ensaios (BASS2-M1) |
| `parameters/` | registros por ensaio (valor e unidade originais, SI, papel, natureza, estado, revisão) |
| `evidence/` | localização exata (página impressa e do PDF, tabela, linha, coluna, trecho) |
| `gaps/` | lacunas (AUSENTE), com onde foram procuradas |
| `source_manifest.json` | manifesto de download da equipe (não entra no `dataset_version`) |
| `ai_cache/` | cache do assistente (não entra no `dataset_version`) |

Regras: dados científicos não são preenchidos com valores inventados; `EXTRAIDO_NAO_REVISADO` não equivale a `CONFERIDO_FONTE`; a promoção a `CONFERIDO_FONTE` só acontece por revisão humana, com `scripts/review_record.py`.

**Estado em 14/11/2026:** BASS2-M1 com 9 registros `EXTRAIDO_NAO_REVISADO` e 12 lacunas. Revisão humana pendente.
