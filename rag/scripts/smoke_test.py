from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from rag.chunking import Chunker
from rag.config import get_settings
from rag.parsing import DocumentParser
from rag.stores import MetadataStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local parser/chunker/store smoke test.")
    parser.add_argument(
        "--path",
        default=str(Path(__file__).resolve().parent.parent / "sample_data"),
        help="Directory containing markdown/text sample files.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    sample_dir = Path(args.path).resolve()
    settings = get_settings()
    parser = DocumentParser(settings)
    chunker = Chunker(
        target_tokens=settings.chunk_target_tokens,
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )

    documents = []
    chunks = []
    for path in sorted(sample_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        document = parser.parse(path)
        documents.append(document)
        chunks.extend(chunker.chunk_document(document))

    with tempfile.TemporaryDirectory(prefix="rag-smoke-") as temp_dir:
        store = MetadataStore(Path(temp_dir) / "metadata.sqlite3")
        store.replace_corpus(documents, chunks)
        payload = {
            "sample_dir": str(sample_dir),
            "documents": len(documents),
            "chunks": len(chunks),
            "stored_documents": store.document_count(),
            "stored_chunks": store.chunk_count(),
            "document_titles": [document.title for document in documents],
            "first_chunk": asdict(chunks[0]) if chunks else None,
        }

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
