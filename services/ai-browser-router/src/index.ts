import http from "node:http";
import { timingSafeEqual } from "node:crypto";
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
const host = "127.0.0.1";
const port = Number(process.env.AZTLAN_ROUTER_PORT ?? 8765);
const accessToken = process.env.AZTLAN_ROUTER_ACCESS_TOKEN ?? "";
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid AZTLAN_ROUTER_PORT");
if (accessToken.length < 32) throw new Error("AZTLAN_ROUTER_ACCESS_TOKEN must contain at least 32 characters");

function authorized(header: string | undefined): boolean {
  if (!header?.startsWith("Bearer ")) return false;
  const supplied = Buffer.from(header.slice(7), "utf8");
  const expected = Buffer.from(accessToken, "utf8");
  return supplied.length === expected.length && timingSafeEqual(supplied, expected);
}

const server = http.createServer(async (req, res) => {
  res.setHeader("x-content-type-options", "nosniff");
  res.setHeader("x-frame-options", "DENY");
  res.setHeader("referrer-policy", "no-referrer");
  res.setHeader("content-security-policy", "default-src 'none'; frame-ancestors 'none'");
  res.setHeader("cache-control", "no-store");
  if (!authorized(req.headers.authorization)) {
    res.writeHead(401, { "content-type": "application/json", "www-authenticate": "Bearer" });
    res.end(JSON.stringify({ error: { message: "Unauthorized" } }));
    return;
  }
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ status: "ok", providers: providers.filter(p => p.enabled).length }));
    return;
  }
  if (req.method === "GET" && req.url === "/v1/models") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ object: "list", data: registry.listModels() }));
    return;
  }
  if (req.method !== "POST" || req.url !== "/v1/chat/completions") {
    res.writeHead(404, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: { message: "Not found" } }));
    return;
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
    res.writeHead(400, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: { message: "Invalid JSON body" } }));
    return;
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
server.listen(port, host, () => process.stdout.write(`Aztlan router listening on http://${host}:${port}\\n`));
