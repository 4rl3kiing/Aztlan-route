import type { Registry } from "./registry.js";

export class Router {
  constructor(private readonly registry: Registry, private readonly timeoutMs = 120000) {}
  async complete(body: Record<string, unknown>, signal?: AbortSignal): Promise<Response> {
    if (typeof body.model !== "string" || !body.model) throw Object.assign(new Error("model is required"), { status: 400 });
    const { provider, model } = this.registry.resolve(body.model);
    const key = process.env[provider.api_key_env];
    if (!key) throw Object.assign(new Error(`Missing environment variable ${provider.api_key_env}`), { status: 503 });
    const timeout = AbortSignal.timeout(this.timeoutMs);
    const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;
    return fetch(`${provider.base_url}/chat/completions`, {
      method: "POST",
      headers: { "authorization": `Bearer ${key}`, "content-type": "application/json", "accept": "application/json, text/event-stream" },
      body: JSON.stringify({ ...body, model: model.id }),
      signal: combined
    });
  }
}
