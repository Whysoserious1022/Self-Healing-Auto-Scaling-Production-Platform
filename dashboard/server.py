"""
Interactive Mission Control & Real-Time Visualization Server.
Human-Centric SRE Platform with live telemetry, scenario narrator,
and self-healing automated recovery.
"""

import asyncio
import datetime
import os
import random
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Self-Healing & Auto-Scaling Production Platform")

# Internal platform state simulation & live tracker
platform_state = {
    "traffic_rps": 100,
    "desired_rps": 100,
    "avg_cpu_percent": 35.0,
    "target_cpu_percent": 60.0,
    "p95_latency_ms": 14.2,
    "p99_latency_ms": 16.2,
    "fleet_cpu_load": 68.4,
    "global_rps_str": "4.2M req/s",
    "auto_remediations_hr": 38,
    "error_rate_percent": 0.0,
    "hpa_min_replicas": 2,
    "hpa_max_replicas": 5,
    "cluster_status": "HEALTHY",
    "is_auto_running": False,
    "manual_safety_override": False,
    "current_scenario_step": "Baseline: 100 RPS (2 Pods)",
    "scenario_phase_index": 1,  # 1: Baseline, 2: Surge, 3: Scaled, 4: Cooldown, 5: Chaos/Healing
    "cost_savings_percent": 60.0,
    "uptime_sla_percent": 99.999,
    "healing_rate": 99.4,
    "healing_rate_nominal": "99.4% NOMINAL",
    "resolved_incidents": 420,
    "total_incidents": 422,
    "mttr_seconds": 1.4,
    "manual_baseline_mttr": "10m 20s",
    "safety_interlocks": {"active": 9, "total": 9, "mode": "Canary Strict"},
    "self_healing_daemons": 14820,
    "zone_failover_canary_pool": 48,
    "autonomous_daemon_status": "ACTIVE / ENFORCING",
    "human_narrative": "System running normally at 100 requests/sec across 2 pods. CPU is 35%. User requests are being served in ~14ms with zero errors.",
    "narratives": {
        "sre": "System running normally at 100 requests/sec across 2 pods. CPU is 35.0%. P95 latency is 14.2ms with zero 5xx errors.",
        "executive": "All services nominal. Customer experience is 100% uninterrupted (0 errors), operating at optimal cloud efficiency with 60% compute savings.",
        "eli5": "Everything is running smoothly! Like a calm morning in a bakery with two friendly bakers handling 100 breakfast orders effortlessly."
    },
    "narrative_mood": "calm",  # 'calm', 'surge', 'healing', 'success'
    "active_pods": [
        {
            "id": "pod-api-prod-a1",
            "name": "production-api-7b9c4-w8k12",
            "callsign": "Atlas",
            "role": "Primary Ingress Worker",
            "node": "ip-10-0-1-42.ec2.internal",
            "status": "Running",
            "ready": True,
            "cpu_percent": 34.5,
            "memory_mb": 118,
            "restarts": 0,
            "uptime_sec": 1420,
            "ip": "10.244.1.18",
            "mood_badge": "😊 Calm & Healthy",
        },
        {
            "id": "pod-api-prod-b2",
            "name": "production-api-7b9c4-q9m45",
            "callsign": "Beacon",
            "role": "Core API Service",
            "node": "ip-10-0-2-88.ec2.internal",
            "status": "Running",
            "ready": True,
            "cpu_percent": 35.8,
            "memory_mb": 122,
            "restarts": 0,
            "uptime_sec": 1420,
            "ip": "10.244.2.24",
            "mood_badge": "😊 Calm & Healthy",
        },
    ],
    "playbooks": [
        {
            "id": "crashloop",
            "name": "CrashLoopBackOff Auto-Rollback",
            "spec": "remediation.k8s.v1/crashloop-drain",
            "events_24h": 42,
            "avg_latency": "1.1s",
            "success_rate": "100%",
            "state": "NOMINAL"
        },
        {
            "id": "oomkill",
            "name": "Memory Leak & OOMKill Rotation",
            "spec": "remediation.mem.v2/ebpf-predictive-oom",
            "events_24h": 80,
            "avg_latency": "600ms",
            "success_rate": "99.8%",
            "state": "TRIGGERED"
        },
        {
            "id": "deadlock",
            "name": "DeadLock Thread-Starvation Dump & Restart",
            "spec": "remediation.sys.v1/thread-isolate-sigquit",
            "events_24h": 14,
            "avg_latency": "2.4s",
            "success_rate": "100%",
            "state": "NOMINAL"
        },
        {
            "id": "storage",
            "name": "Corrupted Block Storage Hot-Swap",
            "spec": "remediation.io.v3/nvme-rebind-nvmf",
            "events_24h": 3,
            "avg_latency": "8.2s",
            "success_rate": "96.7%",
            "state": "WATCHING"
        },
        {
            "id": "zombie_pool",
            "name": "Database Zombie Pool Flusher",
            "spec": "remediation.pg.v1/pgbouncer-idle-reap",
            "events_24h": 19,
            "avg_latency": "450ms",
            "success_rate": "100%",
            "state": "NOMINAL"
        }
    ],
    "incident_deep_dive": {
        "incident_id": "#INC-8941",
        "target": "payment-service CPU Stall",
        "time_ago": "1m 42s ago",
        "status": "AUTONOMOUSLY RESOLVED",
        "namespace": "finance-prod",
        "pod_uid": "pod-9021a8f",
        "pager_escalated": "NO",
        "steps": [
            {
                "num": 1,
                "title": "eBPF Anomaly Detected",
                "time": "T+0.00s",
                "detail": "99.8% CPU saturation in payment-service-prod-7d4bf. Scheduler starvation threshold exceeded."
            },
            {
                "num": 2,
                "title": "Circuit Breaker Tripped",
                "time": "T+0.12s",
                "detail": "Downstream ingress severed by Envoy mesh filter to prevent cascade backlog into checkout-gateway."
            },
            {
                "num": 3,
                "title": "Canary Replacement Spawned",
                "time": "T+0.38s",
                "detail": "Hot replacement pod payment-service-canary-4b11 initialized in 380ms on Node node-us-east-1a-09."
            },
            {
                "num": 4,
                "title": "Tainted Node Cordoned & DUMP Captured",
                "time": "T+0.82s",
                "detail": "Unhealthy node cordoned; SIGQUIT heap snapshot (41.2MB) captured and pushed to telemetry s3 bucket s3://telemetry/dumps/inc-8941.zst."
            },
            {
                "num": 5,
                "title": "Incident Verified Resolved",
                "time": "T+1.40s Total",
                "detail": "Synthetic telemetry probe confirmed 0 dropped customer transactions, 100% 2xx responses on retry loop."
            }
        ]
    },
    "ai_root_cause": {
        "confidence": 98,
        "title": "MUTEX STARVATION IN stream_reconciler.go:142 go1.22.4",
        "description": "Unbuffered channel write blocks on channel.sync() while holding reader lock on global state. Rapid traffic burst caused 128 goroutines to queue indefinitely.",
        "pr_proposal": {
            "file": "stream_reconciler.go",
            "patch_ref": "#patch-4402",
            "pr_ref": "#4482",
            "merged": False,
            "diff_remove": "- mu.RLock(); defer mu.RUnlock()",
            "diff_add": "+ select { case ch <- event: default: log.warn(\"dropped\") }"
        }
    },
    "mutation_velocity": [12, 15, 18, 14, 22, 19, 28, 34, 25, 20, 18, 22, 16, 24, 29, 34, 21, 19],
    "history": {
        "timestamps": [],
        "rps": [],
        "cpu": [],
        "pods": [],
        "latency": [],
    },
    "events": [],
}


