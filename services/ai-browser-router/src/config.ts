import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "yaml";
import type { ProviderDefinition } from "./types.js";

const ID = /^[a-z0-9][a-z0-9._-]{0,63}$/;
const ENV = /^[A-Z][A-Z0-9_]{1,127}$/;

function validateProvider(value: unknown, file: string): ProviderDefinition {
  if (!value || typeof value !== "object") throw new Error(`Invalid provider document: ${file}`);
  const p = value as Record<string, unknown>;
  if (typeof p.id !== "string" || !ID.test(p.id)) throw new Error(`Invalid provider id: ${file}`);
  if (typeof p.name !== "string" || !p.name.trim()) throw new Error(`Invalid provider name: ${file}`);
  if (p.transport !== "openai-compatible") throw new Error(`Unsupported transport in ${file}`);
  if (typeof p.base_url !== "string") throw new Error(`Missing base_url: ${file}`);
  const url = new URL(p.base_url);
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash)
    throw new Error(`Provider base_url must be a clean HTTPS URL: ${file}`);
  if (typeof p.api_key_env !== "string" || !ENV.test(p.api_key_env))
    throw new Error(`Invalid api_key_env: ${file}`);
  if (typeof p.enabled !== "boolean" || !Array.isArray(p.models))
    throw new Error(`Invalid enabled/models fields: ${file}`);
  const models = p.models.map((item: unknown) => {
    if (!item || typeof item !== "object") throw new Error(`Invalid model in ${file}`);
    const m = item as Record<string, unknown>;
    if (typeof m.id !== "string" || !m.id.trim() || m.id.length > 200 ||
        typeof m.name !== "string" || typeof m.enabled !== "boolean")
      throw new Error(`Invalid model entry in ${file}`);
    return { id: m.id, name: m.name, enabled: m.enabled };
  });
  if (new Set(models.map(m => m.id)).size !== models.length)
    throw new Error(`Duplicate model id in ${file}`);
  return { id: p.id, name: p.name, transport: "openai-compatible", base_url: url.toString().replace(/\/$/, ""), api_key_env: p.api_key_env, enabled: p.enabled, models };
}

export async function loadCatalog(directory: string): Promise<ProviderDefinition[]> {
  const entries = (await readdir(directory)).filter(name => name.endsWith(".yaml") || name.endsWith(".yml")).sort();
  const providers: ProviderDefinition[] = [];
  for (const name of entries) {
    const file = path.join(directory, name);
    const provider = validateProvider(parse(await readFile(file, "utf8")), name);
    providers.push(provider);
  }
  if (new Set(providers.map(p => p.id)).size !== providers.length) throw new Error("Duplicate provider id");
  return providers;
}
