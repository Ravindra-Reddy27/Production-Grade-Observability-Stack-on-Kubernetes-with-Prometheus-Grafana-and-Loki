# Production-Grade Observability Stack on Kubernetes

A production-ready observability architecture deployed on Kubernetes using **Prometheus**, **Grafana**, and **Loki**. This repository features a containerized Flask application instrumented with custom Prometheus metrics and structured JSON logging, complete with automated log collection via Promtail, custom latency alert rules, and persistent storage.

---

# Directory Structure

```text
observability-project/
├── alerts/
│   └── flask-alert-rule.yaml      # Custom PrometheusRule manifest (HighLatencyAlert)
├── app/
│   ├── app.py                     # Flask application code (Metrics & JSON Logs)
│   ├── docker-compose.yml         # Local development configuration
│   ├── Dockerfile                 # Container build instructions
│   └── requirements.txt           # Python dependencies
├── kubernetes/
│   ├── alertmanager/              # Alertmanager configurations
│   ├── grafana/
│   │   ├── dashboards/            # Pre-configured Grafana dashboards
│   │   └── loki-datasource.yaml   # Loki data source configuration
│   ├── loki/
│   │   └── values.yaml            # Loki Helm chart values (PVC & Limits)
│   ├── prometheus/
│   │   └── values.yaml            # Prometheus Helm chart values (PVC & Rules)
│   └── sample-app/
│       ├── deployment.yaml        # Flask Deployment (Probes & Resource Limits)
│       ├── service.yaml           # Flask Service definition
│       └── servicemonitor.yaml    # Prometheus ServiceMonitor CRD
└── README.md                      # Project Runbook
```

---

# Prerequisites

Ensure the following tools are installed locally before proceeding:

- Docker Desktop
- Kind (Kubernetes in Docker)
- kubectl
- Helm

---
## Step 0: Clone the Project

Clone the project:

```bash
git clone https://github.com/Ravindra-Reddy27/Production-Grade-Observability-Stack-on-Kubernetes-with-Prometheus-Grafana-and-Loki.git

cd Production-Grade-Observability-Stack-on-Kubernetes-with-Prometheus-Grafana-and-Loki
```

## Step 1: Local Development & Testing (Docker Compose)

Before deploying to Kubernetes, test the Flask application locally.

Navigate to the `app` directory and start the application:

```bash
cd app
docker-compose up --build -d
```

Verify the application:

```bash
curl "http://localhost:5000/hello"
curl "http://localhost:5000/metrics"
```

Stop the local environment:

```bash
docker-compose down
cd ..
```

---

## Step 2: Create the Kind Kubernetes Cluster

Create the Kind cluster:

```bash
kind create cluster --name observability-cluster
```

Verify the cluster:

```bash
kubectl cluster-info --context kind-observability-cluster
```

Create namespaces:

```bash
kubectl create namespace observability
kubectl create namespace application
```

---

## Step 3: Build and Load the Application Image

Build the Docker image:

```bash
docker build -t flask-app:v1 ./app
```

Load the image into the Kind cluster:

```bash
kind load docker-image flask-app:v1 --name observability-cluster
```

---

## Step 4: Deploy the Observability Stack

## Add Helm Repositories

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

## Install Prometheus & Grafana

```bash
helm install prometheus prometheus-community/kube-prometheus-stack `
  --namespace observability `
  --values kubernetes/prometheus/values.yaml
```

wait 4-5 minutes for Pods running.

Verify the deployment and Pod status:
```bash
kubectl get pods -n observability
```

## Install Loki & Promtail

```bash
helm install loki grafana/loki-stack `
  --namespace observability `
  --values kubernetes/loki/values.yaml
```
wait 2-3 minutes for Pods running.

Verify the deployment:
```bash
kubectl get pods -n observability
```



---

## Step 5: Deploy the Application

Deploy the Flask application:

Apply the app and service to the application namespace

