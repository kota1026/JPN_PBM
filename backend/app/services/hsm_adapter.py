"""HSM 連携アダプタ (戦略会議 #7 採択 B)。

Phase 2 (R6/R7) では env で秘密鍵を管理しているが、Phase 3 では HSM
(Hardware Security Module, 例: AWS CloudHSM / Thales Luna / Yubico FIPS) で
鍵を抱え、署名は HSM 内で行う形に切り替える。

本モジュールは「HSM 抽象インターフェース + Mock 実装」を提供する。
本番ではこのインターフェースを PKCS#11 や AWS CloudHSM SDK でラップした
クラスに差し替えるだけで動く。

【インターフェース】
    HsmBackend (Protocol):
        - list_keys() -> list[HsmKeyInfo]
        - get_address(key_id) -> str
        - sign_digest(key_id, digest_32) -> bytes (65 bytes r||s||v)

【ENV 切替】
    JPN_PBM_HSM_BACKEND = "env" (default = key_management.py 経由) | "mock" | "pkcs11"
    JPN_PBM_HSM_MOCK_KEYS = "key_id_a:<privhex>,key_id_b:<privhex>"
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Protocol

from app.services import key_management as km
from app.services.sol_compat import (
    address_of,
    privkey_from_hex,
    sign_coupon_eip191,
    SolCoupon,
)


@dataclass(frozen=True)
class HsmKeyInfo:
    key_id: str
    address: str
    label: str = ""


class HsmBackend(Protocol):
    def list_keys(self) -> list[HsmKeyInfo]: ...
    def get_address(self, key_id: str) -> str: ...
    def sign_coupon(self, key_id: str, coupon: SolCoupon) -> bytes: ...


# ----------------------------- env backend (= 既存 key_management) -----------------------------


class EnvBackend:
    """env から直接秘密鍵を読む既存の key_management を HsmBackend にラップ。"""

    def list_keys(self) -> list[HsmKeyInfo]:
        keys = km.load_keys()
        return [
            HsmKeyInfo(key_id=f"env-{i}", address=k.address, label="active" if k.is_active else "")
            for i, k in enumerate(keys)
        ]

    def get_address(self, key_id: str) -> str:
        if not key_id.startswith("env-"):
            raise KeyError(f"unknown env key id: {key_id}")
        idx = int(key_id.removeprefix("env-"))
        keys = km.load_keys()
        if idx < 0 or idx >= len(keys):
            raise KeyError(f"env-{idx} out of range")
        return keys[idx].address

    def sign_coupon(self, key_id: str, coupon: SolCoupon) -> bytes:
        if not key_id.startswith("env-"):
            raise KeyError(f"unknown env key id: {key_id}")
        idx = int(key_id.removeprefix("env-"))
        keys = km.load_keys()
        sk = privkey_from_hex(keys[idx].privkey_hex)
        return sign_coupon_eip191(coupon, sk)


# ----------------------------- mock backend (HSM API シグネチャ) -----------------------------


class MockBackend:
    """HSM の API シグネチャに揃えた Mock 実装。

    JPN_PBM_HSM_MOCK_KEYS=label1:<hex>,label2:<hex> から複数鍵を読む。
    本物の HSM では list_keys / sign は HSM サービスへの REST/gRPC 呼び出しになる。
    """

    def __init__(self, raw: Optional[str] = None):
        raw = raw if raw is not None else os.environ.get("JPN_PBM_HSM_MOCK_KEYS", "")
        self._keys: dict[str, str] = {}
        for token in raw.split(","):
            token = token.strip()
            if not token or ":" not in token:
                continue
            label, hex_str = token.split(":", 1)
            self._keys[label.strip()] = hex_str.strip()

    def list_keys(self) -> list[HsmKeyInfo]:
        return [
            HsmKeyInfo(key_id=label, address=address_of(privkey_from_hex(h)), label=label)
            for label, h in self._keys.items()
        ]

    def get_address(self, key_id: str) -> str:
        if key_id not in self._keys:
            raise KeyError(key_id)
        return address_of(privkey_from_hex(self._keys[key_id]))

    def sign_coupon(self, key_id: str, coupon: SolCoupon) -> bytes:
        if key_id not in self._keys:
            raise KeyError(key_id)
        sk = privkey_from_hex(self._keys[key_id])
        return sign_coupon_eip191(coupon, sk)


# ----------------------------- 切替 -----------------------------


def get_backend() -> HsmBackend:
    """ENV `JPN_PBM_HSM_BACKEND` で実装を切替える。"""
    name = os.environ.get("JPN_PBM_HSM_BACKEND", "env").strip().lower()
    if name == "mock":
        return MockBackend()
    if name == "env":
        return EnvBackend()
    raise NotImplementedError(f"HSM backend {name!r} not implemented (only 'env'/'mock')")


def status() -> dict[str, object]:
    """SOC ダッシュボード用。鍵の数 + address のみ返す (秘密鍵は出さない)。"""
    backend = get_backend()
    keys = backend.list_keys()
    return {
        "backend": os.environ.get("JPN_PBM_HSM_BACKEND", "env"),
        "key_count": len(keys),
        "keys": [
            {"key_id": k.key_id, "address": k.address, "label": k.label}
            for k in keys
        ],
    }
