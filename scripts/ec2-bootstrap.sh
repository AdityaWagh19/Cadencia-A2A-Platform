#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# Cadencia — EC2 Bootstrap Script (run once on a fresh Ubuntu 24.04 instance)
#
# This script:
#   1. Installs Docker + Docker Compose plugin
#   2. Clones the Cadencia repo
#   3. Prompts for GHCR PAT and logs into GHCR
#   4. Pulls pre-built images
#   5. Runs database migrations
#   6. Starts all services
#
# Prerequisites:
#   - Ubuntu 24.04 LTS EC2 instance (t3.medium recommended)
#   - Security group: ports 22, 80, 443 open
#   - .env file prepared (see deployment.md Phase 3)
#
# Usage:
#   ssh -i your-key.pem ubuntu@<EC2-IP>
#   curl -sSL <raw-url-to-this-script> | bash
#   # OR
#   bash scripts/ec2-bootstrap.sh
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

REPO_URL="https://github.com/AdityaWagh19/Cadencia-A2A-Platform.git"
INSTALL_DIR="/home/ubuntu/cadencia"
COMPOSE_FILE="docker-compose.cloud.yml"

echo "══════════════════════════════════════════════"
echo "  Cadencia — EC2 Bootstrap"
echo "══════════════════════════════════════════════"

# ── Step 1: Install Docker ────────────────────────────────────────────────
echo ""
echo "[1/6] Installing Docker..."
if ! command -v docker &>/dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y docker.io docker-compose-plugin git curl
    sudo usermod -aG docker ubuntu
    echo "Docker installed. You may need to re-login for group changes."
else
    echo "Docker already installed, skipping."
fi

# ── Step 2: Clone repository ─────────────────────────────────────────────
echo ""
echo "[2/6] Cloning repository..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Repo already exists at $INSTALL_DIR, pulling latest..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── Step 3: Check .env file ──────────────────────────────────────────────
echo ""
echo "[3/6] Checking .env file..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "ERROR: .env file not found at $INSTALL_DIR/.env"
    echo ""
    echo "Create it first (see deployment.md Phase 3):"
    echo "  nano $INSTALL_DIR/.env"
    echo ""
    echo "Then re-run this script."
    exit 1
fi
echo ".env file found."

# ── Step 4: Login to GHCR ────────────────────────────────────────────────
echo ""
echo "[4/6] Authenticating with GitHub Container Registry..."
echo "Enter your GitHub Personal Access Token (needs read:packages scope):"
read -rs GHCR_PAT
echo "$GHCR_PAT" | docker login ghcr.io -u AdityaWagh19 --password-stdin
echo "GHCR login successful."

# ── Step 5: Pull images and run migrations ────────────────────────────────
echo ""
echo "[5/6] Pulling images and running migrations..."
cd "$INSTALL_DIR"
docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head
echo "Migrations complete."

# ── Step 6: Start services ───────────────────────────────────────────────
echo ""
echo "[6/6] Starting services..."
docker compose -f "$COMPOSE_FILE" up -d
echo ""
echo "══════════════════════════════════════════════"
echo "  Cadencia is running!"
echo ""
echo "  Frontend:  http://$(curl -s ifconfig.me)"
echo "  Health:    http://$(curl -s ifconfig.me)/v1/../health"
echo ""
echo "  Logs:      docker compose -f $COMPOSE_FILE logs -f"
echo "  Stop:      docker compose -f $COMPOSE_FILE down"
echo "══════════════════════════════════════════════"
