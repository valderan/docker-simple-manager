#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON_BIN="python3.13"

info() {
  printf '\033[1;34m[setup]\033[0m %s\n' "$1"
}

if ! command -v uv >/dev/null 2>&1; then
  info "uv is not installed. Falling back to standard venv and pip."
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    info "Using fallback interpreter: $PYTHON_BIN"
  fi

  "$PYTHON_BIN" -m venv "$VENV_PATH"
  # shellcheck source=/dev/null
  source "$VENV_PATH/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install -e ".[dev]"
else
  info "Using uv for dependency management."
  uv venv "$VENV_PATH"
  # shellcheck source=/dev/null
  source "$VENV_PATH/bin/activate"
  uv pip install -e ".[dev]"
fi

info "Installing pre-commit hooks (if configured)."
if [ -f "$PROJECT_ROOT/.pre-commit-config.yaml" ]; then
  pre-commit install
else
  info "No .pre-commit-config.yaml found yet. Skipping."
fi

info "Setup complete. Activate the environment with 'source .venv/bin/activate'."
