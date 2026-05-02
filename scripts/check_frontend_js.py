"""frontend/*.html のインライン JS の構文チェック (戦略会議 #3 ハーネス強化)。

Node.js があれば `node --check` で各 inline <script> をパース。Node が無ければ skip。
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONT = ROOT / "frontend"


SCRIPT_RE = re.compile(r"<script>\n([\s\S]*?)</script>", re.M)


def main() -> int:
    if not FRONT.exists():
        print("no frontend/")
        return 0
    if not shutil.which("node"):
        print("front-js: node 未インストール — skip")
        return 0
    files = sorted(FRONT.glob("*.html"))
    fails: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        scripts = SCRIPT_RE.findall(text)
        for i, s in enumerate(scripts):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fp:
                fp.write(s)
                tmp = fp.name
            r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
            if r.returncode != 0:
                fails.append(f"{f.name}: inline script #{i+1}: {r.stderr.strip().splitlines()[0] if r.stderr else 'parse error'}")
    if fails:
        print("front-js validation failed:")
        for x in fails:
            print("  -", x)
        return 1
    print(f"front-js ok: {len(files)} html file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
