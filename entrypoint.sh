#!/usr/bin/env sh
set -eu
exec /app/.venv/bin/uvicorn rest.app:app --host 0.0.0.0 --port "${PORT:-8000}" "$@"