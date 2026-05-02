"""POS SDK 本体。

加盟店 POS が JPN-PBM システムと話す唯一のエントリポイント。

【典型的な利用】
    cfg = PosConfig(base_url="https://pbm.metro.tokyo.lg.jp", store_id="store-aeon-koto")
    client = PBMPosClient(cfg)

    # 平時: バーコードスキャン → 購入
    res = client.purchase(citizen_pid=pid, jan="4901111111118", qty=1)
    print(res["subsidy_jpy"])

    # 有事: オフライン coupon を読んで給付 → ローカルキューに保存
    coupon = OfflineCouponData(...)  # QR から取得
    client.redeem_offline(coupon, amount_jpy=3000)

    # 復旧後: ローカルキューを batch 提出
    summary = client.flush_offline_queue()
    print(summary["accepted_count"])
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass
class PosConfig:
    base_url: str
    store_id: str
    queue_path: str | None = None  # None なら ~/.jpn_pbm_pos/<store_id>.jsonl
    timeout_sec: float = 5.0
    user_agent: str = "jpn-pbm-pos-sdk/0.1"


@dataclass
class OfflineCouponData:
    """都が事前配布した QR ペイロード。"""

    program_id: str
    pid: str
    month_index: int
    cap_jpy: int
    expires_at: int
    signature: str

    @classmethod
    def from_qr_json(cls, qr_text: str) -> "OfflineCouponData":
        d = json.loads(qr_text)
        return cls(**{k: d[k] for k in (
            "program_id", "pid", "month_index", "cap_jpy", "expires_at", "signature"
        )})


# ----------------------------- ローカルキュー -----------------------------


class LocalQueue:
    """端末のローカル append-only ログ (JSONL)。

    スレッドセーフ。flush 時は読み込み → POST → 成功なら truncate。
    """

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, item: dict[str, Any]) -> None:
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self._lock, self.path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def clear(self) -> None:
        with self._lock:
            if self.path.exists():
                self.path.unlink()

    def __len__(self) -> int:
        return len(self.read_all())


# ----------------------------- HTTP -----------------------------


def _post(base: str, path: str, body: dict[str, Any], *, timeout: float, ua: str) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url=base.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": ua},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_error": True, "status": e.code, "body": e.read().decode("utf-8", errors="replace")}


def _get(base: str, path: str, *, timeout: float, ua: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url=base.rstrip("/") + path,
        headers={"User-Agent": ua},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_error": True, "status": e.code, "body": e.read().decode("utf-8", errors="replace")}


# ----------------------------- クライアント -----------------------------


class PBMPosClient:
    def __init__(self, config: PosConfig):
        self.config = config
        queue_path = config.queue_path or str(
            Path.home() / ".jpn_pbm_pos" / f"{config.store_id}.jsonl"
        )
        self.queue = LocalQueue(queue_path)

    # ---- 平時 API ----

    def purchase(self, *, citizen_pid: str, jan: str, qty: int = 1) -> dict[str, Any]:
        return _post(
            self.config.base_url, "/purchase",
            body={
                "citizen_pid": citizen_pid,
                "store_id": self.config.store_id,
                "jan": jan,
                "qty": qty,
            },
            timeout=self.config.timeout_sec, ua=self.config.user_agent,
        )

    # ---- 有事 API: オフライン redemption ----

    def redeem_offline(
        self,
        coupon: OfflineCouponData,
        *,
        amount_jpy: int,
        redeemed_at: int | None = None,
    ) -> dict[str, Any]:
        """ネット断中の給付。ローカルキューに append し、復旧時に flush で精算。"""
        if amount_jpy <= 0:
            return {"_error": True, "reason": "amount_jpy must be positive"}
        if amount_jpy > coupon.cap_jpy:
            return {"_error": True, "reason": "amount > coupon.cap_jpy"}
        if redeemed_at is None:
            redeemed_at = int(datetime.now(tz=timezone.utc).timestamp())

        item = {
            **asdict(coupon),
            "store_id": self.config.store_id,
            "amount_jpy": amount_jpy,
            "redeemed_at": redeemed_at,
        }
        self.queue.append(item)
        return {"queued": True, "queue_size": len(self.queue), "item": item}

    def queue_size(self) -> int:
        return len(self.queue)

    def flush_offline_queue(self) -> dict[str, Any]:
        """ローカルキューを redeem-batch に送信し、成功なら queue を消す。"""
        items = self.queue.read_all()
        if not items:
            return {"accepted_count": 0, "rejected_count": 0, "total_paid_jpy": 0}
        res = _post(
            self.config.base_url, "/offline/redeem-batch",
            body={"store_id": self.config.store_id, "items": items},
            timeout=self.config.timeout_sec, ua=self.config.user_agent,
        )
        if not res.get("_error"):
            # 成功: queue クリア (rejected があっても本体側で記録済 = 二重提出を避ける)
            self.queue.clear()
        return res

    # ---- ヘルスチェック ----

    def server_audit(self) -> dict[str, Any]:
        return _get(
            self.config.base_url, "/treasury/audit",
            timeout=self.config.timeout_sec, ua=self.config.user_agent,
        )

    def server_consumed(self, pid: str, month_index: int) -> dict[str, Any]:
        return _get(
            self.config.base_url,
            f"/offline/consumed?pid={pid}&month_index={month_index}",
            timeout=self.config.timeout_sec, ua=self.config.user_agent,
        )
