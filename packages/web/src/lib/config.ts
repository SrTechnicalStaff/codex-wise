/**
 * Settings persisted in localStorage.
 * Keys are prefixed with "codex_wise_".
 * All helpers are safe to call in SSR — they return defaults when window is undefined.
 */

const KEYS = {
  apiKey: "codex_wise_api_key",
  apiUrl: "codex_wise_api_url",
  provider: "codex_wise_default_provider",
  model: "codex_wise_default_model",
  embedder: "codex_wise_embedder",
} as const;

const LEGACY_KEYS: Record<string, string> = {
  [KEYS.apiKey]: "repowise_api_key",
  [KEYS.apiUrl]: "repowise_api_url",
  [KEYS.provider]: "repowise_default_provider",
  [KEYS.model]: "repowise_default_model",
  [KEYS.embedder]: "repowise_embedder",
};

function read(key: string): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(key) ?? localStorage.getItem(LEGACY_KEYS[key] ?? "") ?? "";
}

function write(key: string, value: string): void {
  if (typeof window === "undefined") return;
  if (value) {
    localStorage.setItem(key, value);
  } else {
    localStorage.removeItem(key);
  }
}

export const config = {
  getApiKey: () => read(KEYS.apiKey),
  setApiKey: (v: string) => write(KEYS.apiKey, v),

  getApiUrl: () => read(KEYS.apiUrl),
  setApiUrl: (v: string) => write(KEYS.apiUrl, v),

  getProvider: () => read(KEYS.provider) || "litellm",
  setProvider: (v: string) => write(KEYS.provider, v),

  getModel: () => read(KEYS.model),
  setModel: (v: string) => write(KEYS.model, v),

  getEmbedder: () => read(KEYS.embedder) || "mock",
  setEmbedder: (v: string) => write(KEYS.embedder, v),
};
