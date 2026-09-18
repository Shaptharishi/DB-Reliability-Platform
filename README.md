# DB Reliability & Incident Response Platform — Kubernetes (k3s) Deployment

This branch (`version-k3s`) is a parallel deployment of the same monitoring platform found on the `versions` branch, running on **Kubernetes (k3s)** instead of Docker Compose. It uses the identical underlying application code and the same AWS-provisioned RDS/ElastiCache databases — only the container orchestration layer differs.

## Why This Branch Exists

The `versions` branch proves the platform works with Docker Compose. This branch demonstrates the same platform running under real container orchestration — automatic restarts, declarative desired-state management, and Kubernetes-native networking — to show genuine, hands-on Kubernetes competency rather than Docker Compose alone.

## What It Does

A Python collector checks PostgreSQL, MySQL, and Redis every 30 seconds, running automated diagnostic checks (connection usage, replication lag, idle transactions, table bloat, slow queries) through a rule engine that produces a specific root-cause diagnosis rather than a generic alert. Metrics and alerts are stored in ClickHouse, visualized in Grafana, and pushed to Slack in real time.

## Architecture

```
                    ┌─────────────────────┐
                    │   AWS RDS/ElastiCache │
                    │  PostgreSQL / MySQL /  │
                    │       Redis             │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Collector Pod       │  (Python, runs every 30s)
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   ClickHouse Pod      │  (metrics + alerts store)
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Grafana Pod          │  (dashboards, NodePort 30000)
                    └────────────────────────┘
```

All three components run as Kubernetes Deployments with Services, on a single-node k3s cluster provisioned via Terraform on an AWS EC2 instance.

## Infrastructure

- **Terraform** provisions the EC2 instance, RDS PostgreSQL, RDS MySQL, ElastiCache (Valkey), and all VPC security groups — identical to the `versions` branch's infrastructure code.
- **A self-bootstrapping `user_data.sh.tpl` script**, executed automatically on the EC2 instance's first boot, installs Docker (used only to build the collector image), installs k3s, builds and imports the collector image into k3s's containerd store, generates a Kubernetes Secret containing real database credentials, and applies all five Kubernetes manifests.
- **Kubernetes manifests** (in `k8s/`): `clickhouse-deployment.yaml`, `clickhouse-service.yaml`, `grafana-deployment.yaml`, `grafana-service.yaml`, `collector-deployment.yaml`, and `collector-secret.example.yaml` (a placeholder committed to Git; the real, populated `collector-secret.yaml` is generated at boot and gitignored).

## Real Production Issues Diagnosed on This Branch

- **DiskPressure eviction** — k3s's own control-plane overhead, combined with an 8GB root disk, caused repeated Pod evictions. Diagnosed via `kubectl describe pod`, confirmed by the Events section explicitly naming `DiskPressure`. Fixed by increasing the EBS volume to 20GB.
- **`kubectl` permission denied** — the `ubuntu` user lacked correct ownership of `~/.kube/config` after k3s installation. Fixed by explicitly setting `KUBECONFIG` and correcting file ownership.
- **A genuine startup race condition** — the collector Pod occasionally starts before ClickHouse is ready to accept connections, exhausting its retry logic and crashing. Kubernetes' Deployment controller automatically restarts it, and it connects successfully on the next attempt — a real, live demonstration of self-healing, though a readiness probe or init container would be the more correct long-term fix (not yet implemented on this branch).
- **Git divergent branches on the EC2 instance** — caused by root-owned repository files after running commands as root during initial setup. Fixed with `git config --global --add safe.directory` and correcting ownership.

## Running This Branch

```bash
git checkout version-k3s
cd terraform-dbrp
terraform init
terraform apply
```

Terraform will provision the infrastructure and the EC2 instance's boot script will automatically install k3s and deploy the application. Full bootstrap takes approximately 8–10 minutes.

Once complete, connect via SSH and verify:

```bash
kubectl get pods
kubectl get nodes
```

Grafana is reachable at `http://<ec2-public-ip>:30000` (NodePort, not the default port 3000).

## Known Limitations

- Storage is backed by `emptyDir`, not a `PersistentVolumeClaim` — data does not survive a Pod restart. This was a deliberate simplification for a personal project; a production deployment would use persistent storage.
- Terraform state is local and shared with the `versions` branch. Applying either branch replaces whatever is currently deployed — only one version is genuinely live at a time. Proper isolation would require Terraform workspaces or separate state backends.
- No Ingress controller; Grafana is exposed directly via NodePort for simplicity.
