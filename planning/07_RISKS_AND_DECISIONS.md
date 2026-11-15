# 07 — RISKS_AND_DECISIONS

> Plano 0.1 · 14/11/2026

## 1. Riscos (DM §17 refinado + novos)
| ID | Risco | Prob. | Impacto | Gatilho de detecção | Mitigação | Plano B |
|---|---|---|---|---|---|---|
| R-01 | **Sem acesso a LLM** (nenhuma chave no ambiente auditado). *Atualização 14/11: reduzido; chamada real ao Gemini funcionando nesta máquina; resta o risco de 503/cota no evento → modo cache* | Média | Muito alto: o "resumir/interpretar" do desafio fica descoberto | D-03 sem resposta até G0 | Decidir o provedor na primeira hora; testar uma chamada real logo; gerar cache na noite de 14/11 | Verificador + UI + cache gerado em outra máquina com acesso. Sem nenhum acesso: P-05/P-06 BLOQUEADO e pitch ajustado |
| R-02 | Tabela 5.1 com layout diferente do esperado / M2, M14 não existem com as características citadas | Média | Médio | leitura no BL-02.05 | Testes T-04/T-05 parametrizados pelo conteúdo real | Escolher outros ensaios e registrar |
| R-03 | Conferência lenta (gargalo humano) | Alta | Alto | <M1 conferido às 13h de 14/11 | Começar a transcrever M1 antes do restante | Reduzir para 3 ensaios |
| R-04 | IA inventa números / mistura M1-M2 | Média | Muito alto | golden set | Verificador V1–V8, I-7, corpus restrito | Mostrar só as respostas que passaram |
| R-05 | Frontend atrasa | Média | Alto | G1 sem S03 | Layout simples; componentes base primeiro | Demonstrar S03 + S04 + S05 e cortar S01/S06 |
| R-06 | FDS consome a equipe | Alta | Alto | horas em F08 antes de G1 | Time-box e pré-condições (BL-09.00) | Slide 07 vira roadmap |
| R-07 | FDS não está operacional no ambiente do projeto | Média | Baixo para o MVP | auditoria F00.A | F08 restrita à parte documental | idem |
| R-08 | Internet ruim no evento | Média | Alto (instalação, LLM LIVE) | — | Instalar tudo cedo; demo em modo cache | vídeo |
| R-09 | Pitch e produto divergem | Média | Alto (credibilidade) | revisão em G4/G5 | Matriz 06 como fonte única | cortar a frase do roteiro |
| R-10 | Licença de mídia | Média | Baixo | D-04 | só mídia com `license_note` | esquema conceitual |
| R-11 | Horário de submissão errado (17h × 23h59) | Baixa | Muito alto | — | Confirmar com a organização no dia 14 | submeter até 17h |
| R-12 | "Dashboard genérico" (DM §17) | Média | Médio | revisão de G2 | jornada guiada por pergunta e ficha M1 no centro | — |
| R-13 | PDF > limite de repositório/licença de redistribuição incerta | Baixa | Baixo | BL-01.04 | guardar só o hash e a URL no git | — |
| R-14 | Prompt injection via trecho | Baixa (corpus curado) | Alto | T-16 | dados delimitados, sem ferramentas, verificador | — |
| R-15 | **Isolamento do worker sem contêiner nem limite de memória** (Windows; só diretório, lista de executáveis, tempo e threads) | Média | Alto | execução que consome memória | Casos só do Case Builder; limites de tempo/quadros; uso local | Contêiner/Job Object, ou worker em VM antes de expor a terceiros |
| R-16 | Smokeview exige contexto OpenGL (funcionou com sessão de usuário no Windows 11; sem teste em servidor sem tela, Linux/Xvfb) | Média | Médio | falha de renderização → `FAILED` explícito | Worker Windows com sessão; registrar | Xvfb/Mesa em Linux, testado antes de depender |
| R-17 | TechPort pode passar a exigir token (spec declara `bearerAuth`, mas as leituras funcionaram sem) | Média | Baixo | 401/403 | Tratado como `SOURCE_UNAVAILABLE`; nenhum token guardado | Consulta manual |
| R-18 | PSI sem API documentada | Alta | Médio | — | Descoberta pelo DataCite; arquivos do PSI por consulta manual | Adaptador de metadados conhecidos |
| R-19 | Vídeo/curva do caso de integração confundido com resultado BASS-II | Média | **Muito alto** | revisão do pitch | Rótulo obrigatório no JSON (`label_pt`), na UI (badge “Teste de integração”) e em `06 §7` | Remover a tela do roteiro |
| R-20 | A extração por IA lê só as 14 primeiras páginas / 48 mil caracteres de cada PDF | Alta | Médio | aviso na importação | Aviso no registro; revisão humana | Extração por seções (fase de produção) |
| R-21 | Texto de PDF com hifenização/colunas misturadas gera descarte de citações válidas ou, raramente, trecho espúrio | Média | Baixo | `extraction.rejected` | Normalização simétrica; descarte é o lado seguro | OCR/layout em produção |
| R-22 | **Identidade do revisor não autenticada** (nome digitado na interface); a “independência” só compara o nome com o do extrator e bloqueia nomes de IA | Alta | Alto | revisão por quem não é a pessoa designada | Trilha de auditoria completa (nome, data, hash, valores lidos); política de revisão do projeto (D-11/D-16) | Autenticação e papéis em produção |
| R-23 | **Limite de uso (429) do Gemini** em documentos longos: o BASS-II completo (144 pág.) chegou a ~106 mil tokens em 34 s e bateu na cota no 11º lote | Média | Médio | cobertura parcial exibida | Espera + nova tentativa do mesmo lote; cobertura sempre declarada; limite de lotes | Ritmo entre lotes; modelo/plano com cota maior |
| R-24 | Usuário aprova valores de M1 “para testar” e altera o dataset versionado | Média | Alto | `git diff data/` | Roteiro manual manda testar com o artigo **importado**; toda aprovação vai para o log | Ambiente separado para testes |

