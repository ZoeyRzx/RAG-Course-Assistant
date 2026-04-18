#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="python3"
QUESTION="What is retrieval-augmented generation?"
TOP_K="3"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"
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

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is not set." >&2
  exit 1
fi

cd "${REPO_ROOT}"
"${PYTHON_BIN}" -m rag.cli query "${QUESTION}" --top-k "${TOP_K}"
