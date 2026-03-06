from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path
import shutil

from l1_compute.analysis.atm_decay.storage import AtmDecayStorage


class _FakeRedis:
    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}
        self.kv: dict[str, str] = {}

    async def rpush(self, key: str, value: str):
        self.lists.setdefault(key, []).append(value)

    async def lrange(self, key: str, start: int, end: int):
        values = self.lists.get(key, [])
        if end == -1:
            return values[start:]
        return values[start : end + 1]

    async def llen(self, key: str) -> int:
        return len(self.lists.get(key, []))

    async def delete(self, key: str):
        self.lists.pop(key, None)

    async def get(self, key: str):
        return self.kv.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.kv[key] = value

    def pipeline(self):
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, redis: _FakeRedis):
        self.redis = redis
        self.ops: list[tuple[str, str, str | int]] = []

    def rpush(self, key: str, value: str):
        self.ops.append(("rpush", key, value))
        return self

    def expire(self, key: str, ttl_seconds: int):
        self.ops.append(("expire", key, ttl_seconds))
        return self

    async def execute(self):
        for op, key, value in self.ops:
            if op == "rpush":
                self.redis.lists.setdefault(key, []).append(str(value))
        return []


def _sample_row(i: int) -> dict:
    second = i % 60
    return {
        "timestamp": f"2026-03-06T09:30:{second:02d}-05:00",
        "strike": 672.0 + (i % 5),
        "call_pct": -0.2 + (i * 0.0001),
        "put_pct": -0.1 + (i * 0.0001),
        "straddle_pct": -0.15 + (i * 0.0001),
    }


def _run_legacy_full_rewrite_benchmark(path: Path, ticks: int) -> tuple[float, int]:
    rows: list[dict] = []
    total_written_bytes = 0
    t0 = time.perf_counter()
    for i in range(ticks):
        rows.append(_sample_row(i))
        payload = json.dumps(rows)
        path.write_text(payload, encoding="utf-8")
        total_written_bytes += len(payload.encode("utf-8"))
    elapsed = time.perf_counter() - t0
    return elapsed, total_written_bytes


async def _run_jsonl_append_benchmark(path_dir: Path, ticks: int) -> tuple[float, int]:
    redis = _FakeRedis()
    storage = AtmDecayStorage(
        redis_client=redis,
        cold_dir=path_dir,
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )
    date_str = "20260306"
    t0 = time.perf_counter()
    for i in range(ticks):
        await storage.append_series(date_str, _sample_row(i))
    elapsed = time.perf_counter() - t0
    jsonl_path = path_dir / f"atm_series_{date_str}.jsonl"
    bytes_written = jsonl_path.stat().st_size if jsonl_path.exists() else 0
    return elapsed, bytes_written


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark ATM decay cold storage write strategy.")
    parser.add_argument("--ticks", type=int, default=5000, help="Number of synthetic ticks to write.")
    args = parser.parse_args()

    root = Path("tmp/pytest_cache/benchmarks")
    root.mkdir(parents=True, exist_ok=True)
    tmp_dir = root / f"atm_decay_bench_{uuid.uuid4().hex[:10]}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        legacy_path = tmp_dir / "legacy_full_rewrite.json"

        legacy_elapsed, legacy_bytes = _run_legacy_full_rewrite_benchmark(legacy_path, args.ticks)
        jsonl_elapsed, jsonl_bytes = await _run_jsonl_append_benchmark(tmp_dir, args.ticks)

        print("[benchmark] ATM decay storage")
        print(f"[benchmark] ticks={args.ticks}")
        print(f"[legacy] elapsed_s={legacy_elapsed:.6f} total_written_bytes={legacy_bytes}")
        print(f"[jsonl ] elapsed_s={jsonl_elapsed:.6f} file_size_bytes={jsonl_bytes}")
        if jsonl_elapsed > 0:
            print(f"[speedup] legacy/jsonl={legacy_elapsed / jsonl_elapsed:.2f}x")
        if jsonl_bytes > 0:
            print(f"[write_amp_ratio] legacy_written/jsonl_file={legacy_bytes / jsonl_bytes:.2f}x")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
