# Checklist de validação humana (o que só uma pessoa pode fechar)

Registre o resultado de cada linha (PASS / FAIL / NOT_RUN), a data, quem testou e o aparelho. Não marque PASS sem executar.

## 1. Celular de verdade

1. Backend: `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000` (somente localhost).
2. Frontend exposto na rede local: `cd frontend; npm run dev -- --host`. O Vite repassa `/api` ao backend, que continua fechado à rede.
3. No celular, na mesma rede Wi-Fi, abra o endereço `Network` que o Vite imprime (ex.: `http://192.168.x.x:5173`). Use só em rede de confiança e feche o servidor depois.
4. Verifique, em retrato e paisagem:

| # | Teste | Resultado |
|---|---|---|
| 1 | Menu abre/fecha com o polegar; não cobre conteúdo | |
| 2 | Ficha M1: parâmetros em cartões, "Ver origem" abre o painel | |
| 3 | Assistente: com o teclado aberto, o campo e o botão Enviar continuam visíveis | |
| 4 | Assistente: texto digitado não dá zoom automático (iOS) | |
| 5 | Documento: "Abrir em nova aba" abre o PDF na página certa | |
| 6 | Tela de resultado: o vídeo toca e os controles são tocáveis | |
| 7 | Nenhuma tela tem rolagem horizontal da página | |

## 2. Roteiro manual S01–S07

Execute `docs/manual_test_roteiro_S01-S07.md` e registre o resultado de cada passo neste arquivo ou no próprio roteiro. O status "validação visual" do frontend só deixa de ser `NOT_RUN` depois disso.

## 3. Leitor de tela (opcional, mas recomendado)

NVDA (Windows) ou VoiceOver (iOS): percorrer a ficha M1 e o Assistente. Conferir se estados (conferido, ausente, bloqueado) são lidos por texto, e não só por cor.

## O que já foi verificado automaticamente (não repetir)
- Teclado em Chrome real: `scripts/check_keyboard.py` (Tab, foco visível, Enter, Esc) — ver `docs/evidence/keyboard_check_*.json`.
- Sem rolagem horizontal e alvos de toque ≥ 44 px, em 360–1920 px, por emulação de viewport.
