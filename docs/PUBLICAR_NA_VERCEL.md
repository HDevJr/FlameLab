# Publicar a demonstração na Vercel (somente leitura)

A publicação pública é uma **demonstração somente leitura**: o backend FastAPI roda como função Python, o frontend é estático e **nenhuma rota grava dados**. Importar PDF, revisar, decidir lacunas e simular respondem `403 READ_ONLY_DEMO`. O assistente responde **do cache** (sem chave do Gemini no servidor).

## Arquivos que fazem isso funcionar
- `vercel.json`: build do frontend (`frontend/dist`), reescritas de `/api/*` para a função e fallback de SPA.
- `api/index.py`: entrada da função (`app` do FastAPI) e padrões seguros de ambiente.
- `requirements.txt` (raiz): só o necessário para a demonstração (sem `google-genai`, `imageio-ffmpeg`, `uvicorn`).
- `.vercelignore`: exclui saídas pesadas do FDS, protótipos e planejamento do pacote.
- `backend/app/readonly.py` + middleware em `backend/app/main.py`.

## Passo a passo (dashboard da Vercel)
1. **Add New → Project** e importe o repositório do GitHub (`Sam280903/FlameLab` ou `HDevJr/FlameLab` depois do merge). Escolha a branch (`feat/ui-p0` ou `main`).
2. **Framework Preset:** `Other`. Deixe o *Root Directory* na raiz. Os comandos de build vêm do `vercel.json`.
3. **Environment Variables** (Production e Preview), todas **sem segredo**:

| Variável | Valor |
|---|---|
| `FLAMELAB_READ_ONLY` | `true` |
| `FLAMELAB_LLM_MODE` | `cache` |
| `FLAMELAB_AI_CACHE_WRITE` | `false` |
| `FLAMELAB_NASA_MODE` | `fixture` |

   **Não cadastre `GEMINI_API_KEY`.** Sem chave, o servidor público nunca chama o Gemini nem gasta a sua cota.
4. **Deploy.** Abra o link e confira: banner amarelo "Demonstração pública somente leitura"; `GET /api/status` com `"read_only": true`; botão de importação desativado.

## Conferências recomendadas depois do deploy
- Abrir `/experimentos/BASS2-M1` e "Ver origem" (abre o PDF na página).
- No Assistente, perguntar "Qual foi a velocidade de propagação da chama no ensaio M1?" (resposta do cache). Perguntas novas devem mostrar "fonte indisponível, sem resposta em cache".
- Tentar importar um PDF: deve ser recusado.

## Limites conhecidos
- O disco da Vercel é somente leitura: análises calculadas na hora não são salvas.
- O pacote inclui `var/imports/*/source.pdf` (≈50 MB). Se o deploy falhar por tamanho (limite de 250 MB descompactado), mova os PDFs para um armazenamento externo ou adicione-os ao `.vercelignore` (o "Abrir PDF" deixa de funcionar).
- A configuração não foi testada na Vercel de dentro desta sessão (sem acesso de criação de projeto); o modo somente leitura foi testado localmente (`FLAMELAB_READ_ONLY=true`).
