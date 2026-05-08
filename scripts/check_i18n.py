"""戦略文書の英訳カバレッジ チェック (戦略会議 #10 採択 C2)。

docs/strategy-*.md (和文) に対して docs/strategy-*-en.md (英訳) が
揃っているかを確認する。揃っていなければ exit 1。

【ルール】
- docs/strategy-*-en.md は除外して和文として列挙
- ペアになる英訳ファイルが存在 → ok
- 存在しなければ → fail (但し最新ラウンドの 1 本は warn として許容)

【使い方】
    python scripts/check_i18n.py
    bash scripts/verify.sh i18n
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def main() -> int:
    if not DOCS.exists():
        print("no docs/ dir")
        return 0

    ja_files = sorted(
        p for p in DOCS.glob("strategy-*.md")
        if not p.stem.endswith("-en")
    )

    missing: list[str] = []
    ok: list[str] = []
    for ja in ja_files:
        en_path = ja.with_name(f"{ja.stem}-en{ja.suffix}")
        if en_path.exists():
            ok.append(ja.stem)
        else:
            missing.append(ja.stem)

    print(f"== i18n coverage: strategy docs ==\n")
    print(f"  ja files     : {len(ja_files)}")
    print(f"  en pairs     : {len(ok)}")
    print(f"  missing en   : {len(missing)}")
    print()
    for stem in ok:
        print(f"  ✓ {stem} ↔ {stem}-en")
    if missing:
        print()
        print("missing translations:")
        for stem in missing:
            print(f"  ✗ {stem} (no {stem}-en.md)")

    if not missing:
        print("\n✓ i18n FULL")
        return 0
    # 最新 1 本未訳は warn 許容 (running translation lag)
    if len(missing) == 1:
        print(f"\n⚠ i18n LAG: {missing[0]} 未訳 (1 本までは許容)")
        return 0
    print(f"\n✗ i18n GAP: {len(missing)} files missing translations")
    return 1


if __name__ == "__main__":
    sys.exit(main())
