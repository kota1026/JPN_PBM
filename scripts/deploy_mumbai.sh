#!/usr/bin/env bash
# Polygon Mumbai testnet へのデプロイ orchestrator (戦略会議 #11)
#
# 前提:
#   - foundry がインストール済 (`curl -L https://foundry.paradigm.xyz | bash && foundryup`)
#   - Mumbai testnet wallet に MATIC が入っている (faucet: https://faucet.polygon.technology/)
#   - Test JPYC アドレスが分かっている (なければ自前 ERC20 を deploy する path もあり)
#
# 環境変数:
#   POLYGON_MUMBAI_RPC_URL   alchemy/infura RPC URL (必須)
#   GOVERNOR_PRIVKEY         32 byte hex (必須, 0x prefix なし)
#   JPYC_TESTNET_ADDRESS     Mumbai 上の JPYC test token (必須)
#   POLYGONSCAN_API_KEY      コントラクト verify 用 (任意)
#   DRY_RUN=1                デプロイせず simulate のみ
#
# 使い方:
#   export POLYGON_MUMBAI_RPC_URL=https://polygon-mumbai.g.alchemy.com/v2/XXXXX
#   export GOVERNOR_PRIVKEY=$(openssl rand -hex 32)
#   export JPYC_TESTNET_ADDRESS=0x0000...
#   bash scripts/deploy_mumbai.sh
#
# CI / sandbox 環境ではこのスクリプトを実行しないこと (実 RPC 必要のため).
# ただし `--dry-check` フラグで「環境変数チェック + script syntax 確認」のみ実行可能.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

step() { printf "\n\033[1;36m[deploy:%s]\033[0m %s\n" "$1" "$2"; }
ok()   { printf "  \033[1;32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[1;33m⚠\033[0m %s\n" "$1" >&2; }
fail() { printf "  \033[1;31m✗\033[0m %s\n" "$1" >&2; exit 1; }

DRY_CHECK="${1:-}"
DRY_RUN="${DRY_RUN:-0}"

# ---------- 環境変数チェック ----------
step "env" "deployment 環境変数の確認"
MISSING=()
for var in POLYGON_MUMBAI_RPC_URL GOVERNOR_PRIVKEY JPYC_TESTNET_ADDRESS; do
  if [ -z "${!var:-}" ]; then
    MISSING+=("$var")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  if [ "$DRY_CHECK" = "--dry-check" ]; then
    warn "環境変数未設定 (dry-check モードなので続行): ${MISSING[*]}"
  else
    fail "必須環境変数が未設定: ${MISSING[*]} ─ README 参照"
  fi
else
  ok "環境変数 OK"
fi

# ---------- foundry 確認 ----------
step "tooling" "foundry の確認"
if ! command -v forge >/dev/null 2>&1; then
  if [ "$DRY_CHECK" = "--dry-check" ]; then
    warn "forge 未インストール (dry-check なので続行)"
    warn "実デプロイ時は: curl -L https://foundry.paradigm.xyz | bash && foundryup"
  else
    fail "forge 未インストール ─ curl -L https://foundry.paradigm.xyz | bash && foundryup"
  fi
else
  ok "forge: $(forge --version)"
fi

# ---------- contract syntax の事前チェック ----------
step "syntax" "Sol 構文の事前確認 (check_sol.py)"
python scripts/check_sol.py || fail "Solidity 構文 NG"
ok "syntax"

# ---------- audit ----------
step "audit" "本番デプロイ前 self-audit"
python scripts/contract_audit.py || fail "audit NG (本番デプロイは止めるべき)"
ok "audit"

# dry-check モードはここで終わり
if [ "$DRY_CHECK" = "--dry-check" ]; then
  printf "\n\033[1;32m✓ deploy_mumbai.sh dry-check passed\033[0m\n"
  printf "  実デプロイは: bash scripts/deploy_mumbai.sh (with env vars)\n"
  exit 0
fi

# ---------- forge build ----------
step "build" "forge build"
forge build || fail "build NG"
ok "build"

# ---------- forge script ----------
step "deploy" "Polygon Mumbai (chainId 80001) にデプロイ"

EXTRA_FLAGS=""
if [ "$DRY_RUN" = "1" ]; then
  warn "DRY_RUN=1 ─ broadcast せず simulate のみ"
else
  EXTRA_FLAGS="--broadcast"
fi
if [ -n "${POLYGONSCAN_API_KEY:-}" ]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --verify"
fi

forge script scripts/forge/DeployPBM.s.sol \
  --rpc-url "$POLYGON_MUMBAI_RPC_URL" \
  $EXTRA_FLAGS \
  -vvv || fail "deploy NG ─ 詳細は forge script のログ参照"

ok "deploy"

printf "\n\033[1;32m✓ Polygon Mumbai deployment complete\033[0m\n"
printf "  次に backend を結線: docs/deploy-mumbai.md の §3 参照\n"
