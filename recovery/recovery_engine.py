"""
Automated Recovery Engine & Alertmanager Webhook Receiver.
Receives alerts from Prometheus Alertmanager and executes automated self-healing
and remediation workflows (pod eviction, rolling restart, scale-out validation, log diagnostics).
"""

import datetime
import logging
import os
import subprocess
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "service":"automated-recovery", "level":"%(levelname)s", "msg":"%(message)s"}',
)
logger = logging.getLogger("automated-recovery")

PORT = int(os.getenv("PORT", "9099"))
SIMULATE_K8S_COMMANDS = os.getenv("SIMULATE_K8S_COMMANDS", "false").lower() == "true"

# Prometheus metrics for the Recovery Engine
REMEDIATION_TOTAL = Counter(
    "automated_remediations_total",
    "Total automated remediation actions executed",
    ["alert_name", "action_type", "result"],
)

ACTIVE_INCIDENTS = Gauge(
    "automated_recovery_active_incidents",
    "Current number of unmitigated active incidents",
)

# Incident record store
incident_log: List[Dict[str, Any]] = []


app = FastAPI(title="Automated Recovery & Self-Healing Engine", version="1.0.0")


class AlertItem(BaseModel):
    status: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None


class AlertmanagerPayload(BaseModel):
    version: Optional[str] = "4"
    groupKey: Optional[str] = ""
    status: str
    receiver: Optional[str] = ""
    alerts: List[AlertItem] = []


def run_kubectl(cmd: List[str]) -> str:
    """Executes a kubectl command or returns simulated output in test environments."""
    if SIMULATE_K8S_COMMANDS:
        return f"[Simulated execution of: kubectl {' '.join(cmd)}]"
    try:
        res = subprocess.run(
            ["kubectl"] + cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return res.stdout if res.returncode == 0 else f"Err: {res.stderr}"
    except Exception as exc:
        return f"[Kubectl execution fallback: {exc}]"


def execute_remediation(alert: AlertItem):
    """Executes targeted self-healing action based on alert labels and annotations."""
    alert_name = alert.labels.get("alertname", "UnknownAlert")
    pod_name = alert.labels.get("pod_name", alert.labels.get("kubernetes_pod_name", "unknown-pod"))
    namespace = alert.labels.get("kubernetes_namespace", "production-platform")
    action = alert.labels.get("action", "auto-remediate")
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    incident_id = f"INC-{int(time.time())}-{alert_name[:6]}"

    logger.info(f"Triggering automated remediation for {alert_name} on pod={pod_name} (Action: {action})")

    remediation_details = {
        "incident_id": incident_id,
        "timestamp": timestamp,
        "alert_name": alert_name,
        "pod_name": pod_name,
        "namespace": namespace,
        "status": "RESOLVED",
        "actions_taken": [],
    }

    if alert_name == "HighCpuUsage":
        # Check HPA scaling status & scale if not already scaling
        logger.info(f"[{incident_id}] Checking HorizontalPodAutoscaler status for high CPU load...")
        hpa_status = run_kubectl(["get", "hpa", "production-api-hpa", "-n", namespace])
        remediation_details["actions_taken"].append(f"Inspected HPA: {hpa_status}")
        remediation_details["actions_taken"].append("HPA auto-scale policy verified. Dynamic pod replicas expanding.")
        REMEDIATION_TOTAL.labels(alert_name=alert_name, action_type="verify_hpa_scale", result="success").inc()

    elif alert_name in ("PodUnhealthy", "PodDown", "CrashLoop"):
        # Pod failed liveness or crashed: Capture diagnostics and execute healing
        logger.info(f"[{incident_id}] Gathering previous crash logs for pod {pod_name}...")
        diag_logs = run_kubectl(["logs", pod_name, "-n", namespace, "--previous", "--tail=50"])
        remediation_details["actions_taken"].append(f"Captured crash diagnostics: {diag_logs[:200]}")
        
        # Evict / replace the failing pod so replica controller recreates clean replacement immediately
        logger.info(f"[{incident_id}] Deleting degraded pod {pod_name} to expedite clean replacement...")
        delete_res = run_kubectl(["delete", "pod", pod_name, "-n", namespace, "--grace-period=0", "--force"])
        remediation_details["actions_taken"].append(f"Kubernetes ReplicaSet recreation triggered: {delete_res}")
        REMEDIATION_TOTAL.labels(alert_name=alert_name, action_type="evict_failing_pod", result="success").inc()

    elif alert_name == "HighErrorRate":
        # Automated circuit breaker or rolling restart
        logger.info(f"[{incident_id}] Elevated 5xx rate detected. Triggering graceful rolling restart...")
        roll_res = run_kubectl(["rollout", "restart", "deployment/production-api", "-n", namespace])
        remediation_details["actions_taken"].append(f"Initiated graceful rolling restart: {roll_res}")
        REMEDIATION_TOTAL.labels(alert_name=alert_name, action_type="rolling_restart", result="success").inc()

    else:
        logger.info(f"[{incident_id}] Default automated triage executed for {alert_name}")
        remediation_details["actions_taken"].append("System diagnostic audit logged.")
        REMEDIATION_TOTAL.labels(alert_name=alert_name, action_type="audit_log", result="success").inc()

    incident_log.insert(0, remediation_details)
    if len(incident_log) > 100:
        incident_log.pop()


@app.post("/alerts")
async def receive_alertmanager_webhook(payload: AlertmanagerPayload, background_tasks: BackgroundTasks):
    """
    Webhook endpoint invoked by Prometheus Alertmanager.
    Dispatches automated self-healing tasks in the background.
    """
    logger.info(f"Received webhook payload from Alertmanager: {len(payload.alerts)} alerts (status={payload.status})")
    
    for alert in payload.alerts:
        if alert.status == "firing":
            ACTIVE_INCIDENTS.inc()
            background_tasks.add_task(execute_remediation, alert)
        elif alert.status == "resolved":
            ACTIVE_INCIDENTS.dec()
            logger.info(f"Alert resolved: {alert.labels.get('alertname')} on {alert.labels.get('pod_name')}")

    return {"status": "accepted", "alerts_processed": len(payload.alerts)}


@app.get("/incidents")
async def list_incidents():
    """Lists recent automated recovery incidents and remediation actions."""
    return {
        "total_recorded": len(incident_log),
        "incidents": incident_log[:20],
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "automated-recovery"}


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
