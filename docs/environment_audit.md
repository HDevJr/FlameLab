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
