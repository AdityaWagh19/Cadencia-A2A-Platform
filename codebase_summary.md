# 📊 Cadencia A2A Platform — Codebase Summary

> Repository: [github.com/AdityaWagh19/Cadencia-A2A-Platform](https://github.com/AdityaWagh19/Cadencia-A2A-Platform)  
> Audited: 2026-04-15

---

## 📈 Lines of Code — Overall

| Layer | Language | Files | LOC |
|-------|----------|------:|----:|
| **Backend** | Python | 201 | 23,901 |
| **Backend Tests** | Python | 38 | 5,468 |
| **Frontend** | TypeScript / TSX | 106 | 11,494 |
| **Frontend** | CSS | 2 | 259 |
| **SQL** | SQL | 2 | 400 |
| **Smart Contracts** | TEAL + Python | 5 | 635 |
| **Infrastructure** | Docker / Caddyfile | 8 | 708 |
| **CI/CD** | YAML | 2 | 197 |
| **TOTAL (code)** | | **364** | **43,062** |

> *Excludes `node_modules/`, `.git/`, auto-generated cache files, and documentation*

---

## 🐍 Backend — Module Breakdown

| Module | Domain | Files | LOC |
|--------|--------|------:|----:|
| `negotiation` | AI-driven price negotiation engine | 32 | 5,216 |
| `settlement` | Escrow + on-chain settlement | 23 | 4,125 |
| `identity` | Auth, enterprise, user management | 22 | 3,154 |
| `compliance` | Audit trail, FEMA/GST reporting | 20 | 1,954 |
| `marketplace` | RFQ matching, liquidity pools | 20 | 2,142 |
| `shared` | Infra: DB, Redis, events, logging | 35 | 2,659 |
| `treasury` | FX positions, Frankfurter feed | 18 | 1,302 |
| `admin` | Admin panel endpoints | 8 | 1,040 |
| `wallet` | Algorand wallet integration | 4 | 405 |
| `health` | Health checks, readiness | 2 | 215 |
| `alembic/migrations` | DB schema (12 migrations) | 15 | 1,424 |
| **TOTAL** | | **199** | **23,636** |

**Architecture**: Hexagonal (Ports & Adapters) — 10 bounded domains  
**Framework**: FastAPI + SQLAlchemy (async) + Alembic + Gunicorn

---

## ⚛️ Frontend — Module Breakdown

| Folder | Purpose | Files | LOC |
|--------|---------|------:|----:|
| `app/` | Next.js pages & routes | 15 | 4,732 |
| `components/` | UI components (shared + ui) | 62 | 4,508 |
| `context/` | Auth + Wallet React contexts | 2 | 674 |
| `mocks/` | MSW dev mock handlers | 15 | 917 |
| `types/` | TypeScript type definitions | 1 | 366 |
| `lib/` | API client, utils, constants | 6 | 161 |
| `hooks/` | React custom hooks | 4 | 115 |
| `styles` (CSS) | Global styles | 2 | 259 |
| **TOTAL** | | **107** | **11,732** |

**Framework**: Next.js 15 (App Router) + TypeScript + Tailwind CSS  
**Output**: Standalone (Docker-optimized)

---

## 🧪 Test Suite Breakdown

| Type | Files | LOC | Coverage Area |
|------|------:|----:|---------------|
| Unit | 22 | 3,610 | Services, domain logic, validators |
| Integration | 6 | 510 | API endpoints, DB interactions |
| E2E | 3 | 678 | Full trade loop flows |
| Performance | 3 | 529 | Load & stress tests |
| Smoke | 2 | 97 | Health & startup checks |
| **TOTAL** | **36** | **5,424** | |

---

## 📦 Dependencies

### Backend (Python)
| Category | Count |
|----------|------:|
| Total Python packages in `pyproject.toml` | ~38 production |
| Runtime (FastAPI, SQLAlchemy, Pydantic, etc.) | 30+ |
| Dev/test (pytest, ruff, mypy) | ~8 |

Key packages: `fastapi`, `sqlalchemy[asyncio]`, `alembic`, `gunicorn`, `uvicorn`, `pydantic`, `py-algorand-sdk`, `groq`, `redis`, `structlog`, `prometheus-client`, `supabase`

### Frontend (Node.js)
| Category | Count |
|----------|------:|
| Runtime dependencies | 34 |
| Dev dependencies | 10 |

Key packages: `next 15`, `react 19`, `@perawallet/connect`, `@tanstack/react-query`, `msw`, `tailwindcss`, `recharts`, `sonner`

---

## 🗂️ Total Repository

| Metric | Count |
|--------|------:|
| Total files (excl. node_modules, .git) | 2,117 |
| Source code files only | 364 |
| Database migrations | 12 |
| Algorand smart contract artifacts | 4 (TEAL + ARC56 JSON) |
| Docker Compose files | 4 (dev, prod, cloud, backend-only) |
| GitHub Actions workflows | 2 (CI + CD) |

---

## 🏗️ Architecture Overview

```
Cadencia A2A Platform
├── backend/                    ← FastAPI monolith (hexagonal)
│   ├── src/                    ← 10 domain bounded contexts
│   │   ├── identity/           ← Auth, JWT, enterprise, users
│   │   ├── marketplace/        ← RFQ matching, liquidity
│   │   ├── negotiation/        ← AI agent negotiation engine
│   │   ├── settlement/         ← Algorand escrow + settlement
│   │   ├── compliance/         ← Audit trails, FEMA/GST
│   │   ├── treasury/           ← FX positions, rates
│   │   ├── wallet/             ← Algorand wallet
│   │   ├── admin/              ← Admin management
│   │   ├── health/             ← Health endpoints
│   │   └── shared/             ← Infra: DB, Redis, events
│   ├── alembic/                ← 12 DB migrations
│   ├── scripts/                ← Seed data, migrate runner
│   ├── tests/                  ← 36 test files
│   ├── artifacts/              ← Compiled TEAL contracts
│   └── infra/                  ← Terraform + Grafana dashboards
│
├── frontend/                   ← Next.js 15 App Router
│   └── src/
│       ├── app/                ← 15 page routes
│       ├── components/         ← 62 UI components
│       └── mocks/              ← 15 MSW dev handlers
│
├── .github/workflows/          ← CI (lint/build) + CD (GHCR + EC2)
└── docker-compose.cloud.yml    ← Full-stack cloud deployment
```

---

## 🔑 Key Technical Stats

| Feature | Detail |
|---------|--------|
| API endpoints | ~60+ REST endpoints under `/v1/` |
| DB tables (migrations) | ~25+ tables across 12 migrations |
| Algorand network | TestNet (TEAL smart contracts) |
| LLM provider | Groq (llama-3.3-70b-versatile) |
| Auth | RS256 JWT (asymmetric keys) |
| DB | Supabase PostgreSQL (cloud-managed) |
| Caching / Rate limiting | Redis 7 |
| Observability | Prometheus `/metrics` + Structlog JSON |
| Infra-as-code | Terraform (ECS, ElastiCache, RDS modules) |
