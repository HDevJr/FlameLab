# FlameLab — briefing de contexto (15/11/2026)

> Documento autocontido para colar ou anexar em outra ferramenta de IA. Não contém chaves, `.env` nem dados pessoais. Fonte: repositório https://github.com/HDevJr/FlameLab (branch `main`).

## 1. O que é o projeto
FlameLab é um painel de investigação de combustão em microgravidade, feito para o **NASA Space Apps Challenge 2026 — "Flame in Freefall"** (Rio Verde-GO, 14–15/11). Ele organiza dados de experimentos reais da NASA com origem verificável, mostra lacunas em vez de estimá-las, e oferece um assistente de IA que só responde com base em evidências e se abstém quando não há suporte. A simulação física (FDS/Smokeview) é uma trilha separada e experimental. **Projeto independente, não endossado pela NASA nem pelo NIST.**

Fonte científica: NASA/TM-20210011385, *BASS-II Summary Report* (Tabela 5.1, ensaio M1).

## 2. Princípios inegociáveis
- Rastreabilidade: todo valor científico aponta para documento, página, tabela, linha e coluna.
- Ausência é informação: dado não encontrado é `AUSENTE`, nunca estimativa.
- A IA interpreta trechos delimitados; **não calcula nem simula** fogo. Um verificador determinístico (V1–V8) bloqueia afirmações sem suporte.
- `EXTRAIDO_NAO_REVISADO` ≠ `CONFERIDO_FONTE`. Só revisão humana promove.
- Resultado observado (ex.: velocidade de propagação) nunca é entrada nem alvo de calibração de modelo.
- Tudo que aparece no pitch precisa corresponder a evidência real da aplicação.

## 3. Arquitetura
- **Backend:** Python 3.12, FastAPI. `data/` guarda o dataset científico versionado (JSON, validado no startup; dataset inválido impede o servidor de subir). `var/` é a área de trabalho local.
- **Assistente (`POST /api/ask`):** recuperação de evidências → portão de suficiência determinístico → cache → provedor Gemini → verificador → resposta. Modos `live`, `cache`, `off`. Abstenção e indisponibilidade são estados da resposta (HTTP 200).
- **Plataforma v2:** importação de PDF, enriquecimento NASA (NTRS, DataCite, TechPort), revisão humana assistida, auditoria de integridade, worker isolado FDS → Smokeview → FFmpeg.
- **Frontend:** React 18 + TypeScript + Vite (protótipo navegável). Há ainda um protótipo de design em HTML (`prototypes/`) com a identidade visual proposta.

## 4. Dados do ensaio M1 (conferidos na fonte, p. 57, Tabela 5.1)
| Condição de entrada | Valor |
|---|---|
| Material | PMMA (clear cast) |
| Espessura | 1 mm |
| Largura | 2,2 cm |
| Faces em combustão | 1 |
| Velocidade do ar (fluxo oposto) | 9 cm/s |
| O₂ inicial | 22,2 vol% |

| Resultado observado | Valor |
|---|---|
| Velocidade de propagação da chama | 0,071 mm/s |
| Tempo de queima | 6,4 min |
| O₂ final | 21,9 vol% |

**12 lacunas declaradas** (todas impedem reproduzir o ensaio no FDS), entre elas: comprimento da amostra, geometria do duto, suporte/substrato, pressão, temperatura, perfil do escoamento, posição do anemômetro, procedimento de ignição, propriedades de pirólise do PMMA, perfil temporal de O₂, incertezas, método de rastreio da frente de chama.

Ressalvas registradas: largura "1 ou 2 cm" no texto × 1,2 e 2,2 cm na tabela; O₂ medido só no início e no fim.

## 5. Estado real hoje
| Camada | Estado |
|---|---|
| Dataset M1 | 9 registros conferidos, 12 lacunas, evidências com localização |
| Backend e assistente | Implementados e testados (provedor simulado + smoke real do Gemini). Cache e golden set reais com os registros conferidos **ainda não gerados**. Prompt v1 sem revisão científica |
| Frontend | Protótipo navegável; validação visual **NOT_RUN** |
| Telemetria (Arduino Uno + BMP180 + 2 potenciômetros, Wokwi) | **Nenhum CSV real no repositório** |
| FDS | Verificado em caso **genérico**; reprodução do M1 **bloqueada** (G1 geometria, G2 material, G4 comparação) |
| Não implementado | busca/ranking, comparação lado a lado, relatório de exportação, vídeo de fallback |

Gates FDS: G0-env (ambiente) verificado; G1 geometria bloqueado; G2 material (pirólise do PMMA) bloqueado; G3 execução só no caso genérico; G4 comparação bloqueado; G5 alteração futuro.

## 6. Identidade visual
Tema "scientific dark / clean lab": base azul-petróleo (`#0B1220`, `#111C2E`), superfícies de leitura claras, ação `#2563EB`, dados `#06B6D4`, aviso `#D97706`, perigo `#DC2626`, sucesso `#15803D`. Tipografia Inter + JetBrains Mono. Estados nunca dependem só de cor (ícone + rótulo). Logo: esfera fluida em azul/ciano sobre fundo preto, wordmark "FLAMELAB", subtítulo "Ferramenta de análise de combustão em microgravidade".

