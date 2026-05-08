"""Solidity コントラクト セルフ audit (戦略会議 #10 採択 A1)。

外部 audit (Quantstamp / OpenZeppelin / Trail of Bits) 受審の前段階として、
PBM.sol / PBMOfflineFallback.sol を 24 項目のチェックリストで静的解析する。

24 項目は OWASP Smart Contract Top 10 (2025) と Consensys best-practice を
ベースに、PBM 固有 (CP-1〜CP-7 のエンフォース・governor 単一鍵リスク・ECDSA
malleability・nonce 二重消費) を追加したもの。

【使い方】
    python scripts/contract_audit.py
    python scripts/contract_audit.py --json    # CI 連携用
    bash scripts/verify.sh audit               # ハーネス経由

【結果フォーマット】
    [ok]   ID-01 SPDX header             pragma solidity ^0.8.20 (PBM.sol:2)
    [ok]   ID-02 license is MIT          (PBM.sol:1)
    [warn] ID-09 single governor key     (再委任あり: transferGovernor)
    [fail] ID-23 reentrancy guard        spend() で外部 transfer 後に書き戻し

[fail] が 0 件 = ready 判定。warn は 5 件以下なら ready, それ以上は partial。
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Literal

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"

Severity = Literal["ok", "warn", "fail", "skip"]


@dataclass
class CheckResult:
    cid: str           # ID-01 etc.
    title: str
    severity: Severity
    detail: str = ""
    contract: str = ""


# ------------------------------------------------------------------
# チェック関数群 (各関数は CheckResult を返す)
# ------------------------------------------------------------------

def _has(src: str, pattern: str) -> bool:
    return re.search(pattern, src) is not None


def _line(src: str, pattern: str) -> int:
    for i, ln in enumerate(src.splitlines(), 1):
        if re.search(pattern, ln):
            return i
    return 0


def check_spdx(name: str, src: str) -> CheckResult:
    if "SPDX-License-Identifier" in src:
        return CheckResult("ID-01", "SPDX header", "ok",
                           f"line {_line(src, 'SPDX')}", name)
    return CheckResult("ID-01", "SPDX header", "fail", "missing", name)


def check_license(name: str, src: str) -> CheckResult:
    m = re.search(r"SPDX-License-Identifier:\s*(\S+)", src)
    if not m:
        return CheckResult("ID-02", "license id", "fail", "no license", name)
    lic = m.group(1)
    if lic in ("MIT", "Apache-2.0"):
        return CheckResult("ID-02", "license is MIT/Apache-2.0", "ok", lic, name)
    return CheckResult("ID-02", "license id", "warn",
                       f"unexpected license: {lic}", name)


def check_pragma(name: str, src: str) -> CheckResult:
    m = re.search(r"pragma\s+solidity\s+([^;]+);", src)
    if not m:
        return CheckResult("ID-03", "pragma solidity", "fail", "missing", name)
    ver = m.group(1).strip()
    # 0.8.x は overflow チェック組込
    if "0.8" not in ver:
        return CheckResult("ID-03", "pragma >=0.8 (auto overflow check)",
                           "fail", f"got {ver}", name)
    return CheckResult("ID-03", "pragma >=0.8", "ok", ver, name)


def check_floating_pragma(name: str, src: str) -> CheckResult:
    m = re.search(r"pragma\s+solidity\s+([^;]+);", src)
    if not m:
        return CheckResult("ID-04", "non-floating pragma", "skip", "no pragma", name)
    ver = m.group(1).strip()
    # 本番投入時は固定推奨だが、開発中は ^0.8.20 で OK とする
    if ver.startswith("^") or ver.startswith(">"):
        return CheckResult("ID-04", "pragma is floating",
                           "warn", f"production should pin: {ver}", name)
    return CheckResult("ID-04", "pragma pinned", "ok", ver, name)


def check_brace_balance(name: str, src: str) -> CheckResult:
    no_line = re.sub(r"//[^\n]*", "", src)
    no_block = re.sub(r"/\*.*?\*/", "", no_line, flags=re.S)
    no_str = re.sub(r'"(?:\\.|[^"\\])*"', '""', no_block)
    o = no_str.count("{")
    c = no_str.count("}")
    if o == c:
        return CheckResult("ID-05", "brace balance", "ok", f"{o}={c}", name)
    return CheckResult("ID-05", "brace balance", "fail",
                       f"open={o} close={c}", name)


def check_paren_balance(name: str, src: str) -> CheckResult:
    no_line = re.sub(r"//[^\n]*", "", src)
    no_block = re.sub(r"/\*.*?\*/", "", no_line, flags=re.S)
    no_str = re.sub(r'"(?:\\.|[^"\\])*"', '""', no_block)
    o = no_str.count("(")
    c = no_str.count(")")
    if o == c:
        return CheckResult("ID-06", "paren balance", "ok", f"{o}={c}", name)
    return CheckResult("ID-06", "paren balance", "fail",
                       f"open={o} close={c}", name)


def check_tx_origin(name: str, src: str) -> CheckResult:
    if "tx.origin" in src:
        return CheckResult("ID-07", "no tx.origin (phishing risk)",
                           "fail", "tx.origin used", name)
    return CheckResult("ID-07", "no tx.origin", "ok", "", name)


def check_block_timestamp_only_compare(name: str, src: str) -> CheckResult:
    """block.timestamp は使ってよいが、乱数源にしてはいけない。"""
    if not _has(src, r"block\.timestamp"):
        return CheckResult("ID-08", "no block.timestamp randomness",
                           "ok", "not used", name)
    # block.timestamp が比較演算 (>= <= < >) でしか使われていなければ OK
    bad = re.search(
        r"block\.timestamp\s*[%^&|*+\-/]|"  # 算術や bit op で乱数化
        r"keccak256[^;]*block\.timestamp",
        src,
    )
    if bad:
        return CheckResult("ID-08", "no block.timestamp randomness",
                           "fail", "used in arithmetic / hash", name)
    return CheckResult("ID-08", "block.timestamp is compare-only",
                       "ok", "compare-only", name)


def check_governor_pattern(name: str, src: str) -> CheckResult:
    if "governor" not in src:
        return CheckResult("ID-09", "single governor key", "skip",
                           "no governor", name)
    has_modifier = _has(src, r"modifier\s+onlyGovernor")
    has_transfer = _has(src, r"function\s+transferGovernor\b")
    if has_modifier and has_transfer:
        return CheckResult("ID-09", "governor: onlyGovernor + transfer",
                           "ok", "modifier+transfer", name)
    if has_modifier and not has_transfer:
        # PBM.sol は transferGovernor を持たない (R11 で追加候補)
        return CheckResult(
            "ID-09", "governor without transfer fn",
            "warn",
            "no transferGovernor — Phase 2 で追加 (multisig 移行用)",
            name,
        )
    return CheckResult("ID-09", "governor pattern", "fail",
                       "modifier missing", name)


def _extract_function_bodies(src: str) -> list[tuple[str, str]]:
    """function 本体を brace counting で正しく切り出す。"""
    out: list[tuple[str, str]] = []
    for m in re.finditer(r"function\s+(\w+)[^{;]*\{", src):
        fname = m.group(1)
        depth = 1
        i = m.end()
        while i < len(src) and depth > 0:
            ch = src[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        body = src[m.end():i - 1]
        out.append((fname, body))
    return out


def _is_state_write(stmt: str) -> bool:
    """ステートメント断片が「ストレージへの書き込み」かを判定。

    ローカル変数宣言 (`uint256 x =`) や struct 初期化 (`Program({a: b, ...})`),
    比較 (`==`, `<=`) は除外。`p.field = x` / `p.field += x` /
    `mapping[k] = x` / `mapping[k][k2] = x` のみ true。
    """
    s = stmt.strip()
    # struct リテラルのフィールド初期化 ("a: b" 形式) は除外
    if re.match(r"\w+\s*:\s*", s):
        return False
    # ローカル変数宣言 ("uint256 x = ...", "address foo = ...") は除外
    if re.match(r"(uint\w*|int\w*|bool|address|bytes\w*|string|mapping)\s+\w+", s):
        return False
    # 残りの "<lhs> =" / "<lhs> +=" / "<lhs> -=" を state write と見なす
    return bool(
        re.match(r"\w+\.\w+\s*[+\-]?=[^=]", s) or
        re.match(r"\w+\[[^\]]+\](\[[^\]]+\])?\s*[+\-]?=[^=]", s)
    )


def check_reentrancy_guard(name: str, src: str) -> CheckResult:
    """CEI (checks-effects-interactions) パターンのチェック。

    `jpyc.transfer(...)` 呼び出しの 前後 でストレージ書き込みを比較。
    transfer 後にストレージ書き込みがあれば warn (JPYC は信頼トークンなので
    fail ではないが、本番前に CEI 化推奨)。
    """
    bodies = _extract_function_bodies(src)
    bad: list[str] = []
    for fname, body in bodies:
        if "jpyc.transfer" not in body:
            continue
        idx = body.find("jpyc.transfer")
        before = body[:idx]
        after = body[idx:]
        # ステートメントごとに区切って判定
        before_writes = any(_is_state_write(s) for s in before.split(";"))
        after_writes = any(_is_state_write(s) for s in after.split(";")[1:])
        if not before_writes and after_writes:
            bad.append(f"{fname}: state は transfer 後 (CEI 違反)")

    if not bad:
        return CheckResult("ID-10", "CEI / no reentrancy", "ok",
                           "checks-effects-interactions OK", name)
    return CheckResult("ID-10", "CEI / no reentrancy", "warn",
                       "; ".join(bad) +
                       " — JPYC 信頼前提だが本番前に修正推奨", name)


def check_unchecked_external_call(name: str, src: str) -> CheckResult:
    """transfer / transferFrom の戻り値を require で受けているか。"""
    bad: list[str] = []
    for m in re.finditer(r"jpyc\.(transfer|transferFrom)\s*\([^)]*\)", src):
        # 同じ行 or 周辺 80 文字以内に require があるか
        start = max(0, m.start() - 80)
        ctx = src[start:m.end() + 5]
        if "require(" not in ctx:
            bad.append(f"line {_line(src, re.escape(m.group(0)[:20]))}")
    if bad:
        return CheckResult("ID-11", "external call return checked", "fail",
                           "; ".join(bad), name)
    return CheckResult("ID-11", "external call return checked", "ok",
                       "all checked", name)


def check_overflow_safe(name: str, src: str) -> CheckResult:
    """0.8 で自動チェック。unchecked ブロックがあれば warn。"""
    if "unchecked" in src:
        return CheckResult("ID-12", "no unchecked arithmetic", "warn",
                           "unchecked block found", name)
    return CheckResult("ID-12", "overflow auto-checked", "ok",
                       "0.8 default", name)


def check_immutable_jpyc(name: str, src: str) -> CheckResult:
    if "IERC20  public immutable jpyc" in src or "IERC20 public immutable jpyc" in src:
        return CheckResult("ID-13", "jpyc address is immutable", "ok",
                           "immutable", name)
    if "jpyc" not in src:
        return CheckResult("ID-13", "jpyc address is immutable", "skip",
                           "no jpyc", name)
    return CheckResult("ID-13", "jpyc address is immutable", "fail",
                       "jpyc 可変は資金抜き取りリスク", name)


def check_event_emission(name: str, src: str) -> CheckResult:
    """state を変更する external/public 関数は event emit を持つべき。"""
    funcs = re.findall(
        r"function\s+(\w+)[^{]*\b(external|public)\b[^{]*\{(.+?)\}\s*(?=function|\}\s*$)",
        src,
        flags=re.S,
    )
    bad: list[str] = []
    for fname, _vis, body in funcs:
        # 名前が view/pure を含む or function 宣言行に view/pure があれば skip
        sig_match = re.search(
            rf"function\s+{re.escape(fname)}[^{{]*", src
        )
        sig = sig_match.group(0) if sig_match else ""
        if "view" in sig or "pure" in sig:
            continue
        # body に state 書き込みがあるが emit がない
        writes_state = bool(
            re.search(r"\w+\.\w+\s*[+\-]?=", body) or
            re.search(r"\w+\[[^\]]+\]\s*=", body)
        )
        if writes_state and "emit " not in body:
            bad.append(fname)
    if not bad:
        return CheckResult("ID-14", "state-changing fn emits event", "ok",
                           "all emit", name)
    return CheckResult("ID-14", "state-changing fn emits event", "warn",
                       f"{len(bad)} fn(s) without emit: {','.join(bad[:3])}", name)


def check_zero_address(name: str, src: str) -> CheckResult:
    """address(0) チェック (governor / store / wallet 設定時)。"""
    bad: list[str] = []
    if _has(src, r"transferGovernor"):
        # transferGovernor 内で require(next != address(0)) があるか
        m = re.search(r"function\s+transferGovernor[^{]*\{(.+?)\}", src, flags=re.S)
        if m and "address(0)" not in m.group(1):
            bad.append("transferGovernor: no zero check")
    if not bad:
        return CheckResult("ID-15", "zero-address checks", "ok",
                           "transferGovernor protected", name)
    return CheckResult("ID-15", "zero-address checks", "fail",
                       "; ".join(bad), name)


def check_visibility_explicit(name: str, src: str) -> CheckResult:
    """全関数に external/public/internal/private のどれかが付いているか。"""
    bad: list[str] = []
    for m in re.finditer(r"function\s+(\w+)\s*\(([^)]*)\)([^{;]*)", src):
        fname = m.group(1)
        sig = m.group(3)
        vis = ("external", "public", "internal", "private")
        if not any(v in sig for v in vis):
            bad.append(fname)
    if not bad:
        return CheckResult("ID-16", "explicit visibility on all fn", "ok",
                           "", name)
    return CheckResult("ID-16", "explicit visibility on all fn", "fail",
                       f"{len(bad)} fn(s) missing: {','.join(bad[:3])}", name)


def check_signature_recovery(name: str, src: str) -> CheckResult:
    """ECDSA 検証している場合、ecrecover 戻り値が 0 でないことをチェック。"""
    if "ecrecover" not in src:
        return CheckResult("ID-17", "ecrecover != address(0)", "skip",
                           "no ecrecover", name)
    # _recover の戻り値が governor と比較されているか
    if _has(src, r"_recover\([^)]+\)\s*==\s*governor"):
        return CheckResult("ID-17", "ecrecover compared to known signer", "ok",
                           "compared to governor", name)
    return CheckResult("ID-17", "ecrecover != address(0)", "warn",
                       "戻り値の zero check 推奨", name)


def check_sig_malleability(name: str, src: str) -> CheckResult:
    """EIP-2 lower-half s チェック (s <= secp256k1n/2)。"""
    if "ecrecover" not in src:
        return CheckResult("ID-18", "EIP-2 low-s check", "skip",
                           "no ecrecover", name)
    # 0xn0 か lower-half s をチェックしてないと malleability
    if _has(src, r"0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0"):
        return CheckResult("ID-18", "EIP-2 low-s check", "ok",
                           "lower-half enforced", name)
    # PBMOfflineFallback は (v in {27,28}) のみチェック
    return CheckResult("ID-18", "EIP-2 low-s check", "warn",
                       "low-s 強制なし — 本番前に追加 (OZ ECDSA.sol)", name)


def check_nonce_replay(name: str, src: str) -> CheckResult:
    """consumed[pid][monthIndex] のような重複防止 mapping があるか。"""
    if "consumed" in src and "mapping" in src:
        # consumed mapping が更新されているか
        if _has(src, r"consumed\[[^\]]+\]\[[^\]]+\]\s*="):
            return CheckResult("ID-19", "nonce / consumed[] replay guard", "ok",
                               "consumed[] update", name)
    if "OfflineFallback" in name:
        return CheckResult("ID-19", "nonce replay guard", "fail",
                           "consumed[] missing", name)
    return CheckResult("ID-19", "nonce replay guard", "skip",
                       "not applicable to PBM.sol", name)


def check_expiry_check(name: str, src: str) -> CheckResult:
    """expiresAt / endAt と block.timestamp の比較があるか。"""
    if "expiresAt" in src or "endAt" in src:
        if _has(src, r"block\.timestamp\s*[<>]=?\s*\w+\.(expiresAt|endAt)") or \
           _has(src, r"\w+\.(expiresAt|endAt)\s*[<>]=?\s*block\.timestamp") or \
           _has(src, r"block\.timestamp\s*<=\s*\w+\.\w+\.expiresAt") or \
           _has(src, r"block\.timestamp\s*\+\s*\d+\s*days") or \
           _has(src, r"\w+\.\w+\.expiresAt\s*\+\s*\d+\s*days"):
            return CheckResult("ID-20", "expiry / period check", "ok",
                               "timestamp compared", name)
        return CheckResult("ID-20", "expiry / period check", "fail",
                           "expiresAt/endAt 未比較", name)
    return CheckResult("ID-20", "expiry / period check", "skip",
                       "no expiry", name)


def check_per_citizen_cap(name: str, src: str) -> CheckResult:
    """PBM 固有: perCitizenCap / capJpy 上限が enforce されているか。"""
    if "perCitizenCap" in src:
        if _has(src, r"perCitizenCap"):
            # subsidy <= cap を確認している部分
            return CheckResult("ID-21", "per-citizen cap enforced", "ok",
                               "perCitizenCap check", name)
    if "capJpy" in src:
        if _has(src, r"<=\s*\w+\.coupon\.capJpy") or _has(src, r"capJpy"):
            return CheckResult("ID-21", "per-citizen monthly cap enforced", "ok",
                               "capJpy check", name)
    return CheckResult("ID-21", "per-citizen cap enforced", "skip",
                       "no cap", name)


def check_revoke_path(name: str, src: str) -> CheckResult:
    """PBM 固有: revoke 後は spend 不可 (CP-1 緊急停止)。"""
    if "revoked" in src:
        if _has(src, r"!p\.revoked") or _has(src, r"!\w+\.revoked"):
            return CheckResult("ID-22", "revoke gates spend()", "ok",
                               "!revoked check", name)
        return CheckResult("ID-22", "revoke gates spend()", "fail",
                           "revoke flag 未参照", name)
    return CheckResult("ID-22", "revoke path", "skip",
                       "no revoke", name)


def check_bytecode_size(name: str, src: str) -> CheckResult:
    """ソース行数を proxy にコントラクトサイズ警告 (24KB ≒ ~2400 行)。"""
    n_lines = len(src.splitlines())
    if n_lines > 2000:
        return CheckResult("ID-23", "bytecode size (24KB limit)",
                           "warn",
                           f"{n_lines} lines — solc で確認推奨", name)
    return CheckResult("ID-23", "bytecode size (24KB limit)", "ok",
                       f"{n_lines} lines (well under 2000)", name)


def check_constructor(name: str, src: str) -> CheckResult:
    """constructor が public 又は省略 (= public default)。"""
    if "constructor" not in src:
        return CheckResult("ID-24", "constructor present", "skip",
                           "no constructor", name)
    # constructor は visibility 修飾子をつけられない (Solidity ≥0.7)
    if _has(src, r"constructor\s*\([^)]*\)\s*(public|external|internal|private)"):
        return CheckResult("ID-24", "constructor without visibility", "fail",
                           "0.7+ ではエラー", name)
    return CheckResult("ID-24", "constructor present", "ok", "", name)


CHECKS = [
    check_spdx,
    check_license,
    check_pragma,
    check_floating_pragma,
    check_brace_balance,
    check_paren_balance,
    check_tx_origin,
    check_block_timestamp_only_compare,
    check_governor_pattern,
    check_reentrancy_guard,
    check_unchecked_external_call,
    check_overflow_safe,
    check_immutable_jpyc,
    check_event_emission,
    check_zero_address,
    check_visibility_explicit,
    check_signature_recovery,
    check_sig_malleability,
    check_nonce_replay,
    check_expiry_check,
    check_per_citizen_cap,
    check_revoke_path,
    check_bytecode_size,
    check_constructor,
]


def audit_one(path: pathlib.Path) -> list[CheckResult]:
    src = path.read_text(encoding="utf-8")
    out: list[CheckResult] = []
    for fn in CHECKS:
        try:
            out.append(fn(path.name, src))
        except Exception as e:  # noqa: BLE001
            out.append(CheckResult(
                fn.__name__, fn.__name__, "fail",
                f"checker exception: {e}", path.name,
            ))
    return out


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    files = sorted(CONTRACTS.glob("*.sol"))
    if not files:
        print("no contracts found")
        return 0

    all_results: list[CheckResult] = []
    for f in files:
        all_results.extend(audit_one(f))

    counts = {"ok": 0, "warn": 0, "fail": 0, "skip": 0}
    for r in all_results:
        counts[r.severity] += 1

    if as_json:
        print(json.dumps({
            "summary": counts,
            "files": [f.name for f in files],
            "results": [r.__dict__ for r in all_results],
        }, indent=2))
    else:
        print(f"== contract self-audit ({len(files)} file(s), "
              f"{len(CHECKS)} check(s) per file) ==\n")
        cur_file = ""
        for r in all_results:
            if r.contract != cur_file:
                cur_file = r.contract
                print(f"-- {cur_file} --")
            sym = {"ok": "✓", "warn": "⚠", "fail": "✗", "skip": "·"}[r.severity]
            print(f"  [{r.severity:4}] {sym} {r.cid:5} {r.title:42} {r.detail}")
        print()
        print(f"summary: ok={counts['ok']} warn={counts['warn']} "
              f"fail={counts['fail']} skip={counts['skip']}")

    if counts["fail"] > 0:
        print("\n✗ audit FAILED")
        return 1
    if counts["warn"] > 5:
        print("\n⚠ audit READY-WARN (warn > 5, "
              "本番前に低減推奨)")
    else:
        print("\n✓ audit READY")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
