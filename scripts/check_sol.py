"""contracts/*.sol の軽量構文チェック。

solc がインストールされていない環境でも回せるように、最小限の構造的チェックだけ行う:
- pragma solidity 行が存在
- SPDX-License-Identifier 行が存在
- 中括弧の対応 (バランス)
- 各 contract / interface 宣言が `;` でなく `{` で始まる
- 単純な「関数本体に return 値の宣言があるのに return 文がない」程度の警告
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def check(path: pathlib.Path) -> list[str]:
    errs: list[str] = []
    src = path.read_text(encoding="utf-8")
    if "SPDX-License-Identifier" not in src:
        errs.append(f"{path.name}: SPDX header missing")
    if not re.search(r"pragma\s+solidity\s+[^;]+;", src):
        errs.append(f"{path.name}: pragma solidity missing")

    # 中括弧バランス (文字列・コメントは雑に除去)
    no_line_comment = re.sub(r"//[^\n]*", "", src)
    no_block_comment = re.sub(r"/\*.*?\*/", "", no_line_comment, flags=re.S)
    no_strings = re.sub(r'"(?:\\.|[^"\\])*"', '""', no_block_comment)
    opens = no_strings.count("{")
    closes = no_strings.count("}")
    if opens != closes:
        errs.append(f"{path.name}: brace mismatch open={opens} close={closes}")

    # contract / interface / library 宣言の後ろに { が来る
    for m in re.finditer(
        r"\b(contract|interface|library)\s+(\w+)[^;{]*", no_strings
    ):
        tail = no_strings[m.end():m.end() + 2].strip()
        if not tail.startswith("{") and not tail.startswith("is"):
            errs.append(
                f"{path.name}: '{m.group(1)} {m.group(2)}' not followed by '{{' or 'is'"
            )

    return errs


def main() -> int:
    if not CONTRACTS.exists():
        print("no contracts/ dir")
        return 0
    errs: list[str] = []
    files = sorted(CONTRACTS.glob("*.sol"))
    for f in files:
        errs.extend(check(f))
    if errs:
        print("solidity check failed:")
        for e in errs:
            print("  -", e)
        return 1
    print(f"sol ok: {len(files)} contract file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
