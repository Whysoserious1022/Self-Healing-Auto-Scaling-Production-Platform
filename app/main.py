"""
Production API Service with built-in Prometheus Telemetry,
Kubernetes Health Probes, and Chaos Testing Hooks for Self-Healing validation.
"""

import asyncio
import logging
import math
import os
import sys
import time
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .config import settings
from .metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    ACTIVE_REQUESTS,
    POD_HEALTH_STATUS,
    CHAOS_EVENTS,
    update_system_metrics,
    POD_NAME,
    NODE_NAME,
    APP_VERSION,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "pod":"' + POD_NAME + '", "message":"%(message)s"}',
)
logger = logging.getLogger("production-api")

# Internal state for health probes & chaos testing
state = {
    "is_alive": True,
    "is_ready": True,
    "failure_reason": None,
    "leaked_memory_blocks": [],
    "synthetic_cpu_burn": False,
    "synthetic_latency_ms": 0,
    "error_rate_injection": 0.0,  # 0.0 - 1.0 probability of returning 500
    "start_time": time.time(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"API service starting up on pod {POD_NAME} (version: {APP_VERSION})")
    update_system_metrics()
    yield
    logger.info(f"API service shutting down gracefully on pod {POD_NAME}")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)


@app.middleware("http")
async def prometheus_and_latency_middleware(request: Request, call_next):
    """Tracks Golden Signals: Latency, Error Rate, and Concurrency."""
    ACTIVE_REQUESTS.inc()
    start_time = time.perf_counter()
    endpoint = request.url.path

    # Simulate injected artificial latency if configured
    if state["synthetic_latency_ms"] > 0:
        await asyncio.sleep(state["synthetic_latency_ms"] / 1000.0)

    # Simulate injected failure rate if configured
    if state["error_rate_injection"] > 0:
        import random
        if random.random() < state["error_rate_injection"]:
            ACTIVE_REQUESTS.dec()
            REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status_code=500).inc()
            return JSONResponse(
                status_code=500,
                content={"error": "Injected chaos internal server error", "pod": POD_NAME},
            )

    try:
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        
        # Record Prometheus metrics
        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
        REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status_code=response.status_code).inc()
        
        # Periodic update of system resources
        update_system_metrics()
        return response
    except Exception as exc:
        duration = time.perf_counter() - start_time
        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
        REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status_code=500).inc()
        logger.error(f"Unhandled exception processing {endpoint}: {exc}")
        raise exc
    finally:
        ACTIVE_REQUESTS.dec()


# -------------------------------------------------------------
# Kubernetes Probes & Observability Endpoints
# -------------------------------------------------------------

@app.get("/", tags=["General"])
async def root():
    """Service status and pod metadata."""
    uptime = round(time.time() - state["start_time"], 2)
    return {
        "service": settings.app_name,
        "pod_name": POD_NAME,
        "node_name": NODE_NAME,
        "version": APP_VERSION,
        "status": "HEALTHY" if state["is_alive"] and state["is_ready"] else "DEGRADED",
        "uptime_seconds": uptime,
        "timestamp": time.time(),
    }


@app.get("/healthz", tags=["Kubernetes Probes"])
async def liveness_probe():
    """
    Kubernetes Liveness Probe.
    Returns 200 OK if the pod is alive.
    If 500 is returned, Kubernetes kubelet will detect failure, terminate,
    and restart the container (Self-Healing).
    """
    if not state["is_alive"]:
        POD_HEALTH_STATUS.labels(pod_name=POD_NAME).set(0)
        logger.warning(f"Liveness probe FAILED on {POD_NAME}: {state['failure_reason']}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "DEAD", "reason": state["failure_reason"], "pod": POD_NAME},
        )
    POD_HEALTH_STATUS.labels(pod_name=POD_NAME).set(1)
    return {"status": "ALIVE", "pod": POD_NAME}


