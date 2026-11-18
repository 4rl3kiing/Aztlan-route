from pathlib import Path
import sys

import pytest
from platformdirs import user_data_dir


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux XDG layout only")
def test_linux_data_directory_matches_uninstaller_contract():
    data_path = Path(user_data_dir("Aztlan-route", "Aztlan"))
    assert data_path.parts[-2:] == ("Aztlan", "Aztlan-route")
