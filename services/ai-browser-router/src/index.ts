import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadCatalog } from "./config.js";
import { Registry } from "./registry.js";
import { Router } from "./router.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const catalogDir = path.resolve(process.env.AZTLAN_ROUTER_CATALOG ?? path.join(root, "config/providers"));
const providers = await loadCatalog(catalogDir);
const registry = new Registry(providers);
const router = new Router(registry);
const host = process.env.AZTLAN_ROUTER_HOST ?? "127.0.0.1";
const port = Number(process.env.AZTLAN_ROUTER_PORT ?? 8765);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid AZTLAN_ROUTER_PORT");
if (host !== "127.0.0.1" && host !== "::1" && process.env.AZTLAN_ROUTER_ALLOW_REMOTE !== "1")
  throw new Error("Remote bind refused; set AZTLAN_ROUTER_ALLOW_REMOTE=1 only behind an authenticated gateway");

const server = http.createServer(async (req, res) => {
  res.setHeader("x-content-type-options", "nosniff");
  res.setHeader("cache-control", "no-store");
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "content-type": "application/json" }); res.end(JSON.stringify({ status: "ok", providers: providers.filter(p => p.enabled).length })); return;
  }
  if (req.method === "GET" && req.url === "/v1/models") {
    res.writeHead(200, { "content-type": "application/json" }); res.end(JSON.stringify({ object: "list", data: registry.listModels() })); return;
  }
  if (req.method !== "POST" || req.url !== "/v1/chat/completions") {
    res.writeHead(404, { "content-type": "application/json" }); res.end(JSON.stringify({ error: { message: "Not found" } })); return;
  }
  let raw = "";
  req.setEncoding("utf8");
  for await (const chunk of req) {
    raw += chunk;
    if (Buffer.byteLength(raw) > 1_048_576) { res.writeHead(413); res.end(); return; }
  }
  let body: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Expected JSON object");
    body = parsed as Record<string, unknown>;
  } catch {
    res.writeHead(400, { "content-type": "application/json" }); res.end(JSON.stringify({ error: { message: "Invalid JSON body" } })); return;
  }
  try {
    const upstream = await router.complete(body);
    res.writeHead(upstream.status, {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      ...(upstream.headers.get("cache-control") ? { "cache-control": upstream.headers.get("cache-control")! } : {})
    });
    if (!upstream.body) { res.end(); return; }
    const reader = upstream.body.getReader();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (!res.write(value)) await new Promise<void>(resolve => res.once("drain", resolve));
      }
      res.end();
    } finally { reader.releaseLock(); }
  } catch (error) {
    const e = error as Error & { status?: number };
    if (!res.headersSent) {
      res.writeHead(e.status ?? 502, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { message: e.message || "Upstream request failed" } }));
    } else res.destroy();
  }
});
server.listen(port, host, () => process.stdout.write(`Aztlan router listening on http://${host}:${port}\n`));
