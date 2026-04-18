# AI6130 Course Q&A Assistant - Front_End Build

This folder is a frontend-only build for integration testing.

## Current frontend functionality

- No mock mode. All requests go to real backend APIs.
- Multi-file PDF upload in one batch.
- Upload progress pipeline display:
- `Parse PDF`
- `Chunk Text`
- `Create Embeddings`
- `Index in Vector DB`
- Document library list from backend (`name`, `pages`, `chunks`, `status`, `createdAt`).
- Question input and run button.
- Answer style controls:
- `answer_language`: `auto` / `zh` / `en`
- `terminology_policy`: English terms preferred toggle
- Side-by-side answer panels:
- `Direct LLM` panel
- `RAG Answer` panel
- Per-panel latency display (`directMs`, `ragMs`).
- Citation interaction:
- Parse inline citation markers like `[1]` in RAG answer
- Click citation marker or citation list item to view source snippet detail
- Evaluation panel charts:
- `Answer Correctness` (Direct vs RAG)
- `Citation Hit Rate` (Direct vs RAG)

## Removed in this build

- Mock mode toggle
- Sample question buttons
- User rating UI and `User Score` chart
- Feedback API call from frontend

## Prerequisites

- Backend service is running and reachable.
- Backend CORS allows frontend origin.
- Required backend endpoints:
- `GET /api/v1/documents`
- `POST /api/v1/documents/upload`
- `POST /api/v1/query`

## Run frontend (Windows PowerShell)

```powershell
# run from repository root
cd .\Front_End
powershell -ExecutionPolicy Bypass -File .\serve.ps1 -Port 5173
```

Open: `http://localhost:5173`

## Backend URL and runtime config

Default backend URL is `http://localhost:8000`.

If needed, set runtime config in `index.html` before:

```html
<script type="module" src="./src/main.js"></script>
```

Example:

```html
<script>
  window.__RAG_DEMO_CONFIG__ = {
    apiBaseUrl: "http://localhost:8000",
    topK: 4,
    requestTimeoutMs: 20000
  };
</script>
```

## API contract used by this frontend

### 1) List documents

- Method: `GET`
- Path: `/api/v1/documents`

Response item:

```json
{
  "id": "doc-1",
  "name": "Lecture-1.pdf",
  "pages": 42,
  "chunks": 135,
  "status": "ready",
  "createdAt": "2026-04-07 10:20"
}
```

### 2) Upload one PDF

- Method: `POST`
- Path: `/api/v1/documents/upload`
- Content-Type: `multipart/form-data`
- Field name: `file`

Note: frontend uploads selected files one by one in sequence.

### 3) Query (Direct + RAG)

- Method: `POST`
- Path: `/api/v1/query`

Request:

```json
{
  "question": "What is retrieval-augmented generation?",
  "top_k": 4,
  "answer_language": "auto",
  "terminology_policy": "english_terms_preferred"
}
```

Response:

```json
{
  "questionId": "q-123",
  "directAnswer": "Direct LLM answer text",
  "ragAnswer": "RAG answer text with citations [1][2]",
  "citations": [
    {
      "id": 1,
      "title": "Lecture-5.pdf",
      "page": 8,
      "score": 0.91,
      "text": "evidence snippet..."
    }
  ],
  "metrics": {
    "correctness": { "direct": 0.62, "rag": 0.89 },
    "citationHitRate": { "direct": 0.0, "rag": 0.93 }
  },
  "runtime": { "directMs": 980, "ragMs": 1410 }
}
```

Field mapping used by frontend:

- Direct answer panel uses `directAnswer`.
- RAG answer panel uses `ragAnswer`.
- Citation list/detail uses `citations`.
- Evaluation charts use `metrics.correctness` and `metrics.citationHitRate`.
- Latency tags use `runtime.directMs` and `runtime.ragMs`.
- Query tag uses `questionId`.

## Quick integration check

1. Start backend and verify `GET /healthz` returns success.
2. Start frontend with `serve.ps1`.
3. Open `http://localhost:5173`.
4. Upload at least one PDF.
5. Ask one question and confirm both panels render.
6. Click a citation `[n]` in RAG answer and confirm citation detail updates.

## Common failures

- 404 on API calls:
- backend path prefix is not `/api/v1`
- CORS error in browser:
- backend CORS not configured for frontend origin
- Query returns empty citations:
- no indexed documents yet, or retrieval pipeline not ready
