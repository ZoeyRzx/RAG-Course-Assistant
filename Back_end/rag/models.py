from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TextBlock:
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    block_index: int = 0


@dataclass
class ParsedDocument:
    doc_id: str
    title: str
    source_path: str
    doc_type: str
    raw_text: str
    blocks: list[TextBlock]
    page_count: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    chunk_index: int
    page_start: Optional[int]
    page_end: Optional[int]
    section: Optional[str]
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSummary:
    doc_id: str
    title: str
    source_path: str
    doc_type: str
    page_count: Optional[int]
    chunk_count: int
    created_at: str


@dataclass
class ChunkHit:
    source_id: Optional[int]
    chunk_id: str
    doc_id: str
    title: str
    text: str
    page_start: Optional[int]
    page_end: Optional[int]
    section: Optional[str]
    retrieval_score: Optional[float] = None
    rerank_score: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexBuildResult:
    indexed_documents: int
    indexed_chunks: int
    skipped_files: list[str] = field(default_factory=list)


@dataclass
class QueryResult:
    question: str
    normalized_question: str
    answer: str
    direct_answer: str | None
    citations: list[ChunkHit]
    supporting_chunks: list[ChunkHit]
    retrieved_chunks: list[ChunkHit]
    used_fallback: bool
    decision: str