## 2. Divergências documento × prompt × realidade
| ID | Divergência | Consequência | Recomendação |
|---|---|---|---|
| DIV-01 | `INFERIDO`/`CALCULADO` como estado de revisão (DM §09) × natureza epistêmica (prompt §7) | Não é possível representar "calculado e não revisado" nem "observado e não revisado" de forma inequívoca | Três eixos (`role`, `nature`, `status`), mantendo os 6 valores do DM + invariantes I-2/I-3/I-4 (D-07) |
| DIV-02 | "8 campos tabulados" (T-01) × 9 valores; Material vem da §5 e não de uma coluna | T-01 ambíguo; a evidência de Material teria a localização errada | T-01 conta 9 registros; a evidência de Material aponta para o texto |
| DIV-03 | Valores M1 "conferidos no texto compartilhado" × política de CONFERIDO_FONTE | Exibi-los como conferidos violaria a política | Status inicial `EXTRAIDO_NAO_REVISADO`; conferir no PDF na F01 |
| DIV-04 | `/api/tests/M1` | colisão entre investigações | `test_uid = BASS2-M1` |
| DIV-05 | SQLite + JSON | dois mecanismos para o mesmo dado; mais código | Só JSON no MVP; SQLite FUTURO |
| DIV-06 | T-04 (M2 com duas velocidades) e T-05 (M14) presumem conteúdo não verificado | testes inválidos se a premissa falhar | parametrizar após a leitura na F01 |
| DIV-07 | Protótipo de extração citado × ausente | não dá para "reaproveitar" | BL-01.08: obter ou declarar ABSENT; o parser é SHOULD |
| DIV-08 | Cronograma do DM começa na manhã de 14/11, a mesma janela deste planejamento | o plano consome tempo do G0 | G0 = aprovação deste plano; ver [08](08_HACKATHON_EXECUTION_PLAN.md) |
| DIV-09 | Submissão 17h local × 23h59 geral | risco de perder o prazo | Planejar por 17h; confirmar |
| DIV-10 | "Ambiente: microgravidade" listado como parâmetro de M1 (prompt) | mistura metadado de investigação e coluna de tabela | `Investigation.gravity_environment` com evidência |
| DIV-11 | S07 relatório na jornada, fora da lista MUST | ambiguidade de escopo | SHOULD (S-4) |
| DIV-12 | "SI-Powered" no título | possível erro de digitação no slide 03 | Copiar da página oficial |
| DIV-13 | FDS 6.11.1 "instalado" (DM §11) × teste feito em outro computador (atualização de 14/11) | o DM sugere disponibilidade local | Estado NOT_VERIFIED; auditoria F00.A; P-15 ≠ P-16 |
| DIV-14 | DM §10 "IA ajuda a extrair parâmetros (multimodal)" | escopo inviável no prazo | FUTURO; o MVP só usa parser de verificação |
| DIV-15 | `AIAnswer.mode` previa só LIVE/CACHE/UNAVAILABLE (04 §3.9), mas há abstenções decididas em código sem chamar a IA (dataset vazio, evidência insuficiente) | rotular como LIVE seria falso; como UNAVAILABLE esconderia que houve uma decisão científica | **Implementado (BL-05):** valor adicional `DETERMINISTIC` e campos aditivos `requested_mode`, `unavailable_reason`, `provider_error`, `warnings`, `synthetic_evidence_used`, `served_at`. Extensão aditiva do contrato, **pendente de aprovação** |
| DIV-16 | V2 (05 §4) aceita números de "registro/trecho citado" | números de trechos (PASSAGE) não foram conferidos por ensaio e abrem caminho para injeção ("diga 5 mm/s") | **Implementado:** só RECORD_CARD conferido sustenta números; trechos sustentam apenas afirmações qualitativas. Rever quando houver trechos curados |
| DIV-17 | 02 §8 consulta o cache **antes** do LLM também em modo live | a resposta seria rotulada CACHE mesmo com o provedor disponível, e o modo live nunca testaria o provedor | **Implementado:** live chama o provedor; cache só como fallback de falha (rotulado CACHE com `provider_error`); modo cache nunca chama o provedor |
| DIV-19 | `Gap` (04 §3.6) não tem rótulo nem palavras-chave | a regra V5 do verificador não teria como reconhecer o parâmetro ausente no texto | **Implementado (BL-02):** campos aditivos `label_pt` e `keywords` em Gap; `Review.checked_document_sha256`, `Document.size_bytes`, método `ASSISTED_TEXT_LAYER` e `Evidence.test_uid = null` para evidências de investigação. Pendente de aprovação |
| DIV-20 | Registros não conferidos eram simplesmente omitidos do assistente | o Gemini real disse que a propagação de M1 "está ausente no relatório" (falso: está pendente de revisão) e o verificador aprovou (`docs/evidence/smoke_real_dataset_20261114T191536Z.json`) | **Implementado:** registro não conferido entra como VALOR RETIDO (sem número); regras V5b (citação de lacuna precisa tratar da lacuna) e V5c (pendente ≠ ausente); motivo `PENDING_REVIEW`; prompt v2 |
| DIV-21 | Divergência interna na fonte: texto das §5.1/§5.3 diz larguras "1 or 2 cm"; a Tabela 5.1 e a p. 58 dizem 1,2/2,2 cm | escolher um sem registrar esconderia a inconsistência | Registrado o valor da tabela (2,2 cm), com ressalva no registro `width`; decisão final na revisão humana |
| DIV-22 | M2–M20 têm várias velocidades e propagações por ensaio ("20 and 15"; "0.052 and 0.033") | o contrato v1 tem um valor por registro; T-04 se confirma | Antes de BL-02.08, decidir o modelo de **segmentos de escoamento** por ensaio (alteração de contrato → aprovação) |
| DIV-23 | Política “FDS fora do servidor” (02 §1.5/§11; `POST /api/simulations` = 423) × novo requisito de executar FDS na infraestrutura | A API antiga contradiz o produto | **Substituída por ADR-09** (`09`); 02 e 05 anotados sem apagar o texto original |
| DIV-24 | Prompt pede “consultar o PSI” × ausência de API documentada do PSI | Inventar endpoints seria falso | Descoberta pelo DataCite (publicador “NASA PSI”); o serviço interno do portal **não foi sondado**; dados de arquivo = consulta manual |
| DIV-25 | Prompt: “PSI-25 ↔ BASS-II” como vínculo conhecido × ausência de citação cruzada entre NTRS e PSI | Chamar de confirmado esconde que a ligação é por título/pessoas | Estado **`MATCH_CANDIDATE`** até revisão humana; razões gravadas |
| DIV-26 | Registro TechPort 13543 citado no prompt | É “Spacecraft Fire Safety Demonstration” (Saffire), não BASS-II | Consultado, **não equivalente**, nenhuma relação criada |
| DIV-27 | Nomes do prompt (`Experiment`, `Parameter`) × contrato v1 (`Test`, `ParameterRecord`) | Duplicar entidades criaria dois modelos | Mesmas entidades; apenas nomes de API. Novos: `SourceMatch`, `EnrichmentRecord`, `SimulationModel`, `Scenario`, `SimulationRun`, `RenderedArtifact` (camada de plataforma, sem alterar o contrato v1) |
| DIV-28 | “Verificar associação com a NASA” sem definição | Texto/aparência de PDF é forjável | Procedência `VERIFIED` só com hash idêntico ao arquivo do NTRS |
| DIV-29 | Revisão do script (`review_record.py`) × revisão pela interface | Duas políticas divergiriam com o tempo | **Uma só**: `check_review`; o script e a API chamam o mesmo código; o teste `test_review_api.py` cobre as mesmas recusas |
| DIV-30 | Política de unidade fora da tabela v1 (ex.: °C) na revisão | Com a regra antiga, esses parâmetros nunca poderiam ser conferidos | Regra estrita: valor igual **e** mesmo texto de unidade; unidade conhecida continua comparada em SI |
| DIV-31 | Vídeo da v2 tinha ~3,8× a velocidade física (13 quadros para 5 s) | O usuário não conseguia observar a evolução | Quadros a cada 0,1 s simulado, todos renderizados, 10 fps (1×); ver ADR-09.7 |
| DIV-32 | Extração lia só 14 páginas (limite da v2) | Cobertura parcial não estava clara | Lotes + cobertura explícita; ADR-09.5 |
| DIV-18 | Schema JSON gerado pelo Pydantic | rejeitado com HTTP 400 por `gemini-3.5-flash-lite` (evidência: `docs/evidence/smoke_gemini_20261114T184138Z.json`) | **Implementado:** schema do provedor declarado à mão (`LLM_OUTPUT_PROVIDER_SCHEMA`); validação estrita mantida no Pydantic |

