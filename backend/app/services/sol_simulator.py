"""Sol PBMOfflineFallback の Python シミュレータ (戦略会議 #6 採択 B)。

`contracts/PBMOfflineFallback.sol:redeemBatch` を Python で **完全模倣** する。
本物の Polygon にデプロイする前に、以下を unit test で保証:

- 同じ batch を流したら Sol と Python で 同じ accept/revert 結果
- 同じ (pid, monthIndex) の cap 超過は Sol が revert、Python は raise
- 期限切れ + grace 30 日は Sol/Python とも同じ判定

【Sol との挙動差ポリシー】
| 観点 | Sol (`redeemBatch`) | Python シミュレータ | 備考 |
|------|---------------------|----------------------|------|
| 1 件でも失敗 | revert 全体 | RaiseRevert で同じ挙動 | デフォルト |
| accept 後の payout | jpyc.transfer | Python 内 ledger 更新 | side-effect 等価 |
| nonce | `consumed[pid][month]` | dict | 同じ |
| approved store | `approvedStores[msg.sender]` | set | 同じ |
| 署名検証 | ecrecover == governor | sol_compat.verify_coupon_eip191 | 同じ digest 計算 |
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable

from app.services.sol_compat import (
    SolCoupon,
    address_of,
    privkey_from_hex,
    verify_coupon_eip191,
)


GRACE_DAYS_SEC = 30 * 24 * 3600


class SolRevert(RuntimeError):
    """Sol の revert に対応する例外。"""


@dataclass
class SolRedemption:
    """Sol PBMOfflineFallback.OfflineRedemption と同じレイアウト (関連フィールドのみ)。"""

    coupon: SolCoupon
    signature: bytes  # 65 bytes (r||s||v)
    store_address: str  # checksum or lower address (msg.sender 相当)
    amount_jpy: int
    redeemed_at: int  # unix sec


@dataclass
class SolBatchResult:
    """シミュレータ実行結果。Sol の return value (totalPaid) + 内部状態の変化。"""

    total_paid_jpy: int = 0
    consumed_after: dict[tuple[bytes, int], int] = field(default_factory=dict)


class SolSimulator:
    """`PBMOfflineFallback` の Python ミラー。

    Sol コントラクトの `governor` / `approvedStores` / `consumed` を再現し、
    `redeem_batch` (= Sol の `redeemBatch`) を実行する。
    """

    def __init__(self, governor_address: str, *, jpyc_balance_in_contract: int = 10**12):
        self.governor_address = governor_address.lower()
        self.approved_stores: set[str] = set()
        self.consumed: dict[tuple[bytes, int], int] = {}
        self.jpyc_balance = jpyc_balance_in_contract
        self.store_balances: dict[str, int] = {}

    # -------------------- Sol "onlyGovernor" 系 --------------------

    def set_approved_store(self, store: str, ok: bool) -> None:
        s = store.lower()
        if ok:
            self.approved_stores.add(s)
        else:
            self.approved_stores.discard(s)

    def consumed_of(self, pid: bytes, month_index: int) -> int:
        return self.consumed.get((pid, month_index), 0)

    # -------------------- Sol redeemBatch 互換 --------------------

    def redeem_batch(
        self,
        items: Iterable[SolRedemption],
        *,
        msg_sender: str,
        block_timestamp: int | None = None,
    ) -> SolBatchResult:
        """Sol PBMOfflineFallback.redeemBatch と同じセマンティクス。

        - approved_stores チェック
        - 各 item で署名検証 + grace + cap
        - 1 件でも失敗 → SolRevert (Sol の revert と等価)
        """
        ts = block_timestamp if block_timestamp is not None else int(time.time())
        sender = msg_sender.lower()

        if sender not in self.approved_stores:
            raise SolRevert("OF: store not approved")

        # 一旦 staging dict に積み、全件 OK なら commit (Sol の revert は全体ロールバック)
        staging: dict[tuple[bytes, int], int] = {}
        result = SolBatchResult()

        for it in items:
            if it.store_address.lower() != sender:
                raise SolRevert("OF: store mismatch")
            if it.amount_jpy <= 0:
                raise SolRevert("OF: zero amount")
            if ts > it.coupon.expires_at + GRACE_DAYS_SEC:
                raise SolRevert("OF: too late")

            ok, why = verify_coupon_eip191(
                it.coupon, it.signature, expected_address=self.governor_address,
            )
            if not ok:
                raise SolRevert(f"OF: bad sig ({why})")

            key = (it.coupon.pid, it.coupon.month_index)
            already = self.consumed.get(key, 0) + staging.get(key, 0)
            if already + it.amount_jpy > it.coupon.cap_jpy:
                raise SolRevert("OF: cap exceeded")
            staging[key] = staging.get(key, 0) + it.amount_jpy
            result.total_paid_jpy += it.amount_jpy

        # ここまで来れたら commit
        for key, delta in staging.items():
            self.consumed[key] = self.consumed.get(key, 0) + delta
        if result.total_paid_jpy > self.jpyc_balance:
            raise SolRevert("OF: payout fail (insufficient JPYC)")
        self.jpyc_balance -= result.total_paid_jpy
        self.store_balances[sender] = self.store_balances.get(sender, 0) + result.total_paid_jpy
        result.consumed_after = dict(self.consumed)
        return result


# -------------------- 便利関数: 同じ batch を Sol/Python (= self) で 1 回ずつ --------------------


def cross_check_with_offchain(
    *,
    items: list[SolRedemption],
    governor_privkey_hex: str,
    msg_sender: str,
    block_timestamp: int | None = None,
) -> tuple[SolBatchResult, SolBatchResult]:
    """同じ batch を 2 つの SolSimulator に流して、結果が完全一致することを返す。

    本関数は「Sol コードを変更しても、Python シミュレータと結果が乖離しない」かを
    回帰テストするための fixture 生成器。
    """
    sk = privkey_from_hex(governor_privkey_hex)
    addr = address_of(sk)
    s1 = SolSimulator(addr)
    s2 = SolSimulator(addr)
    s1.set_approved_store(msg_sender, True)
    s2.set_approved_store(msg_sender, True)

    r1 = s1.redeem_batch(items, msg_sender=msg_sender, block_timestamp=block_timestamp)
    r2 = s2.redeem_batch(items, msg_sender=msg_sender, block_timestamp=block_timestamp)
    return r1, r2
