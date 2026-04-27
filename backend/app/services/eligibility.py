"""マイナンバー 4 情報 × プログラム要件の照合。"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.citizen import Citizen
from app.models.program import Program
from app.services.privacy import age


@dataclass
class EligibilityResult:
    ok: bool
    reason: str = ""


def check(citizen: Citizen, program: Program) -> EligibilityResult:
    e = program.eligibility or {}

    wards = e.get("wards")
    if wards and citizen.ward not in wards:
        return EligibilityResult(False, f"住所 ({citizen.ward}) が対象外")

    a = age(citizen.dob)
    min_age = e.get("min_age")
    max_age = e.get("max_age")
    if min_age is not None and a < min_age:
        return EligibilityResult(False, f"年齢 {a} は最低年齢 {min_age} 未満")
    if max_age is not None and a > max_age:
        return EligibilityResult(False, f"年齢 {a} は上限年齢 {max_age} 超過")

    genders = e.get("genders")
    if genders and citizen.gender not in genders:
        return EligibilityResult(False, "性別要件を満たさない")

    return EligibilityResult(True, "OK")
