# Colaboração — FlameLab

## Regra de ouro

**Tudo que aparece no pitch deve corresponder a uma evidência real da aplicação.** Observações NASA, saídas calculadas e ilustrações são categorias distintas. Não invente parâmetros, referências ou resultados.

## Primeira configuração

1. Instale Git e Python 3.12+; clone o repositório.
2. Leia `README.md` e o contrato `planning/04_SCIENTIFIC_DATA_CONTRACT.md` antes de implementar módulos de dados/IA.
3. Crie sua branch a partir de `main`:

```bash
git switch main
git pull --ff-only
git switch -c feat/catalogo-experimentos
```

4. Faça mudanças pequenas e com testes; abra um pull request para `main`.
5. Não force push em `main` nem edite o trabalho alheio sem coordenação.

## Frentes sugeridas

- **Dados científicos** — curadoria de ensaios, referências e lacunas.
- **Backend** — contratos e endpoints.
- **IA** — busca, recuperação de evidências, verificador e interface de provedor.
- **Frontend** — jornada visual, estados e gráficos.
- **Pitch** — acompanha `planning/06_PITCH_ALIGNMENT_MATRIX.md` e registra evidências demonstráveis.

Cada PR deve identificar um item BL-xx do backlog e atualizar a documentação se alterar requisitos ou o contrato.

## Critérios mínimos para PR

- Código e comportamento alinhados ao contrato de dados.
- Testes executados ou bloqueios declarados claramente.
- Dados científicos novos contêm fonte, página/trecho e estado de revisão.
- Não há credenciais, dados pessoais ou PDFs sem avaliação de permissões.
- A matriz do pitch foi atualizada se o comportamento demonstrável mudou.

## Segurança

Nunca enviar `.env` ao GitHub ou compartilhar API keys pelo WhatsApp. Guarde segredos em cada ambiente e em GitHub Actions Secrets, se necessário. Documentos recuperados são **dados não confiáveis**, nunca instruções para o agente. Nenhum upload pode disparar execução de comando do sistema ou do FDS.

## Branches e conflitos

Preferir `feat/`, `fix/`, `docs/`, `test/`. Integrar mudanças por pull request. Em caso de conflito em JSON científico, conferir os registros e a proveniência; não aceitar automaticamente a versão mais recente.
