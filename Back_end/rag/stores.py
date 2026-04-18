from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import ChunkRecord, ChunkHit, DocumentSummary, ParsedDocument


class MetadataStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    structure_json TEXT NOT NULL,
                    page_count INTEGER,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    text TEXT NOT NULL,
                    page_start INTEGER,
                    page_end INTEGER,
                    section TEXT,
                    token_count INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks(chunk_index);
                """
            )

    def replace_corpus(self, documents: list[ParsedDocument], chunks: list[ChunkRecord]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM chunks")
            connection.execute("DELETE FROM documents")

            for document in documents:
                connection.execute(
                    """
                    INSERT INTO documents (
                        doc_id, title, source_path, doc_type, raw_text, structure_json, page_count, metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.doc_id,
                        document.title,
                        document.source_path,
                        document.doc_type,
                        document.raw_text,
                        json.dumps(
                            [
                                {
                                    "block_index": block.block_index,
                                    "text": block.text,
                                    "page": block.page,
                                    "section": block.section,
                                }
                                for block in document.blocks
                            ],
                            ensure_ascii=True,
                        ),
                        document.page_count,
                        json.dumps(document.metadata, ensure_ascii=True),
                    ),
                )

            for chunk in chunks:
                connection.execute(
                    """
                    INSERT INTO chunks (
                        chunk_id, doc_id, chunk_index, title, text, page_start, page_end,
                        section, token_count, metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id,
                        chunk.doc_id,
                        chunk.chunk_index,
                        chunk.title,
                        chunk.text,
                        chunk.page_start,
                        chunk.page_end,
                        chunk.section,
                        chunk.token_count,
                        json.dumps(chunk.metadata, ensure_ascii=True),
                    ),
                )

    def list_documents(self) -> list[DocumentSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    d.doc_id,
                    d.title,
                    d.source_path,
                    d.doc_type,
                    d.page_count,
                    d.created_at,
                    COUNT(c.chunk_id) AS chunk_count
                FROM documents d
                LEFT JOIN chunks c ON c.doc_id = d.doc_id
                GROUP BY d.doc_id
                ORDER BY d.created_at DESC, d.title ASC
                """
            ).fetchall()

        return [
            DocumentSummary(
                doc_id=row["doc_id"],
                title=row["title"],
                source_path=row["source_path"],
                doc_type=row["doc_type"],
                page_count=row["page_count"],
                chunk_count=row["chunk_count"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_chunks(self, chunk_ids: list[str]) -> dict[str, ChunkRecord]:
        if not chunk_ids:
            return {}

        placeholders = ", ".join("?" for _ in chunk_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT chunk_id, doc_id, title, text, chunk_index, page_start, page_end,
                       section, token_count, metadata_json
                FROM chunks
                WHERE chunk_id IN ({placeholders})
                """,
                chunk_ids,
            ).fetchall()

        records: dict[str, ChunkRecord] = {}
        for row in rows:
            records[row["chunk_id"]] = ChunkRecord(
                chunk_id=row["chunk_id"],
                doc_id=row["doc_id"],
                title=row["title"],
                text=row["text"],
                chunk_index=row["chunk_index"],
                page_start=row["page_start"],
                page_end=row["page_end"],
                section=row["section"],
                token_count=row["token_count"],
                metadata=json.loads(row["metadata_json"]),
            )
        return records

    def chunk_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
        return int(row["count"]) if row else 0

    def document_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM documents").fetchone()
        return int(row["count"]) if row else 0


def chunk_record_to_hit(chunk: ChunkRecord) -> ChunkHit:
    return ChunkHit(
        source_id=None,
        chunk_id=chunk.chunk_id,
        doc_id=chunk.doc_id,
        title=chunk.title,
        text=chunk.text,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        section=chunk.section,
        metadata=chunk.metadata,
    )
