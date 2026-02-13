# Kubernetes Deployment

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- nginx-ingress controller installed
- Container images pushed to ghcr.io (or update image references)

## Quick Start

```bash
# 1. Create namespace and base resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml

# 2. Deploy backend and frontend
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml

# 3. Configure ingress
kubectl apply -f k8s/ingress.yaml
```

Or apply everything at once:

```bash
kubectl apply -f k8s/
```

## Configuration

### Secrets

Update `secret.yaml` with real base64-encoded values before deploying:

```bash
echo -n 'your-jwt-secret' | base64
echo -n 'your-db-password' | base64
```

For production, use an external secret manager (e.g., Sealed Secrets, Vault, AWS Secrets Manager).

### Ingress

Update the host in `ingress.yaml` from `10mwt.example.com` to your actual domain.

For TLS, create a certificate secret or use cert-manager:

```bash
kubectl create secret tls 10mwt-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n 10mwt
```

### Container Images

Update the image references in the deployment files to match your registry:

- `backend-deployment.yaml`: `ghcr.io/10mwt/backend:latest`
- `frontend-deployment.yaml`: `ghcr.io/10mwt/frontend:latest`

## Verify Deployment

```bash
kubectl get all -n 10mwt
kubectl get ingress -n 10mwt
```

## Storage

- **uploads-pvc** (5Gi): Stores uploaded video files
- **database-pvc** (1Gi): Stores the SQLite database file

Both PVCs use `ReadWriteOnce` access mode. For multi-replica write access, consider migrating to PostgreSQL or using a shared filesystem (e.g., NFS, EFS).
