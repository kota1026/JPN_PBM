"""POS SDK のローカルキュー部分のユニットテスト。

HTTP 部分は test_consent_and_offline で実機 (TestClient) と統合する。
ここではキュー append / read / clear と redeem_offline の事前検証 (cap 超え拒否) を
カバーする。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# SDK をテストから直接 import するため sys.path に追加
SDK = Path(__file__).resolve().parents[2] / "sdk" / "python"
sys.path.insert(0, str(SDK))

from jpn_pbm_pos import LocalQueue, OfflineCouponData, PBMPosClient, PosConfig  # noqa: E402


def test_local_queue_append_and_read(tmp_path):
    q = LocalQueue(tmp_path / "q.jsonl")
    assert len(q) == 0
    q.append({"a": 1})
    q.append({"b": 2})
    assert len(q) == 2
    rows = q.read_all()
    assert rows == [{"a": 1}, {"b": 2}]
    q.clear()
    assert len(q) == 0
    # clear 後に再 append できる
    q.append({"c": 3})
    assert q.read_all() == [{"c": 3}]


def test_redeem_offline_amount_must_be_positive(tmp_path):
    client = PBMPosClient(PosConfig(
        base_url="http://localhost:0",  # ネット使わない
        store_id="store-x",
        queue_path=str(tmp_path / "q.jsonl"),
    ))
    coupon = OfflineCouponData(
        program_id="p", pid="a" * 64, month_index=202604, cap_jpy=5000,
        expires_at=9999999999, signature="00" * 32,
    )
    r = client.redeem_offline(coupon, amount_jpy=0)
    assert r["_error"] is True


def test_redeem_offline_blocks_amount_over_cap(tmp_path):
    client = PBMPosClient(PosConfig(
        base_url="http://localhost:0",
        store_id="store-x",
        queue_path=str(tmp_path / "q.jsonl"),
    ))
    coupon = OfflineCouponData(
        program_id="p", pid="a" * 64, month_index=202604, cap_jpy=1000,
        expires_at=9999999999, signature="00" * 32,
    )
    r = client.redeem_offline(coupon, amount_jpy=2000)
    assert r["_error"] is True
    assert "cap_jpy" in r["reason"]


def test_redeem_offline_queues_valid(tmp_path):
    client = PBMPosClient(PosConfig(
        base_url="http://localhost:0",
        store_id="store-aeon-koto",
        queue_path=str(tmp_path / "q.jsonl"),
    ))
    coupon = OfflineCouponData(
        program_id="prog-koto-kosodate-2026", pid="b" * 64,
        month_index=202604, cap_jpy=5000,
        expires_at=9999999999, signature="ab" * 32,
    )
    r1 = client.redeem_offline(coupon, amount_jpy=1500, redeemed_at=1000)
    r2 = client.redeem_offline(coupon, amount_jpy=2500, redeemed_at=2000)
    assert r1["queued"] and r1["queue_size"] == 1
    assert r2["queued"] and r2["queue_size"] == 2

    rows = client.queue.read_all()
    assert [r["amount_jpy"] for r in rows] == [1500, 2500]
    assert all(r["store_id"] == "store-aeon-koto" for r in rows)


def test_offline_coupon_data_from_qr_json():
    qr = (
        '{"program_id":"p","pid":"' + "c" * 64 + '",'
        '"month_index":202605,"cap_jpy":3000,'
        '"expires_at":9999999999,"signature":"de' + "ad" * 31 + '"}'
    )
    c = OfflineCouponData.from_qr_json(qr)
    assert c.month_index == 202605
    assert c.cap_jpy == 3000
