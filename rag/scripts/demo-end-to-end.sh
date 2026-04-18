#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="python3"
QUESTION="What chunk size and overlap are recommended for a first RAG system?"
TOP_K="3"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
DATA_PATH="${REPO_ROOT}/rag/sample_data"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --data-path)
      DATA_PATH="$2"
      shift 2
      ;;
    --question)
      QUESTION="$2"
      shift 2
      ;;
    --top-k)
      TOP_K="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is not set." >&2
  exit 1
fi

cd "${REPO_ROOT}"

echo "== Smoke test =="
"${PYTHON_BIN}" -m rag.scripts.smoke_test --path "${DATA_PATH}"

echo
echo "== Build index =="
"${PYTHON_BIN}" -m rag.cli build-index "${DATA_PATH}"

echo
echo "== List documents =="
"${PYTHON_BIN}" -m rag.cli list-docs

echo
echo "== Query =="
"${PYTHON_BIN}" -m rag.cli query "${QUESTION}" --top-k "${TOP_K}"
