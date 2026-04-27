#!/usr/bin/env bash
# Codespaces / VS Code Dev Container 初回起動時に1度だけ実行される。
# Python 依存をインストールし、サンプル DB が空なら seed を促す。
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Python 依存をインストール"
pip install --upgrade pip
pip install -r backend/requirements.txt

echo
echo "==> セットアップ完了"
echo "    起動: bash .devcontainer/start.sh"
echo "    UI  : http://localhost:8000/ui/index.html"
echo "    API : http://localhost:8000/docs"
