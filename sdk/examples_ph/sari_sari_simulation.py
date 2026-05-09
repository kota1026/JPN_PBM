"""Sari-sari 4Ps 給付フロー シミュレーション (戦略会議 #13 採択 T2)。

サリサリ店主と 4Ps 受給者の典型的な買い物 1 回を、
PHP POS SDK 越しに mock 実行する。

実行前提:
- backend が `cd backend && uvicorn app.main:app` で起動中
- `POST /seed/load?locale=ph` でシード投入済

実行:
    python sdk/examples_ph/sari_sari_simulation.py
"""

from __future__ import annotations

import sys

from jpn_pbm_pos_ph import PhPosClient, PhPosConfig


# Aling Maria's sari-sari store (MCC 5411 grocery, Quezon City)
# qr_ph build_qr_ph で生成した payload (R13 で実装済 services/qr_ph.build_qr_ph)
MERCHANT_QR_PAYLOAD = (
    "0002010102113026"  # tag 00='01' + tag 01='11' + tag 26 ...
    "0014PH.PPMI.QRPH"
    "0121MERCHANT-MARIA-QC-001"
    "52045411"
    "5303608"
    "5802PH"
    "5917ALING MARIA STORE"
    "6011QUEZON CITY"
    "6304"
)
# 注: 実テストでは services/qr_ph.build_qr_ph() を使い、CRC 込で生成する。
# CI では別途 SDK ↔ qr_ph 連携テストで動作確認する。


def main() -> int:
    cfg = PhPosConfig(
        base_url="http://127.0.0.1:8000",
        merchant_id="ph-store-aling-maria-qc",
        merchant_qr_ph_payload="",  # 後で set
        locale="tl",
    )
    client = PhPosClient(cfg)

    # ① merchant QR の verify (production では QR をスキャン)
    # 簡易テスト用に build_qr_ph で生成 (qr_ph モジュールが import 出来る前提)
    try:
        from app.services.qr_ph import build_qr_ph
        cfg.merchant_qr_ph_payload = build_qr_ph(
            merchant_id="MERCHANT-MARIA-QC-001",
            mcc=5411,
            merchant_name="ALING MARIA STORE",
            merchant_city="QUEZON CITY",
        )
    except ImportError:
        print("⚠ qr_ph not available; using static demo payload")
        cfg.merchant_qr_ph_payload = MERCHANT_QR_PAYLOAD

    info = client.verify_merchant_qr()
    print(f"✓ merchant: {info.merchant_name} ({info.merchant_city}, MCC {info.mcc})")
    print(f"  4Ps acceptable: {info.is_4ps_acceptable}, CRC valid: {info.is_valid_crc}")
    if not info.is_4ps_acceptable:
        print(f"  blocked: {info.reason}")
        return 1

    # ② 受給者の典型的な買い物
    print("\n② Adding items to cart...")
    client.add_barcoded_item(jan="4806515600015", qty=1)         # Bear Brand 300g
    client.add_barcoded_item(jan="4801234560015", qty=2)         # Lucky Me x2
    client.add_tingi_item(price_centavos=1500, label="米 1 カップ")  # PHP 15
    client.add_tingi_item(price_centavos=2000, label="砂糖 1 cup")  # PHP 20

    # ③ 試算
    print("\n③ Estimating cart for citizen PH-0001 / prog-4ps-2026...")
    citizen_pid = "abc123" * 10 + "abcd"  # 64 hex (HMAC PSN を仮定)
    citizen_pid = citizen_pid[:64]
    try:
        est = client.estimate_cart(
            citizen_pid=citizen_pid, program_id="prog-4ps-2026",
        )
    except RuntimeError as e:
        print(f"  ✗ estimate failed: {e}")
        print("  Hint: run `POST /seed/load?locale=ph` first.")
        return 1

    php = lambda c: f"PHP {c/100:>7.2f}"  # noqa: E731
    print(f"  Total cart price : {php(est.total_price_centavos)}")
    print(f"  Eligible portion : {php(est.total_eligible_centavos)}")
    print(f"  4Ps subsidy      : {php(est.total_subsidy_centavos)} (PHPC)")
    print(f"  Self-pay (cash)  : {php(est.self_pay_centavos)} (GCash/cash)")
    print(f"  No-barcode used  : {php(est.no_barcode_used_centavos)} / "
          f"{php(est.no_barcode_cap_centavos)}")
    if est.notes:
        print("  Notes:")
        for n in est.notes:
            print(f"    - {n}")

    # ④ GCash で決済 (mock)
    print("\n④ Charging via GCash (mock)...")
    rcpt = client.charge_via_gcash(est)
    print(f"  ✓ payment_reference: {rcpt.payment_reference}")
    print(f"  ✓ paid_at:           {rcpt.paid_at}")
    print(f"  ✓ self-pay sent     : {php(rcpt.total_paid_centavos)}")
    print(f"  ✓ subsidy in PHPC   : {php(rcpt.subsidy_paid_phpc_centavos)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
