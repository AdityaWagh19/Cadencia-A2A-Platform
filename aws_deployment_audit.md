# 🚀 Cadencia — AWS Deployment Readiness Audit

---

## 🔴 CRITICAL — Must Fix Before Deploying

### 1. Real secrets committed/exposed in `backend/.env`
The `.env` is correctly in `.gitignore` and NOT tracked by git — **good**.  
BUT the file contains plaintext production secrets that will be on your local disk and could leak.  
For AWS, **never copy `.env` to the server**. Use **AWS Secrets Manager** or **SSM Parameter Store** instead.

Secrets currently in `.env` that need AWS-safe equivalents:
| Secret | Current Value |
|--------|--------------|
| `DATABASE_URL` / `DATABASE_DIRECT_URL` | Real Supabase prod credentials + password `Cadencia1234` |
| `POSTGRES_PASSWORD` | `Cadencia1234` (weak, plaintext) |
| `JWT_PRIVATE_KEY` | Full RSA private key embedded in file |
| `ALGORAND_ESCROW_CREATOR_MNEMONIC` | Full 25-word mnemonic in plaintext |
| `GROQ_API_KEY` | Real live key (`gsk_yeXq...`) |
| `CADENCIA_ADMIN_PASSWORD` | `Admin@1234` plaintext |

> **Action**: Store all of the above in AWS Secrets Manager. Inject via ECS task definition env vars or SSM at runtime.

---

### 2. `CORS_ALLOWED_ORIGINS` still set to `localhost`
In `backend/.env`:
```
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```
In `docker-compose.cloud.yml`:
```
CORS_ALLOWED_ORIGINS: http://localhost:3000
```
**This will block your frontend on AWS from hitting the API.**

> **Action**: Set `CORS_ALLOWED_ORIGINS=https://your-aws-frontend-domain.com` in your production env config.

---

### 3. `frontend/.env.local` has hardcoded `localhost:8000`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
The `docker-compose.cloud.yml` uses relative URL (unset) which is correct.  
But `.env.local` will override this if it's copied or present on the server.

> **Action**: Do NOT copy `frontend/.env.local` to AWS. Use Docker build args or SSM-injected env at deploy time. Or keep `NEXT_PUBLIC_API_URL` **empty** (the proxy rewrite in `next.config.ts` handles it correctly).

---

### 4. `Caddyfile.prod` domain is placeholder `api.cadencia.in`
```
{$CADDY_DOMAIN:api.cadencia.in}
```
This is the fallback default. You need to either:
- Set the `CADDY_DOMAIN` environment variable to your actual AWS domain/subdomain, OR
- Replace `api.cadencia.in` with your real domain before deploying

> **Action**: Set `CADDY_DOMAIN=your-actual-domain.com` in your AWS environment.

---

### 5. MinIO creds are dev placeholders in both `.env` and `docker-compose.cloud.yml`
```
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_S3_ENDPOINT=http://localhost:9000   (in .env)
AWS_S3_ENDPOINT=http://minio:9000       (in docker-compose.cloud.yml)
```
For real AWS deployment, you should use **actual AWS S3** with IAM roles — not MinIO.

> **Action**: Replace MinIO with real S3. Remove `minio:` service from compose. Set `AWS_S3_ENDPOINT=` (blank = native S3), use IAM instance role or real `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`.

---

## 🟠 IMPORTANT — Should Fix

### 6. `docker-compose.cloud.yml` Redis has **no password**
```yaml
redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]   # no -a password flag
```
And backend overrides:
```
REDIS_URL: redis://redis:6379/0   # no password!
```
The dev compose sets a password; the cloud compose doesn't.

> **Action**: Add `REDIS_PASSWORD` to the cloud compose and secure the Redis instance.

---

### 7. `APP_ENV` is set to `development` in `.env`, not `production`
```
APP_ENV=development
```
This enables Swagger `/docs`, `/redoc`, `/openapi.json` — blocked by Caddy but still served internally.

