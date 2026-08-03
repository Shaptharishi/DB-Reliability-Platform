#!/bin/bash
set -e

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install git
apt-get update
apt-get install -y git

# Clone the project
cd /home/ubuntu
git clone -b versions https://github.com/Shaptharishi/DB-Reliability-Platform.git
cd DB-Reliability-Platform

# Generate .env with real values from Terraform
cat > .env << EOF
POSTGRES_HOST=${postgres_host}
POSTGRES_PASSWORD=${postgres_password}
MYSQL_HOST=${mysql_host}
MYSQL_PASSWORD=${mysql_password}
REDIS_HOST=${redis_host}
SLACK_WEBHOOK_URL=${slack_webhook_url}
EOF

chown -R ubuntu:ubuntu /home/ubuntu/DB-Reliability-Platform

# Start everything
docker compose up -d --build