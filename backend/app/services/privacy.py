"""プライバシー保護ユーティリティ。

マイナンバー由来の ID を HMAC で擬似 ID 化する。秘密鍵は本番では HSM 管理を想定。
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import date

PRIVACY_SECRET = os.environ.get("JPN_PBM_PRIVACY_SECRET", "demo-secret-change-me").encode()


def pseudonymize(maina_id: str) -> str:
    """マイナンバーカード ID 等を不可逆なハッシュへ変換。"""
    mac = hmac.new(PRIVACY_SECRET, maina_id.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def age_band(dob: date, today: date | None = None) -> str:
    """生年月日 → 10 歳刻みの階級 ("60-69" など)。"""
    today = today or date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    lo = (age // 10) * 10
    return f"{lo}-{lo + 9}"


def age(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
