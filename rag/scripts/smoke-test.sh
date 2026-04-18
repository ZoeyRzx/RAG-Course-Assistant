#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="python3"

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
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

cd "${REPO_ROOT}"
"${PYTHON_BIN}" -m rag.scripts.smoke_test --path "${DATA_PATH}"
