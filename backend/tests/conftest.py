import pytest

from backend.app.api.platform import Services


@pytest.fixture(autouse=True)
def _isolated_workspace(tmp_path, monkeypatch):
    """Cada teste usa um var/ próprio; nada de rede por padrão; nenhum executor real."""
    monkeypatch.setenv("FLAMELAB_VAR_DIR", str(tmp_path / "var"))
    monkeypatch.setenv("FLAMELAB_NASA_MODE", "fixture")
    Services.reset()
    Services.transport_factory = None
    Services.executor = None
    Services.provider = None
    Services.run_async = False
    yield
    Services.reset()
    Services.executor = None
    Services.provider = "unset"
    Services.run_async = True
