const runtimeConfig = window.__RAG_DEMO_CONFIG__ || {};

export const appConfig = {
  apiBaseUrl: runtimeConfig.apiBaseUrl || "http://localhost:8000",
  topK: runtimeConfig.topK || 4,
  requestTimeoutMs: runtimeConfig.requestTimeoutMs || 20000,
};
