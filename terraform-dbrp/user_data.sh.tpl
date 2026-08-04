#!/bin/bash
set -e

# Install Docker (still needed to BUILD the collector image)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install k3s
curl -sfL https://get.k3s.io | sh -

# Install git
apt-get update
apt-get install -y git

# Clone the project (k3s-deployment branch)
cd /home/ubuntu
git clone -b version-k3s https://github.com/Shaptharishi/DB-Reliability-Platform.git
cd DB-Reliability-Platform

# Set up kubectl access
mkdir -p /home/ubuntu/.kube
k3s kubectl config view --raw > /home/ubuntu/.kube/config
chmod 600 /home/ubuntu/.kube/config
chown -R ubuntu:ubuntu /home/ubuntu/.kube
ln -sf /usr/local/bin/k3s /usr/local/bin/kubectl

# Build the collector image and import into k3s
docker build -t db-reliability-platform-collector:latest .
docker save db-reliability-platform-collector:latest -o /tmp/collector-image.tar
k3s ctr images import /tmp/collector-image.tar
rm /tmp/collector-image.tar

# Create the secret (real values injected by Terraform)
cat > /home/ubuntu/DB-Reliability-Platform/k8s/collector-secret.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: collector-secrets
type: Opaque
stringData:
  POSTGRES_PASSWORD: "${postgres_password}"
  MYSQL_PASSWORD: "${mysql_password}"
  SLACK_WEBHOOK_URL: "${slack_webhook_url}"
EOF

# Apply all manifests
cd /home/ubuntu/DB-Reliability-Platform/k8s
kubectl apply -f collector-secret.yaml
kubectl apply -f clickhouse-deployment.yaml
kubectl apply -f clickhouse-service.yaml
kubectl apply -f grafana-deployment.yaml
kubectl apply -f grafana-service.yaml
kubectl apply -f collector-deployment.yaml

chown -R ubuntu:ubuntu /home/ubuntu/DB-Reliability-Platform

echo "Bootstrap complete."