@app.get("/ready", tags=["Kubernetes Probes"])
async def readiness_probe():
    """
    Kubernetes Readiness Probe.
    Returns 200 OK if ready to accept incoming traffic.
    If 503 is returned, Kubernetes Service removes the pod from endpoints
    without restarting it, protecting users from errors during warmup/degraded states.
    """
    if not state["is_ready"]:
        logger.warning(f"Readiness probe NOT READY on {POD_NAME}: {state['failure_reason']}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "NOT_READY", "reason": state["failure_reason"], "pod": POD_NAME},
        )
    return {"status": "READY", "pod": POD_NAME}


@app.get("/metrics", response_class=PlainTextResponse, tags=["Observability"])
async def metrics():
    """Prometheus Scrape Endpoint."""
    update_system_metrics()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# -------------------------------------------------------------
# Business Workload Endpoint (CPU & Request Scaling target)
# -------------------------------------------------------------

@app.get("/api/v1/work", tags=["Workload"])
async def do_work(
    compute_cycles: Optional[int] = None,
    delay_ms: int = 5,
):
    """
    Simulates production transaction/API workload.
    Executes algorithmic work to simulate realistic CPU consumption
    and latency characteristics under variable load.
    """
    cycles = compute_cycles if compute_cycles is not None else settings.base_cpu_work_cycles
    
    # Simulate CPU computational work (e.g. hashing / JSON processing / cryptography)
    start_time = time.perf_counter()
    total = 0.0
    for i in range(cycles):
        total += math.sqrt(i) * math.sin(i)

    # Simulate DB or network I/O delay
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000.0)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return {
        "status": "success",
        "pod": POD_NAME,
        "elapsed_ms": elapsed_ms,
        "cycles_processed": cycles,
    }


# -------------------------------------------------------------
# Chaos Engineering & Self-Healing Testing Hooks
# -------------------------------------------------------------

@app.post("/chaos/kill", tags=["Chaos Testing"])
async def chaos_kill_pod():
    """
    Deliberately kills the API process immediately.
    Demonstrates:
    1. Container process sudden termination
    2. Kubernetes detects dead pod
    3. Replacement pod created automatically
    4. Service traffic seamlessly routed to surviving pods
    """
    CHAOS_EVENTS.labels(scenario="kill_pod", pod_name=POD_NAME).inc()
    logger.critical(f"CHAOS INJECTED: Sudden process termination on pod {POD_NAME}!")
    
    # Schedule process exit shortly so response can be transmitted
    def terminate():
        time.sleep(0.1)
        os._exit(1)

    import threading
    threading.Thread(target=terminate, daemon=True).start()
    return {
        "message": f"Fatal crash injected. Process on pod {POD_NAME} terminating now.",
        "expected_result": "Kubernetes should detect exit status 1 and restart/replace pod.",
        "pod": POD_NAME,
    }


@app.post("/chaos/cpu", tags=["Chaos Testing"])
async def chaos_cpu_spike(duration_seconds: int = 15, intensity: int = 4):
    """
    Spikes CPU utilization to 75%+ across multiple threads.
    Triggers:
    1. CPU threshold breach (> 60-70%)
    2. Kubernetes Horizontal Pod Autoscaler (HPA) triggers scale out (2 -> 5 pods)
    3. Alertmanager fires HighCPUUsage alert
    """
    CHAOS_EVENTS.labels(scenario="cpu_spike", pod_name=POD_NAME).inc()
    logger.warning(f"CHAOS INJECTED: High CPU spike initiated for {duration_seconds}s on {POD_NAME}")

    def burn_cpu():
        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            _ = [math.sqrt(x) * math.tan(x) for x in range(10000)]

    import threading
    for _ in range(intensity):
        threading.Thread(target=burn_cpu, daemon=True).start()

    return {
        "message": f"CPU spike launched ({intensity} threads for {duration_seconds}s) on {POD_NAME}",
        "expected_result": "CPU utilization will jump to 75%+, triggering HPA scaling.",
        "pod": POD_NAME,
    }


