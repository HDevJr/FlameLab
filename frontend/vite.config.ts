import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// O backend (FastAPI) roda em 127.0.0.1:8000; o proxy evita CORS no desenvolvimento.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
  test: { environment: "node" },
});
