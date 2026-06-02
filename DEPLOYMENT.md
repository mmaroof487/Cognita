# Cognita Deployment Guide

This guide details how to deploy the Cognita backend to a production environment (like a VPS or bare metal server). 
The deployment uses Docker Compose, Nginx (as a reverse proxy), and GitHub Actions for continuous deployment.

## Prerequisites

- A Virtual Private Server (VPS) running Ubuntu 22.04 or 24.04 (e.g., DigitalOcean, AWS EC2, Linode).
- A domain name pointing to your VPS IP address (e.g., `api.cognita.com`).
- A GitHub repository with this codebase to utilize GitHub Actions.

---

## 1. Initial Server Provisioning

1. SSH into your VPS as `root`.
2. Upload the setup script:
   ```bash
   scp scripts/setup_vps.sh root@<YOUR_VPS_IP>:/root/
   ```
3. Run the setup script to install Docker, configure UFW (Firewall), and create the directory structure:
   ```bash
   bash /root/setup_vps.sh
   ```

## 2. Server Configuration

1. Transfer your configuration files to the server's `/opt/cognita` directory.
   ```bash
   scp docker-compose.prod.yml root@<YOUR_VPS_IP>:/opt/cognita/
   scp -r infra/nginx root@<YOUR_VPS_IP>:/opt/cognita/infra/
   scp .env.production.example root@<YOUR_VPS_IP>:/opt/cognita/.env
   ```

2. SSH into your VPS and edit the `.env` file in `/opt/cognita/.env`. 
   ```bash
   cd /opt/cognita
   nano .env
   ```
   Fill in all the required secrets, especially the database passwords, `JWT_SECRET`, and API keys.

## 3. GitHub Actions CI/CD Setup

To enable automated deployment via GitHub Actions, add the following Repository Secrets to your GitHub repository:

- `VPS_HOST`: The IP address of your VPS.
- `VPS_USERNAME`: The SSH username (e.g., `root` or `ubuntu`).
- `VPS_SSH_KEY`: The private SSH key allowing access to the VPS.

When you push to the `main` branch, the `CI` workflow will run tests and build a Docker image. If successful, the `Deploy to Production` workflow will automatically SSH into your server, pull the latest image, and restart the containers.

## 4. First Time Deployment

If you want to manually trigger the first deployment instead of waiting for GitHub Actions:

1. Build and push the Docker image locally (or let GitHub Actions do it):
   ```bash
   docker build -t ghcr.io/<YOUR_GITHUB_USERNAME>/cognita/api:latest ./backend
   docker push ghcr.io/<YOUR_GITHUB_USERNAME>/cognita/api:latest
   ```
2. On your VPS, run the containers:
   ```bash
   cd /opt/cognita
   docker compose -f docker-compose.prod.yml pull
   docker compose -f docker-compose.prod.yml up -d
   ```
3. Run the database migrations to set up your tables:
   ```bash
   docker compose -f docker-compose.prod.yml exec api alembic -c alembic/alembic.ini upgrade head
   ```

## 5. Seeding Demo Data

To create an initial tenant and admin user, run the seed script:
```bash
docker compose -f docker-compose.prod.yml exec api python scripts/seed_demo.py
```
**Important:** Save the generated credentials outputted by this script immediately!

## 6. SSL Configuration (Optional but Recommended)

By default, the provided `nginx.conf` listens on port 80. To secure your API with HTTPS:

1. Install Certbot on your VPS:
   ```bash
   apt-get install -y certbot python3-certbot-nginx
   ```
2. Run Certbot to generate and install SSL certificates:
   ```bash
   certbot --nginx -d api.yourdomain.com
   ```
Certbot will automatically update your Nginx configuration to support HTTPS.
