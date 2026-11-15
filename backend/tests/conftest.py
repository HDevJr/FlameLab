import pytest

from backend.app.api.platform import Services


def _clean():
    Services.reset()
    Services.transport_factory = None
    Services.executor = None
    Services.dataset_dirs = None
    Services.curation_log_dir = None


@pytest.fixture(autouse=True)
def _isolated_workspace(tmp_path, monkeypatch):
    """Cada teste usa um var/ próprio; nada de rede por padrão; nenhum executor real;
    revisões nunca escrevem no data/ nem nos logs reais do repositório."""
    monkeypatch.setenv("FLAMELAB_VAR_DIR", str(tmp_path / "var"))
    monkeypatch.setenv("FLAMELAB_NASA_MODE", "fixture")
    _clean()
    Services.provider = None
    Services.run_async = False
    Services.quota_wait_s = 0
    Services.curation_log_dir = tmp_path / "curation_logs"
    yield
    _clean()
    Services.provider = "unset"
    Services.run_async = True
    Services.quota_wait_s = None
