#!/usr/bin/env bash
# Codespaces / Dev Container にアタッチされた時に毎回実行される。
# uvicorn を foreground で起動するので、停止は Ctrl+C。
set -euo pipefail

cd "$(dirname "$0")/../backend"

echo "==> JPN PBM サーバ起動 (http://localhost:8000)"
echo "    UI  : http://localhost:8000/ui/index.html"
echo "    Docs: http://localhost:8000/docs"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
