#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="python3"
QUESTION="What chunk size and overlap are recommended for a first RAG system?"
TOP_K="3"
GENERATOR_MODEL="Qwen/Qwen2.5-7B-Instruct"
EMBEDDING_MODEL="BAAI/bge-m3"
DEVICE="cpu"
DTYPE="auto"

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
    --generator-model)
      GENERATOR_MODEL="$2"
      shift 2
      ;;
    --embedding-model)
      EMBEDDING_MODEL="$2"
      shift 2
      ;;
    --device)
      DEVICE="$2"
      shift 2
      ;;
    --dtype)
      DTYPE="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

cd "${REPO_ROOT}"

echo "== Smoke test =="
"${PYTHON_BIN}" -m rag.scripts.smoke_test --path "${DATA_PATH}"

echo
echo "== Build local index =="
EMBEDDING_BACKEND=local \
LOCAL_EMBEDDING_MODEL="${EMBEDDING_MODEL}" \
ENABLE_RERANKER=false \
"${PYTHON_BIN}" -m rag.cli build-index "${DATA_PATH}"

echo
echo "== List documents =="
"${PYTHON_BIN}" -m rag.cli list-docs

echo
echo "== Local Qwen query =="
EMBEDDING_BACKEND=local \
LOCAL_EMBEDDING_MODEL="${EMBEDDING_MODEL}" \
GENERATOR_BACKEND=local \
LOCAL_GENERATOR_MODEL="${GENERATOR_MODEL}" \
LOCAL_GENERATOR_DEVICE="${DEVICE}" \
LOCAL_GENERATOR_DTYPE="${DTYPE}" \
ENABLE_RERANKER=false \
"${PYTHON_BIN}" -m rag.cli query "${QUESTION}" --top-k "${TOP_K}"
