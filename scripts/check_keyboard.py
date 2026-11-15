"""Checagem de teclado (Tab/Shift+Tab/Enter/Esc) com Chrome real via Playwright. Acionamento explícito.

Exige o frontend em http://localhost:5173 (npm run dev) e o backend em :8000.
Para cada rota: percorre o foco com Tab, registra os elementos, exige foco visível e ausência de armadilha.
Grava docs/evidence/keyboard_check_<UTC>.json. Uso: python scripts/check_keyboard.py (no venv)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
ROUTES = ["/", "/importar", "/assistente", "/validacao-fds", "/demonstracao-fds", "/execucoes", "/auditoria",
          "/experimentos/BASS2-M1", "/documentos/NASA-TM-20210011385", "/documentos/NASA-TM-20210011385/analise"]
DESCRIBE = """() => { const a = document.activeElement; if (!a || a === document.body) return null;
  const cs = getComputedStyle(a); const visible = (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || cs.boxShadow !== 'none';
  const name = (a.getAttribute('aria-label') || a.textContent || a.value || a.placeholder || a.id || '').trim().slice(0, 40);
  const r = a.getBoundingClientRect();
  return { tag: a.tagName, name, visible, inView: r.bottom > 0 && r.top < innerHeight, inMain: !!a.closest('main'), inSide: !!a.closest('.side') }; }"""


def run_route(page, route: str, tabs: int = 40) -> dict:
    page.goto(BASE + route)
    page.wait_for_timeout(1800)
    seen, hidden_focus, trap = [], [], False
    for _ in range(tabs):
        page.keyboard.press("Tab")
        d = page.evaluate(DESCRIBE)
        if d is None:
            continue
        seen.append(d)
        if not d["visible"]:
            hidden_focus.append(f'{d["tag"]} {d["name"]}')
    keys = [f'{d["tag"]}|{d["name"]}' for d in seen]
    trap = len(keys) > 8 and len(set(keys)) <= 2  # preso em poucos elementos
    return {"route": route, "focusable_reached": len(set(keys)), "reaches_main": any(d["inMain"] for d in seen),
            "without_visible_focus": sorted(set(hidden_focus))[:8], "keyboard_trap": trap}


def main() -> int:
    out = {"executed_at_utc": datetime.now(timezone.utc).isoformat(), "browser": "chrome (Playwright)", "routes": [], "checks": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        for r in ROUTES:
            out["routes"].append(run_route(page, r))
        # Assistente: foco no campo, digitar, Enter envia, resposta anunciada
        page.goto(BASE + "/assistente"); page.wait_for_timeout(1200)
        page.focus("#ask-input"); page.keyboard.type("Qual era a pressão no ensaio M1?"); page.keyboard.press("Enter"); page.wait_for_timeout(3500)
        out["checks"]["assistant_enter_sends"] = page.locator(".ai-answer").count() == 1
        # Menu no celular: abrir com Enter, fechar com Esc, foco volta ao botão
        m = browser.new_page(viewport={"width": 412, "height": 923}); m.goto(BASE + "/"); m.wait_for_timeout(1500)
        m.focus(".menu-btn"); m.keyboard.press("Enter"); m.wait_for_timeout(300)
        opened = m.evaluate("document.querySelector('.shell').classList.contains('nav-open')")
        m.keyboard.press("Escape"); m.wait_for_timeout(300)
        out["checks"]["mobile_menu"] = {"opens_with_enter": opened, "closes_with_esc": m.evaluate("!document.querySelector('.shell').classList.contains('nav-open')"),
                                        "focus_returns": m.evaluate("document.activeElement.classList.contains('menu-btn')")}
        browser.close()
    bad = [r for r in out["routes"] if r["without_visible_focus"] or r["keyboard_trap"] or not r["reaches_main"]]
    out["overall"] = "PASS" if not bad and out["checks"]["assistant_enter_sends"] and all(out["checks"]["mobile_menu"].values()) else "FAIL"
    path = Path(__file__).resolve().parents[1] / "docs" / "evidence" / f"keyboard_check_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("overall=" + out["overall"], "->", path.name)
    for r in bad:
        print("  atenção:", r)
    return 0 if out["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
