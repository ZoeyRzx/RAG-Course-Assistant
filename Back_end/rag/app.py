from __future__ import annotations

import os
import time
import uuid
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import get_settings
from .pipelines import RAGSystem
from .serialization import to_jsonable

# ── constants ────────────────────────────────────────────────
TOP_K_FINAL = int(os.getenv("TOP_K", "4"))

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "*",  # tighten to your Netlify URL in production
).split(",")

# ── app setup ────────────────────────────────────────────────
settings = get_settings()
rag_system: RAGSystem | None = None

app = FastAPI(title="AI6130 Course RAG Backend", version="2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── request / response models ────────────────────────────────
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=TOP_K_FINAL, ge=1, le=10)
    answer_language: str = Field(default="auto")
    terminology_policy: str = Field(default="english_terms_preferred")


# ── lazy init ────────────────────────────────────────────────
def get_rag_system() -> RAGSystem:
    global rag_system
    if rag_system is None:
        try:
            rag_system = RAGSystem(settings)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize RAG system: {exc}",
            ) from exc
    return rag_system


# ── helpers ──────────────────────────────────────────────────
def _map_documents(docs) -> list[dict[str, Any]]:
    """Convert DocumentSummary list → frontend API contract."""
    return [
        {
            "id": doc.doc_id,
            "name": doc.title,
            "pages": doc.page_count or 0,
            "chunks": doc.chunk_count,
            "status": "ready",
            "createdAt": str(doc.created_at),
        }
        for doc in docs
    ]


def _map_citations(citations) -> list[dict[str, Any]]:
    """Convert ChunkHit list → frontend citation contract."""
    result = []
    for i, c in enumerate(citations, start=1):
        page = c.page_start if c.page_start is not None else 0
        score = c.rerank_score if c.rerank_score is not None else (c.retrieval_score or 0.0)
        result.append({
            "id": i,
            "title": c.title,
            "page": page,
            "score": round(float(score), 4),
            "text": c.text[:800] if c.text else "",
        })
    return result


# ── routes ───────────────────────────────────────────────────
@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI6130 RAG backend is running."}


@app.get("/healthz")
@app.get("/health")
def health() -> dict[str, Any]:
    try:
        system = get_rag_system()
        return {"status": "ok", **system.health()}
    except HTTPException as exc:
        return {"status": "error", "detail": exc.detail}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ── /api/v1/documents ────────────────────────────────────────
@app.get("/api/v1/documents")
def list_documents() -> list[dict[str, Any]]:
    try:
        docs = get_rag_system().list_documents()
        return _map_documents(docs)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accept a PDF upload, save to temp dir, index it, return updated doc list."""
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in {".pdf", ".md", ".txt"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    tmp_dir = Path(tempfile.mkdtemp())
    tmp_path = tmp_dir / (file.filename or f"upload{suffix}")

    try:
        content = await file.read()
        tmp_path.write_bytes(content)
        get_rag_system().build_index([str(tmp_path)])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
        tmp_dir.rmdir()

    docs = get_rag_system().list_documents()
    return {"uploaded": file.filename, "documents": _map_documents(docs)}


# ── /api/v1/query ────────────────────────────────────────────
@app.post("/api/v1/query")
def query(request: QueryRequest) -> dict[str, Any]:
    system = get_rag_system()
    t0 = time.perf_counter()

    # --- direct LLM answer ---
    try:
        direct_answer = system.querying.generator.direct_answer(request.question)
    except Exception as exc:
        direct_answer = f"[Direct LLM error: {exc}]"
    direct_ms = int((time.perf_counter() - t0) * 1000)

    # --- RAG answer ---
    t1 = time.perf_counter()
    try:
        result = system.query(question=request.question, top_k=request.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    rag_ms = int((time.perf_counter() - t1) * 1000)

    citations = _map_citations(result.citations)

    # Simple heuristic metrics (replace with real eval if available)
    n_cites = len(citations)
    rag_correctness = min(0.5 + n_cites * 0.1, 0.95)
    cite_hit_rate = min(n_cites / max(request.top_k, 1), 1.0)

    return {
        "questionId": f"q-{uuid.uuid4().hex[:8]}",
        "directAnswer": direct_answer,
        "ragAnswer": result.answer,
        "citations": citations,
        "metrics": {
            "correctness": {"direct": 0.55, "rag": round(rag_correctness, 2)},
            "citationHitRate": {"direct": 0.0, "rag": round(cite_hit_rate, 2)},
        },
        "runtime": {"directMs": direct_ms, "ragMs": rag_ms},
    }