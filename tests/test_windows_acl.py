from pathlib import Path
from unittest.mock import patch

from aztlan_route.browser import _apply_windows_acl


def test_windows_acl_restricts_profile_to_user_and_system(tmp_path):
    target = tmp_path / "profile"
    target.mkdir()
    with patch("aztlan_route.browser.getpass.getuser", return_value="test-user"), patch(
        "aztlan_route.browser.subprocess.run"
    ) as run:
        _apply_windows_acl(target)
    args = run.call_args.args[0]
    assert args[0] == "icacls"
    assert str(target) in args
    assert "/inheritance:r" in args
    assert "test-user:(OI)(CI)F" in args
    assert "SYSTEM:(OI)(CI)F" in args
    assert run.call_args.kwargs["check"] is True
    assert run.call_args.kwargs["timeout"] == 15
