import json
from pathlib import Path
import pytest
from aztlan_route.providers import Provider, load_providers

def test_load_catalog():
    catalog = Path(__file__).parents[1] / "config" / "providers.json"
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
    entry = {"id":"same","name":"Same","url":"https://example.com",
             "browser_support":["chromium"],"integration_mode":"manual_browser",
             "automation_allowed":False,"notes":"test"}
    path = tmp_path / "providers.json"
    path.write_text(json.dumps({"schema_version":1,"providers":[entry,entry]}))
    with pytest.raises(ValueError, match="unique"):
        load_providers(path)
