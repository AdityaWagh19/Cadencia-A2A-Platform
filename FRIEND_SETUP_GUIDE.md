# Cadencia — Quick Start Guide (Docker Hub)

This guide lets you run the full Cadencia stack from pre-built Docker images.
No need to build anything — just pull and run.

---

## Prerequisites

1. **Docker Desktop** installed and running
   - Windows: https://docs.docker.com/desktop/setup/install/windows-install/
   - Mac: https://docs.docker.com/desktop/setup/install/mac-install/
   - Linux: https://docs.docker.com/engine/install/

2. **Git** (to clone the repo for config files)

---

## Step 1: Clone the Repository

```bash
git clone <repo-url>
cd Cadencia-most-final
git checkout testing
```

> You only need the repo for the `.env` files and `docker-compose.hub.yml`.
> The actual code runs from Docker Hub images — no build needed.

---

## Step 2: Set Up Environment Variables

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in the required values. For local development, the
defaults mostly work out of the box. The key ones to configure:

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | local postgres | Auto-configured by docker-compose |
| `REDIS_URL` | local redis | Auto-configured by docker-compose |
| `JWT_PRIVATE_KEY` | — | Ask Shreyas for the dev keys |
| `JWT_PUBLIC_KEY` | — | Ask Shreyas for the dev keys |
| `ALGORAND_ESCROW_CREATOR_MNEMONIC` | — | Ask Shreyas or generate a testnet account |
| `LLM_PROVIDER` | `stub` | Use `stub` for dev (no API key needed) |
| `GROQ_API_KEY` | — | Only needed if `LLM_PROVIDER=groq` |

> **Important:** Database and Redis URLs are overridden by docker-compose to use
> Docker internal networking. You don't need to change them in `.env`.

---

## Step 3: Pull and Run

```bash
# Pull all images (first time / updates)
docker compose -f docker-compose.hub.yml pull

# Start the full stack
docker compose -f docker-compose.hub.yml up
```

Add `-d` to run in background:
```bash
docker compose -f docker-compose.hub.yml up -d
```

---

## Step 4: Verify

Once everything is running (give it ~60 seconds for health checks):

| Service | URL | Check |
|---------|-----|-------|
| Frontend | http://localhost:3000 | Main app UI |
| Backend API | http://localhost:8000/health | Should return `{"status": "ok"}` |
| MinIO Console | http://localhost:9001 | Login: minioadmin / minioadmin |
| Algorand | http://localhost:4001/health | Localnet node |

---

## Common Commands

```bash
# View logs
docker compose -f docker-compose.hub.yml logs -f

# View logs for a specific service
docker compose -f docker-compose.hub.yml logs -f backend

# Stop everything
docker compose -f docker-compose.hub.yml down

# Stop and remove all data (fresh start)
docker compose -f docker-compose.hub.yml down -v

# Pull latest images (when Shreyas pushes updates)
docker compose -f docker-compose.hub.yml pull
docker compose -f docker-compose.hub.yml up -d
```

---

## Updating to Latest Version

When Shreyas pushes new images:

```bash
docker compose -f docker-compose.hub.yml pull
docker compose -f docker-compose.hub.yml up -d
```

That's it — Docker will replace the old containers with the new images.

---

## Troubleshooting

**Backend won't start?**
- Check `backend/.env` has valid JWT keys
- Run `docker compose -f docker-compose.hub.yml logs backend` for errors

**Database migration fails?**
- Run `docker compose -f docker-compose.hub.yml down -v` for a fresh start
- Then `docker compose -f docker-compose.hub.yml up`

**Port conflicts?**
- Make sure ports 3000, 5432, 6379, 8000, 9000, 9001, 4001, 4002 are free
- Stop other Docker containers or local services using those ports

**Need to reset everything?**
```bash
docker compose -f docker-compose.hub.yml down -v
docker compose -f docker-compose.hub.yml pull
docker compose -f docker-compose.hub.yml up
```
