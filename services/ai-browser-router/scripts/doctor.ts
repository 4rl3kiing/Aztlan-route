import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadCatalog } from "../src/config.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const directory = path.resolve(process.env.AZTLAN_ROUTER_CATALOG ?? path.join(root, "config/providers"));
const providers = await loadCatalog(directory);
let errors = 0;
for (const provider of providers) {
  const configured = Boolean(process.env[provider.api_key_env]);
  const models = provider.models.filter(m => m.enabled).length;
  process.stdout.write(`${provider.id}: enabled=${provider.enabled} models=${models} api_key_configured=${configured}\n`);
  if (provider.enabled && !configured) errors++;
}
process.stdout.write(`Catalog valid: ${providers.length} providers; missing credentials: ${errors}\n`);
if (errors) process.exitCode = 1;
