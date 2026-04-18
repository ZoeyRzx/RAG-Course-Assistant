from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .config import get_settings
from .pipelines import RAGSystem
from .serialization import to_jsonable


settings = get_settings()
rag_system = RAGSystem(settings)

app = FastAPI(title="Course Material RAG Backend", version="2.0")


class BuildIndexRequest(BaseModel):
    paths: list[str] = Field(..., min_items=1)

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=TOP_K_FINAL, ge=1, le=10)
    return_retrieved_docs: bool = True
    include_direct_answer: bool = True

@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Course Material RAG backend is running. Use /health, /documents, /index/rebuild, and /query."
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", **rag_system.health()}


@app.get("/documents")
def list_documents() -> list[dict[str, Any]]:
    return to_jsonable(rag_system.list_documents())


@app.post("/index/rebuild")
def rebuild_index(request: BuildIndexRequest) -> dict[str, Any]:
    try:
        result = rag_system.build_index(request.paths)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return to_jsonable(result)


@app.post("/query")
def query(request: QueryRequest) -> dict[str, Any]:
    try:
        result = rag_system.query(question=request.question, top_k=request.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return to_jsonable({
        "question": result.question,
        "normalized_question": result.normalized_question,
        "direct_answer": result.direct_answer,
        "rag_answer": result.answer,
        "citations": [asdict(item) for item in result.citations],
        "supporting_chunks": [asdict(item) for item in result.supporting_chunks],
        "retrieved_chunks": [asdict(item) for item in result.retrieved_chunks],
        "used_fallback": result.used_fallback,
        "decision": result.decision,
    })
