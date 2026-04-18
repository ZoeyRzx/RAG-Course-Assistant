from __future__ import annotations

import argparse
import json
import sys

from .config import get_settings
from .serialization import to_jsonable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Course material RAG backend utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_index = subparsers.add_parser("build-index", help="Parse documents and rebuild the vector index.")
    build_index.add_argument("paths", nargs="+", help="PDF / Markdown / text files or directories.")

    query = subparsers.add_parser("query", help="Run a RAG query against the current index.")
    query.add_argument("question", help="Question to ask.")
    query.add_argument("--top-k", type=int, default=None, help="Number of supporting chunks to keep.")

    subparsers.add_parser("list-docs", help="List indexed documents.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()

    try:
        if args.command == "build-index":
            from .pipelines import IndexingPipeline

            result = IndexingPipeline(settings).build(args.paths)
            print(json.dumps(to_jsonable(result), indent=2))
            return

        if args.command == "query":
            from .pipelines import QueryPipeline

            result = QueryPipeline(settings).run(args.question, top_k=args.top_k)
            print(json.dumps(to_jsonable(result), indent=2))
            return

        if args.command == "list-docs":
            from .stores import MetadataStore

            result = MetadataStore(settings.metadata_db_path).list_documents()
            print(json.dumps(to_jsonable(result), indent=2))
            return

        parser.error(f"Unknown command: {args.command}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
