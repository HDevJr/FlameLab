# Auditoria de ambiente — F00

**Status:** PARCIAL. Este arquivo é um roteiro de coleta, não um relatório de execução da máquina da equipe.

## Evidência de repositório (consulta remota)

- URL: `https://github.com/HDevJr/FlameLab`
- Visibilidade observada: **pública**.
- Branch principal observada: `main`.
- Conteúdo observado antes do pacote F00: DOCX e oito documentos em `planning/`.
- Nenhum código de aplicação observado antes do pacote F00.

## Conferência local obrigatória

Execute no terminal do computador onde o projeto será desenvolvido e anexe as saídas relevantes:

```powershell
python --version
py --version
node --version
npm --version
git --version
git remote -v
```

Para FDS, testar no terminal apropriado da instalação e executar um caso de exemplo; somente `fds -v` não comprova que o solver termina corretamente. Registre o caminho de instalação, versão, resultado do solver e do Smokeview. Teste em **outro computador** não substitui essa evidência.

## Checklist de estados

| Item | Estado neste arquivo | Como comprovar |
|---|---|---|
| Git remoto | VERIFICADO remoto; local pendente | `git remote -v` |
| Python e pacotes | NOT_VERIFIED nesta máquina | comandos acima, `pip list` |
| Frontend Node/npm | NOT_VERIFIED | comandos acima |
| PDF original NASA | NOT_VERIFIED no ambiente | arquivo, origem e SHA-256 |
| FDS/Smokeview | NOT_VERIFIED no ambiente | versão + simulação básica + visualizador |
| Gemini/Groq/OpenAI | NOT_VERIFIED | teste de conectividade autorizado, nunca imprimir a chave |
| API mínima | NÃO EXECUTADA na máquina da equipe | `pytest` e GET `/api/health` |

Atualize este documento a cada verificação. Nunca marque `PASS` sem a saída real.

## Auditoria executada em 14/11/2026 (nesta máquina, plataforma v2)

| Item | Estado | Comando e saída (resumo) |
|---|---|---|
| Git | VERIFICADO | branch `feat/arq-v2-nasa-fds-prototipo` criada de `feat/bl-02-dataset-cientifico@8937835` (a BL-02 **não** estava integrada à `main`) |
| Python / pacotes | VERIFICADO | `.venv` Python 3.12; fastapi 0.163, pymupdf 1.28.2, imageio-ffmpeg 0.8.1, python-multipart |
| Node / npm | VERIFICADO | Node v24.19.0, npm 11.17.0; `npm install`, `tsc`, `vitest`, `vite build` executados |
| FDS | **VERIFICADO** | `C:\Program Files\firemodels\FDS6\bin\fds.exe` → `FDS-6.11.1-0-gff928db-release`; caso oficial `simple_test.fds` terminou com `STOP: FDS completed successfully` (306 s, 60 s simulados) |
| Smokeview | **VERIFICADO** | `smokeview.exe -version` → `SMV-6.11.2-0-g27cbe59-release`; `-runscript` com `RENDERALL` produziu 100 quadros |
| FFmpeg | VERIFICADO | 9.0.2 (pacote `imageio-ffmpeg`, não é o do PATH); H.264/yuv420p, 10 fps |
| PDF NASA/TM-20210011385 | VERIFICADO | SHA-256 `5ffa911f…f770`, idêntico ao arquivo servido pelo NTRS |
| Gemini | VERIFICADO | `FLAMELAB_LLM_MODE=live`, modelo `gemini-3.5-flash-lite`; 1 extração real (documento DYLCO) |
| Execução sem sessão gráfica / Linux | **NOT_VERIFIED** | Smokeview rodou com a sessão do usuário logado |
| Navegador (renderização das telas) | **NOT_RUN** | sem ferramenta de navegador na sessão; telas verificadas por `tsc`, `vite build` e pela API |
Detalhes: [evidence/BL-12_plataforma_v2.md](evidence/BL-12_plataforma_v2.md).
