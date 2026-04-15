# 🚀 Cadencia — GitHub CI/CD + AWS Deployment Plan

## Overview

**Architecture**: Single EC2 instance running Docker Compose (simplest path for a demo)  
**Database**: Supabase Cloud (already configured, no RDS needed)  
**Images**: Built by GitHub Actions → pushed to GitHub Container Registry (GHCR)  
**EC2 pulls images on every release tag** and restarts containers

```
Developer → git push tag → GitHub Actions CI → build images → push to GHCR
                                                                      ↓
                                                              EC2 pulls & restarts
                                                              (docker compose up)
```

---

## Phase 1 — AWS Setup (One-Time)

### Step 1.1 — Launch EC2 Instance

1. Go to **AWS Console → EC2 → Launch Instance**
2. Settings:
   - **Name**: `cadencia-demo`
   - **AMI**: Ubuntu 24.04 LTS (free tier eligible)
   - **Instance type**: `t3.medium` (2 vCPU, 4 GB RAM) — minimum for the full stack
   - **Region**: `ap-south-1` (Mumbai) — matches your Supabase region
   - **Key pair**: Create a new one → download `.pem` file → keep it safe
   - **Security group** (inbound rules):
     | Port | Protocol | Source | Purpose |
     |------|----------|--------|---------|
     | 22 | TCP | Your IP only | SSH |
     | 80 | TCP | 0.0.0.0/0 | HTTP (frontend + API via Caddy) |
     | 443 | TCP | 0.0.0.0/0 | HTTPS (if you add domain later) |
     | 3000 | TCP | 0.0.0.0/0 | Frontend direct access (optional) |
     | 8000 | TCP | 0.0.0.0/0 | Backend direct access (optional, remove in prod) |
   - **Storage**: 20 GB (gp3) — enough for Docker images

3. After launch, note the **Public IPv4 address** and **Public IPv4 DNS** (looks like `ec2-13-235-67-89.ap-south-1.compute.amazonaws.com`)

### Step 1.2 — Assign Elastic IP (Stable Address)

1. **EC2 → Elastic IPs → Allocate Elastic IP**
2. **Associate** it with your `cadencia-demo` instance
3. Note this IP — it won't change even after reboots

### Step 1.3 — Install Docker on EC2

SSH into the instance:
```bash
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
```

Run:
```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin git

# Allow ubuntu user to run Docker without sudo
sudo usermod -aG docker ubuntu
newgrp docker

# Verify
docker --version
docker compose version
```

### Step 1.4 — Create AWS IAM Role (Optional but Recommended)

If you use S3 for storage, attach an IAM role to the EC2 instead of hardcoding keys:
1. **IAM → Roles → Create Role → EC2**
2. Attach: `AmazonS3FullAccess` (or a scoped policy for your bucket)
3. **EC2 → Actions → Security → Modify IAM Role** → attach it

---

## Phase 2 — Secrets Setup

### Step 2.1 — GitHub Repository Secrets

Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets (copy values from your `backend/.env`):

| Secret Name | Value | Purpose |
|-------------|-------|---------|
| `EC2_HOST` | `13.235.67.89` (your Elastic IP) | SSH target |
| `EC2_USER` | `ubuntu` | SSH user |
| `EC2_SSH_KEY` | contents of your `.pem` file | SSH auth |
| `DATABASE_URL` | your Supabase pooler URL | Backend DB |
| `DATABASE_DIRECT_URL` | your Supabase direct URL | Alembic migrations |
| `REDIS_PASSWORD` | a strong password (generate one) | Redis auth |
| `JWT_PRIVATE_KEY` | your RSA private key PEM content | JWT signing |
| `JWT_PUBLIC_KEY` | your RSA public key PEM content | JWT verify |
| `GROQ_API_KEY` | `gsk_yeXq...` | LLM |
| `ALGORAND_ESCROW_CREATOR_MNEMONIC` | your 25-word mnemonic | Escrow |
| `CADENCIA_ADMIN_PASSWORD` | strong password | Admin login |
| `WEBHOOK_SIGNING_SECRET` | random 32-char string | Webhooks |
| `X402_PAYMENT_SECRET` | random 32-char string | Payments |

### Step 2.2 — GitHub Repository Variables (Non-Secret Config)