> **Action**: Set `APP_ENV=production` in the AWS environment. (Caddy already blocks it externally, but it's a defence-in-depth issue.)

---

### 8. `ESCROW_DRY_RUN_ENABLED=true` in `.env`
Should be `false` in a production environment where real escrow is intended.

> **Action**: Set `ESCROW_DRY_RUN_ENABLED=false` for production (or confirm this is intentional for demo).

---

### 9. MSW (Mock Service Worker) still wired into the frontend layout
`frontend/src/app/layout.tsx` wraps everything in `<MSWProvider>`:
```ts
import { MSWProvider } from '@/components/providers/MSWProvider';
```
MSW is correctly gated by `NEXT_PUBLIC_ENABLE_MOCKS=false`, so it won't intercept requests in production — **but** the MSW service worker files will still be bundled and shipped to the browser.

Several pages also have residual mock-only logic:
- `page.tsx`: `setSelectedEscrowId('escrow-001')` default, `/mock/bulk-export.zip` fallback
- Compliance page: `/mock/fema-*.pdf`, `/mock/gst-*.csv`

> **Action**: These are cosmetic but will show broken download links in production. The mock fallbacks should be replaced with real API calls or removed.

---

### 10. `docker-compose.prod.yml` is inside `backend/` — inconsistent with `docker-compose.cloud.yml` at root
The cloud compose (`docker-compose.cloud.yml`) at root is the one to use for full-stack deploy. The `backend/docker-compose.prod.yml` only manages backend services (no frontend). 

> **Action**: Decide on one compose file for AWS deployment. `docker-compose.cloud.yml` at root is the right one for full stack. `backend/docker-compose.prod.yml` can be used if you split frontend/backend deployments.

---

## 🟡 MINOR — Note for Awareness

### 11. `localhost:4001` fallback hardcoded in backend source
In `backend/src/.../router.py` and `algorand_gateway.py`:
```python
os.environ.get("ALGORAND_ALGOD_ADDRESS", "http://localhost:4001")
```
This is just a dev default — in Docker it reads from env which is set to TestNet. Not a blocker.

### 12. Two unfinished TODOs in backend source
- `router.py:319` — `# TODO: track last_embedded_at in profile model`
- `handlers.py:77` — `# TODO Phase Four: SettlementService.deploy_escrow(...)` 

Not blockers, but worth knowing.

### 13. `supabase-root-ca.pem` is in `.gitignore` (`*.pem`)
The root gitignore has `*.pem` which would exclude `supabase-root-ca.pem`.  
The backend Dockerfile `COPY supabase-root-ca.pem` **requires** this file to be present at build time.

> **Action**: Verify `supabase-root-ca.pem` is explicitly un-ignored or available in the build context. Check: `git check-ignore -v backend/supabase-root-ca.pem`

### 14. `Algorand localnet` in `docker-compose.cloud.yml` (DEV_MODE)
The cloud compose still runs Algorand in `DEV_MODE=1` (local dev node). The `.env` points to `testnet-api.4160.nodely.dev` which overrides this for the backend. The local algod node in Docker is wasted compute.

> **Action**: For AWS, remove Algorand localnet from compose. Backend `.env`/environment already points to TestNet directly.

---

## ✅ Already Correct

| Item | Status |
|------|--------|
| `backend/.env` NOT tracked by git | ✅ |
| `frontend/.env.local` NOT tracked by git | ✅ |
| Gunicorn in `pyproject.toml` dependencies | ✅ |
| Multi-stage Dockerfile with non-root user | ✅ |
| Frontend Dockerfile uses `standalone` output | ✅ |
| Alembic migrations in place (12 versions) | ✅ |
| Supabase root CA included in Docker image | ✅ |
| CORS wildcard `*` blocked in production code | ✅ |
| `Caddyfile.prod` with TLS 1.3 + security headers | ✅ |
| `.dockerignore` correctly excludes tests, docs, .env | ✅ |
| `NEXT_PUBLIC_ENABLE_MOCKS=false` in cloud compose | ✅ |
| Next.js proxy rewrite avoids CORS (relative URLs) | ✅ |
