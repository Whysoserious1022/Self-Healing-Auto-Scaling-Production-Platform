# Automated Deployment Script for Production Kubernetes Platform (PowerShell)
param (
    [string]$Action = "deploy" # deploy | delete | test
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Self-Healing & Auto-Scaling Production Platform Deployer" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if ($Action -eq "deploy") {
    Write-Host "[0/5] Building local Docker image 'production-api:latest'..." -ForegroundColor Yellow
    try {
        docker build -t production-api:latest -f app/Dockerfile app
    } catch {
        Write-Host "Warning: Docker build skipped or failed. Continuing with existing images..." -ForegroundColor DarkYellow
    }

    Write-Host "[1/5] Creating Namespace..." -ForegroundColor Yellow
    kubectl apply -f k8s/00-namespace.yaml

    Write-Host "[2/5] Applying ConfigMap..." -ForegroundColor Yellow
    kubectl apply -f k8s/01-configmap.yaml

    Write-Host "[3/5] Applying Metrics Server (Required for HPA)..." -ForegroundColor Yellow
    kubectl apply -f k8s/06-metrics-server.yaml

    Write-Host "[4/5] Deploying API Deployment & PodDisruptionBudget..." -ForegroundColor Yellow
    kubectl apply -f k8s/02-deployment.yaml
    kubectl apply -f k8s/05-pdb.yaml

    Write-Host "[5/5] Exposing Service & Configuring HPA (Min: 2, Max: 5)..." -ForegroundColor Yellow
    kubectl apply -f k8s/03-service.yaml
    kubectl apply -f k8s/04-hpa.yaml

    Write-Host "`n[+] Deployment Completed Successfully!" -ForegroundColor Green
    Write-Host "Check status with: kubectl get pods,hpa,svc -n production-platform" -ForegroundColor Green
}
elseif ($Action -eq "delete") {
    Write-Host "Tearing down Kubernetes resources..." -ForegroundColor Yellow
    kubectl delete namespace production-platform --ignore-not-found=true
    Write-Host "[+] Teardown complete." -ForegroundColor Green
}
elseif ($Action -eq "test") {
    Write-Host "Starting automated verification test suite..." -ForegroundColor Cyan
    python tests/run_full_demonstration.py
}
