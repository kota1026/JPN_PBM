"""本番投入 readiness 自動診断 (戦略会議 #9 採択 B)。

`production-runbook.md` のチェックリストを自動評価し、不足項目をリストアップする。
本スクリプトは sandbox / staging / 本番 のいずれでも安全に走る (DB 書込なし、リクエストなし)。

【チェック項目】
- env: 必須・推奨環境変数の設定有無
- deps: requirements.txt の packages が import 可能
- code: 主要 service/router/contracts ファイルの存在
- harness: scripts/verify.sh が緑になるか (--quick)
- security: 秘密鍵が code/seed/git 履歴に混入していないか (簡易)

使い方:
    python scripts/readiness_check.py             # human-readable
    python scripts/readiness_check.py --json      # CI 用
    python scripts/readiness_check.py --strict    # warn を error 扱い
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Literal


ROOT = pathlib.Path(__file__).resolve().parents[1]


Severity = Literal["ok", "warn", "fail"]


@dataclass
class CheckResult:
    name: str
    severity: Severity
    message: str
    suggestion: str = ""


@dataclass
class Report:
    checks: list[CheckResult] = field(default_factory=list)
    env_phase: str = "unknown"

    @property
    def fails(self) -> list[CheckResult]:
        return [c for c in self.checks if c.severity == "fail"]

    @property
    def warns(self) -> list[CheckResult]:
        return [c for c in self.checks if c.severity == "warn"]

    def add(self, c: CheckResult) -> None:
        self.checks.append(c)


# ----------------------------- 個別チェック -----------------------------


def _detect_phase() -> str:
    """env から現在のデプロイ Phase を推定。"""
    db_url = os.environ.get("JPN_PBM_DB_URL", "")
    if "postgresql" in db_url:
        return "phase3-postgres"
    if os.environ.get("JPN_PBM_HSM_BACKEND", "env") == "pkcs11":
        return "phase3-hsm"
    if os.environ.get("JPN_PBM_GOVERNOR_PRIVKEYS"):
        return "phase2-multikey"
    if os.environ.get("JPN_PBM_GOVERNOR_PRIVKEY"):
        return "phase2-singlekey"
    return "phase1-sandbox"


def check_env_vars(report: Report) -> None:
    phase = report.env_phase
    # 全 phase 共通推奨
    optional = [
        ("JPN_PBM_PRIVACY_SECRET", "HMAC PID 用秘密鍵 (デフォルト demo 値は本番禁止)"),
        ("JPN_PBM_OFFLINE_SECRET", "HMAC オフライン QR 署名用秘密鍵 (本番では HSM 必須)"),
    ]
    for key, why in optional:
        v = os.environ.get(key, "")
        if not v or "demo" in v.lower() or v == "":
            sev: Severity = "warn" if phase.startswith("phase1") else "fail"
            report.add(CheckResult(
                name=f"env.{key}",
                severity=sev,
                message=f"{key} が未設定 or デモ値",
                suggestion=f"本番では強い乱数 (32+ bytes) を設定すること。{why}",
            ))
        else:
            report.add(CheckResult(name=f"env.{key}", severity="ok", message="OK"))

    # phase 別推奨
    if phase.startswith("phase2") or phase.startswith("phase3"):
        if not os.environ.get("JPN_PBM_GOVERNOR_PRIVKEYS") and not os.environ.get("JPN_PBM_GOVERNOR_PRIVKEY"):
            report.add(CheckResult(
                name="env.governor_keys",
                severity="fail",
                message="ECDSA governor 秘密鍵が env に無い",
                suggestion="JPN_PBM_GOVERNOR_PRIVKEYS=key1,key2 形式で設定 (Phase 3 では HSM 推奨)",
            ))

    if phase.startswith("phase3-postgres"):
        if "@" not in os.environ.get("JPN_PBM_DB_URL", ""):
            report.add(CheckResult(
                name="env.db_url",
                severity="fail",
                message="PostgreSQL URL に認証情報が含まれていない",
                suggestion="postgresql://user:pwd@host:5432/db 形式",
            ))


def check_dependencies(report: Report) -> None:
    """主要パッケージが import 可能か。"""
    required = [
        ("fastapi", None),
        ("sqlalchemy", None),
        ("pydantic", None),
        ("ecdsa", "ECDSA 鍵管理 (R5)"),
    ]
    optional = [
        ("Crypto", "pycryptodome (R6 keccak256 = Sol 互換に必須)"),
        ("multipart", "python-multipart (R5 マイナ OAuth Mock の form 解析)"),
        ("psycopg2", "Phase 3 PostgreSQL driver"),
    ]
    for pkg, why in required:
        try:
            importlib.import_module(pkg)
            report.add(CheckResult(name=f"deps.{pkg}", severity="ok", message="OK"))
        except ImportError:
            report.add(CheckResult(
                name=f"deps.{pkg}",
                severity="fail",
                message=f"{pkg} が import できない",
                suggestion=f"pip install -r backend/requirements.txt — {why or 'core dependency'}",
            ))
    for pkg, why in optional:
        try:
            importlib.import_module(pkg)
            report.add(CheckResult(name=f"deps.{pkg}", severity="ok", message="OK"))
        except ImportError:
            report.add(CheckResult(
                name=f"deps.{pkg}",
                severity="warn",
                message=f"{pkg} が import できない",
                suggestion=f"{why}",
            ))


def check_files(report: Report) -> None:
    """主要 service/router/contracts ファイルの存在確認。"""
    required = [
        "backend/app/services/purpose_guard.py",
        "backend/app/services/offline_fallback.py",
        "backend/app/services/sol_compat.py",
        "backend/app/services/sol_simulator.py",
        "backend/app/services/key_management.py",
        "backend/app/services/peg_monitor.py",
        "backend/app/services/treasury_audit.py",
        "contracts/PBM.sol",
        "contracts/PBMOfflineFallback.sol",
        "seed/programs.json",
        "scripts/verify.sh",
        "scripts/loadtest.py",
        "scripts/cron_sweep.py",
    ]
    for rel in required:
        path = ROOT / rel
        if path.exists():
            report.add(CheckResult(name=f"file.{rel}", severity="ok", message="exists"))
        else:
            report.add(CheckResult(
                name=f"file.{rel}",
                severity="fail",
                message="missing",
                suggestion="リポジトリの整合性を確認 (前のラウンドの PR がマージされているか)",
            ))


def check_harness(report: Report) -> None:
    """`bash scripts/verify.sh quick` が緑になるか。"""
    if not (ROOT / "scripts" / "verify.sh").exists():
        report.add(CheckResult(name="harness", severity="fail", message="verify.sh missing"))
        return
    try:
        r = subprocess.run(
            ["bash", "scripts/verify.sh", "quick"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            report.add(CheckResult(name="harness.quick", severity="ok", message="all green"))
        else:
            report.add(CheckResult(
                name="harness.quick",
                severity="fail",
                message=f"verify.sh quick 失敗 (rc={r.returncode})",
                suggestion=r.stdout[-300:] if r.stdout else "詳細はログ参照",
            ))
    except subprocess.TimeoutExpired:
        report.add(CheckResult(name="harness.quick", severity="fail", message="timeout"))


SECRET_PATTERNS = [
    re.compile(r"(?i)(?:private[_-]?key|privkey|seed[_-]?phrase)\s*[=:]\s*[\"'`]?[0-9a-f]{32,}"),
    re.compile(r"(?i)(?:aws[_-]?secret|api[_-]?key)\s*[=:]\s*[\"'`]?[A-Za-z0-9+/]{16,}"),
]


def check_secrets_in_repo(report: Report) -> None:
    """seed / docs に明らかな秘密鍵パターンが混入していないか。"""
    suspect: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (".py", ".json", ".md", ".js", ".html", ".sh", ".yml", ".yaml"):
            continue
        if any(p in path.parts for p in (".git", "node_modules", "__pycache__", ".venv")):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                snippet = m.group(0)
                # demo / test / fixture は許容
                if any(w in path.name.lower() for w in ("test", "fixture")):
                    continue
                if "demo" in snippet.lower() or "change-me" in snippet.lower():
                    continue
                suspect.append(f"{path.relative_to(ROOT)}: {snippet[:60]}...")
    if suspect:
        report.add(CheckResult(
            name="security.no_secrets",
            severity="fail",
            message=f"{len(suspect)} 件の疑わしい鍵パターン検出",
            suggestion="\n".join(suspect[:5]),
        ))
    else:
        report.add(CheckResult(name="security.no_secrets", severity="ok", message="clean"))


# ----------------------------- main -----------------------------


def run() -> Report:
    r = Report(env_phase=_detect_phase())
    check_env_vars(r)
    check_dependencies(r)
    check_files(r)
    check_harness(r)
    check_secrets_in_repo(r)
    return r


def _print_human(r: Report) -> None:
    print(f"detected phase: {r.env_phase}\n")
    by_sev: dict[str, list[CheckResult]] = {"ok": [], "warn": [], "fail": []}
    for c in r.checks:
        by_sev[c.severity].append(c)
    for sev, items in by_sev.items():
        marker = {"ok": "✓", "warn": "⚠", "fail": "✗"}[sev]
        for c in items:
            print(f"  {marker} {c.name}: {c.message}")
            if sev != "ok" and c.suggestion:
                for line in c.suggestion.splitlines()[:3]:
                    print(f"      → {line}")
    print()
    print(f"summary: ok={len(by_sev['ok'])}, warn={len(by_sev['warn'])}, fail={len(by_sev['fail'])}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="JSON 出力")
    parser.add_argument("--strict", action="store_true", help="warn を fail 扱い")
    args = parser.parse_args()

    r = run()
    if args.json:
        print(json.dumps({
            "env_phase": r.env_phase,
            "checks": [asdict(c) for c in r.checks],
            "summary": {
                "ok": sum(1 for c in r.checks if c.severity == "ok"),
                "warn": len(r.warns),
                "fail": len(r.fails),
            },
        }, ensure_ascii=False))
    else:
        _print_human(r)

    if r.fails:
        return 2
    if args.strict and r.warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
