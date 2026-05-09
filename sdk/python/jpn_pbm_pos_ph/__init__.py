"""JPN-PBM POS SDK (Philippine variant) — for sari-sari, Mercury Drug, 7-Eleven 等。

JP 版 (`jpn_pbm_pos`) の姉妹実装。マニラ pilot (4Ps) で必要な差分:

- **EMV QR Ph** (BSP Circular 2019-859) を merchant 識別に利用
- **GCash mock 決済**: production では GCash sandbox API、現状は HTTP mock
- **ハイブリッド eligibility**: barcode 厳格判定 + 月次 no-barcode cap
- **PHPC** centavos 単位 (内部表現は最小単位の整数で JP と等価)

依存ライブラリ:
- 標準ライブラリ + (任意) `requests` のみ。サリサリ店舗の低価格 Android デバイスでも動く設計。

使い方:
    from jpn_pbm_pos_ph import PhPosClient, PhPosConfig

    cfg = PhPosConfig(
        base_url="http://127.0.0.1:8000",
        merchant_id="ph-store-aling-maria-qc",
        merchant_qr_ph_payload="..."  # 店の QR Ph QRコードの中身
    )
    client = PhPosClient(cfg)

    # ① merchant QR を verify
    info = client.verify_merchant_qr()
    assert info.is_4ps_acceptable

    # ② 受給者がカゴに商品を追加 (バーコード or tingi)
    client.add_barcoded_item(jan="4806515600015", qty=1)
    client.add_tingi_item(price_centavos=8000, label="米 1 カップ")

    # ③ カート試算 (subsidy 計算)
    estimate = client.estimate_cart(citizen_pid=pid, program_id="prog-4ps-2026")
    print(estimate.total_subsidy_centavos)

    # ④ GCash QR Ph で決済 (mock)
    receipt = client.charge_via_gcash(estimate)
    print(receipt.payment_reference)
"""

from .client import (
    PhPosClient,
    PhPosConfig,
    CartItem,
    CartEstimate,
    GCashReceipt,
    MerchantQrInfo,
)

__all__ = [
    "PhPosClient",
    "PhPosConfig",
    "CartItem",
    "CartEstimate",
    "GCashReceipt",
    "MerchantQrInfo",
]
