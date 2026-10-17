"""
Prometheus Metrics Instrumentation for Production API Service.
Tracks Golden Signals: Latency, Traffic, Errors, and Saturation.
"""

import os
import psutil
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# Application & Pod Identity Info
POD_NAME = os.getenv("POD_NAME", os.getenv("HOSTNAME", "pod-local-dev"))
NODE_NAME = os.getenv("NODE_NAME", "node-local")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

pod_info = Info("production_api_info", "Metadata about the running API instance")
pod_info.info({
    "pod_name": POD_NAME,
    "node_name": NODE_NAME,
    "version": APP_VERSION,
})

# 1. Traffic & Errors
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total count of HTTP requests processed",
    ["method", "endpoint", "status_code"],
)

# 2. Latency
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Histogram of HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# 3. Concurrency
ACTIVE_REQUESTS = Gauge(
    "http_active_requests",
    "Number of active in-flight HTTP requests",
)

# 4. Saturation & System Metrics
CPU_UTILIZATION_GAUGE = Gauge(
    "process_cpu_utilization_percent",
    "Current CPU utilization percentage of the container",
    ["pod_name"],
)

MEMORY_USAGE_GAUGE = Gauge(
    "process_memory_usage_bytes",
    "Resident set size (RSS) memory consumption in bytes",
    ["pod_name"],
)

# 5. Health & Self-Healing Indicators
POD_HEALTH_STATUS = Gauge(
    "pod_health_status",
    "Health status indicator (1 = Healthy, 0 = Unhealthy/Failing)",
    ["pod_name"],
)
POD_HEALTH_STATUS.labels(pod_name=POD_NAME).set(1)

# 6. Chaos Testing Metric
CHAOS_EVENTS = Counter(
    "chaos_injected_events_total",
    "Total count of injected chaos and failure scenarios",
    ["scenario", "pod_name"],
)


def update_system_metrics():
    """Updates psutil CPU and memory metrics for Prometheus scrape."""
    try:
        process = psutil.Process(os.getpid())
        cpu_pct = process.cpu_percent(interval=None)
        mem_bytes = process.memory_info().rss
        CPU_UTILIZATION_GAUGE.labels(pod_name=POD_NAME).set(cpu_pct)
        MEMORY_USAGE_GAUGE.labels(pod_name=POD_NAME).set(mem_bytes)
    except Exception:
        pass
