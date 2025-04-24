#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/deploy.sh <GCP_PROJECT_ID> <K8S_NAMESPACE>
PROJECT_ID="${1:-my-gcp-project}"
NAMESPACE="${2:-reddit-sentiment}"

echo "🔐 Authenticating Docker with GCR…"
gcloud auth configure-docker --quiet

echo "📦 Building & pushing images to gcr.io/${PROJECT_ID}…"
for SERVICE in backend airflow frontend; do
  IMAGE="gcr.io/${PROJECT_ID}/${SERVICE}:latest"
  echo "  • ${SERVICE} → ${IMAGE}"
  docker build -t "${IMAGE}" "./${SERVICE}"
  docker push "${IMAGE}"
done

echo "🚀 Applying Kubernetes manifests to namespace ${NAMESPACE}…"
kubectl apply -f infra/k8s/namespace.yaml
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "${NAMESPACE}" apply -f infra/k8s/secrets.yaml
kubectl -n "${NAMESPACE}" apply -f infra/k8s/configmap.yaml
kubectl -n "${NAMESPACE}" apply -f infra/k8s/postgres-statefulset.yaml
kubectl -n "${NAMESPACE}" apply -f infra/k8s/airflow-deployment.yaml
kubectl -n "${NAMESPACE}" apply -f infra/k8s/airflow-service.yaml
kubectl -n "${NAMESPACE}" apply -f infra/k8s/backend-deployment.yaml
kubectl -n "${NAMESPACE}" apply -f infra/k8s/backend-service.yaml
kubectl -n "${NAMESPACE}" apply -f infra/k8s/frontend-deployment.yaml
kubectl -n "${NAMESPACE}" apply -f infra/k8s/frontend-service.yaml
kubectl -n "${NAMESPACE}" apply -f infra/k8s/ingress.yaml

echo "✅ Deployment complete!"
