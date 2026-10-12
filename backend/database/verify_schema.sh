#!/usr/bin/env bash
set -euo pipefail

# Locate repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "Running Database Schema Verification Suite..."
cd "${REPO_ROOT}"

# Run Python verification suite
if [ -d "backend/.venv" ]; then
    if [ -f "backend/.venv/bin/python" ]; then
        PYTHON_BIN="backend/.venv/bin/python"
    elif [ -f "backend/.venv/Scripts/python.exe" ]; then
        PYTHON_BIN="backend/.venv/Scripts/python.exe"
    else
        PYTHON_BIN="python3"
    fi
else
    PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" backend/database/verify_schema.py
