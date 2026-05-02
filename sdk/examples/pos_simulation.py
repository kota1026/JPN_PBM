"""POS シミュレーション (sample script)。

ローカルで FastAPI を起動した状態で実行:
    cd backend && uvicorn app.main:app --reload &
    cd ../sdk && python -m examples.pos_simulation

このスクリプトは以下を順に実行する:
1. 都が江東区の加盟店 (store-aeon-koto) を offline approve
2. 住民 (HMAC PID) に coupon 発行
3. 「ネット切断」を装ってクライアントが redeem_offline でローカルキューに溜める
4. 「ネット復旧」して flush_offline_queue で集中精算
5. /treasury/audit で監査結果を表示
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# パッケージインポート (リポジトリ直起動を想定)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from jpn_pbm_pos import OfflineCouponData, PBMPosClient, PosConfig  # noqa: E402


BASE_URL = "http://localhost:8000"


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        url=BASE_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    # 0) クライアント初期化 (POS 端末を江東区イオンとして)
    queue_path = ROOT / "examples" / "_queue.jsonl"
    if queue_path.exists():
        queue_path.unlink()
    client = PBMPosClient(PosConfig(
        base_url=BASE_URL,
        store_id="store-aeon-koto",
        queue_path=str(queue_path),
    ))

    # 1) 都が加盟店を offline approve
    print("[1/5] approve store...")
    _post("/offline/stores/approve", {"store_id": "store-aeon-koto"})

    # 2) 住民の HMAC PID で coupon 発行
    pid_hex = hashlib.sha256(b"MN-SAMPLE-001").hexdigest()
    expires = int((datetime.now(tz=timezone.utc) + timedelta(days=30)).timestamp())
    print("[2/5] issue offline coupon for pid=", pid_hex[:8], "...")
    coupon_dict = _post("/offline/coupons", {
        "program_id": "prog-koto-kosodate-2026",
        "pid": pid_hex,
        "month_index": 202604,
        "cap_jpy": 5000,
        "expires_at": expires,
    })
    coupon = OfflineCouponData(**{k: coupon_dict[k] for k in (
        "program_id", "pid", "month_index", "cap_jpy", "expires_at", "signature"
    )})

    # 3) 「ネット断中」を装って redeem_offline (ローカルキューに溜まる)
    print("[3/5] simulate 3 offline redemptions (network down)...")
    for amount in (1500, 1500, 2000):
        r = client.redeem_offline(coupon, amount_jpy=amount)
        print(f"  queued {amount} JPY (queue size = {r['queue_size']})")
        time.sleep(0.05)

    # 4) ネット復旧 → flush
    print("[4/5] network recovered, flush queue...")
    flush_res = client.flush_offline_queue()
    print(f"  accepted={flush_res['accepted_count']}, "
          f"paid={flush_res['total_paid_jpy']} JPY")

    # 5) 監査
    print("[5/5] audit...")
    audit = client.server_audit()
    print(f"  healthy={audit['healthy']} alerts={audit['alerts']}")
    print(f"  store_balance={audit['totals']['store_balance_jpy']} JPY")

    return 0 if flush_res["accepted_count"] == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
