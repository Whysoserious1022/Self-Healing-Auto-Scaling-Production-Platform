"""
Tests for ChaosTester and LoadGenerator modules against the local application.
"""

import threading
import time
import uvicorn
import pytest
from tests.chaos_test import ChaosTester
from tests.load_generator import LoadGenerator
from app.main import app as production_api
import asyncio


@pytest.fixture(scope="module")
def live_server():
    """Starts a live uvicorn server in a background thread for end-to-end testing."""
    config = uvicorn.Config(production_api, host="127.0.0.1", port=8989, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    
    # Wait for server to be responsive
    tester = ChaosTester(base_url="http://127.0.0.1:8989")
    for _ in range(30):
        res = tester.check_health()
        if res.get("alive"):
            break
        time.sleep(0.1)

    yield "http://127.0.0.1:8989"
    server.should_exit = True


def test_chaos_tester_lifecycle(live_server):
    tester = ChaosTester(base_url=live_server)
    
    # Check initial health
    h = tester.check_health()
    assert h["alive"] is True
    assert h["ready"] is True

    # Test CPU spike trigger
    cpu = tester.trigger_cpu_spike(duration=1, intensity=1)
    assert "CPU spike launched" in cpu.get("message", "")

    # Test Memory leak
    leak = tester.trigger_memory_leak(mb=8)
    assert leak.get("total_leaked_mb", 0) >= 8

    # Test liveness probe failure
    fail = tester.trigger_liveness_failure(reason="E2E test deadlock")
    assert "FAILING" in fail.get("status", "")

    # Check health reflects failure
    h2 = tester.check_health()
    assert h2["alive"] is False

    # Restore health
    rest = tester.restore_health()
    assert rest.get("status") == "RESTORED_HEALTHY"

    # Verify health restored
    h3 = tester.check_health()
    assert h3["alive"] is True
    assert h3["ready"] is True


def test_load_generator_execution(live_server):
    gen = LoadGenerator(target_url=f"{live_server}/api/v1/work")
    res = asyncio.run(gen.run_load(target_rps=50, duration_sec=2, concurrency=4))
    
    assert res["total_requests"] > 0
    assert res["success_200"] > 0
    assert res["errors_5xx"] == 0
    assert res["p50_latency_ms"] >= 0
