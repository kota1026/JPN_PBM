"""ロードマップ進捗 (戦略会議 #7 採択 A + 戦略会議 #10 採択 A4)。

戦略会議 #1 で確定した 18 ヶ月ロードマップ (Phase 1-3) の現在状態を返す。
status は手動メンテだが、達成判定の一部 (テスト数, programs 数, contracts 数,
docs 英訳 N 本) は実コードから自動取得する (#10 で `auto_metrics()` を追加)。

【ステータス】
- done   : 実装/外交/承認 完了
- ready  : 実装は終わったが本番投入待ち (例: ECDSA は実装済 / Polygon Mumbai 未デプロイ)
- partial: 一部実装、残課題あり
- blocked: 実外交/法整備など外部依存
- pending: 未着手

【自動判定】
- evidence_files が全部存在すれば status を "done" or "ready" に格上げできる
- `auto_metrics()` が repo 内の実カウント (tests / contracts / strategy 文書数 等) を
  サマリで返す。フロントの roadmap dashboard が evidence と並べて表示する。
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Literal

ROOT = pathlib.Path(__file__).resolve().parents[3]


Status = Literal["done", "ready", "partial", "blocked", "pending"]


@dataclass
class Milestone:
    phase: int
    code: str           # "M+0", "M+1", ...
    title: str
    status: Status
    notes: str = ""
    evidence_files: list[str] = field(default_factory=list)  # repo 内のファイル
    blocking_reason: str = ""


# ロードマップ台帳。新しいラウンドで追加・更新する。
MILESTONES: list[Milestone] = [
    # ---------- Phase 1 ----------
    Milestone(1, "M+0",  "Founders' MoU (TMG × JPYC × TIS × 江東区)",
              "blocked", blocking_reason="実外交"),
    Milestone(1, "M+1",  "PoC → JPYC 本物トークン (Polygon)",
              "ready",
              notes=(
                  "MVP 差替準備完了。HMAC PID / OAuth Mock / 災害用 QR + "
                  "Polygon Mumbai デプロイ scripts 整備済 (R12 で実行可) ─ "
                  "RPC URL 払出後 3 日で testnet 上稼働"
              ),
              evidence_files=["backend/app/services/privacy.py",
                              "backend/app/routers/myna_oauth.py",
                              "foundry.toml",
                              "scripts/forge/DeployPBM.s.sol",
                              "scripts/deploy_mumbai.sh",
                              "docs/deploy-mumbai.md"]),
    Milestone(1, "M+2",  "加盟店 eKYC + POS SDK 配布",
              "done",
              notes="POS SDK Python (R3) + UI 承認 (R4)",
              evidence_files=["sdk/python/jpn_pbm_pos/__init__.py",
                              "frontend/tokyo.html"]),
    Milestone(1, "M+3",  "Closed alpha 100 世帯 × 10 店舗 (江東区)",
              "ready",
              notes="prog-koto-kosodate-2026 シード + 全 UI 実装",
              evidence_files=["seed/programs.json"]),
    Milestone(1, "M+4",  "KPI 監視 (利用率 / 二重支給 0 / 個情法 0)",
              "done",
              notes="EBPM (k-anon) + CP 違反集計",
              evidence_files=["backend/app/routers/ebpm.py",
                              "backend/app/services/purpose_guard.py"]),
    Milestone(1, "M+5",  "Public beta 1,000 世帯 × 30 店舗",
              "ready",
              notes="負荷試験 5,000 req @ fail 2.66% (R5/R6)",
              evidence_files=["scripts/loadtest.py"]),
    Milestone(1, "M+6",  "都議会報告",
              "done",
              notes="戦略会議 #1〜#7 全英訳完了 (R9)",
              evidence_files=["docs/strategy-2026-04-en.md",
                              "docs/strategy-2026-05-round2-en.md",
                              "docs/strategy-2026-05-round3-en.md",
                              "docs/strategy-2026-05-round4-en.md",
                              "docs/strategy-2026-05-round5-en.md",
                              "docs/strategy-2026-05-round6-en.md",
                              "docs/strategy-2026-05-round7-en.md"]),

    # ---------- Phase 2 ----------
    Milestone(2, "M+6",  "23 区順次拡大",
              "blocked", blocking_reason="実外交"),
    Milestone(2, "M+7",  "防災備蓄ローリング助成 (#2) Closed alpha (3 区)",
              "ready",
              notes="prog-koto-disaster-pack-2026 を江東区フラッグシップに統合 (R8)。多年度予算 ¥50M × 3 年度",
              evidence_files=["seed/programs.json"]),
    Milestone(2, "M+8",  "申請レス: マイナポータル v2 OAuth 完成",
              "ready",
              notes="OAuth Mock + ConsentLog 統合 (R5)",
              evidence_files=["backend/app/routers/myna_oauth.py",
                              "backend/app/routers/consent.py"]),
    Milestone(2, "M+9",  "OSS 化 (Apache 2.0)",
              "done",
              notes="既 repo + LICENSE",
              evidence_files=["LICENSE"]),
    Milestone(2, "M+10", "PBM ラッパー authentication audit",
              "ready",
              notes="セルフ audit checklist 24 項目 ok=39/warn=5/fail=0 (R11)。外部 audit (Quantstamp 等) は本番前",
              evidence_files=["scripts/contract_audit.py",
                              "contracts/PBM.sol",
                              "contracts/PBMOfflineFallback.sol"]),
    Milestone(2, "M+11", "★ 災害時フォールバック (CP-6) 本番投入",
              "ready",
              notes="ECDSA Sol 完全互換 (R5/R6) + 鍵 rotation (R7) + Sol simulator (R7)",
              evidence_files=["contracts/PBMOfflineFallback.sol",
                              "backend/app/services/sol_compat.py",
                              "backend/app/services/key_management.py",
                              "backend/app/services/sol_simulator.py"]),
    Milestone(2, "M+12", "100 万人スケール",
              "partial",
              notes="SQLite WAL で 5,000 req / fail 2.66%。PostgreSQL 移行で本番値"),

    # ---------- Phase 3 ----------
    Milestone(3, "M+12", "税ループ (Tokyo 税電子納付に JPYC 充当)",
              "blocked", blocking_reason="法整備待ち"),
    Milestone(3, "M+14", "サンドボックス + 金融庁共同レポート",
              "blocked", blocking_reason="国 (FSA) との折衝"),
    Milestone(3, "M+15", "リスキリング (中小企業 5,000 社 アルファ)",
              "pending"),
    Milestone(3, "M+16", "他自治体 fork (大阪府 / 愛知県 / Manila)",
              "ready",
              notes=("Manila ツインパイロット仕様完成 (R11-R13): "
                     "PH seed / PhilSys mock / EMV QR Ph parser / "
                     "JICA 申請書 v1 ドラフト + Tagalog/English UI"),
              evidence_files=["docs/expansion-philippines.md",
                              "seed/ph/programs.json",
                              "seed/ph/citizens.json",
                              "seed/ph/products.json",
                              "seed/ph/stores.json",
                              "backend/app/routers/philsys_oauth.py",
                              "backend/app/services/qr_ph.py",
                              "frontend/ph/index.html",
                              "frontend/ph/citizen.html",
                              "docs/jica-application-draft-en.md"]),
    Milestone(3, "M+18", "「東京都モデル」公開ホワイトペーパー",
              "ready",
              notes="戦略会議 #1〜#9 全英訳済 (9/9) + 統合 whitepaper-2026.md (R11)",
              evidence_files=["docs/whitepaper-2026.md",
                              "docs/strategy-2026-04-en.md",
                              "docs/strategy-2026-05-round2-en.md",
                              "docs/strategy-2026-05-round3-en.md",
                              "docs/strategy-2026-05-round4-en.md",
                              "docs/strategy-2026-05-round5-en.md",
                              "docs/strategy-2026-05-round6-en.md",
                              "docs/strategy-2026-05-round7-en.md",
                              "docs/strategy-2026-05-round8-en.md",
                              "docs/strategy-2026-05-round9-en.md"]),
]


def _file_exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def evidence_check(m: Milestone) -> dict[str, bool]:
    """evidence_files の存在チェック結果を返す。"""
    return {f: _file_exists(f) for f in m.evidence_files}


def status_summary() -> dict[str, int]:
    """ステータス別件数。"""
    out: dict[str, int] = {}
    for m in MILESTONES:
        out[m.status] = out.get(m.status, 0) + 1
    return out


def auto_metrics() -> dict[str, int]:
    """repo の実コードから取れる進捗指標を返す (戦略会議 #10 採択 A4)。

    手動の status とは独立に、客観的な数値だけを集計する。
    フロントの roadmap dashboard が evidence と並べて「自動進捗」を表示するのに使う。
    """
    metrics: dict[str, int] = {}

    def _count(rel: str, glob: str) -> int:
        d = ROOT / rel
        return len(list(d.glob(glob))) if d.is_dir() else 0

    metrics["tests"] = _count("backend/tests", "test_*.py")
    metrics["routers"] = _count("backend/app/routers", "*.py") - 1  # __init__ 除外
    metrics["services"] = _count("backend/app/services", "*.py") - 1
    metrics["contracts"] = _count("contracts", "*.sol")
    metrics["seed_programs"] = 0
    seed_p = ROOT / "seed" / "programs.json"
    if seed_p.exists():
        import json as _json
        try:
            data = _json.loads(seed_p.read_text(encoding="utf-8"))
            metrics["seed_programs"] = len(data) if isinstance(data, list) else 0
        except Exception:  # noqa: BLE001
            pass

    # 戦略文書の英訳カバレッジ
    docs_dir = ROOT / "docs"
    if docs_dir.is_dir():
        ja = [
            p for p in docs_dir.glob("strategy-*.md")
            if not p.stem.endswith("-en")
        ]
        en = [p for p in docs_dir.glob("strategy-*-en.md")]
        metrics["strategy_docs_ja"] = len(ja)
        metrics["strategy_docs_en"] = len(en)
    else:
        metrics["strategy_docs_ja"] = 0
        metrics["strategy_docs_en"] = 0

    # ハーネス verify モード数
    verify_sh = ROOT / "scripts" / "verify.sh"
    if verify_sh.exists():
        body = verify_sh.read_text(encoding="utf-8")
        # case 文の各 mode (py/seed/sol/...) をカウント
        import re as _re
        modes = _re.findall(r"^\s*([a-z][a-z0-9]+)\)\s+run_", body, flags=_re.M)
        metrics["verify_modes"] = len(set(modes))
    else:
        metrics["verify_modes"] = 0

    # コントラクト audit 行数 (= checklist 数の proxy)
    audit_py = ROOT / "scripts" / "contract_audit.py"
    metrics["audit_checks"] = (
        audit_py.read_text(encoding="utf-8").count("def check_")
        if audit_py.exists() else 0
    )

    return metrics


def to_dict() -> dict[str, object]:
    """API 出力用 dict。"""
    return {
        "summary": status_summary(),
        "auto_metrics": auto_metrics(),
        "phases": [
            {
                "phase": phase,
                "milestones": [
                    {
                        "code": m.code,
                        "title": m.title,
                        "status": m.status,
                        "notes": m.notes,
                        "blocking_reason": m.blocking_reason,
                        "evidence": evidence_check(m),
                    }
                    for m in MILESTONES if m.phase == phase
                ],
            }
            for phase in (1, 2, 3)
        ],
    }