## 7. Plano de hoje (15/11)
Marcos oficiais a confirmar com a organização: pré-apresentação 15h30, submissão local 17h, prazo geral 23h59.

| Quando | Marco |
|---|---|
| 10h15 | Decidir: FDS NO-GO para M1; levar ou não o design ao frontend real; situação do Wokwi |
| 10h30–12h30 | Trilhas em paralelo: dados/ciência, assistente (cache + golden set reais), frontend (tokens + ficha M1), pitch/QA |
| **12h30** | Congelamento: tag `demo-v1`, testes passando, só correção crítica |
| 13h30 | Demo pronta: vídeo de fallback, README, capturas |
| 14h30 | Roteiro congelado, com revisão cruzada |
| 14h30–15h30 | Ensaio do pitch (plano B: `cache` → `off` → vídeo) |
| 15h30 | Pré-apresentação |
| Antes das 17h | Submissão |

Ordem de corte se faltar tempo: telemetria → port do design → tela FDS vira slide → assistente ao vivo vira cache. **Nunca cortar:** conferência com origem, lacunas visíveis, verificador/abstenção, aviso de independência, plano B da demo.

## 8. O que pode e não pode ser dito no pitch
| Pode (com evidência) | Não pode |
|---|---|
| Ficha M1 com valores conferidos e origem | "Reprodução fiel do ensaio M1" |
| Lacunas declaradas como ausentes | Preencher lacuna com estimativa |
| Assistente cita, verifica e se abstém (dito como cache/gravado, se for o caso) | "A IA prevê incêndios" / "simula o fogo" |
| FDS/Smokeview verificados em caso genérico | Vídeo FDS apresentado como do M1 |
| Protótipo de interface identificado como proposta | Telemetria ou gráfico sem dado real |
| "Projeto independente, não endossado pela NASA" | "Aprovado pela NASA", "simulação oficial" |

## 9. Pedido

**Desenhe as telas do que o FlameLab consegue fazer hoje**, usando só o que existe de verdade (seções 4, 5 e 8). Não desenhe funcionalidades inexistentes como se estivessem prontas; qualquer ideia extra deve vir marcada "proposta futura".

### Telas a desenhar (nesta ordem de prioridade)
1. **Layout principal:** barra lateral (Visão geral, Biblioteca científica › BASS-II › Ensaio M1, Assistente científico, Telemetria, Validação física FDS, Fontes e metodologia), aviso fixo de projeto independente, logo da seção 6.
2. **Ficha do ensaio M1 (tela mais importante):** cabeçalho com referência `NASA-TM-20210011385 · Tabela 5.1`, três blocos distintos (A. Condições de entrada, B. Resultados observados, C. Lacunas declaradas). Cada valor com unidade, selo de estado e acesso ao trecho da fonte (página, tabela, linha, coluna, citação literal). Lacunas em bloco separado, rotuladas `AUSENTE NA FONTE`.
3. **Assistente científico:** fonte ativa fixa, conversa, quatro estados de resposta (respaldado pela fonte, dado ausente, extrapolação bloqueada, fonte indisponível), evidências sob a resposta, afirmações bloqueadas riscadas com o motivo. Exemplo obrigatório: pergunta sobre propagação da chama em Marte, que termina em abstenção e sem número inventado.
4. **Visão geral:** estado das quatro camadas (dados, assistente, telemetria, FDS) com selos Implementado / Validado / Demonstrativo / Pendente / Bloqueado, e o caminho até o ensaio M1.
5. **Prontidão para FDS:** checklist G0–G5 com critério e motivo, lista de bloqueios, veredito "Não pronto para reprodução fiel do ensaio M1" e **nenhum botão de execução ativo**.
6. **Telemetria:** identificação do protótipo, estrutura do CSV `TEMPO_S,PRESSAO_KPA,TEMP_C,O2_PCT,FLUXO_CMS` e **estado vazio** explicando que não há série real carregada. Sem gráfico inventado.
7. **Fontes e metodologia:** documento-fonte, hash, como ler os selos, aviso de independência.

### Regras de design
- Seguir a identidade da seção 6. Cor de estado sempre acompanhada de ícone e texto.
- Desktop (≥1280 px) e celular (375 px) para as telas 1 e 2; as demais, só desktop.
- Valores com algarismos tabulares, vírgula decimal, unidade sempre visível.
- Se faltar a referência detalhada de um campo, exibir "Referência não vinculada"; nunca inventar página, linha ou grau de confiança.
- Interface em português do Brasil.

### Formato da entrega
Para cada tela: (a) objetivo em uma frase, (b) wireframe ou mockup de alta fidelidade, (c) lista dos componentes usados, (d) estados (vazio, carregando, erro, bloqueado), (e) o que é dado real e o que seria proposta futura. Ao final, uma lista de componentes reutilizáveis (cabeçalho de página, selo de estado, valor científico, referência de evidência, aviso de dado ausente, mensagem do assistente, gate de prontidão) com variações.

### Fora do escopo desta rodada
Busca com ranking, comparação lado a lado, relatório de exportação, tema claro/escuro configurável, qualquer tela que dependa de dado que não existe.
