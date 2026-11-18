export interface ModelDefinition {
  id: string;
  name: string;
  enabled: boolean;
}
export interface ProviderDefinition {
  id: string;
  name: string;
  transport: "openai-compatible";
  base_url: string;
  api_key_env: string;
  enabled: boolean;
  models: ModelDefinition[];
}
export interface Catalog {
  providers: ProviderDefinition[];
}