## 3. Decisões pendentes
| ID | Decisão | Opções | Recomendação | Prazo | Bloqueia |
|---|---|---|---|---|---|
| D-01 | Quantos ensaios curar | 3 / 5 / tabela inteira | **5** (M1 + 4 contrastantes); expandir só depois de G2. *14/11: só M1 curado (BL-02); os demais dependem de DIV-22* | antes de BL-02.05 | F01 |
| D-02 | Layout e fluxo de 3 min | — | Trilha: S02 busca → S03 M1 (origem + lacunas) → S04 comparação + gráfico → S05 pergunta O₂ + pergunta Marte | G1 | BL-07 |
| D-03 | **Provedor e chave de LLM; política offline** — **DECIDIDO (14/11)** | Google Gemini API | Provedor **Google Gemini**, modelo testado **`gemini-3.5-flash-lite`** (`google-genai` + `.env` local). Teste manual de conexão ("FLAMELAB_OK"): **PASS informado pela equipe**. Dois testes manuais com evidência sintética (TEST-01): **PASS informado pela equipe**. **Integração implementada (BL-05.04, 14/11):** adaptador isolado, 66 testes automatizados PASS com provedor simulado; smoke test real com evidência sintética **PASS 3/3** após corrigir o schema (DIV-18); ver `docs/evidence/BL-05_assistente_ia.md`. Modo `cache` continua recomendado na demo | — | — |
| D-04 | Mídia oficial | — | Buscar em PSI-25/NASA; só com licença | G2 | BL-08.02 |
| D-05 | Go/no-go FDS | — | Pré-condição BL-09.00; go/no-go às 09h de 15/11 | 15/11 09h | slide 07 |
| D-06 | Congelamento de escopo e claims | — | G3 (funcionalidades) e G5 (roteiro) | ver 08 | pitch |
| D-07 | Eixos de estado (DIV-01) | campo único DM / três eixos | **Três eixos** | antes de BL-02.01 | contrato |
| D-08 | Repositório (remote, visibilidade) e localização do protótipo | — | GitHub da equipe; pedir o protótipo a quem o escreveu | imediato | F00 |
| D-09 | O PDF entra no git? | sim / só hash | *14/11: **só hash** (49 MB; `sources/*.pdf` ignorado; termos NTRS a confirmar). Hash conferido em `docs/evidence/source_hash_check_*`* | BL-01.04 | — |
| D-11 | **Quem faz a revisão humana de M1** (BL-02.07) | pessoa da equipe ≠ extrator | Escolher 1 revisor agora; ~15 min com `scripts/review_record.py`. Bloqueia P-02 e o teste de resposta real | **imediato** | P-02, P-05 |
| D-10 | Idioma das respostas da IA | PT / PT+citação EN | PT com o trecho citado em EN | BL-05.05 | — |
| D-16 | **Quem pode revisar e como se evita a auto-aprovação** (identidade não autenticada, R-22) | lista de revisores autorizados no repositório / autenticação / manter o nome declarado + auditoria | Por ora, auditoria + política de equipe (revisor ≠ extrator); lista de nomes autorizados na produção | antes de usar a revisão fora da equipe | confiança nas aprovações |
| D-17 | Limite de lotes por documento e ritmo entre chamadas (R-23) | 8 / todos / configurável por documento | Padrão 8; configurável (`FLAMELAB_EXTRACT_MAX_BATCHES`); aceitar leitura parcial declarada | produção | documentos longos |
| D-18 | Quadros por segundo simulado do vídeo (hoje 10/s, 1×) | 10 / 20 / 30 | Manter 10; aumentar só se o custo de saída justificar | produção | fluidez do vídeo |
| D-12 | Aprovar ADR-09 (execução de FDS em worker isolado) | aprovar / manter execução manual | **Aprovar**, com a limitação R-15 explícita | antes de expor a terceiros | uso fora da máquina local |
| D-13 | Quando `PSI-25` deixa de ser “candidato” | revisão humana do vínculo; ou citação cruzada | Revisor humano registra a decisão; nunca automático | com D-11 | rótulo “confirmado” |
| D-14 | Onde fica a revisão humana de parâmetros importados | `scripts/review_record.py` só no dataset curado / tela na UI | Tela de revisão (BL-12.12), mantendo as recusas do script | produção | promoção de itens importados |
| D-15 | Segundo executor (Linux/Xvfb) e contêiner | adiar / já | Adiar; registrar R-15/R-16 | produção | hospedagem |

