from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .config import Settings
from .embeddings import LocalSentenceTransformerEmbeddings
from .models import ChunkRecord


class VectorIndex:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._embeddings: Any | None = None
        self._vectorstore: Any | None = None

    def _get_embeddings(self) -> Any:
        if self._embeddings is None:
            if self.settings.embedding_backend == "openai":
                from langchain_openai import OpenAIEmbeddings

                self._embeddings = OpenAIEmbeddings(model=self.settings.embedding_model)
            elif self.settings.embedding_backend == "local":
                self._embeddings = LocalSentenceTransformerEmbeddings(
                    model_name=self.settings.local_embedding_model,
                    device=self.settings.local_embedding_device,
                    normalize_embeddings=self.settings.local_embedding_normalize,
                )
            else:
                raise ValueError(f"Unsupported embedding backend: {self.settings.embedding_backend}")
        return self._embeddings

    def build(self, chunks: list[ChunkRecord]) -> None:
        index_path = self.settings.vector_db_path
        index_path.parent.mkdir(parents=True, exist_ok=True)

        if index_path.exists():
            self._reset_index_dir(index_path)

        if not chunks:
            self._vectorstore = None
            return

        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document

        documents = [
            Document(
                page_content=chunk.text,
                metadata={
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "section": chunk.section,
                    **chunk.metadata,
                },
            )
            for chunk in chunks
        ]
        vectorstore = FAISS.from_documents(documents, self._get_embeddings())
        vectorstore.save_local(str(index_path))
        self._vectorstore = vectorstore

    def load(self) -> Any:
        if self._vectorstore is not None:
            return self._vectorstore
        if not self.settings.vector_db_path.exists():
            raise FileNotFoundError(f"Vector index not found: {self.settings.vector_db_path}")

        from langchain_community.vectorstores import FAISS

        self._vectorstore = FAISS.load_local(
            str(self.settings.vector_db_path),
            self._get_embeddings(),
            allow_dangerous_deserialization=True,
        )
        return self._vectorstore

    def is_built(self) -> bool:
        return self.settings.vector_db_path.exists()

    def _reset_index_dir(self, index_path: Path) -> None:
        resolved = index_path.resolve()
        storage_root = self.settings.data_dir.resolve()
        if storage_root not in resolved.parents and resolved != storage_root:
            raise ValueError(f"Refusing to delete index outside storage dir: {resolved}")
        shutil.rmtree(resolved)
