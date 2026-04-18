from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .chunking import Chunker
from .config import Settings
from .indexing import VectorIndex
from .models import IndexBuildResult, ParsedDocument, QueryResult
from .parsing import DocumentParser
from .stores import MetadataStore


class IndexingPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.parser = DocumentParser(settings)
        self.chunker = Chunker(
            target_tokens=settings.chunk_target_tokens,
            max_tokens=settings.chunk_max_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        )
        self.metadata_store = MetadataStore(settings.metadata_db_path)
        self.vector_index = VectorIndex(settings)

    def build(self, paths: list[str | Path]) -> IndexBuildResult:
        file_paths, skipped_files = self._collect_files(paths)
        if not file_paths:
            joined_paths = ", ".join(str(path) for path in paths)
            raise FileNotFoundError(
                f"No supported files were found for indexing. Checked: {joined_paths}"
            )

        documents: list[ParsedDocument] = []
        chunks = []

        for path in file_paths:
            document = self.parser.parse(path)
            documents.append(document)
            chunks.extend(self.chunker.chunk_document(document))

        self.metadata_store.replace_corpus(documents, chunks)
        self.vector_index.build(chunks)
        return IndexBuildResult(
            indexed_documents=len(documents),
            indexed_chunks=len(chunks),
            skipped_files=skipped_files,
        )

    def _collect_files(self, paths: list[str | Path]) -> tuple[list[Path], list[str]]:
        resolved_paths: list[Path] = []
        skipped_files: list[str] = []

        for item in paths:
            path = Path(item).expanduser().resolve()
            if not path.exists():
                skipped_files.append(str(path))
                continue

            if path.is_dir():
                for child in sorted(path.rglob("*")):
                    if child.is_file() and child.suffix.lower() in self.settings.supported_extensions:
                        resolved_paths.append(child)
                continue

            if path.suffix.lower() in self.settings.supported_extensions:
                resolved_paths.append(path)
            else:
                skipped_files.append(str(path))

        unique_paths = list(dict.fromkeys(resolved_paths))
        return unique_paths, skipped_files


class QueryPipeline:
    def __init__(self, settings: Settings):
        from .generation import AnswerGenerator
        from .retrieval import Retriever

        self.settings = settings
        self.metadata_store = MetadataStore(settings.metadata_db_path)
        self.vector_index = VectorIndex(settings)
        self.retriever = Retriever(settings, self.vector_index, self.metadata_store)
        self.generator = AnswerGenerator(settings)

    def run(self, question: str, top_k: int | None = None) -> QueryResult:
        normalized_question, retrieved_chunks, supporting_chunks = self.retriever.retrieve(
            question=question,
            top_k=top_k,
        )
        answer = self.generator.answer(normalized_question, supporting_chunks)
        used_fallback = answer.strip() == "I don't know based on the provided materials."
        decision = "needs_human_escalation" if used_fallback else "sendable"

        citations = [
            replace(
                chunk,
                text=chunk.text if len(chunk.text) <= 1000 else chunk.text[:997] + "...",
            )
            for chunk in supporting_chunks
        ]

        return QueryResult(
            question=question,
            normalized_question=normalized_question,
            answer=answer,
            direct_answer=None,
            citations=citations,
            supporting_chunks=supporting_chunks,
            retrieved_chunks=retrieved_chunks,
            used_fallback=used_fallback,
            decision=decision,
        )


class RAGSystem:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.indexing = IndexingPipeline(settings)
        self.querying = QueryPipeline(settings)

    def build_index(self, paths: list[str | Path]) -> IndexBuildResult:
        return self.indexing.build(paths)

    def query(self, question: str, top_k: int | None = None) -> QueryResult:
        return self.querying.run(question, top_k=top_k)

    def list_documents(self):
        return self.indexing.metadata_store.list_documents()

    def health(self) -> dict[str, object]:
        return {
            "vector_db_loaded": self.querying.vector_index.is_built(),
            "documents_indexed": self.indexing.metadata_store.document_count(),
            "chunks_indexed": self.indexing.metadata_store.chunk_count(),
            "reranker_enabled": self.querying.retriever.reranker.enabled,
        }
