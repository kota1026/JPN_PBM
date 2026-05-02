"""1 万人スケール負荷試験 (戦略会議 #4 採択 #9)。

Red Team 提案 + 修正案: 「サンドボックス DB を破壊しないよう 100 並列 × 100 反復で代替」。
asyncio + httpx で REST を叩き、レイテンシ分布と失敗率を出す。

使い方:
    # 1) backend を起動
    cd backend && uvicorn app.main:app --port 8000 &
    # 2) 負荷試験
    python scripts/loadtest.py --concurrency 100 --iters 100 --base http://localhost:8000

ターゲット:
    GET /treasury/audit       — 監査の負荷耐性
    GET /ebpm/violations      — Purpose Guardian dashboard の負荷耐性
    GET /ebpm/summary         — EBPM ダッシュボード
    GET /products             — カタログ取得 (citizen ページ初期化と同等)

CI でも回せるよう、デフォルトは軽量 (concurrency=10, iters=10) にしている。
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from typing import Any

try:
    import httpx
except ImportError:
    print("httpx 未インストール: pip install httpx", file=sys.stderr)
    sys.exit(2)


DEFAULT_TARGETS = [
    "/treasury/audit",
    "/ebpm/violations",
    "/ebpm/summary",
    "/products",
]


async def _one_call(client: httpx.AsyncClient, path: str) -> tuple[int, float]:
    t0 = time.perf_counter()
    try:
        r = await client.get(path, timeout=10.0)
        dt = time.perf_counter() - t0
        return r.status_code, dt
    except Exception:
        return 0, time.perf_counter() - t0


async def _worker(
    client: httpx.AsyncClient,
    targets: list[str],
    iters: int,
    results: list[tuple[str, int, float]],
) -> None:
    for i in range(iters):
        path = targets[i % len(targets)]
        code, dt = await _one_call(client, path)
        results.append((path, code, dt))


async def main_async(
    base: str, concurrency: int, iters: int, targets: list[str],
    max_fail_rate: float = 0.0,
) -> int:
    print(f"loadtest: base={base} concurrency={concurrency} iters={iters} targets={len(targets)}")
    results: list[tuple[str, int, float]] = []
    started = time.perf_counter()
    async with httpx.AsyncClient(base_url=base) as client:
        workers = [
            _worker(client, targets, iters, results)
            for _ in range(concurrency)
        ]
        await asyncio.gather(*workers)
    total_dt = time.perf_counter() - started
    n = len(results)
    if n == 0:
        print("FATAL: 0 requests")
        return 1
    durations = [d for _, _, d in results]
    failures = [r for r in results if r[1] != 200]
    p50 = statistics.median(durations)
    p95 = sorted(durations)[int(0.95 * (n - 1))]
    p99 = sorted(durations)[int(0.99 * (n - 1))]
    rps = n / total_dt
    print(f"  total: {n} requests in {total_dt:.2f}s = {rps:.1f} req/s")
    print(f"  p50={p50*1000:.1f}ms p95={p95*1000:.1f}ms p99={p99*1000:.1f}ms")
    print(f"  failures: {len(failures)} ({100*len(failures)/n:.2f}%)")

    # endpoint 別
    by_path: dict[str, list[float]] = {}
    by_path_fail: dict[str, int] = {}
    for path, code, d in results:
        by_path.setdefault(path, []).append(d)
        if code != 200:
            by_path_fail[path] = by_path_fail.get(path, 0) + 1
    for path, ds in by_path.items():
        ds_sorted = sorted(ds)
        p95_ = ds_sorted[int(0.95 * (len(ds_sorted) - 1))] * 1000
        fr = by_path_fail.get(path, 0)
        print(f"    {path}: n={len(ds)} p95={p95_:.1f}ms fail={fr}")

    fail_rate = len(failures) / n
    if fail_rate <= max_fail_rate:
        return 0
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--iters", type=int, default=10)
    parser.add_argument("--targets", nargs="*", default=DEFAULT_TARGETS)
    parser.add_argument(
        "--max-fail-rate", type=float, default=0.0,
        help="Allowed failure rate (0.0 - 1.0). Default 0 means any failure is FAIL.",
    )
    args = parser.parse_args()
    return asyncio.run(main_async(
        args.base, args.concurrency, args.iters, args.targets,
        max_fail_rate=args.max_fail_rate,
    ))


if __name__ == "__main__":
    sys.exit(main())
