"""Bounded HTTP benchmark used for reproducible local baselines."""

import argparse
import asyncio
import json
import math
import time
from collections import Counter

import httpx


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0
    position = min(len(values) - 1, math.ceil(len(values) * fraction) - 1)
    return sorted(values)[position]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--path", action="append", dest="custom_paths")
    args = parser.parse_args()
    if not 1 <= args.requests <= 100_000 or not 1 <= args.concurrency <= 500:
        raise SystemExit("Refusing an unbounded workload")
    paths = tuple(args.custom_paths) if args.custom_paths else (
        "/health/live", "/problems", "/problems/parity-check",
        "/gamification/leaderboard?limit=50", "/contests", "/learning/paths",
    )
    latencies: list[float] = []
    statuses: Counter[int] = Counter()
    semaphore = asyncio.Semaphore(args.concurrency)
    limits = httpx.Limits(max_connections=args.concurrency, max_keepalive_connections=args.concurrency)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=10, limits=limits) as client:
        for index in range(args.warmup):
            await client.get(paths[index % len(paths)])

        async def request(index: int) -> None:
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get(paths[index % len(paths)])
                    statuses[response.status_code] += 1
                except httpx.HTTPError:
                    statuses[0] += 1
                latencies.append((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        await asyncio.gather(*(request(index) for index in range(args.requests)))
        elapsed = time.perf_counter() - started
    failures = sum(count for status, count in statuses.items() if not 200 <= status < 400)
    print(json.dumps({
        "requests": args.requests, "concurrency": args.concurrency,
        "elapsed_seconds": round(elapsed, 3), "requests_per_second": round(args.requests / elapsed, 2),
        "median_ms": round(percentile(latencies, .5), 2), "p95_ms": round(percentile(latencies, .95), 2),
        "p99_ms": round(percentile(latencies, .99), 2), "errors": failures,
        "error_rate_percent": round(failures / args.requests * 100, 3), "statuses": statuses,
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
