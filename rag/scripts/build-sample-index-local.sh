#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="python3"
EMBEDDING_MODEL="BAAI/bge-m3"

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
    --embedding-model)
      EMBEDDING_MODEL="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

cd "${REPO_ROOT}"
EMBEDDING_BACKEND=local \
LOCAL_EMBEDDING_MODEL="${EMBEDDING_MODEL}" \
ENABLE_RERANKER=false \
"${PYTHON_BIN}" -m rag.cli build-index "${DATA_PATH}"
