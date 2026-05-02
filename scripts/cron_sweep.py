"""sweeper の cron エントリポイント (戦略会議 #3 採択 #6)。

systemd timer / cron / k8s CronJob から `python -m scripts.cron_sweep` で叩く想定。
- 毎日 0:05 JST 実行を推奨
- dry-run で影響範囲確認、`--apply` で実適用
- 終了時に exit code = 期限切れトークン件数 (0 なら no-op)

使い方:
    python scripts/cron_sweep.py             # dry-run
    python scripts/cron_sweep.py --apply     # 実行
    python scripts/cron_sweep.py --apply --json  # JSON で結果出力
"""

from __future__ import annotations

import argparse
import json
import sys
import pathlib

# backend を import path に通す
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db import session_scope, init_db  # noqa: E402
from app.services.sweeper import sweep_expired_tokens  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="期限切れ PBM トークンの sweep cron")
    parser.add_argument("--apply", action="store_true", help="実適用 (デフォルトは dry-run)")
    parser.add_argument("--json", action="store_true", help="結果を JSON 出力")
    args = parser.parse_args()

    init_db()
    with session_scope() as db:
        report = sweep_expired_tokens(db, dry_run=not args.apply)

    if args.json:
        print(json.dumps({
            "audited_at": report.now.isoformat() if report.now else None,
            "dry_run": report.dry_run,
            "swept_count": len(report.swept_token_ids),
            "total_refund_jpy": report.total_refund,
            "by_program": report.refunded_jpy_by_program,
        }, ensure_ascii=False))
    else:
        mode = "[DRY-RUN]" if report.dry_run else "[APPLY]"
        print(f"{mode} swept tokens: {len(report.swept_token_ids)}")
        print(f"           refund total: {report.total_refund:,} JPY")
        for pid, jpy in report.refunded_jpy_by_program.items():
            print(f"           - program {pid}: {jpy:,} JPY")

    return len(report.swept_token_ids)


if __name__ == "__main__":
    sys.exit(main())
