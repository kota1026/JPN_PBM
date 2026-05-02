"""seed/*.json の妥当性チェック。

参照整合性 (program.approved_stores 内の store_id が stores.json に存在するか等) を
高速に確認する。pytest 起動より先に走らせて、データ起因の test 失敗を切り分ける。
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEED = ROOT / "seed"


def _load(name: str):
    return json.loads((SEED / name).read_text(encoding="utf-8"))


def main() -> int:
    citizens = _load("citizens.json")
    stores = _load("stores.json")
    programs = _load("programs.json")
    products = _load("products.json")

    errors: list[str] = []

    # citizens
    for i, c in enumerate(citizens):
        for k in ("maina_id", "name", "ward", "dob"):
            if k not in c:
                errors.append(f"citizens[{i}]: missing {k}")

    # stores
    store_ids = {s["id"] for s in stores}
    for i, s in enumerate(stores):
        for k in ("id", "name", "ward"):
            if k not in s:
                errors.append(f"stores[{i}]: missing {k}")

    # programs
    seen_ids = set()
    categories = set()
    for i, p in enumerate(programs):
        for k in (
            "id",
            "name",
            "budget_jpy",
            "subsidy_bps",
            "per_citizen_cap_jpy",
            "start_at",
            "end_at",
            "approved_stores",
        ):
            if k not in p:
                errors.append(f"programs[{i}]: missing {k}")
        if p["id"] in seen_ids:
            errors.append(f"programs[{i}]: duplicate id={p['id']}")
        seen_ids.add(p["id"])
        if not (0 <= p.get("subsidy_bps", -1) <= 10_000):
            errors.append(f"programs[{i}]: subsidy_bps out of range")
        for sid in p.get("approved_stores", []):
            if sid not in store_ids:
                errors.append(
                    f"programs[{i}].approved_stores: unknown store_id={sid}"
                )
        for cat in p.get("eligible_categories", []):
            categories.add(cat)

    # products
    jan_seen: set[str] = set()
    product_categories = {p["category"] for p in products}
    for i, prod in enumerate(products):
        for k in ("jan", "name", "category", "price_jpy"):
            if k not in prod:
                errors.append(f"products[{i}]: missing {k}")
        jan = prod.get("jan", "")
        if jan in jan_seen:
            errors.append(f"products[{i}]: duplicate JAN={jan}")
        jan_seen.add(jan)
        if not (jan.isdigit() and len(jan) in (8, 13)):
            errors.append(f"products[{i}]: invalid JAN={jan!r}")

    # 各 program のカテゴリが少なくとも 1 つは products に存在
    for p in programs:
        cats = p.get("eligible_categories", [])
        if cats and not any(c in product_categories for c in cats):
            errors.append(
                f"programs[{p['id']}]: no product matches categories {cats}"
            )

    if errors:
        print("seed validation failed:")
        for e in errors:
            print("  -", e)
        return 1

    print(
        f"seed ok: citizens={len(citizens)} stores={len(stores)} "
        f"programs={len(programs)} products={len(products)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
