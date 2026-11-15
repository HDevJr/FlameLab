// BL-17.2: modo de trabalho da revisão guiada. A preferência fica só neste navegador; o servidor
// isola os registros do modo TESTE em `var/test_mode/` e nunca os mistura com dados científicos.
import { useSyncExternalStore } from "react";
import type { WorkMode } from "./api";

const KEY = "flamelab.workMode";
const listeners = new Set<() => void>();

function read(): WorkMode {
  try { return localStorage.getItem(KEY) === "TEST" ? "TEST" : "SCIENTIFIC"; } catch { return "SCIENTIFIC"; }
}
let current: WorkMode = read();

export function setWorkMode(mode: WorkMode) {
  current = mode;
  try { localStorage.setItem(KEY, mode); } catch { /* preferência opcional */ }
  listeners.forEach((l) => l());
}

export function useWorkMode(): [WorkMode, (m: WorkMode) => void] {
  const mode = useSyncExternalStore((l) => { listeners.add(l); return () => listeners.delete(l); }, () => current, () => current);
  return [mode, setWorkMode];
}

/** Para testes: volta ao modo científico. */
export function resetWorkMode() { current = "SCIENTIFIC"; listeners.forEach((l) => l()); }
