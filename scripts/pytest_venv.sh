#!/usr/bin/env bash
# scripts/pytest_venv.sh
#
# Create/refresh a local venv for running pytest, install deps, then run pytest.
# Works even if your repo path contains spaces.

set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv-pytest}"
PYTEST_ARGS=()

usage() {
  cat <<'EOF'
Usage:
  scripts/pytest_venv.sh [--recreate] [--no-run] [--] [pytest args...]

Env vars:
  VENV_DIR=.venv-pytest   (default)
  PYTHON=python3.13       (optional; overrides python selection)

Examples:
  ./scripts/pytest_venv.sh
  ./scripts/pytest_venv.sh -- -q
  VENV_DIR=.venv ./scripts/pytest_venv.sh --recreate -- -k config
EOF
}

RECREATE=0
RUN=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --recreate) RECREATE=1; shift ;;
    --no-run) RUN=0; shift ;;
    --) shift; PYTEST_ARGS+=("$@"); break ;;
    *) PYTEST_ARGS+=("$1"); shift ;;
  esac
done

# Find repo root as "parent of this script"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

# Pick python (prefer user override, then python3.13, then python3)
PYTHON_BIN="${PYTHON:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python3.13 >/dev/null 2>&1; then
    PYTHON_BIN="python3.13"
  else
    PYTHON_BIN="python3"
  fi
fi

if [[ "${RECREATE}" -eq 1 && -d "${VENV_DIR}" ]]; then
  echo "Removing existing venv: ${VENV_DIR}"
  rm -rf "${VENV_DIR}"
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating venv in: ${VENV_DIR}  (python: ${PYTHON_BIN})"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# Activate venv
# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip/setuptools/wheel..."
python -m pip install --upgrade pip setuptools wheel >/dev/null

echo "Installing project + test deps..."
# Try dev extras first; if your pyproject doesn't define them, fall back.
if python -m pip install -e ".[dev]" >/dev/null 2>&1; then
  echo "Installed editable with [dev] extras."
else
  echo "No [dev] extras (or install failed). Falling back to minimal test deps..."
  python -m pip install -e . >/dev/null
  python -m pip install pytest pytest-mock >/dev/null
fi

echo "Sanity check imports..."
python - <<'PY'
mods = ["pytest"]
optional = ["pydantic", "pydantic_settings", "psutil"]
import importlib
for m in mods + optional:
    try:
        importlib.import_module(m)
        print(f"OK: {m}")
    except Exception as e:
        print(f"WARN: {m} -> {e}")
PY

if [[ "${RUN}" -eq 1 ]]; then
  echo "Running pytest ${PYTEST_ARGS[*]-} ..."
  pytest "${PYTEST_ARGS[@]}"
else
  echo "Venv ready. Activate with: source ${VENV_DIR}/bin/activate"
fi

