#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/port-forward.sh <K8S_NAMESPACE>
NAMESPACE="${1:-reddit-sentiment}"

echo "🔀 Port‑forwarding services in namespace ${NAMESPACE}…"
echo "  • Postgres → localhost:5432"
kubectl -n "${NAMESPACE}" port-forward statefulset/postgres 5432:5432 &

echo "  • Airflow UI → localhost:8080"
kubectl -n "${NAMESPACE}" port-forward deployment/airflow-webserver 8080:8080 &

echo "  • Backend API → localhost:5000"
kubectl -n "${NAMESPACE}" port-forward deployment/backend 5001:5000 &

echo "  • Streamlit → localhost:8501"
kubectl -n "${NAMESPACE}" port-forward deployment/frontend 8501:8501 &

echo
echo "Press Ctrl+C to stop all port‑forwards."
wait
