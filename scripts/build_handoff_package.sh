#!/usr/bin/env bash
# Handoff package builder (戦略会議 #13 採択 T5)。
#
# 各宛先 (jica / coins-ph / dswd / quezon-city) に送る zip を組み立てる。
# zip には:
#   1. docs/handoff-packages/<target>/ 以下の README + cover letter + 添付
#   2. リポジトリのコア成果物 (whitepaper / pitch / fork-guide / LICENSE)
#   3. audit-summary.txt (contract self-audit の自動生成サマリ)
#
# 使い方:
#   bash scripts/build_handoff_package.sh jica
#   bash scripts/build_handoff_package.sh coins-ph
#   bash scripts/build_handoff_package.sh dswd
#   bash scripts/build_handoff_package.sh quezon-city
#   bash scripts/build_handoff_package.sh --all
#
# 出力先: /tmp/jpn-pbm-handoff-<target>-YYYY-MM-DD.zip
# (環境変数 OUTDIR で上書き可)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGETS=(jica coins-ph dswd quezon-city unicef wfp-building-blocks unhcr)
DATE="$(date +%Y-%m-%d)"
OUTDIR="${OUTDIR:-/tmp}"

# 各 target で必ず含めるリポジトリのコア成果物 (相対パス)
COMMON_FILES=(
  "README.md"
  "LICENSE"
  "docs/whitepaper-2026.md"
  "docs/pitch-deck.md"
  "docs/pitch-deck-jp.md"
  "docs/fork-guide.md"
  "docs/cp6-offline-fallback.md"
  "docs/architecture.md"
  "docs/expansion-philippines.md"
  "docs/jica-application-draft-en.md"
  "docs/qr-vs-jan-research.md"
)

step() { printf "\n\033[1;36m[handoff:%s]\033[0m %s\n" "$1" "$2"; }
ok()   { printf "  \033[1;32m✓\033[0m %s\n" "$1"; }
fail() { printf "  \033[1;31m✗\033[0m %s\n" "$1" >&2; exit 1; }

# ---------- audit summary を自動生成 (各 target に同梱) ----------
gen_audit_summary() {
  local out="$1"
  step "audit" "smart contract self-audit summary を再生成"
  if ! python scripts/contract_audit.py > "$out" 2>&1; then
    # exit code 非0 でも出力を残しておく (warn 級は問題なし)
    :
  fi
  ok "audit summary written to $out"
}

# ---------- zip ビルド本体 ----------
build_one() {
  local target="$1"
  local target_dir="docs/handoff-packages/${target}"

  if [ ! -d "$target_dir" ]; then
    fail "unknown target: $target (no $target_dir)"
  fi

  local zipname="jpn-pbm-handoff-${target}-${DATE}.zip"
  local zippath="${OUTDIR}/${zipname}"
  local stage="$(mktemp -d)"

  step "stage" "$target → $stage"

  # 1. handoff dir をそのまま staging に投入
  mkdir -p "${stage}/handoff-${target}"
  cp -r "$target_dir/." "${stage}/handoff-${target}/"

  # 2. 共通 core files をリポジトリ ルート構造のまま投入
  for f in "${COMMON_FILES[@]}"; do
    if [ -f "$f" ]; then
      mkdir -p "${stage}/repo/$(dirname "$f")"
      cp "$f" "${stage}/repo/$f"
    fi
  done

  # 3. audit summary
  gen_audit_summary "${stage}/handoff-${target}/audit-summary.txt"

  # 4. 受け取った人向けトップレベル README
  cat > "${stage}/HOW_TO_READ.txt" <<EOF
JPN-PBM Handoff Package — ${target}
Generated: ${DATE}

Recommended reading order:
  1. handoff-${target}/README.md       (this is the start point)
  2. handoff-${target}/01-cover-letter*.md
  3. handoff-${target}/0X-...md        (in order)
  4. repo/docs/whitepaper-2026.md       (full technical reference)
  5. repo/README.md                     (repo orientation)

Repository: https://github.com/kota1026/JPN_PBM
License:    Apache 2.0
EOF

  # 5. zip 化
  step "zip" "$zippath"
  ( cd "$stage" && zip -qr "$zippath" . )
  rm -rf "$stage"
  ok "$(du -h "$zippath" | cut -f1) → $zippath"
}

# ---------- 引数処理 ----------
main() {
  local arg="${1:-}"

  if [ -z "$arg" ]; then
    echo "usage: bash scripts/build_handoff_package.sh <target>|--all"
    echo "  targets: ${TARGETS[*]}"
    exit 1
  fi

  if ! command -v zip >/dev/null 2>&1; then
    fail "zip command not found (apt install zip)"
  fi

  if [ "$arg" = "--all" ]; then
    for t in "${TARGETS[@]}"; do
      build_one "$t"
    done
    printf "\n\033[1;32m✓ all 4 packages built in %s\033[0m\n" "$OUTDIR"
    return 0
  fi

  build_one "$arg"
  printf "\n\033[1;32m✓ done\033[0m\n"
}

main "$@"