Go to **Settings → Secrets and variables → Actions → Variables tab**

| Variable Name | Value |
|---------------|-------|
| `NEXT_PUBLIC_API_URL` | `` (leave empty — uses Next.js proxy) |
| `EC2_DEPLOY_PATH` | `/home/ubuntu/cadencia` |

---

## Phase 3 — EC2 Environment File Setup (One-Time)

SSH into EC2 and create the env file that Docker Compose will use:

```bash
mkdir -p /home/ubuntu/cadencia
cat > /home/ubuntu/cadencia/.env << 'EOF'
# This file is managed manually on EC2 — never commit to git
APP_ENV=production
DEBUG=false
APP_VERSION=0.1.0

# Database — Supabase
DATABASE_URL=postgresql+asyncpg://postgres.skjnprzknzcrbkivqfpa:YOUR_PASS@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
DATABASE_DIRECT_URL=postgresql+asyncpg://postgres:YOUR_PASS@db.skjnprzknzcrbkivqfpa.supabase.co:5432/postgres?ssl=require
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YOUR_PASS
POSTGRES_DB=postgres

# Redis
REDIS_PASSWORD=use-a-strong-password-here

# JWT
JWT_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...your key...\n-----END RSA PRIVATE KEY-----
JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\n...your key...\n-----END PUBLIC KEY-----
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Algorand
ALGORAND_NETWORK=testnet
ALGORAND_ALGOD_ADDRESS=https://testnet-api.4160.nodely.dev
ALGORAND_ALGOD_TOKEN=
ALGORAND_ESCROW_CREATOR_MNEMONIC=your 25 word mnemonic here
ESCROW_DRY_RUN_ENABLED=true

# LLM
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_yourkey
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=512
LLM_HEALTH_CHECK_ENABLED=false

# CORS — use your EC2 public DNS or IP
CORS_ALLOWED_ORIGINS=http://YOUR-EC2-DNS.ap-south-1.compute.amazonaws.com,http://YOUR-EC2-IP

# Admin
CADENCIA_ADMIN_EMAIL=admin@cadencia.io
CADENCIA_ADMIN_PASSWORD=use-a-strong-password-here

# Compliance
AUDIT_RETENTION_YEARS=7
DATA_RESIDENCY_REGION=ap-south-1

# S3 (MinIO in cloud compose)
AWS_S3_ENDPOINT=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_MEMORY_CHUNK_SIZE=512
S3_MEMORY_RETENTION_DAYS=7

# KYC / On-Ramp (mock for demo)
KYC_PROVIDER=mock
ONRAMP_PROVIDER=mock

# Webhooks
WEBHOOK_SIGNING_SECRET=generate-32-char-random-string
X402_PAYMENT_SECRET=generate-32-char-random-string
WEBHOOK_TIMEOUT_SECONDS=10
WEBHOOK_MAX_RETRIES=3
ANCHOR_SERVICE_ENABLED=true

# Misc
API_RATE_LIMIT_REQUESTS=100
API_RATE_LIMIT_WINDOW_SECONDS=60
LLM_RATE_LIMIT_REQUESTS=50
LLM_RATE_LIMIT_WINDOW_SECONDS=60
PGSSLROOTCERT=/app/supabase-root-ca.pem
EOF

chmod 600 /home/ubuntu/cadencia/.env
```

---

## Phase 4 — Update `docker-compose.cloud.yml` for EC2

Two changes needed in the cloud compose before deploying:
1. **Redis needs a password** (currently has none)
2. **CORS needs your EC2 DNS**

These will be injected from the `.env` file on EC2 — update `docker-compose.cloud.yml`:

```yaml
# Redis — add password from env
redis:
  command: redis-server --requirepass ${REDIS_PASSWORD}
  healthcheck:
    test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]

# Backend — update CORS and Redis URL
backend:
  environment:
    REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
    CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS}
```

---

## Phase 5 — Update GitHub Actions CD for EC2 Deployment

The current `cd.yml` only pushes to GHCR. Add a **deploy job** that SSHes into EC2:

