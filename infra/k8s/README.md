# Kubernetes manifests

Apply in order (or `kubectl apply -f infra/k8s/`):

```bash
kubectl apply -f infra/k8s/00-namespace.yaml
kubectl apply -f infra/k8s/01-config.yaml      # EDIT secrets first
kubectl apply -f infra/k8s/02-postgres.yaml
kubectl apply -f infra/k8s/03-migrate-job.yaml # runs alembic upgrade head
kubectl apply -f infra/k8s/04-api.yaml
kubectl apply -f infra/k8s/05-web.yaml
kubectl apply -f infra/k8s/06-ingress.yaml
```

Notes:
- Replace every `REPLACE_*` value in `01-config.yaml` using a real secret store
  (External Secrets Operator / Sealed Secrets). Never commit real credentials.
- In production prefer **Azure Database for PostgreSQL Flexible Server** (with the
  `vector` extension enabled) over the in-cluster StatefulSet; point
  `DATABASE_URL` at it and delete `02-postgres.yaml`.
- Storage uses **SharePoint** (Microsoft Graph, app-only token); the in-cluster
  pods need network egress to `graph.microsoft.com` and `login.microsoftonline.com`,
  and the Entra app must hold the **application** permission `Sites.ReadWrite.All`
  (admin-consented).
- The migrate Job should run as a Helm/Argo pre-upgrade hook so schema changes
  land before new API pods start.
