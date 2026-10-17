#!/usr/bin/env bash
# Automated Deployment Script for Production Kubernetes Platform (Bash / Linux)

set -euo pipefail

ACTION="${1:-deploy}"

echo -e "\033[96m============================================================\033[0m"
echo -e "\033[96m  Self-Healing & Auto-Scaling Production Platform Deployer  \033[0m"
echo -e "\033[96m============================================================\033[0m"

if [ "$ACTION" == "deploy" ]; then
    echo -e "\033[93m[1/5] Creating Namespace...\033[0m"
    kubectl apply -f k8s/00-namespace.yaml

    echo -e "\033[93m[2/5] Applying ConfigMap...\033[0m"
    kubectl apply -f k8s/01-configmap.yaml

    echo -e "\033[93m[3/5] Applying Metrics Server (Required for HPA)...\033[0m"
    kubectl apply -f k8s/06-metrics-server.yaml

    echo -e "\033[93m[4/5] Deploying API Deployment & PodDisruptionBudget...\033[0m"
    kubectl apply -f k8s/02-deployment.yaml
    kubectl apply -f k8s/05-pdb.yaml

    echo -e "\033[93m[5/5] Exposing Service & Configuring HPA (Min: 2, Max: 5)...\033[0m"
    kubectl apply -f k8s/03-service.yaml
    kubectl apply -f k8s/04-hpa.yaml

    echo -e "\n\033[92m[+] Deployment Completed Successfully!\033[0m"
    echo -e "\033[92mCheck status with: kubectl get pods,hpa,svc -n production-platform\033[0m"

elif [ "$ACTION" == "delete" ]; then
    echo -e "\033[93mTearing down Kubernetes resources...\033[0m"
    kubectl delete namespace production-platform --ignore-not-found=true
    echo -e "\033[92m[+] Teardown complete.\033[0m"

elif [ "$ACTION" == "test" ]; then
    echo -e "\033[96mStarting automated verification test suite...\033[0m"
    python tests/run_full_demonstration.py
fi