@app.post("/chaos/leak", tags=["Chaos Testing"])
async def chaos_memory_leak(mb_to_leak: int = 64):
    """
    Simulates a memory leak by retaining allocated buffers in memory.
    Triggers:
    1. Memory growth monitoring alerts
    2. OOMKilled by Linux kernel/cgroups when container limit (512Mi) is exceeded
    3. Kubernetes automatically restarts the pod
    """
    CHAOS_EVENTS.labels(scenario="memory_leak", pod_name=POD_NAME).inc()
    # Allocate bytearray (1MB = 1024 * 1024 bytes)
    block = bytearray(mb_to_leak * 1024 * 1024)
    state["leaked_memory_blocks"].append(block)
    total_leaked_mb = len(state["leaked_memory_blocks"]) * mb_to_leak
    
    logger.warning(f"CHAOS INJECTED: Leaked {mb_to_leak}MB on {POD_NAME}. Total leaked: {total_leaked_mb}MB")
    update_system_metrics()
    return {
        "message": f"Allocated and retained {mb_to_leak}MB of uncollectable memory.",
        "total_leaked_mb": total_leaked_mb,
        "pod": POD_NAME,
    }


@app.post("/chaos/fail-liveness", tags=["Chaos Testing"])
async def chaos_fail_liveness(reason: str = "Deadlock / internal state corruption"):
    """
    Forces the /healthz liveness probe to return 500 Internal Server Error.
    Kubernetes kubelet detects 3 consecutive failures and restarts container.
    """
    state["is_alive"] = False
    state["failure_reason"] = reason
    POD_HEALTH_STATUS.labels(pod_name=POD_NAME).set(0)
    CHAOS_EVENTS.labels(scenario="fail_liveness", pod_name=POD_NAME).inc()
    logger.warning(f"CHAOS INJECTED: Liveness probe disabled on {POD_NAME}: {reason}")
    return {
        "status": "Liveness probe set to FAILING (500)",
        "reason": reason,
        "pod": POD_NAME,
    }


@app.post("/chaos/fail-readiness", tags=["Chaos Testing"])
async def chaos_fail_readiness(reason: str = "Database connection pool exhausted"):
    """
    Forces the /ready readiness probe to return 503 Service Unavailable.
    Kubernetes immediately stops sending traffic to this pod.
    """
    state["is_ready"] = False
    state["failure_reason"] = reason
    CHAOS_EVENTS.labels(scenario="fail_readiness", pod_name=POD_NAME).inc()
    logger.warning(f"CHAOS INJECTED: Readiness probe set to NOT_READY on {POD_NAME}: {reason}")
    return {
        "status": "Readiness probe set to UNREADY (503)",
        "reason": reason,
        "pod": POD_NAME,
    }


@app.post("/chaos/error-rate", tags=["Chaos Testing"])
async def chaos_inject_errors(rate: float = 0.5):
    """Injects synthetic 500 error rate (e.g. 0.5 = 50% errors)."""
    state["error_rate_injection"] = rate
    CHAOS_EVENTS.labels(scenario="inject_errors", pod_name=POD_NAME).inc()
    return {
        "status": f"Injected error rate set to {rate * 100}%",
        "pod": POD_NAME,
    }


@app.post("/chaos/restore", tags=["Chaos Testing"])
async def chaos_restore_normal():
    """Resets all injected chaos states to healthy defaults."""
    state["is_alive"] = True
    state["is_ready"] = True
    state["failure_reason"] = None
    state["synthetic_latency_ms"] = 0
    state["error_rate_injection"] = 0.0
    state["leaked_memory_blocks"].clear()
    POD_HEALTH_STATUS.labels(pod_name=POD_NAME).set(1)
    logger.info(f"Pod {POD_NAME} restored to NORMAL healthy state.")
    return {"status": "RESTORED_HEALTHY", "pod": POD_NAME}


@app.get("/chaos/status", tags=["Chaos Testing"])
async def chaos_status():
    """Inspects the current chaos state of this pod instance."""
    return {
        "pod_name": POD_NAME,
        "is_alive": state["is_alive"],
        "is_ready": state["is_ready"],
        "failure_reason": state["failure_reason"],
        "leaked_blocks_count": len(state["leaked_memory_blocks"]),
        "injected_error_rate": state["error_rate_injection"],
        "synthetic_latency_ms": state["synthetic_latency_ms"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
