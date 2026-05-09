"""PH POS SDK 本体 (戦略会議 #13 採択 T2)。

GCash QR Ph + バックエンド (`/products/{jan}`, `/programs`, `/seed/load?locale=ph`) との連携を持つ
薄い HTTP クライアント。現状 GCash 部分は mock (実 sandbox は Coins.ph 接触後 Round 15+)。

【設計原則】
- JP `jpn_pbm_pos.PBMPosClient` と **API 形を可能な限り合わせる** (将来の統合を容易に)
- ただし PH 固有概念 (QR Ph, MCC, tingi, centavos) は専用クラスで露出
- ECDSA 署名やオフライン coupon は **共通サービス** (`backend/app/services/qr_ph.py` 等) を再利用
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


# ============================================================
# データクラス
# ============================================================


@dataclass
class PhPosConfig:
    base_url: str
    merchant_id: str
    merchant_qr_ph_payload: str = ""        # 店の QR Ph payload (parser に渡す)
    timeout_sec: float = 5.0
    user_agent: str = "jpn-pbm-pos-ph-sdk/0.1"
    locale: str = "tl"                      # tl|en (POS UI 表示用)


@dataclass
class MerchantQrInfo:
    """merchant QR を parse した結果。"""
    merchant_name: str
    merchant_city: str
    mcc: int
    is_static: bool                          # tag 01 == "11"
    is_valid_crc: bool
    is_4ps_acceptable: bool
    reason: str                              # acceptable=False の理由


@dataclass
class CartItem:
    has_barcode: bool
    jan: str | None
    name: str
    price_centavos: int
    qty: int = 1
    is_tingi: bool = False                   # has_barcode=False の便宜フラグ


@dataclass
class CartEstimate:
    items: list[CartItem]
    total_price_centavos: int
    total_eligible_centavos: int
    total_subsidy_centavos: int
    self_pay_centavos: int                   # 自己負担 = total - subsidy
    no_barcode_used_centavos: int
    no_barcode_cap_centavos: int
    program_id: str
    citizen_pid: str
    notes: list[str] = field(default_factory=list)


@dataclass
class GCashReceipt:
    payment_reference: str                   # mock UUID
    paid_at: str                             # ISO timestamp
    merchant_id: str
    citizen_pid_short: str                   # pid の先頭 8 文字 (privacy)
    total_paid_centavos: int                 # 受給者が GCash で実際に払う額 = self_pay + (subsidy が PHPC で merchant に行く分は別途)
    subsidy_paid_phpc_centavos: int
    is_mock: bool = True


# ============================================================
# HTTP helper
# ============================================================


def _get(base: str, path: str, *, timeout: float, ua: str) -> Any:
    req = urllib.request.Request(
        url=base.rstrip("/") + path,
        headers={"User-Agent": ua, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {path}: {body[:200]}")


# ============================================================
# QR Ph parser proxy
# ============================================================


def _parse_qr_ph_local(payload: str) -> MerchantQrInfo:
    """sys.path に backend が居れば直接 services/qr_ph を呼ぶ。

    SDK 単体ユーザ (バックエンドソースが手元にない) のために、
    ImportError なら超軽量フォールバック (CRC 検証無し) を使う。
    """
    try:
        from app.services.qr_ph import is_4ps_acceptable, parse_qr_ph
        info = parse_qr_ph(payload, verify_crc=True)
        ok, reason = is_4ps_acceptable(info)
        return MerchantQrInfo(
            merchant_name=info.merchant_name or "",
            merchant_city=info.merchant_city or "",
            mcc=info.merchant_category_code or 0,
            is_static=(info.point_of_initiation == "11"),
            is_valid_crc=info.is_valid_crc,
            is_4ps_acceptable=ok,
            reason=reason,
        )
    except ImportError:
        # フォールバック (SDK のみインストール想定)
        # 実用環境では verify_crc=True を強く推奨。
        return _parse_qr_ph_minimal(payload)


def _parse_qr_ph_minimal(payload: str) -> MerchantQrInfo:
    """super-minimal な TLV parser (CRC 検証なし、フィールド抽出のみ)。"""
    fields: dict[str, str] = {}
    i = 0
    while i + 4 <= len(payload):
        tag = payload[i:i + 2]
        try:
            length = int(payload[i + 2:i + 4])
        except ValueError:
            break
        if i + 4 + length > len(payload):
            break
        fields[tag] = payload[i + 4:i + 4 + length]
        i += 4 + length

    mcc = 0
    try:
        mcc = int(fields.get("52", "0"))
    except ValueError:
        pass

    BLOCKED = {5921, 5993, 5813, 7995}
    ok = mcc != 0 and mcc not in BLOCKED
    reason = "OK" if ok else (f"MCC {mcc} blocked" if mcc in BLOCKED else "MCC missing")
    return MerchantQrInfo(
        merchant_name=fields.get("59", ""),
        merchant_city=fields.get("60", ""),
        mcc=mcc,
        is_static=(fields.get("01") == "11"),
        is_valid_crc=False,  # 軽量 fallback では検証しない
        is_4ps_acceptable=ok,
        reason=reason,
    )


# ============================================================
# Client 本体
# ============================================================


class PhPosClient:
    """マニラ用 POS クライアント。

    state は self._cart / self._merchant_info の 2 つだけ。
    citizen_pid は estimate_cart() の引数として都度渡す (持ち回さない)。
    """

    def __init__(self, cfg: PhPosConfig) -> None:
        self.cfg = cfg
        self._cart: list[CartItem] = []
        self._merchant_info: MerchantQrInfo | None = None
        self._no_barcode_used_centavos: int = 0  # 月内 (本 SDK 内では reset 自由)

    # -------- merchant QR --------

    def verify_merchant_qr(self, payload: str | None = None) -> MerchantQrInfo:
        """merchant QR を解析し、4Ps 適合性を判定する。"""
        text = payload if payload is not None else self.cfg.merchant_qr_ph_payload
        if not text:
            raise ValueError("merchant_qr_ph_payload not provided")
        info = _parse_qr_ph_local(text)
        self._merchant_info = info
        return info

    @property
    def merchant_info(self) -> MerchantQrInfo | None:
        return self._merchant_info

    # -------- カート操作 --------

    def add_barcoded_item(
        self, *, jan: str, qty: int = 1, fetch_master: bool = True
    ) -> CartItem:
        """バーコード付き商品を追加。fetch_master=True で `/products/{jan}` を引く。"""
        name = ""
        price = 0
        if fetch_master:
            try:
                p = _get(
                    self.cfg.base_url, f"/products/{urllib.parse.quote(jan)}",
                    timeout=self.cfg.timeout_sec, ua=self.cfg.user_agent,
                )
                name = p.get("name", "")
                price = int(p.get("price_jpy", 0))   # 内部最小単位 = centavos
            except Exception:
                pass  # マスタ未登録なら空のまま (後段で対象外扱い)
        item = CartItem(
            has_barcode=True, jan=jan, name=name or f"(unregistered {jan})",
            price_centavos=price, qty=qty, is_tingi=False,
        )
        self._cart.append(item)
        return item

    def add_tingi_item(
        self, *, price_centavos: int, label: str = "Tingi item"
    ) -> CartItem:
        """バーコードなし商品 (tingi / 量り売り) を追加。"""
        if price_centavos <= 0:
            raise ValueError("price_centavos must be > 0")
        item = CartItem(
            has_barcode=False, jan=None, name=label,
            price_centavos=price_centavos, qty=1, is_tingi=True,
        )
        self._cart.append(item)
        return item

    def reset_cart(self) -> None:
        self._cart.clear()

    @property
    def cart(self) -> list[CartItem]:
        return list(self._cart)

    # -------- 試算 --------

    def estimate_cart(
        self,
        *,
        citizen_pid: str,
        program_id: str,
    ) -> CartEstimate:
        """ハイブリッド eligibility に基づき subsidy を算出する。

        merchant QR が verify されており、MCC が 4Ps acceptable である前提。
        """
        if self._merchant_info is None:
            raise RuntimeError("call verify_merchant_qr() first")
        if not self._merchant_info.is_4ps_acceptable:
            raise RuntimeError(f"merchant rejected: {self._merchant_info.reason}")

        # /programs から該当 program 情報を引く
        progs = _get(self.cfg.base_url, "/programs",
                     timeout=self.cfg.timeout_sec, ua=self.cfg.user_agent)
        prog = next((p for p in progs if p["id"] == program_id), None)
        if prog is None:
            raise RuntimeError(f"program not found: {program_id}")

        eligible_jans = set(prog.get("eligible_jans") or [])
        eligible_categories = set(prog.get("eligible_categories") or [])
        excluded_jans = set(prog.get("excluded_jans") or [])
        subsidy_bps = int(prog.get("subsidy_bps", 0))
        # PH の per_citizen_cap_jpy は centavos として保存されている
        per_cap_centavos = int(prog.get("per_citizen_cap_jpy") or 0)
        # cap_no_barcode は seed JSON 由来だが API では出ないので heuristic に PHP 300 = 30000
        cap_no_barcode = 30000

        notes: list[str] = []
        total_price = 0
        total_eligible = 0
        total_subsidy = 0
        no_barcode_running = self._no_barcode_used_centavos

        for it in self._cart:
            line_price = it.price_centavos * it.qty
            total_price += line_price
            eligible = False
            if it.has_barcode:
                if it.jan in excluded_jans:
                    notes.append(f"{it.name}: excluded_jan")
                else:
                    # 商品マスタの category を確認するために /products/{jan} を引く必要があるが
                    # ここでは簡易: jan match なら eligible
                    if it.jan in eligible_jans:
                        eligible = True
                    else:
                        # category マッチ判定は backend を再度叩いて category を取る
                        try:
                            p = _get(
                                self.cfg.base_url,
                                f"/products/{urllib.parse.quote(it.jan or '')}",
                                timeout=self.cfg.timeout_sec, ua=self.cfg.user_agent,
                            )
                            if p.get("category") in eligible_categories:
                                eligible = True
                        except Exception:
                            pass
            else:
                # tingi: MCC + no_barcode cap
                if (self._merchant_info.mcc in {5411, 5499, 5912}
                        and no_barcode_running + line_price <= cap_no_barcode):
                    eligible = True
                    no_barcode_running += line_price

            if eligible:
                total_eligible += line_price
                line_subsidy = line_price * subsidy_bps // 10000
                total_subsidy += line_subsidy

        # per_citizen_cap で全体クランプ
        if per_cap_centavos and total_subsidy > per_cap_centavos:
            notes.append(
                f"subsidy clamped by per_citizen_cap: {total_subsidy} → {per_cap_centavos}"
            )
            total_subsidy = per_cap_centavos

        return CartEstimate(
            items=self.cart,
            total_price_centavos=total_price,
            total_eligible_centavos=total_eligible,
            total_subsidy_centavos=total_subsidy,
            self_pay_centavos=total_price - total_subsidy,
            no_barcode_used_centavos=no_barcode_running,
            no_barcode_cap_centavos=cap_no_barcode,
            program_id=program_id,
            citizen_pid=citizen_pid,
            notes=notes,
        )

    # -------- 決済 (GCash mock) --------

    def charge_via_gcash(self, estimate: CartEstimate) -> GCashReceipt:
        """GCash QR Ph での決済を mock 実行。

        production: GCash Sandbox API を呼ぶ。current: 単に receipt を組み立てる。
        副作用として no_barcode 使用累計を更新する (月内連続スキャン想定)。
        """
        ref = "GCASHQR-" + uuid.uuid4().hex[:12]
        self._no_barcode_used_centavos = estimate.no_barcode_used_centavos
        return GCashReceipt(
            payment_reference=ref,
            paid_at=datetime.now(tz=timezone.utc).isoformat(),
            merchant_id=self.cfg.merchant_id,
            citizen_pid_short=estimate.citizen_pid[:8],
            total_paid_centavos=estimate.self_pay_centavos,
            subsidy_paid_phpc_centavos=estimate.total_subsidy_centavos,
            is_mock=True,
        )

    # -------- diagnostics --------

    def to_dict(self) -> dict:
        return {
            "config": asdict(self.cfg),
            "merchant_info": asdict(self._merchant_info) if self._merchant_info else None,
            "cart_size": len(self._cart),
            "no_barcode_used_centavos": self._no_barcode_used_centavos,
        }
