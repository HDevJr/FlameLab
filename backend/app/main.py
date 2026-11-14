"""FlameLab F00 — apenas infraestrutura mínima, sem acesso NASA/LLM/FDS."""

from fastapi import FastAPI

app = FastAPI(title="FlameLab API", version="0.0.0-f00")


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    """Não implica que IA, dados ou FDS estejam disponíveis."""
    return {"status": "ok", "stage": "F00"}
