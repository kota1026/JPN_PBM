"""JPN-PBM POS SDK (Python).

加盟店 POS 端末から本 PBM システムを呼ぶための薄いクライアント。
平時はオンライン購入、有事はオフライン coupon 給付 + 復旧後の batch 精算をサポート。

設計目標:
- 依存は urllib (標準ライブラリ) のみ。組み込み Linux POS でも動く
- ネット切断中でも redeem できる (ローカルキューに append)
- 復旧時に redeem-batch を 1 回叩くだけで精算完了
- 端末ごとに 端末ID を持ち、queue ファイルに端末 ID を含めて多重処理を防ぐ
"""

from .client import (
    PBMPosClient,
    PosConfig,
    LocalQueue,
    OfflineCouponData,
)

__all__ = [
    "PBMPosClient",
    "PosConfig",
    "LocalQueue",
    "OfflineCouponData",
]
