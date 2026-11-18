import type { ProviderDefinition } from "./types.js";

export class Registry {
  constructor(readonly providers: ProviderDefinition[]) {}
  listModels() {
    return this.providers.filter(p => p.enabled).flatMap(p =>
      p.models.filter(m => m.enabled).map(m => ({ id: m.id, object: "model", created: 0, owned_by: p.id, name: m.name }))
    );
  }
  resolve(modelId: string) {
    for (const provider of this.providers) {
      if (!provider.enabled) continue;
      const model = provider.models.find(m => m.enabled && m.id === modelId);
      if (model) return { provider, model };
    }
    throw Object.assign(new Error(`Unknown or disabled model: ${modelId}`), { status: 404 });
  }
}
