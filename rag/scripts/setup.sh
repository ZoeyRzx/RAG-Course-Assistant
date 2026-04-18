#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="python3"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"
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
REQUIREMENTS_PATH="${REPO_ROOT}/rag/requirements.txt"

cd "${REPO_ROOT}"
"${PYTHON_BIN}" -m pip install -r "${REQUIREMENTS_PATH}"