## 4. Hipóteses assumidas neste plano
- H-1: a Tabela 5.1 do NASA/TM-20210011385 é texto selecionável (não imagem). Verificar no BL-02.04.
- H-2: há pelo menos 4 outros ensaios na Tabela 5.1 com os mesmos campos de M1.
- H-3: a equipe tem pelo menos 2 pessoas capazes de conferir valores no PDF.
- H-4: a máquina de demo é Windows, com Python 3.12 e Node ≥18.
- H-5: a demo pode rodar em `127.0.0.1` sem restrição da rede do evento.

## 5. Critérios para reduzir ou ampliar o escopo
| Situação | Ação |
|---|---|
| G1 não alcançado até o fim da tarde de 14/11 | Cortar BL-08 inteiro e F08; reduzir para 3 ensaios |
| D-03 sem solução até G1 | IA só com cache gerado em outro ambiente; se não houver nenhum, P-05/P-06 BLOQUEADO e o reforço vai para ranking + comparação (os verbos classificar e interpretar via regras) |
| G2 alcançado com folga antes da meia-noite | Liberar BL-08.01 (esquema), BL-02.12 (crosscheck) e, por último, F08 documental |
| FDS VERIFIED + §5.5 com dimensões do duto | Liberar BL-09.04 (escoamento frio) com time-box |
| Qualquer teste MUST falha após G3 | Remover a funcionalidade da trilha e rebaixar o status em 06; não corrigir ao vivo |
