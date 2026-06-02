#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Cognita VPS Provisioning Script
# Run this on a fresh Ubuntu 22.04 LTS or 24.04 LTS server as root.
# Usage: bash setup_vps.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "========================================="
echo " Starting Cognita VPS Provisioning       "
echo "========================================="

# 1. Update and upgrade system packages
echo ">>> Updating system packages..."
apt-get update && apt-get upgrade -y

# 2. Install essential tools
echo ">>> Installing essential tools..."
apt-get install -y curl wget git ufw certbot

# 3. Install Docker and Docker Compose plugin
echo ">>> Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "Docker already installed."
fi

# 4. Setup UFW Firewall
echo ">>> Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# 5. Create deployment directory
echo ">>> Setting up deployment directory..."
mkdir -p /opt/cognita
mkdir -p /opt/cognita/infra/nginx/certs
chown -R $USER:$USER /opt/cognita

echo "========================================="
echo " Provisioning Complete!                  "
echo " Next Steps:                             "
echo " 1. Copy docker-compose.prod.yml to /opt/cognita/"
echo " 2. Copy infra/nginx to /opt/cognita/infra/nginx"
echo " 3. Create .env file in /opt/cognita/"
echo " 4. Run: docker compose -f docker-compose.prod.yml up -d"
echo "========================================="