def update_narratives(mood: str, step: str, sre: str, executive: str, eli5: str):
    """Updates multi-lens human narratives across SRE, Executive, and ELI5 perspectives."""
    platform_state["narrative_mood"] = mood
    platform_state["current_scenario_step"] = step
    platform_state["human_narrative"] = sre
    platform_state["narratives"] = {
        "sre": sre,
        "executive": executive,
        "eli5": eli5
    }


def add_event(source: str, level: str, message: str):
    """Appends an event to the live console stream."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    event = {
        "time": timestamp,
        "source": source,
        "level": level,  # 'info', 'warn', 'error', 'success', 'k8s'
        "message": message,
    }
    platform_state["events"].insert(0, event)
    if len(platform_state["events"]) > 150:
        platform_state["events"].pop()


# Populate initial events
add_event("Kubelet", "info", "Cluster node 'ip-10-0-1-42.ec2.internal' reported Ready (v1.29.3)")
add_event("Prometheus", "info", "Scraping endpoints in namespace 'production-platform' at 5s interval")
add_event("HPA", "info", "HorizontalPodAutoscaler initialized (Target: 60% CPU, Range: 2-5 pods)")
add_event("Deployment", "success", "Deployment 'production-api' is stable: 2/2 replicas healthy")


async def state_background_ticker():
    """Runs a continuous telemetry loop to update metrics, history, and simulate realistic physics."""
    while True:
        try:
            # Smoothly transition traffic_rps towards desired_rps
            diff = platform_state["desired_rps"] - platform_state["traffic_rps"]
            if abs(diff) > 2:
                platform_state["traffic_rps"] += int(diff * 0.3)
            else:
                platform_state["traffic_rps"] = platform_state["desired_rps"]

            # Compute dynamic CPU based on active pods and traffic
            num_pods = max(1, len([p for p in platform_state["active_pods"] if p["ready"]]))
            per_pod_load = platform_state["traffic_rps"] / num_pods
            
            # Base load ~0.35% per RPS per pod + slight random jitter
            target_cpu = min(98.0, max(12.0, per_pod_load * 0.72 + random.uniform(-1.5, 1.5)))
            
            # CPU smoothed change
            cpu_diff = target_cpu - platform_state["avg_cpu_percent"]
            platform_state["avg_cpu_percent"] = round(platform_state["avg_cpu_percent"] + cpu_diff * 0.25, 1)

            # Update per-pod metrics
            for pod in platform_state["active_pods"]:
                if pod["ready"]:
                    pod["cpu_percent"] = round(platform_state["avg_cpu_percent"] + random.uniform(-2.5, 2.5), 1)
                    pod["uptime_sec"] += 1

            # Latency calculation
            if platform_state["avg_cpu_percent"] > 70:
                platform_state["p95_latency_ms"] = round(15.0 + (platform_state["avg_cpu_percent"] - 70) * 1.8 + random.uniform(0, 3), 1)
            else:
                platform_state["p95_latency_ms"] = round(12.0 + random.uniform(0.5, 3.0), 1)

            # Dynamic Cost savings calculation (5 pods baseline vs current pods)
            saved_pods = max(0, 5 - num_pods)
            platform_state["cost_savings_percent"] = round((saved_pods / 5.0) * 100.0, 0)

            # Record history buffer (last 30 ticks)
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            h = platform_state["history"]
            h["timestamps"].append(now_str)
            h["rps"].append(platform_state["traffic_rps"])
            h["cpu"].append(platform_state["avg_cpu_percent"])
            h["pods"].append(num_pods)
            h["latency"].append(platform_state["p95_latency_ms"])
            if len(h["timestamps"]) > 30:
                h["timestamps"].pop(0)
                h["rps"].pop(0)
                h["cpu"].pop(0)
                h["pods"].pop(0)
                h["latency"].pop(0)

        except Exception:
            pass
        await asyncio.sleep(1.0)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(state_background_ticker())


# -------------------------------------------------------------
# REST Endpoints
# -------------------------------------------------------------

@app.get("/api/state")
async def get_state():
    """Returns real-time platform telemetry and pod health."""
    return platform_state


class ControlRequest(BaseModel):
    action: str
    target_rps: Optional[int] = None
    pod_id: Optional[str] = None
    scenario_phase: Optional[int] = None
    playbook_id: Optional[str] = None
    pr_id: Optional[str] = None


@app.post("/api/control")
async def handle_control(req: ControlRequest, background_tasks: BackgroundTasks):
    action = req.action

    if action == "set_traffic":
        rps = req.target_rps or 100
        platform_state["desired_rps"] = rps
        if rps >= 450:
            platform_state["scenario_phase_index"] = 2
            update_narratives(
                mood="surge",
                step="Traffic Surge: 500 RPS (CPU spiking)",
                sre="⚠️ Flash Surge: 500 req/s ingress! Cluster CPU climbed to 75.0% (exceeding 60% HPA target). HorizontalPodAutoscaler evaluating replica target = 5 pods.",
                executive="⚡ Sudden high user rush detected! The platform is absorbing 500 req/sec while keeping transaction latency smooth and preventing 504 Gateway Timeouts.",
                eli5="☕ A huge tour bus just arrived at our bakery with 500 hungry people! The kitchen is buzzing, so we're automatically calling in 3 backup chefs!"
            )
        elif rps <= 40:
            platform_state["scenario_phase_index"] = 4
            update_narratives(
                mood="calm",
                step="Traffic Normalized: Cool-Down (Pods 5 -> 2)",
                sre="📉 Ingress normalized to 30 req/s. Average CPU dropped to 18.2%. HPA 45s stabilization cooldown active to avoid flapping before terminating excess pods.",
                executive="💰 Demand has normalized. System is safely scaling down idle infrastructure to maintain peak cost efficiency, saving up to 60% in cloud bills.",
                eli5="💤 Rush hour is over! We only have 30 customers left, so the extra backup helpers can take a break to save money."
            )
        else:
            platform_state["scenario_phase_index"] = 1
            update_narratives(
                mood="calm",
                step=f"Traffic set to {rps} RPS",
                sre=f"Nominal steady-state traffic: {rps} req/sec across healthy pods. CPU at ~35.0%, latency at ~14ms with 0.00% error rate.",
                executive=f"Healthy customer flow ({rps} req/sec). 100% of user transactions are succeeding with sub-15ms response times.",
                eli5=f"A nice, sunny morning! {rps} orders per minute are being served happily with zero waiting in line."
            )
        add_event("LoadBalancer", "info", f"Incoming user traffic set to {rps} req/sec")
        return {"status": "ok", "traffic_rps": rps}

    elif action == "kill_pod":
        pod_id = req.pod_id
        victim = None
        for p in platform_state["active_pods"]:
            if pod_id is None or p["id"] == pod_id:
                victim = p
                break
        
        if victim:
            victim_name = victim["name"]
            victim_callsign = victim.get("callsign", "Worker")
            victim["status"] = "Terminating (Crash)"
            victim["ready"] = False
            victim["cpu_percent"] = 0.0
            victim["mood_badge"] = "💥 Crashed"
            platform_state["scenario_phase_index"] = 5
            update_narratives(
                mood="healing",
                step=f"Chaos Injected: Killed {victim_callsign} ({victim_name})",
                sre=f"💥 Injected crash on pod {victim_callsign} ({victim_name}). Kubelet detected termination. EndpointSlice evicted endpoint; client traffic instantly redirected with 0s downtime.",
                executive=f"🛡️ Server crash detected on pod '{victim_callsign}'! User traffic was immediately redirected to surviving healthy pods. Zero user sessions were lost.",
                eli5=f"💥 Baker {victim_callsign} suddenly dropped their tray! But Baker Beacon instantly stepped in, so no customer noticed any delay!"
            )
            add_event("ChaosEngine", "error", f"CRITICAL: Sudden fatal crash injected into {victim_callsign} ({victim_name})")
            add_event("Kubelet", "warn", f"Liveness probe failed for {victim_name}: container exited with code 1")

            # Schedule automated Kubernetes self-healing
            async def heal_flow():
                await asyncio.sleep(1.5)
                add_event("ReplicaSet", "k8s", f"Detected replica deficit (Desired: {len(platform_state['active_pods'])}, Ready: {len(platform_state['active_pods'])-1})")
                await asyncio.sleep(1.0)
                
                # Remove dead pod
                platform_state["active_pods"] = [p for p in platform_state["active_pods"] if p["id"] != victim["id"]]
                
                # Spawn replacement
                new_suffix = f"{random.randint(100, 999)}"
                new_pod = {
                    "id": f"pod-api-prod-rep-{new_suffix}",
                    "name": f"production-api-7b9c4-heal{new_suffix}",
                    "callsign": f"Phoenix-{new_suffix[-2:]}",
                    "role": "Self-Healed Replacement",
                    "node": "ip-10-0-1-42.ec2.internal",
                    "status": "ContainerCreating",
                    "ready": False,
                    "cpu_percent": 15.0,
                    "memory_mb": 94,
                    "restarts": 0,
                    "uptime_sec": 1,
                    "ip": f"10.244.1.{random.randint(30, 90)}",
                    "mood_badge": "🌱 Starting Up",
                }
                platform_state["active_pods"].append(new_pod)
                add_event("Scheduler", "k8s", f"Scheduled replacement pod {new_pod['name']} to node-worker-1")
                
                await asyncio.sleep(1.5)
                new_pod["status"] = "Running"
                new_pod["ready"] = True
                new_pod["mood_badge"] = "😊 Calm & Healthy"
                add_event("Kubelet", "success", f"Readiness probe passed for {new_pod['name']} (200 OK)")
                add_event("EndpointSlice", "success", f"Pod {new_pod['name']} joined LoadBalancer pool. Zero downtime preserved.")
                update_narratives(
                    mood="success",
                    step="Self-Healing Completed: Healthy Replicas Restored",
                    sre=f"✅ Self-Healing Complete: Replacement pod {new_pod['callsign']} is passing probes and actively receiving user traffic. Zero 5xx errors recorded.",
                    executive=f"✅ Complete autonomous recovery in 1.4 seconds. No engineer had to be paged, and 100% of user traffic remained served.",
                    eli5=f"🎉 A fresh, energetic replacement baker ({new_pod['callsign']}) washed their hands and joined the counter. Perfect teamwork!"
                )

            background_tasks.add_task(heal_flow)
            return {"status": "killed", "pod": victim_name}
        return {"status": "not_found"}

    elif action == "fail_liveness":
        pod_id = req.pod_id
        target = platform_state["active_pods"][0]
        for p in platform_state["active_pods"]:
            if pod_id and p["id"] == pod_id:
                target = p
                break
        target["ready"] = False
        target["status"] = "CrashLoopBackOff"
        target["mood_badge"] = "⚠️ Unhealthy (500)"
        update_narratives(
            mood="healing",
            step=f"Liveness Failure: {target.get('callsign', 'Pod')} Deadlocked",
            sre=f"⚠️ Liveness probe failure (HTTP 500) injected on {target['name']}. Kubelet detected container deadlock and is triggering automatic container restart.",
            executive=f"⚠️ Internal process deadlock detected on '{target.get('callsign', 'Pod')}'. Self-healing supervisor is restarting container with zero customer impact.",
            eli5=f"⚠️ Baker {target.get('callsign', 'Pod')} got confused by a recipe! Supervisor is stepping in to help them start fresh."
        )
        add_event("ChaosEngine", "warn", f"Forced /healthz liveness failure (500) on {target['name']}")
        add_event("Kubelet", "error", f"3 consecutive liveness probe failures on {target['name']}. Triggering container restart.")
        req_kill = ControlRequest(action="kill_pod", pod_id=target["id"])
        return await handle_control(req_kill, background_tasks)

    elif action == "leak_memory":
        target = platform_state["active_pods"][0]
        target["memory_mb"] += 180
        target["mood_badge"] = "🧪 High RAM"
        update_narratives(
            mood="healing",
            step=f"Memory Leak Injected: {target.get('callsign', 'Pod')} RAM Climbing",
            sre=f"🧪 Synthetic memory leak: {target['name']} RAM climbed to {target['memory_mb']}MiB. Linux cgroup limit (512MiB) will safely isolate and OOMKill if breached.",
            executive=f"🧪 Memory leak simulation: System safeguards are containing memory growth to protect neighboring customer workloads from crashing.",
            eli5=f"🧪 Someone left too many mixing bowls on the counter ({target['memory_mb']}MB used)! If it gets too full, the kitchen manager cleans it up automatically."
        )
        add_event("ChaosEngine", "warn", f"Memory leak injected in {target['name']}: RSS memory jumped to {target['memory_mb']}Mi")
        if target["memory_mb"] > 450:
            add_event("Kubelet", "error", f"Pod {target['name']} exceeded memory limit (512Mi). Kernel cgroup OOMKilled triggered.")
            target["ready"] = False
            target["status"] = "OOMKilled"
            target["mood_badge"] = "💥 OOMKilled"
            req2 = ControlRequest(action="kill_pod", pod_id=target["id"])
            await handle_control(req2, background_tasks)
        return {"status": "leaked", "memory_mb": target["memory_mb"]}

    elif action == "reset":
        platform_state["desired_rps"] = 100
        platform_state["traffic_rps"] = 100
        platform_state["avg_cpu_percent"] = 35.0
        platform_state["scenario_phase_index"] = 1
        update_narratives(
            mood="calm",
            step="Nominal Baseline: 100 RPS (2 Pods)",
            sre="Platform reset to nominal baseline: 2 healthy pods running, 100 RPS traffic, CPU at ~35.0%, P95 latency ~14ms.",
            executive="Baseline state restored: High reliability, minimal cloud footprint, 0 customer errors.",
            eli5="Everything is calm and clean again! Two bakers ready to serve fresh coffee and pastries."
        )
        platform_state["active_pods"] = [
            {
                "id": "pod-api-prod-a1",
                "name": "production-api-7b9c4-w8k12",
                "callsign": "Atlas",
                "role": "Primary Ingress Worker",
                "node": "ip-10-0-1-42.ec2.internal",
                "status": "Running",
                "ready": True,
                "cpu_percent": 34.5,
                "memory_mb": 118,
                "restarts": 0,
                "uptime_sec": 1420,
                "ip": "10.244.1.18",
                "mood_badge": "😊 Calm & Healthy",
            },
            {
                "id": "pod-api-prod-b2",
                "name": "production-api-7b9c4-q9m45",
                "callsign": "Beacon",
                "role": "Core API Service",
                "node": "ip-10-0-2-88.ec2.internal",
                "status": "Running",
                "ready": True,
                "cpu_percent": 35.8,
                "memory_mb": 122,
                "restarts": 0,
                "uptime_sec": 1420,
                "ip": "10.244.2.24",
                "mood_badge": "😊 Calm & Healthy",
            },
        ]
        platform_state["is_auto_running"] = False
        add_event("System", "info", "Platform state reset to nominal baseline (2 pods, 100 RPS, CPU ~35%)")
        return {"status": "reset"}

    elif action == "run_full_demonstration":
        if platform_state["is_auto_running"]:
            return {"status": "already_running"}

        async def full_demo_workflow():
            platform_state["is_auto_running"] = True
            
            # --- PHASE 1 ---
            platform_state["scenario_phase_index"] = 1
            platform_state["desired_rps"] = 100
            update_narratives(
                mood="calm",
                step="Phase 1: Baseline Load (100 RPS, CPU ~35%, 2 Pods)",
                sre="Phase 1: Dispatching nominal baseline traffic (100 req/sec) through the AWS Load Balancer. Both pods share load cleanly with ~35% CPU.",
                executive="Phase 1: Standard operating conditions. Customer transactions flowing smoothly at 99.999% SLA with cost-optimized minimal compute.",
                eli5="Phase 1: A peaceful morning in the bakery. 100 orders per minute served easily by 2 bakers."
            )
            add_event("DemoSuite", "info", ">>> PHASE 1: Baseline traffic at 100 RPS (Target CPU ~35%, 2 pods)")
            await asyncio.sleep(4)

            # --- PHASE 2 ---
            platform_state["scenario_phase_index"] = 2
            platform_state["desired_rps"] = 500
            update_narratives(
                mood="surge",
                step="Phase 2: Traffic Surge to 500 RPS (CPU spiking to 75%)",
                sre="Phase 2: Traffic surging 5x to 500 req/sec! CPU spikes to 75%, breaching the 60% autoscaling target. Kubernetes HPA detects the surge.",
                executive="Phase 2: Massive 5x flash traffic event! System senses the demand spike before any customers experience sluggish performance.",
                eli5="Phase 2: A sudden rush of 500 customers arrives! The temperature rises to 75%, sounding the signal for backup!"
            )
            add_event("DemoSuite", "warn", ">>> PHASE 2: Flash Surge! Traffic ramping 100 -> 500 req/sec")
            await asyncio.sleep(3)
            
            # --- PHASE 3 ---
            platform_state["scenario_phase_index"] = 3
            update_narratives(
                mood="surge",
                step="Phase 3: Scaled to 5 Pods (CPU normalized to 38%)",
                sre="Phase 3: Horizontal Pod Autoscaler dynamically scales deployment from 2 to 5 pods! Traffic is rebalanced across all 5 pods, dropping per-pod CPU back down to 38%.",
                executive="Phase 3: Automatic horizontal expansion complete. All 5 pods handling traffic in parallel; response latency remains lightning fast (<16ms).",
                eli5="Phase 3: Three extra bakers sprint in! Each baker now only handles a few orders, so work feels breezy and nobody waits in line."
            )
            add_event("Prometheus", "warn", "Alert firing: HighCpuUsage (Average CPU > 70% threshold)")
            add_event("HPA", "k8s", "HPA detected CPU utilization 75% > 60% target. Calculating desired replicas = 5")
            
            callsigns = ["Chronos", "Delta", "Echo"]
            # Scale out pods: 2 -> 3 -> 4 -> 5
            for idx, i in enumerate(range(3, 6)):
                await asyncio.sleep(1.2)
                cs = callsigns[idx]
                p = {
                    "id": f"pod-api-prod-hpa-{i}",
                    "name": f"production-api-7b9c4-scale{i}",
                    "callsign": cs,
                    "role": "Autoscaled Reinforcement",
                    "node": f"ip-10-0-{(i%3)+1}-{(i*17)%100}.ec2.internal",
                    "status": "Running",
                    "ready": True,
                    "cpu_percent": 38.0,
                    "memory_mb": 115,
                    "restarts": 0,
                    "uptime_sec": 5,
                    "ip": f"10.244.2.{i*10 + 2}",
                    "mood_badge": "🏃 Sprinting in Sync",
                }
                platform_state["active_pods"].append(p)
                add_event("ReplicaSet", "success", f"Scaled pod {cs} ({p['name']}) successfully (Active Replicas: {len(platform_state['active_pods'])})")

            await asyncio.sleep(5)

            # --- PHASE 4 ---
            platform_state["scenario_phase_index"] = 4
            platform_state["desired_rps"] = 30
            update_narratives(
                mood="calm",
                step="Phase 4: Traffic Drops to 30 RPS (HPA Scale-Down to 2 Pods)",
                sre="Phase 4: The traffic spike ends. Requests drop to 30 req/sec. HPA waits for cooldown stabilization, then gracefully terminates 3 extra pods to reduce cloud infrastructure costs.",
                executive="Phase 4: Traffic normalized. The platform automatically reclaims idle compute capacity, cutting cloud costs by 60% without human intervention.",
                eli5="Phase 4: The crowd leaves! We gently say thank you to the 3 helper bakers so the business doesn't pay for idle staff."
            )
            add_event("DemoSuite", "info", ">>> PHASE 4: Traffic falling back to baseline (30 req/sec)")
            await asyncio.sleep(3)
            
            add_event("HPA", "k8s", "Cooldown stabilization satisfied (CPU < 60%). Scaling in replicas: 5 -> 2")
            while len(platform_state["active_pods"]) > 2:
                await asyncio.sleep(1.2)
                popped = platform_state["active_pods"].pop()
                add_event("ReplicaSet", "info", f"Terminated excess pod {popped.get('callsign', 'Pod')} ({popped['name']}) gracefully")

            await asyncio.sleep(4)

            # --- PHASE 5 ---
            platform_state["scenario_phase_index"] = 5
            platform_state["desired_rps"] = 80
            victim = platform_state["active_pods"][0]
            victim_cs = victim.get("callsign", "Atlas")
            update_narratives(
                mood="healing",
                step=f"Phase 5 Chaos Test: Fatal Crash Injected on {victim_cs}",
                sre=f"Phase 5 Chaos Test: Injecting fatal crash on {victim_cs} ({victim['name']})! Load balancer keeps servicing user traffic via surviving pod. Kubelet detects exit code and provisions replacement pod.",
                executive=f"Phase 5 Chaos Test: Testing catastrophic node/container crash. Redundant capacity ensures zero user transactions are dropped.",
                eli5=f"Phase 5 Chaos Test: Baker {victim_cs} accidentally slips on flour! Let's watch the supervisor instantly bring in a new baker with zero lost orders."
            )
            add_event("DemoSuite", "error", f">>> PHASE 5: Injecting fatal crash / SIGKILL on {victim_cs} ({victim['name']}) under active traffic!")
            victim["status"] = "Terminating (Dead)"
            victim["ready"] = False
            victim["mood_badge"] = "💥 Crashed"
            
            await asyncio.sleep(1.5)
            add_event("Kubelet", "warn", f"Kubelet detected container exit status 1 on {victim['name']}")
            
            await asyncio.sleep(1.2)
            platform_state["active_pods"] = [p for p in platform_state["active_pods"] if p["id"] != victim["id"]]
            
            new_heal = {
                "id": f"pod-api-prod-healed-{random.randint(100, 999)}",
                "name": f"production-api-7b9c4-heal{random.randint(100, 999)}",
                "callsign": "Phoenix-01",
                "role": "Self-Healed Replacement",
                "node": "ip-10-0-1-42.ec2.internal",
                "status": "Running",
                "ready": True,
                "cpu_percent": 34.0,
                "memory_mb": 110,
                "restarts": 0,
                "uptime_sec": 3,
                "ip": "10.244.1.99",
                "mood_badge": "😊 Calm & Healthy",
            }
            platform_state["active_pods"].append(new_heal)
            add_event("ReplicaSet", "success", f"Self-Healing: Replacement pod {new_heal['callsign']} ({new_heal['name']}) created and added to LoadBalancer!")
            add_event("DemoSuite", "success", "ALL SCENARIOS COMPLETED: 100% Zero-Downtime Verified ✔")

            update_narratives(
                mood="success",
                step="Demonstration Completed Successfully! (All tests passed)",
                sre="🎉 Verification Complete: Auto-Scaling and Self-Healing fully proved! Zero downtime observed across all traffic surges, scale-ins, and pod crashes.",
                executive="🎉 100% Uptime Validated: Zero dropped customer requests, automatic elasticity, and autonomous self-healing without late-night engineer pages.",
                eli5="🎉 Test complete! The bakery handled everything effortlessly—from massive crowds to sudden hiccups—with zero unhappy customers!"
            )
            platform_state["is_auto_running"] = False

        background_tasks.add_task(full_demo_workflow)
        return {"status": "started"}

    elif action == "trigger_playbook":
        pb_id = req.playbook_id or "crashloop"
        matched = next((p for p in platform_state["playbooks"] if p["id"] == pb_id), platform_state["playbooks"][0])
        matched["events_24h"] += 1
        matched["state"] = "TRIGGERED"
        platform_state["auto_remediations_hr"] += 1
        platform_state["resolved_incidents"] += 1
        platform_state["total_incidents"] += 1

        add_event("PlaybookEngine", "warn", f"EXEC: Triggered Playbook '{matched['name']}' ({matched['spec']})")
        add_event("eBPF", "info", f"Telemetry intercept active on cgroup: isolated offending process in {matched['avg_latency']}")
        
        async def reset_playbook_state():
            await asyncio.sleep(2.0)
            matched["state"] = "NOMINAL"
            add_event("PlaybookEngine", "success", f"RESOLVED: Playbook '{matched['name']}' completed successfully (100% SLA preserved)")

        background_tasks.add_task(reset_playbook_state)
        return {"status": "triggered", "playbook": matched["name"]}

    elif action == "merge_pr":
        pr_info = platform_state["ai_root_cause"]["pr_proposal"]
        pr_info["merged"] = True
        add_event("GitOps", "success", f"MERGED: {pr_info['pr_ref']} into main branch ({pr_info['file']} patch applied)")
        add_event("CanaryDeployer", "info", f"Building & rolling out hotfix container to 3 AZ zones (Zero-downtime rolling update)")
        return {"status": "merged", "pr": pr_info["pr_ref"]}

    elif action == "toggle_override":
        platform_state["manual_safety_override"] = not platform_state["manual_safety_override"]
        mode = "MANUAL OVERRIDE ENGAGED" if platform_state["manual_safety_override"] else "L4 FULL AUTONOMOUS ACTIVE"
        level = "warn" if platform_state["manual_safety_override"] else "info"
        add_event("SafetyInterlock", level, f"Supervisor state updated: {mode}")
        return {"status": "toggled", "manual_override": platform_state["manual_safety_override"]}

    elif action == "trigger_dry_run":
        add_event("DryRunEngine", "info", "INIT: Executing synthetic dry-run across all 5 active remediation playbooks...")
        add_event("DryRunEngine", "success", "PASS: All 9 Multi-Region Interlocks validated. Blast-radius clamp <= 5.0% verified.")
        return {"status": "dry_run_executed", "results": "All 5 playbooks nominal. Quorum active."}

    return {"status": "unknown_action"}


# -------------------------------------------------------------
# Guardian Conversational Assistant Endpoints
# -------------------------------------------------------------

GUARDIAN_FAQS = [
    {
        "id": "hpa_cooldown",
        "question": "Why does HPA scale up fast, but wait 45s before scaling down?",
        "short_answer": "To prevent rapid scaling thrashing (flapping) during momentary traffic dips.",
        "detailed_answer": "In production, traffic naturally surges and dips in small waves. If Kubernetes immediately killed pods the moment traffic dipped for 3 seconds, it would soon have to spin them up again 5 seconds later. This thrashing wastes CPU and causes latency spikes. The 45-second scale-down stabilization window ensures the lull is genuine before safely releasing cloud resources.",
        "tag": "Auto-Scaling"
    },
    {
        "id": "zero_downtime",
        "question": "How does Kubernetes guarantee zero dropped requests when a pod dies?",
        "short_answer": "Kubelet detects failure in milliseconds and EndpointSlice instantly disconnects the pod from the Load Balancer.",
        "detailed_answer": "When a container exits or fails its health check, Kubernetes does two things simultaneously: (1) It immediately removes the pod IP from the Service EndpointSlice so the Load Balancer stops routing any new connections to it, and (2) ReplicaSet instructs the scheduler to launch a fresh pod on a healthy worker node. Active connections are allowed to drain gracefully.",
        "tag": "Self-Healing"
    },
    {
        "id": "probes_diff",
        "question": "What is the difference between Liveness and Readiness probes in plain English?",
        "short_answer": "Liveness decides if the container needs to be killed; Readiness decides if it can receive customer traffic.",
        "detailed_answer": "• Liveness Probe: 'Are you deadlocked/crashed?' If this fails, Kubernetes restarts the container.\n• Readiness Probe: 'Are you ready to handle user requests right now?' If this fails (e.g. during a slow database warm-up), Kubernetes temporarily stops sending traffic to the pod without killing it.",
        "tag": "Health Probes"
    },
    {
        "id": "cost_savings",
        "question": "How much money does dynamic auto-scaling really save?",
        "short_answer": "Up to 60% compared to paying for static peak capacity 24 hours a day.",
        "detailed_answer": "Without autoscaling, you must pay for 5 large servers 24 hours a day, 7 days a week, just in case a traffic peak happens. With HPA, you run 2 baseline pods overnight (paying for minimal compute) and dynamically burst to 5 pods only during peak hours. This cuts compute expenses by over half.",
        "tag": "Cloud Economics"
    }
]


@app.get("/api/guardian/faq")
async def get_guardian_faqs():
    """Returns curated human-friendly SRE FAQs and explanations."""
    return {"faqs": GUARDIAN_FAQS}


class AskRequest(BaseModel):
    query: str


@app.post("/api/guardian/ask")
async def ask_guardian(req: AskRequest):
    """Conversational platform assistant that explains cluster state and Kubernetes concepts."""
    q = req.query.lower().strip()
    
    # Check if matches any FAQ
    for faq in GUARDIAN_FAQS:
        if faq["id"] in q or any(word in q for word in faq["question"].lower().split() if len(word) > 4):
            return {
                "answer": faq["detailed_answer"],
                "topic": faq["tag"],
                "cluster_context": f"Current Pod Count: {len(platform_state['active_pods'])} | Traffic: {platform_state['traffic_rps']} RPS"
            }
    
    # Context-aware real-time dynamic response
    num_pods = len([p for p in platform_state["active_pods"] if p["ready"]])
    rps = platform_state["traffic_rps"]
    cpu = platform_state["avg_cpu_percent"]
    
    return {
        "answer": f"Right now, our platform is running {num_pods} healthy pods serving {rps} requests per second with an average CPU utilization of {cpu}%. All health probes are passing cleanly, and our automated recovery webhook is standing by in case of anomalies!",
        "topic": "Live System State",
        "cluster_context": f"Status: {platform_state['cluster_status']} | SLA: 99.999%"
    }


@app.get("/api/export-logs")
async def export_logs():
    """Exports recorded events as JSON audit trail."""
    return {
        "export_time": datetime.datetime.now().isoformat(),
        "cluster": "EKS production-platform-cluster",
        "events_count": len(platform_state["events"]),
        "events": platform_state["events"],
    }


# Mount static directory for frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root_index():
    return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    print("[*] Starting Mission Control Dashboard on http://localhost:5050 ...")
    uvicorn.run(app, host="0.0.0.0", port=5050)
