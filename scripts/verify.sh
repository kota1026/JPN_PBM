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

run_offline_fallback_e2e() {
  step "cp6" "CP-6 オフラインフォールバック スモークテスト"
  ( cd backend && python -m pytest -q tests/test_offline_fallback.py ) \
    || fail "CP-6 スモーク NG"
  ok "cp6"
}

case "$MODE" in
  py)    run_pytest ;;
  seed)  run_seed_check ;;
  sol)   run_sol_check ;;
  cp6)   run_offline_fallback_e2e ;;
  quick) run_pytest; run_seed_check ;;
  all|*) run_pytest; run_seed_check; run_sol_check ;;
esac

printf "\n\033[1;32m✓ verify(%s) all green\033[0m\n" "$MODE"
