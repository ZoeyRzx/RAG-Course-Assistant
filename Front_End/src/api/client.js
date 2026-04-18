import { appConfig } from "../config.js";

function buildUrl(pathname) {
  return `${appConfig.apiBaseUrl}${pathname}`;
}

function withTimeout(promise) {
  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => reject(new Error("Request timeout")), appConfig.requestTimeoutMs);
  });
  return Promise.race([promise, timeoutPromise]);
}

async function request(pathname, options) {
  const response = await withTimeout(fetch(buildUrl(pathname), options));
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
}

export async function listDocuments() {
  return request("/api/v1/documents", { method: "GET" });
}

export async function uploadDocument(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);
  const result = await request("/api/v1/documents/upload", {
    method: "POST",
    body: formData,
  });

  if (onProgress) {
    onProgress(100);
  }
  return result;
}

export async function askQuestion(question, options = {}) {
  return request("/api/v1/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      top_k: appConfig.topK,
      answer_language: options.answerLanguage || "auto",
      terminology_policy: options.englishTerms
        ? "english_terms_preferred"
        : "localized_terms",
      }),
  });
}
