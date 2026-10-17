"""
Asynchronous High-Throughput Load Generator.
Generates controlled HTTP request load (e.g. 100 RPS, 500 RPS) to test
Horizontal Pod Autoscaler and API responsiveness.
"""

import asyncio
import time
import sys
from typing import Dict, Optional
import requests


class LoadGenerator:
    def __init__(self, target_url: str = "http://localhost:8000/api/v1/work"):
        self.target_url = target_url
        self.stop_signal = False
        self.stats = {
            "total_sent": 0,
            "success_200": 0,
            "errors_5xx": 0,
            "other": 0,
            "latencies": [],
        }

    async def _worker_batch(self, rps: int, duration_sec: int):
        """Dispatches requests at target rate per second."""
        interval = 1.0 / rps if rps > 0 else 0.01
        end_time = time.time() + duration_sec
        loop = asyncio.get_event_loop()

        while time.time() < end_time and not self.stop_signal:
            t0 = time.perf_counter()
            try:
                # Run synchronous HTTP request in thread executor
                res = await loop.run_in_executor(
                    None,
                    lambda: requests.get(self.target_url, timeout=4.0)
                )
                latency = time.perf_counter() - t0
                self.stats["total_sent"] += 1
                self.stats["latencies"].append(latency)
                if res.status_code == 200:
                    self.stats["success_200"] += 1
                elif res.status_code >= 500:
                    self.stats["errors_5xx"] += 1
                else:
                    self.stats["other"] += 1
            except Exception:
                self.stats["errors_5xx"] += 1

            elapsed = time.perf_counter() - t0
            sleep_needed = interval - elapsed
            if sleep_needed > 0:
                await asyncio.sleep(sleep_needed)

    async def run_load(self, target_rps: int, duration_sec: int, concurrency: int = 10) -> Dict:
        """Runs multi-worker load generation."""
        self.stop_signal = False
        self.stats = {
            "total_sent": 0,
            "success_200": 0,
            "errors_5xx": 0,
            "other": 0,
            "latencies": [],
        }
        
        per_worker_rps = max(1, target_rps // concurrency)
        tasks = [
            self._worker_batch(per_worker_rps, duration_sec)
            for _ in range(concurrency)
        ]
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        total_time = max(0.1, time.time() - start_time)

        actual_rps = round(self.stats["total_sent"] / total_time, 1)
        latencies = self.stats["latencies"]
        p50 = round(sorted(latencies)[int(len(latencies) * 0.5)] * 1000, 2) if latencies else 0
        p95 = round(sorted(latencies)[int(len(latencies) * 0.95)] * 1000, 2) if latencies else 0

        return {
            "target_rps": target_rps,
            "actual_rps": actual_rps,
            "duration_sec": round(total_time, 2),
            "total_requests": self.stats["total_sent"],
            "success_200": self.stats["success_200"],
            "errors_5xx": self.stats["errors_5xx"],
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
        }


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1/work"
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    print(f"[*] Starting Load Test against {url} (Target: {target} RPS for {duration}s)...")
    gen = LoadGenerator(url)
    res = asyncio.run(gen.run_load(target, duration))
    print(f"[+] Load Test Results: {res}")
