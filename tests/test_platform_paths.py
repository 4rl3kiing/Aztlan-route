import sys
from pathlib import Path

import pytest
from platformdirs import user_data_dir


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux XDG layout only")
def test_linux_data_directory_matches_uninstaller_contract(monkeypatch, tmp_path):
    xdg_data_home = tmp_path / "xdg-data"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))
    data_path = Path(user_data_dir("Aztlan-route", "Aztlan"))
    assert data_path == xdg_data_home / "Aztlan-route"
