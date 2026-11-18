import json
from pathlib import Path

import pytest

from aztlan_route.providers import Provider, load_providers


def test_load_catalog():
    catalog = Path(__file__).parents[1] / "src" / "aztlan_route" / "providers.json"
    providers = load_providers(catalog)
    assert {p.id for p in providers} >= {"chatgpt", "gemini", "qwen"}


def test_rejects_non_https_provider():
    with pytest.raises(ValueError, match="HTTPS"):
        Provider("unsafe", "Unsafe", "http://example.com", ("chromium",),
                 "manual_browser", False, "test")


def test_rejects_automation_without_documented_integration():
    with pytest.raises(ValueError, match="documented integration"):
        Provider("test", "Test", "https://example.com", ("chromium",),
                 "manual_browser", True, "test")


def test_rejects_duplicate_ids(tmp_path):
    entry = {"id": "same", "name": "Same", "url": "https://example.com",
             "browser_support": ["chromium"], "integration_mode": "manual_browser",
             "automation_allowed": False, "notes": "test"}
    path = tmp_path / "providers.json"
    path.write_text(json.dumps({"schema_version": 1, "providers": [entry, entry]}))
    with pytest.raises(ValueError, match="unique"):
        load_providers(path)


@pytest.mark.parametrize("provider_id", ["x" * 65, "café", "../escape", "bad.id", ""])
def test_rejects_invalid_provider_identifiers(provider_id):
    with pytest.raises(ValueError, match="provider id"):
        Provider(provider_id, "Test", "https://example.com", ("chromium",),
                 "manual_browser", False, "test")


def test_rejects_string_boolean_in_catalog(tmp_path):
    entry = {"id": "safe", "name": "Safe", "url": "https://example.com",
             "browser_support": ["chromium"], "integration_mode": "documented_api",
             "automation_allowed": "false", "notes": "test"}
    path = tmp_path / "providers.json"
    path.write_text(json.dumps({"schema_version": 1, "providers": [entry]}))
    with pytest.raises(ValueError, match="boolean"):
        load_providers(path)


def test_rejects_non_string_catalog_fields(tmp_path):
    entry = {"id": "safe", "name": "Safe", "url": "https://example.com",
             "browser_support": ["chromium", 7], "integration_mode": "manual_browser",
             "automation_allowed": False, "notes": "test"}
    path = tmp_path / "providers.json"
    path.write_text(json.dumps({"schema_version": 1, "providers": [entry]}))
    with pytest.raises(ValueError, match="browser configuration"):
        load_providers(path)
