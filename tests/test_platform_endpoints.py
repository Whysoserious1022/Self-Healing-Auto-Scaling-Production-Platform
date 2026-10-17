"""
Comprehensive Test Suite for Self-Healing & Auto-Scaling Production Platform.
Tests all features across:
1. Production API Service (Health probes, Golden signals, Prometheus metrics, Chaos hooks)
2. Recovery Engine (Alertmanager webhook, Automated remediation workflows, Incident tracking)
3. Mission Control Dashboard API (Telemetry, Chaos controls, Playbooks, Guardian Assistant, Exports)
"""

import pytest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app as production_api
from recovery.recovery_engine import app as recovery_app
from dashboard.server import app as dashboard_app


# =====================================================================
# 1. Production API Service Tests
# =====================================================================

class TestProductionAPI:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(production_api)

    def test_root_metadata(self):
        """Verify root endpoint returns healthy metadata."""
        res = self.client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert "service" in data
        assert "uptime_seconds" in data

    def test_healthz_liveness_nominal(self):
        """Verify liveness probe returns 200 OK under nominal state."""
        res = self.client.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ALIVE"

    def test_ready_readiness_nominal(self):
        """Verify readiness probe returns 200 OK under nominal state."""
        res = self.client.get("/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "READY"

    def test_workload_execution(self):
        """Verify /api/v1/work processes compute load and returns golden signals."""
        res = self.client.get("/api/v1/work", params={"compute_cycles": 1000, "delay_ms": 2})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "elapsed_ms" in data
        assert "pod" in data
        assert data["cycles_processed"] == 1000

    def test_prometheus_metrics_export(self):
        """Verify /metrics exports Prometheus formatted metrics."""
        res = self.client.get("/metrics")
        assert res.status_code == 200
        assert "http_requests_total" in res.text or "python_info" in res.text

    def test_chaos_liveness_failure_and_restore(self):
        """Verify chaos injection for liveness failure and subsequent recovery."""
        # Inject failure
        fail_res = self.client.post("/chaos/fail-liveness", params={"reason": "Test Deadlock"})
        assert fail_res.status_code == 200
        assert "FAILING" in fail_res.json()["status"]

        # Liveness probe must now return 500 Internal Server Error
        h_res = self.client.get("/healthz")
        assert h_res.status_code == 500
        assert h_res.json()["status"] == "DEAD"

        # Restore health
        rest_res = self.client.post("/chaos/restore")
        assert rest_res.status_code == 200
        assert rest_res.json()["status"] == "RESTORED_HEALTHY"

        # Verify restored to 200 OK
        assert self.client.get("/healthz").status_code == 200
        assert self.client.get("/ready").status_code == 200

    def test_chaos_readiness_failure_and_restore(self):
        """Verify readiness probe failure returns 503 and protects downstream."""
        fail_res = self.client.post("/chaos/fail-readiness", params={"reason": "DB pool exhausted"})
        assert fail_res.status_code == 200
        assert "UNREADY" in fail_res.json()["status"]

        # Readiness probe must now return 503
        r_res = self.client.get("/ready")
        assert r_res.status_code == 503
        assert r_res.json()["status"] == "NOT_READY"

        # Restore
        self.client.post("/chaos/restore")
        assert self.client.get("/ready").status_code == 200

    def test_chaos_memory_leak(self):
        """Verify simulated memory leak allocation."""
        leak_res = self.client.post("/chaos/leak", params={"mb_to_leak": 16})
        assert leak_res.status_code == 200
        assert "total_leaked_mb" in leak_res.json()
        self.client.post("/chaos/restore")

    def test_chaos_cpu_spike(self):
        """Verify CPU spike trigger."""
        cpu_res = self.client.post("/chaos/cpu", params={"duration_seconds": 1, "intensity": 2})
        assert cpu_res.status_code == 200
        assert "CPU spike launched" in cpu_res.json()["message"]

    def test_chaos_status_inspect(self):
        """Verify chaos status inspection endpoint."""
        res = self.client.get("/chaos/status")
        assert res.status_code == 200
        data = res.json()
        assert "is_alive" in data
        assert "is_ready" in data


# =====================================================================
# 2. Recovery Engine Tests
# =====================================================================

class TestRecoveryEngine:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(recovery_app)

    def test_recovery_healthz(self):
        """Verify recovery service health check."""
        res = self.client.get("/healthz")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_alertmanager_webhook_high_cpu(self):
        """Verify recovery engine processes HighCpuUsage alert."""
        payload = {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighCpuUsage",
                        "kubernetes_pod_name": "production-api-7b9c4-w8k12",
                        "kubernetes_namespace": "production-platform"
                    },
                    "annotations": {
                        "description": "CPU utilization above 70% threshold"
                    }
                }
            ]
        }
        res = self.client.post("/alerts", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["alerts_processed"] == 1

        # Check incidents endpoint
        inc_res = self.client.get("/incidents")
        assert inc_res.status_code == 200
        assert inc_res.json()["total_recorded"] >= 1

    def test_alertmanager_webhook_oom_killed(self):
        """Verify recovery engine handles PodOOMKilling alert and restarts."""
        payload = {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "PodOOMKilling",
                        "kubernetes_pod_name": "production-api-7b9c4-oom99",
                        "kubernetes_namespace": "production-platform"
                    },
                    "annotations": {
                        "description": "Container memory limit exceeded"
                    }
                }
            ]
        }
        res = self.client.post("/alerts", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["alerts_processed"] == 1

    def test_incidents_log_retrieval(self):
        """Verify recorded incidents can be retrieved."""
        res = self.client.get("/incidents")
        assert res.status_code == 200
        data = res.json()
        assert "incidents" in data
        assert isinstance(data["incidents"], list)


# =====================================================================
# 3. Mission Control Dashboard API Tests
# =====================================================================

class TestDashboardAPI:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(dashboard_app)

    def test_dashboard_state(self):
        """Verify /api/state returns comprehensive cluster and pod telemetry."""
        res = self.client.get("/api/state")
        assert res.status_code == 200
        data = res.json()
        assert "traffic_rps" in data
        assert "avg_cpu_percent" in data
        assert "active_pods" in data
        assert "events" in data
        assert "history" in data
        assert len(data["active_pods"]) >= 2

    def test_dashboard_set_traffic(self):
        """Verify dynamic traffic setting via control endpoint."""
        res = self.client.post("/api/control", json={"action": "set_traffic", "target_rps": 250})
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_dashboard_kill_pod_chaos(self):
        """Verify simulated pod kill and self-healing trigger."""
        res = self.client.post("/api/control", json={"action": "kill_pod"})
        assert res.status_code == 200
        assert res.json()["status"] in ["killed", "not_found"]

    def test_dashboard_reset(self):
        """Verify system reset restores baseline nominal state."""
        res = self.client.post("/api/control", json={"action": "reset"})
        assert res.status_code == 200
        assert res.json()["status"] == "reset"

    def test_guardian_faqs(self):
        """Verify Guardian assistant FAQs are available."""
        res = self.client.get("/api/guardian/faq")
        assert res.status_code == 200
        assert "faqs" in res.json()
        assert len(res.json()["faqs"]) >= 4

    def test_guardian_ask(self):
        """Verify Guardian assistant answers natural language questions."""
        res = self.client.post("/api/guardian/ask", json={"query": "Why does HPA scale down slowly?"})
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert "cluster_context" in data

    def test_export_logs(self):
        """Verify JSON audit log export."""
        res = self.client.get("/api/export-logs")
        assert res.status_code == 200
        data = res.json()
        assert "events" in data
        assert "cluster" in data

    def test_root_index_html(self):
        """Verify index.html is served at root."""
        res = self.client.get("/")
        assert res.status_code == 200
        assert "html" in res.headers.get("content-type", "").lower()
