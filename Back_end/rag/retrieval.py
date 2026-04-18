from __future__ import annotations

from dataclasses import replace
from typing import Any

from .config import Settings
from .indexing import VectorIndex
from .models import ChunkHit
from .stores import MetadataStore, chunk_record_to_hit
from .utils import normalize_inline_text, truncate_text


class QueryPreprocessor:
    def preprocess(self, question: str) -> str:
        normalized = normalize_inline_text(question)
        if not normalized:
            raise ValueError("Question must not be empty.")
        return normalized


class OptionalReranker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = settings.enable_reranker
        self._model: Any | None = None

    def _get_model(self) -> Any | None:
        if not self.enabled:
            return None
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import CrossEncoder
        except Exception:
            self.enabled = False
            return None

        self._model = CrossEncoder(self.settings.reranker_model)
        return self._model

    def rerank(self, question: str, chunks: list[ChunkHit]) -> list[ChunkHit]:
        if not self.enabled or not chunks:
            return chunks

        model = self._get_model()
        if model is None:
            return chunks

        pairs = [(question, truncate_text(chunk.text, 1400)) for chunk in chunks]
        scores = model.predict(pairs)
        scored = [
            replace(chunk, rerank_score=float(score))
            for chunk, score in zip(chunks, scores)
        ]
        scored.sort(key=lambda item: item.rerank_score or float("-inf"), reverse=True)

        threshold = self.settings.rerank_score_threshold
        if threshold is None:
            return scored
        return [chunk for chunk in scored if (chunk.rerank_score or float("-inf")) >= threshold]


class Retriever:
    def __init__(self, settings: Settings, vector_index: VectorIndex, metadata_store: MetadataStore):
        self.settings = settings
        self.vector_index = vector_index
        self.metadata_store = metadata_store
        self.preprocessor = QueryPreprocessor()
        self.reranker = OptionalReranker(settings)

    def retrieve(self, question: str, top_k: int | None = None) -> tuple[str, list[ChunkHit], list[ChunkHit]]:
        normalized_question = self.preprocessor.preprocess(question)
        desired_top_k = top_k or self.settings.retrieval_top_k
        fetch_k = max(desired_top_k, self.settings.retrieval_fetch_k)

        vectorstore = self.vector_index.load()
        raw_hits = vectorstore.similarity_search_with_score(normalized_question, k=fetch_k)

        if not raw_hits:
            return normalized_question, [], []

        chunk_ids = [doc.metadata.get("chunk_id") for doc, _score in raw_hits if doc.metadata.get("chunk_id")]
        stored_chunks = self.metadata_store.get_chunks(chunk_ids)

        retrieved_chunks: list[ChunkHit] = []
        for doc, distance in raw_hits:
            chunk_id = doc.metadata.get("chunk_id")
            chunk_record = stored_chunks.get(chunk_id) if chunk_id else None
            hit = chunk_record_to_hit(chunk_record) if chunk_record else ChunkHit(
                source_id=None,
                chunk_id=chunk_id or "unknown",
                doc_id=doc.metadata.get("doc_id", "unknown"),
                title=doc.metadata.get("title", "unknown"),
                text=doc.page_content,
                page_start=doc.metadata.get("page_start"),
                page_end=doc.metadata.get("page_end"),
                section=doc.metadata.get("section"),
                metadata=doc.metadata,
            )
            hit.retrieval_score = self._distance_to_similarity(distance)
            retrieved_chunks.append(hit)

        reranked_chunks = self.reranker.rerank(normalized_question, retrieved_chunks)
        supporting_chunks = reranked_chunks[:desired_top_k]
        numbered_support = [
            replace(chunk, source_id=index)
            for index, chunk in enumerate(supporting_chunks, start=1)
        ]
        return normalized_question, retrieved_chunks, numbered_support

    def _distance_to_similarity(self, distance: float) -> float:
        return float(1.0 / (1.0 + max(distance, 0.0)))
