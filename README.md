# RAG-Course-Assistant
 Course RAG — Dashboard Web App 
# 🎓 Course Q&A Assistant

> A **Retrieval-Augmented Generation (RAG)** demo built for the NTU AI6130 Large Language Models course.  
> Compare Direct LLM answers vs. RAG-grounded answers side by side, with evidence-backed citations.

![Dashboard Preview](docs/preview.png)

---

## ✨ Features

- **Side-by-side comparison** — Direct LLM vs. RAG answer panels with typing animation
- **PDF ingestion pipeline** — Upload course slides, visualize Parse → Chunk → Embed → Index stages
- **Clickable citations** — Inline `[n]` markers link to source document snippets with similarity scores
- **Evaluation metrics** — Answer Correctness and Citation Hit Rate bar charts
- **Language control** — Auto / Chinese / English answer language, English terminology toggle
- **Dark dashboard UI** — Glassmorphism panels, animated background, responsive layout

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│             Browser (Frontend)           │
│  index.html · styles.css · src/main.js  │
│         src/api/client.js               │
└────────────────┬────────────────────────┘
                 │ REST API (JSON)
                 ▼
┌─────────────────────────────────────────┐
│           Backend  (Python)             │
│  FastAPI · LangChain · Vector DB        │
├─────────────────────────────────────────┤
│  POST /api/v1/query                     │
│  POST /api/v1/documents/upload          │
│  GET  /api/v1/documents                 │
└─────────────────────────────────────────┘
```

**RAG Pipeline:**
```
PDF Upload → Parse → Chunk → Embed (sentence-transformers) → Index (FAISS / Chroma)
                                                                    ↓
User Query → Embed Query → Retrieve Top-K Chunks → Augment Prompt → LLM → Answer + Citations
```

---

## 📁 Project Structure

```
AI6130-RAG/
├── Front_End/
│   ├── index.html          # Main dashboard UI
│   ├── styles.css          # Dark theme design system
│   ├── serve.ps1           # PowerShell dev server (Windows)
│   ├── src/
│   │   ├── main.js         # App logic, rendering, state
│   │   ├── config.js       # Runtime config (apiBaseUrl, topK)
│   │   └── api/
│   │       └── client.js   # Fetch wrappers for all API calls
│   └── README.md
├── Back_End/               # Python backend (FastAPI)
│   ├── main.py
│   ├── requirements.txt
│   └── ...
└── README.md               # ← You are here
```

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/AI6130-RAG.git
cd AI6130-RAG
```

### 2. Start the backend

```bash
cd Back_End
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

> Make sure CORS is configured to allow `http://localhost:5173`.

### 3. Start the frontend

```powershell
# Windows PowerShell
cd Front_End
powershell -ExecutionPolicy Bypass -File .\serve.ps1 -Port 5173
```

Open **http://localhost:5173** in your browser.

### 4. Try it out

1. Upload one or more course PDF slides via **Document Library**
2. Type a question, e.g. *"What is the difference between RAG and fine-tuning?"*
3. Click **Run Comparison** — watch both panels fill in
4. Click any `[n]` citation to inspect the source chunk

---

## ⚙️ Configuration

Override the default backend URL before loading `main.js` in `index.html`:

```html
<script>
  window.__RAG_DEMO_CONFIG__ = {
    apiBaseUrl: "https://your-backend.onrender.com",
    topK: 4,
    requestTimeoutMs: 20000
  };
</script>
```

| Key | Default | Description |
|-----|---------|-------------|
| `apiBaseUrl` | `http://localhost:8000` | Backend base URL |
| `topK` | `4` | Number of retrieved chunks |
| `requestTimeoutMs` | `20000` | API call timeout (ms) |

---

## 📡 API Contract

### `GET /api/v1/documents`
Returns list of indexed documents.

### `POST /api/v1/documents/upload`
Multipart form upload, field name: `file`.

### `POST /api/v1/query`

**Request:**
```json
{
  "question": "What is RAG?",
  "top_k": 4,
  "answer_language": "auto",
  "terminology_policy": "english_terms_preferred"
}
```

**Response:**
```json
{
  "questionId": "q-123",
  "directAnswer": "...",
  "ragAnswer": "... [1][2] ...",
  "citations": [
    { "id": 1, "title": "Lecture-5.pdf", "page": 8, "score": 0.91, "text": "..." }
  ],
  "metrics": {
    "correctness": { "direct": 0.62, "rag": 0.89 },
    "citationHitRate": { "direct": 0.0, "rag": 0.93 }
  },
  "runtime": { "directMs": 980, "ragMs": 1410 }
}
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla JS (ES Modules), CSS Variables |
| Fonts | Space Grotesk, Noto Sans SC |
| Backend | Python, FastAPI |
| Embeddings | sentence-transformers |
| Vector Store | FAISS / Chroma |
| LLM | OpenAI / local model |

---

## 📚 Course Context

This project was built as part of **AI6130 — Large Language Models** at NTU/NUS.  
It demonstrates core RAG concepts covered in the course:

- Dense retrieval and semantic similarity
- Chunk-level evidence attribution
- Evaluation of answer quality vs. grounded generation

---

## 📄 License

MIT — feel free to fork and adapt for your own course projects.
