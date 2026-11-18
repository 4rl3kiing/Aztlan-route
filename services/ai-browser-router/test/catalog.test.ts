import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { loadCatalog } from "../src/config.js";
import { Registry } from "../src/registry.js";

test("loads declarative providers and exposes enabled models", async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), "aztlan-router-"));
  try {
    await writeFile(path.join(dir, "provider.yaml"), [
      "id: test", "name: Test", "transport: openai-compatible",
      "base_url: https://api.example.test/v1", "api_key_env: TEST_API_KEY", "enabled: true",
      "models:", "  - id: model-a", "    name: Model A", "    enabled: true", ""
    ].join("\n"));
    const registry = new Registry(await loadCatalog(dir));
    assert.equal(registry.listModels()[0]?.id, "model-a");
    assert.equal(registry.resolve("model-a").provider.id, "test");
    assert.throws(() => registry.resolve("missing"), /Unknown or disabled model/);
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test("rejects non-HTTPS provider endpoints", async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), "aztlan-router-"));
  try {
    await writeFile(path.join(dir, "bad.yaml"), [
      "id: bad", "name: Bad", "transport: openai-compatible",
      "base_url: http://127.0.0.1:8080/v1", "api_key_env: BAD_API_KEY", "enabled: true", "models: []", ""
    ].join("\n"));
    await assert.rejects(loadCatalog(dir), /HTTPS/);
  } finally { await rm(dir, { recursive: true, force: true }); }
});
