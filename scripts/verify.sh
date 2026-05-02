#!/usr/bin/env bash
# 実装→検証タイトループ用のハーネス。
# Claude Code 開発チームの内部実践 (小さく変更→即検証→次へ) を本リポに移植。
#
# 使い方:
#   bash scripts/verify.sh            # 全部
#   bash scripts/verify.sh quick      # pytest + JSON のみ
#   bash scripts/verify.sh py         # pytest のみ
#   bash scripts/verify.sh seed       # seed JSON 妥当性のみ
#   bash scripts/verify.sh sol        # Solidity 軽量構文チェックのみ
#
# 失敗時は最初に落ちたチェックの所で exit 1 して、原因を即可視化する。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-all}"

step() { printf "\n\033[1;36m[verify:%s]\033[0m %s\n" "$1" "$2"; }
ok()   { printf "  \033[1;32m✓\033[0m %s\n" "$1"; }
fail() { printf "  \033[1;31m✗\033[0m %s\n" "$1" >&2; exit 1; }

run_pytest() {
  step "pytest" "backend ユニットテスト"
  ( cd backend && python -m pytest -q ) || fail "pytest 失敗"
  ok "pytest"
}

run_seed_check() {
  step "seed" "seed/*.json の妥当性 (必須キー・参照整合)"
  python scripts/check_seed.py || fail "seed 妥当性 NG"
  ok "seed"
}

run_sol_check() {
  step "sol" "contracts/*.sol の軽量構文チェック"
  python scripts/check_sol.py || fail "Solidity 構文 NG"
  ok "sol"
}

run_front_js_check() {
  step "front" "frontend/*.html の inline JS 構文チェック"
  python scripts/check_frontend_js.py || fail "frontend JS 構文 NG"
  ok "front"
}

run_offline_fallback_e2e() {
  step "cp6" "CP-6 オフラインフォールバック スモークテスト"
  ( cd backend && python -m pytest -q tests/test_offline_fallback.py ) \
    || fail "CP-6 スモーク NG"
  ok "cp6"
}

run_sweep_dryrun() {
  step "sweep" "期限切れ PBM の dry-run sweep"
  python scripts/cron_sweep.py 2>&1 | sed 's/^/    /' || fail "sweep NG"
  ok "sweep"
}

run_load() {
  step "load" "100 並列 × 100 反復のスモーク負荷試験"
  if ! python -c "import httpx" 2>/dev/null; then
    printf "  \033[1;33m⊝\033[0m httpx 未インストール — skip\n"
    return 0
  fi
  # 内蔵 uvicorn を一時的に立ち上げて叩く (port 8765)
  ( cd backend && JPN_PBM_DB_URL=sqlite:////tmp/loadtest.db python -c "
import uvicorn, threading, time, sys, os
from app.main import app
cfg = uvicorn.Config(app, host='127.0.0.1', port=8765, log_level='warning')
srv = uvicorn.Server(cfg)
import threading
t = threading.Thread(target=srv.run, daemon=True); t.start()
for _ in range(40):
    if srv.started: break
    time.sleep(0.1)
" > /tmp/loadsrv.log 2>&1 ) &
  local LSPID=$!
  ( cd backend && JPN_PBM_DB_URL=sqlite:////tmp/loadtest.db uvicorn app.main:app \
      --host 127.0.0.1 --port 8766 --log-level warning > /tmp/loadsrv2.log 2>&1 ) &
  local LSPID2=$!
  # wait for server
  for i in 1 2 3 4 5 6 7 8; do
    if curl -sf http://127.0.0.1:8766/api > /dev/null 2>&1; then break; fi
    sleep 0.4
  done
  python scripts/loadtest.py --base http://127.0.0.1:8766 --concurrency 20 --iters 20 \
    | sed 's/^/    /' || { kill $LSPID2 2>/dev/null; rm -f /tmp/loadtest.db; fail "load NG"; }
  kill $LSPID $LSPID2 2>/dev/null
  wait 2>/dev/null
  rm -f /tmp/loadtest.db
  ok "load"
}

run_e2e() {
  step "e2e" "Playwright E2E (tokyo→citizen→retailer 通し)"
  if ! command -v playwright >/dev/null 2>&1; then
    printf "  \033[1;33m⊝\033[0m Playwright 未インストール — skip\n"
    return 0
  fi
  if [ ! -d "$HOME/.cache/ms-playwright" ] && [ ! -x "$(command -v chromium)" ] && [ ! -x "$(command -v google-chrome)" ]; then
    printf "  \033[1;33m⊝\033[0m ブラウザ未インストール — skip (実環境で 'cd e2e && npm i && npx playwright install chromium' 後に再実行)\n"
    return 0
  fi
  ( cd e2e && npx playwright test --reporter=list ) || fail "E2E NG"
  ok "e2e"
}

case "$MODE" in
  py)    run_pytest ;;
  seed)  run_seed_check ;;
  sol)   run_sol_check ;;
  cp6)   run_offline_fallback_e2e ;;
  sweep) run_sweep_dryrun ;;
  e2e)   run_e2e ;;
  front) run_front_js_check ;;
  load)  run_load ;;
  quick) run_pytest; run_seed_check ;;
  all|*) run_pytest; run_seed_check; run_sol_check; run_front_js_check ;;
esac

printf "\n\033[1;32m✓ verify(%s) all green\033[0m\n" "$MODE"