```bash
kubectl apply -f kubernetes/sample-app/deployment.yaml -n application
kubectl apply -f kubernetes/sample-app/service.yaml -n application
```
Apply the ServiceMonitor to the observability namespace
```bash
kubectl apply -f kubernetes/sample-app/servicemonitor.yaml -n observability
```

Deploy custom Prometheus alert rules:

```bash
kubectl apply -f alerts/ -n observability
```

Verify the application:

```bash
kubectl get pods -n application
```

---

## Step 6: Access Grafana

---

## Configure the Loki Datasource

Remove the Helm-generated datasource and apply the custom datasource configuration.

## Step 1: Delete the Helm-Generated Loki ConfigMap

Remove the default ConfigMap created by the Loki Helm chart:

```powershell
kubectl delete configmap loki-loki-stack -n observability
```


## Step 2: Apply the Custom Loki Datasource

Apply the custom datasource configuration so Grafana automatically imports it through the sidecar:

```powershell
kubectl apply -f kubernetes/grafana/loki-datasource.yaml -n observability
```


## Step 3: Verify the Datasources

Confirm that only the custom Loki datasource and the Prometheus datasource are available:

```powershell
kubectl get configmap -n observability -l grafana_datasource="1"
```

### Expected Output

```text
NAME                                            DATA   AGE
grafana-loki-datasource                         1      ...
prometheus-kube-prometheus-grafana-datasource   1      ...
```

After completing these steps, Grafana will use your custom **Loki** datasource configuration alongside the automatically created **Prometheus** datasource.

Port-forward the Grafana service:

```bash
kubectl port-forward svc/prometheus-grafana 3000:80 -n observability
```

## Retrieve the Admin Password

### Linux/macOS/Git Bash

```bash
kubectl get secret --namespace observability prometheus-grafana \
-o jsonpath="{.data.admin-password}" | base64 --decode
echo
```

### Windows PowerShell

```powershell
kubectl get secret --namespace observability prometheus-grafana `
-o jsonpath="{.data.admin-password}"
```

Copy the Base64 output and decode it using any Base64 decoder.

### Login Credentials

| Field | Value |
|-------|-------|
| URL | http://localhost:3000 |
| Username | admin |
| Password | Decoded password |

---

## Step 7: Generate Metrics & Trigger Alerts

Port-forward the Flask application:

```bash
kubectl port-forward svc/flask-app-service 5000:5000 -n application
```

## Normal Request

```bash
curl "http://localhost:5000/hello"
```

## Trigger High Latency Alert

Introduce a delay longer than the configured threshold:

```bash
curl "http://localhost:5000/hello?delay=3.0"
```

---

## Verify Alert Status

Port-forward Prometheus:

```bash
kubectl port-forward svc/prometheus-kube-prometheus-prometheus `
9090:9090 -n observability

```

Open:

```
http://localhost:9090/alerts
```

The **HighLatencyAlert** will move through the following states:

```text
Inactive
    ↓
Pending
    ↓
Firing
```

---

# Step 8: Cleanup

Delete the Kind cluster:

```bash
kind delete cluster --name observability-cluster
```

---

# Tech Stack

| Component | Purpose |
|-----------|---------|
| Kubernetes (Kind) | Local Kubernetes Cluster |
| Flask | Sample Application |
| Prometheus | Metrics Collection |
| Grafana | Visualization |
| Loki | Log Aggregation |
| Promtail | Log Collection |
| Alertmanager | Alert Routing |
| Helm | Kubernetes Package Manager |
| Docker | Containerization |

---

# Features

- Production-ready Kubernetes deployment
- Prometheus metrics collection
- Structured JSON logging
- Loki centralized log aggregation
- Promtail automatic log shipping
- Grafana dashboards
- Custom ServiceMonitor
- Custom Prometheus alert rules
- High latency alert simulation
- Persistent storage for Prometheus and Loki
- Resource limits and readiness/liveness probes
- Docker Compose support for local development