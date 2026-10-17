"""
Chaos Engineering and Failure Injection Test Suite.
Verifies Kubernetes Self-Healing, Liveness probe restarts, and Zero-Downtime resilience.
"""

import time
import requests
from typing import Dict, List, Optional


class ChaosTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def check_health(self) -> Dict:
        """Queries /healthz and /ready endpoints."""
        try:
            h_res = requests.get(f"{self.base_url}/healthz", timeout=3.0)
            r_res = requests.get(f"{self.base_url}/ready", timeout=3.0)
            return {
                "alive": h_res.status_code == 200,
                "ready": r_res.status_code == 200,
                "liveness_code": h_res.status_code,
                "readiness_code": r_res.status_code,
            }
        except Exception as exc:
            return {"alive": False, "ready": False, "error": str(exc)}

    def trigger_pod_kill(self) -> Dict:
        """Simulates sudden pod fatal crash."""
        print(f"[*] Sending kill signal to {self.base_url}/chaos/kill ...")
        try:
            res = requests.post(f"{self.base_url}/chaos/kill", timeout=3.0)
            return res.json() if res.status_code == 200 else {"status": "sent"}
        except requests.exceptions.RequestException:
            # Expected because process terminates immediately
            return {"status": "process_terminated_successfully"}

    def trigger_cpu_spike(self, duration: int = 15, intensity: int = 4) -> Dict:
        """Triggers high CPU spike to test HPA."""
        print(f"[*] Triggering CPU spike ({duration}s, intensity={intensity})...")
        res = requests.post(
            f"{self.base_url}/chaos/cpu",
            params={"duration_seconds": duration, "intensity": intensity},
            timeout=5.0,
        )
        return res.json()

    def trigger_memory_leak(self, mb: int = 64) -> Dict:
        """Injects memory leak."""
        print(f"[*] Ingesting memory leak ({mb}MB)...")
        res = requests.post(
            f"{self.base_url}/chaos/leak",
            params={"mb_to_leak": mb},
            timeout=5.0,
        )
        return res.json()

    def trigger_liveness_failure(self, reason: str = "Simulated Deadlock") -> Dict:
        """Fails liveness probe to trigger Kubelet container restart."""
        print(f"[*] Forcing liveness probe failure: {reason}")
        res = requests.post(
            f"{self.base_url}/chaos/fail-liveness",
            params={"reason": reason},
            timeout=5.0,
        )
        return res.json()

    def restore_health(self) -> Dict:
        """Restores pod to healthy state."""
        res = requests.post(f"{self.base_url}/chaos/restore", timeout=5.0)
        return res.json()

    def verify_continuous_availability(self, duration_sec: int = 10, probe_interval_sec: float = 0.5) -> Dict:
        """
        Continuously probes the API while failure happens.
        Proves service continuity and zero-downtime.
        """
        end_time = time.time() + duration_sec
        probes_sent = 0
        probes_succeeded = 0

        while time.time() < end_time:
            probes_sent += 1
            try:
                r = requests.get(f"{self.base_url}/api/v1/work", timeout=2.0)
                if r.status_code == 200:
                    probes_succeeded += 1
            except Exception:
                pass
            time.sleep(probe_interval_sec)

        availability_pct = round((probes_succeeded / max(1, probes_sent)) * 100, 2)
        return {
            "probes_sent": probes_sent,
            "probes_succeeded": probes_succeeded,
            "availability_pct": availability_pct,
            "zero_downtime_preserved": availability_pct >= 95.0,
        }