```yaml
# Add this job after 'publish' in cd.yml
deploy:
  name: Deploy to EC2
  runs-on: ubuntu-latest
  needs: publish
  environment: production

  steps:
    - uses: actions/checkout@v4

    - name: Deploy via SSH
      uses: appleboy/ssh-action@v1
      with:
        host: ${{ secrets.EC2_HOST }}
        username: ${{ secrets.EC2_USER }}
        key: ${{ secrets.EC2_SSH_KEY }}
        script: |
          cd /home/ubuntu/cadencia

          # Login to GHCR
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin

          # Pull latest images
          docker pull ghcr.io/${{ github.repository }}/backend:latest
          docker pull ghcr.io/${{ github.repository }}/frontend:latest

          # Copy compose file from repo
          cp docker-compose.cloud.yml /home/ubuntu/cadencia/docker-compose.yml || true

          # Update compose to use GHCR images instead of building locally
          docker compose down --remove-orphans
          docker compose up -d

          # Clean old images
          docker image prune -f
```

---

## Phase 6 — First Deploy (Manual Bootstrap)

Do this once to bootstrap the EC2:

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@<EC2-IP>

# Clone the repo
cd /home/ubuntu
git clone https://github.com/harsh-mogalgiddikar/cadencia-platform.git cadencia
cd cadencia

# Copy the .env you created in Phase 3 (already there)
# The docker-compose.cloud.yml is in the repo root

# Login to GHCR (use GitHub Personal Access Token with read:packages scope)
echo YOUR_GITHUB_PAT | docker login ghcr.io -u harsh-mogalgiddikar --password-stdin

# Build & start (first time — builds locally)
docker compose -f docker-compose.cloud.yml up -d --build

# Run migrations (once)
docker exec cadencia-backend alembic upgrade head

# Verify everything is up
docker compose -f docker-compose.cloud.yml ps
curl http://localhost:8000/health
```

---

## Phase 7 — Ongoing Deployment Flow

After the initial setup, every deployment is:

```
1. Make code changes locally
2. git add . && git commit -m "fix: ..."  
3. git push origin main         → triggers CI (lint + build check)
4. git tag v1.0.1               → triggers CD (build + push to GHCR + deploy to EC2)
5. git push origin v1.0.1
```

GitHub Actions will:
- Build Docker images with the tag
- Push to `ghcr.io/harsh-mogalgiddikar/cadencia-platform/backend:latest`
- SSH into EC2, pull new images, restart containers

---

## Phase 8 — Access Your App

After deploy, your app is accessible at:

| Service | URL |
|---------|-----|
| Frontend | `http://<EC2-ELASTIC-IP>` |
| Backend API | `http://<EC2-ELASTIC-IP>:8000` |
| API Health | `http://<EC2-ELASTIC-IP>:8000/health` |
| Swagger docs | `http://<EC2-ELASTIC-IP>:8000/docs` (disabled in prod — set `APP_ENV=development` temporarily to enable) |

---

## Checklist Summary

| # | Task | Where |
|---|------|--------|
| ☐ | Launch EC2 t3.medium in ap-south-1 | AWS Console |
| ☐ | Assign Elastic IP | AWS Console |
| ☐ | Open ports 22, 80, 3000, 8000 in Security Group | AWS Console |
| ☐ | Install Docker + Docker Compose plugin on EC2 | SSH |
| ☐ | Create `/home/ubuntu/cadencia/.env` with real secrets | SSH |
| ☐ | Add all GitHub Secrets (EC2_HOST, EC2_SSH_KEY, etc.) | GitHub Settings |
| ☐ | Fix `docker-compose.cloud.yml` (Redis password + CORS) | Code |
| ☐ | Update `cd.yml` to add deploy-to-EC2 job | Code |
| ☐ | Commit & push all changes to `main` | Git |
| ☐ | Bootstrap EC2 manually (first `docker compose up`) | SSH |
| ☐ | Run `alembic upgrade head` on EC2 | SSH |
| ☐ | Tag a release `v1.0.0` and confirm CD runs end-to-end | Git |

---

## Cost Estimate (ap-south-1)

| Resource | Cost/month |
|----------|-----------|
| EC2 t3.medium | ~$30/mo |
| Elastic IP (attached) | Free |
| EBS 20 GB gp3 | ~$1.6/mo |
| Data transfer (out) | ~$0.09/GB |
| **Total** | **~$32/mo** |

> Supabase free tier is sufficient for a demo. Algorand TestNet is free.
