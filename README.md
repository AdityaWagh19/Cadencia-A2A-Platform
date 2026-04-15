<br><div align="center">

# Cadencia

### AI-Native Agentic B2B Trade Platform for Indian MSMEs

[![CI](https://github.com/AdityaWagh19/Cadencia-A2A-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/AdityaWagh19/Cadencia-A2A-Platform/actions/workflows/ci.yml)
[![CD](https://github.com/AdityaWagh19/Cadencia-A2A-Platform/actions/workflows/cd.yml/badge.svg)](https://github.com/AdityaWagh19/Cadencia-A2A-Platform/actions/workflows/cd.yml)
![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)
![Algorand](https://img.shields.io/badge/Algorand-TestNet-teal?logo=algorand)
![License](https://img.shields.io/badge/License-MIT-purple)

**Upload one RFQ. Cadencia autonomously handles seller discovery, AI negotiation, blockchain escrow, settlement, and regulatory compliance — end to end.**

[Features](#features) · [Architecture](#system-architecture) · [Quick Start](#quick-start) · [API Reference](#api-reference) · [Deployment](#deployment)

</div>

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [System Architecture](#system-architecture)
4. [Trade Flow — End to End](#trade-flow--end-to-end)
5. [Domain Event Architecture](#domain-event-architecture)
6. [Database Schema](#database-schema)
7. [Smart Contract — CadenciaEscrow](#smart-contract--cadenciaescrow)
8. [API Reference](#api-reference)
9. [Tech Stack](#tech-stack)
10. [Codebase Statistics](#codebase-statistics)
11. [Quick Start (Local Dev)](#quick-start)
12. [Deployment](#deployment)
13. [Environment Variables](#environment-variables)
14. [Security](#security)
15. [Testing](#testing)

---

## Overview

Cadencia is a **closed-loop, AI-native agentic B2B marketplace** purpose-built for Indian MSMEs. It transforms the friction-laden procurement cycle — traditionally involving phone calls, WhatsApp negotiations, manual compliance filing, and slow bank settlements — into a **single-upload autonomous workflow**.

### The Problem

| Pain Point | Current Reality |
|-----------|----------------|
| Vendor Discovery | 30–40% of procurement bandwidth spent on manual outreach |
| Settlement Latency | 3–7 banking days lock working capital |
| Compliance | Manual FEMA Form A2 and GST filing, error-prone and audit-intensive |
| Fragmentation | No single platform combines discovery + negotiation + settlement + compliance |

### The Solution

```mermaid
flowchart TD
    A[Buyer uploads RFQ] --> B[LLM parses fields: product, HSN, budget, window]
    B --> C[pgvector finds Top-N matching sellers in < 2 seconds]
    C --> D[AI agents negotiate autonomously: buyer + seller LLM agents]
    D --> E[Algorand escrow deployed on-chain via smart contract]
    E --> F[Delivery confirmed → escrow released → FEMA + GST records auto-generated]
```

---

## Features

| Feature | Description |
|---------|-------------|
| **AI Negotiation Engine** | Autonomous buyer + seller LLM agents with configurable risk profiles, budget ceilings, and convergence detection |
| **pgvector Matching** | 1536-dimensional vector embeddings with IVFFlat cosine similarity search across 10,000+ seller profiles in < 2s |
| **Algorand Escrow** | ARC-4 smart contract (Puya) with deploy → fund → release → refund lifecycle; Merkle root anchored on-chain |
| **Compliance Automation** | Auto-generated FEMA Form A2 and GST records on every settlement; PDF/CSV export; 7-year retention |
| **Real-time SSE Stream** | Live agent negotiation turn-by-turn visibility via Server-Sent Events |
| **Human Override** | Inject manual offers mid-session; agent profile learns from corrections |
| **Treasury Dashboard** | INR/USDC pool balances, Frankfurter FX feed, 30-day liquidity runway |
| **Enterprise Auth** | RS256 JWT, httpOnly refresh cookies, HMAC-hashed API keys, RBAC |
| **Observability** | Prometheus metrics, structlog JSON, Caddy security headers |

---

## System Architecture

### Seven-Layer Architecture

```mermaid
flowchart TD
    subgraph Layer 1: Marketplace & Onboarding
        1A[RFQ Upload] --> 1B[LLM NLP Parsing]
        1B --> 1C[pgvector Similarity Search]
        1C --> 1D[Top-N Seller Ranking]
    end

    subgraph Layer 2: Agent Personalization Engine
        2A[AgentProfile] -.- 2B[Strategy Weights]
        2A -.- 2C[History Embeddings]
        2A -.- 2D[Playbooks]
    end

    subgraph Layer 3: API Gateway
        3A[FastAPI] -.- 3B[JWT Validation]
        3A -.- 3C[Rate Limiting & CORS]
        3A -.- 3D[SSE Stream]
    end

    subgraph Layer 4: Core Services
        4A[NeutralEngine: Negotiation] -.- 4B[SettlementService]
        4A -.- 4C[ComplianceGenerator]
    end

    subgraph Layer 5: Algorand Interaction
        5A[Puya Contract Client] -.- 5B[algosdk]
        5A -.- 5C[Dry-Run Safety & Merkle Anchoring]
    end

    subgraph Layer 6: Data Layer
        6A[PostgreSQL 16 + pgvector] -.- 6B[Async SQLAlchemy & UoW]
        6A -.- 6C[Redis 7]
    end

    subgraph Layer 7: External Integrations
        7A[Frankfurter FX Feed] -.- 7B[INR/USDC On/Off-Ramp]
        7A -.- 7C[KYC Provider]
    end
```

### Hexagonal Architecture (Ports & Adapters)

```mermaid
flowchart TD
    HTTP["API / FastAPI (HTTP Adapters)"] --> App
    
    subgraph App["Application Layer"]
        CQ["Commands, Queries, Use Cases"]
    end
    
    App --> Domain
    App --> DE["Domain Events (Publisher/Handlers)"]
    
    subgraph Domain["Domain Layer (Core)"]
        Ent["Entities & Aggregates"] -.- VO["Value Objects"]
        VO -.- Rules["Domain Rules"]
    end
    
    Domain --> Infra
    
    subgraph Infra["Infrastructure Layer"]
        DB["PostgreSQL / Redis / Algorand / LLM / S3"]
    end
```

### Bounded Contexts (Domain-Driven Design)

```mermaid
flowchart LR
    subgraph Identity
        I1[Enterprise, Users, KYC] -.- I2[JWT Auth, API Keys]
    end
    
    subgraph Marketplace
        M1[RFQ Upload, NLP Parsing] -.- M2[pgvector Matching]
    end
    
    subgraph Negotiation
        N1[LLM Agents, NeutralEngine] -.- N2[SSE Stream, Human Override]
    end
    
    subgraph Settlement
        S1[CadenciaEscrow, Algorand SDK] -.- S2[Dry-Run Safety, Merkle]
    end
    
    subgraph Compliance
        C1[Audit Log] -.- C2[FEMA & GST Records]
    end
    
    subgraph Treasury
        T1[INR/USDC, FX Feed] -.- T2[Liquidity Forecast]
    end
    
    Identity --> Marketplace
    Marketplace --"RFQConfirmed"--> Negotiation
    Negotiation --"SessionAgreed"--> Settlement
    Settlement --"EscrowReleased"--> Compliance
    Treasury -.-> Settlement
```

---

## Trade Flow — End to End

```mermaid
sequenceDiagram
    participant B as Buyer
    participant API as Cadencia API (FastAPI)
    participant DB as Postgres/pgvector
    participant LLM as AI Agents (LLMs)
    participant ALGO as Algorand Blockchain
    participant S as Seller

    B->>API: POST /v1/marketplace/rfq (Text)
    API->>LLM: NLP Field Extraction
    API->>DB: Cosine Similarity Search
    DB-->>API: Match List
    API-->>B: Return Top matches (Scores)
    
    B->>API: POST /v1/rfq/{id}/confirm
    Note over API: RFQConfirmed event
    
    loop Negotiation Rounds
        LLM-->>B: SSE: Round N offer (Buyer AI)
        LLM-->>S: SSE: Round N offer (Seller AI)
        Note over LLM: Detect price gap <= 2%
    end
    
    LLM-->>API: Convergence Detected
    API-->>B: SSE: {event: "agreed"}
    API-->>S: SSE: {event: "agreed"}
    
    Note over API: SessionAgreed event
    API->>ALGO: Deploy CadenciaEscrow (Dry-run -> Broadcast)
    B->>API: POST /v1/escrow/{id}/fund
    
    Note right of B: Independent Delivery (off-platform)
    
    API->>ALGO: Release escrow (Admin)
    ALGO-->>S: ALGO payment transferred
    
    Note over API: Merkle root anchored on-chain<br>EscrowReleased event
    API-->>B: Auto-generate FEMA & GST records
    API-->>S: Auto-generate FEMA & GST records
```

---

## Domain Event Architecture

Events are the **only** way bounded contexts communicate. Direct cross-domain imports are prohibited and enforced by Ruff linting (TID252).

```mermaid
flowchart LR
    Marketplace --"RFQConfirmed"--> Negotiation
    Negotiation --"SessionAgreed"--> Settlement
    Settlement --"EscrowDeployed"--> Compliance
    Settlement --"EscrowFunded"--> Compliance
    Settlement --"EscrowReleased"--> Compliance
    Settlement --"EscrowRefunded"--> Compliance
    Negotiation --"HumanOverride"--> Negotiation
```

| Event | Publisher | Subscriber | Effect |
|-------|-----------|------------|--------|
| `RFQConfirmed` | marketplace | negotiation | Create NegotiationSession |
| `SessionAgreed` | negotiation | settlement | Deploy CadenciaEscrow on Algorand |
| `EscrowDeployed` | settlement | compliance | Append audit event |
| `EscrowFunded` | settlement | compliance | Append audit event |
| `EscrowReleased` | settlement | compliance | Generate FEMA + GST records; anchor Merkle root |
| `EscrowRefunded` | settlement | compliance | Append refund audit event |
| `HumanOverride` | negotiation | negotiation | Update AgentProfile strategy weights |

---

## Database Schema

### Entity-Relationship Overview

```mermaid
erDiagram
    ENTERPRISES ||--o{ USERS : "contains"
    ENTERPRISES ||--o{ API_KEYS : "owns"
    ENTERPRISES ||--o{ RFQS : "submits"
    ENTERPRISES ||--|| CAPABILITY_PROFILES : "has"
    ENTERPRISES ||--|| AGENT_PROFILES : "configures"
    ENTERPRISES ||--o{ AUDIT_LOG : "has"
    ENTERPRISES ||--o{ COMPLIANCE_RECORDS : "receives"
    
    RFQS ||--o{ MATCHES : "generates"
    MATCHES ||--|| NEGOTIATION_SESSIONS : "becomes"
    NEGOTIATION_SESSIONS ||--o{ OFFERS : "contains"
    NEGOTIATION_SESSIONS ||--|| ESCROW_CONTRACTS : "triggers"
    ESCROW_CONTRACTS ||--o{ SETTLEMENTS : "processes"
```

### Key Tables

| Table | Domain | Key Columns |
|-------|--------|-------------|
| `enterprises` | identity | `enterprise_id`, `pan` (unique), `gstin` (unique), `kyc_status`, `trade_role`, `algorand_wallet` |
| `rfqs` | marketplace | `rfq_id`, `raw_text`, `status` (DRAFT→SETTLED), `embedding` (vector 1536), `hsn_code` |
| `capability_profiles` | marketplace | `profile_id`, `enterprise_id`, `embedding` (vector 1536, IVFFlat index) |
| `negotiation_sessions` | negotiation | `session_id`, `status` (ACTIVE→AGREED\|FAILED), `agreed_price`, `round_count` |
| `offers` | negotiation | `offer_id`, `price`, `proposer_role`, `is_human_override`, `agent_reasoning` |
| `agent_profiles` | negotiation | `risk_profile` (JSONB), `strategy_weights` (JSONB), `automation_level` |
| `escrow_contracts` | settlement | `algo_app_id`, `status` (DEPLOYED→FUNDED→RELEASED), `merkle_root`, `frozen` |
| `audit_log` | compliance | `entry_hash`, `prev_hash` (SHA-256 chain), `event_type`, `event_data` |
| `compliance_records` | compliance | `record_type` (FEMA\|GST), `record_data` (JSONB) |

### Vector Indexes

```sql
-- Seller matching (primary: IVFFlat cosine similarity)
CREATE INDEX ON capability_profiles
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- RFQ reverse-matching (HNSW)
CREATE INDEX ON rfqs
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

---

## Smart Contract — CadenciaEscrow

**Language**: Algorand Python (Puya) · **Standard**: ARC-4 + ARC-56 · **Network**: Algorand TestNet

### State Machine

```mermaid
stateDiagram-v2
    [*] --> DEPLOYED : initialize()
    DEPLOYED --> FUNDED : fund()
    FUNDED --> RELEASED : release()
    FUNDED --> REFUNDED : refund()
    
    state FROZEN_MODE {
        Normal --> Frozen : freeze()
        Frozen --> Normal : unfreeze()
    }
    
    note right of FROZEN_MODE
        Safety: dry-run REQUIRED before every ALGO tx
        FROZEN flag halts transfers in DEPLOYED and FUNDED
    end note
```

### ABI Methods

| Method | Access | Pre-condition | Effect |
|--------|--------|---------------|--------|
| `initialize(buyer, seller, amount, session_id)` | Creator | CREATE call | Sets all global state; status=0 |
| `fund(payment: PaymentTxn)` | Buyer | status==0, frozen==0, payment==amount | status=1 |
| `release(merkle_root)` | Creator | status==1, frozen==0 | Inner payment → seller; status=2 |
| `refund(reason)` | Creator | status==1 | Inner payment → buyer; status=3 |
| `freeze()` | Buyer\|Seller\|Creator | Any status | frozen=1 |
| `unfreeze()` | Creator only | frozen==1 | frozen=0 |

### Safety Requirements

- Every call preceded by `algod.dryrun()` — dry-run failure raises `BlockchainSimulationError` and **aborts** the transaction
- `fund()` verifies `payment.amount == escrow.amount` atomically — partial funding rejected
- `release()` and `refund()` blocked when `frozen==1`
- Merkle root of all session audit events anchored on-chain in transaction Note field
- Idempotent submission — safe to retry without double-spend

---

## API Reference

All endpoints versioned under `/v1/`. All responses use the standard envelope:

```json
{ "success": true,  "data": { ... },  "error": null,    "request_id": "uuid" }
{ "success": false, "data": null,      "error": { "code": "...", "message": "..." }, "request_id": "uuid" }
```

### Authentication & Identity

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/v1/auth/register` | None | Register enterprise + admin user |
| `POST` | `/v1/auth/login` | None | Returns JWT access + refresh tokens |
| `POST` | `/v1/auth/refresh` | Refresh JWT | Rotate access token |
| `POST` | `/v1/auth/api-keys` | JWT | Create M2M API key |
| `DELETE` | `/v1/auth/api-keys/{key_id}` | JWT | Revoke API key |
| `GET` | `/v1/enterprises/{id}` | JWT | Get enterprise profile |
| `PATCH` | `/v1/enterprises/{id}/kyc` | JWT | Submit KYC documents |
| `PUT` | `/v1/enterprises/{id}/agent-config` | JWT | Update agent personalization |

### Marketplace

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/v1/marketplace/rfq` | JWT | Upload free-text RFQ → NLP parse → match |
| `GET` | `/v1/marketplace/rfq/{id}` | JWT | Get RFQ with parsed fields + matches |
| `POST` | `/v1/marketplace/rfq/{id}/confirm` | JWT | Select match → create negotiation session |
| `PUT` | `/v1/marketplace/capability-profile` | JWT | Update seller capability profile |
| `POST` | `/v1/marketplace/capability-profile/embeddings` | JWT | Recompute vector embeddings |

### Negotiation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/v1/sessions/{id}` | JWT | Get session state + offer history |
| `GET` | `/v1/sessions/{id}/stream` | JWT | **SSE stream** — live agent turn events |
| `POST` | `/v1/sessions/{id}/override` | JWT | Human override: inject offer mid-session |
| `POST` | `/v1/sessions/{id}/terminate` | JWT | Admin-terminate session |

### Escrow

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/v1/escrow/{session_id}` | JWT | Get escrow state + Algorand app info |
| `POST` | `/v1/escrow/{id}/fund` | JWT | Fund escrow (atomic PaymentTxn + AppCall) |
| `POST` | `/v1/escrow/{id}/release` | JWT | Release to seller + anchor Merkle root |
| `POST` | `/v1/escrow/{id}/refund` | JWT | Refund buyer (dispute) |
| `POST` | `/v1/escrow/{id}/freeze` | JWT | Freeze during dispute |

### Compliance, Audit & Treasury

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/v1/audit/log` | JWT (AUDITOR) | Paginated audit log |
| `GET` | `/v1/audit/proof/{session_id}` | JWT | Merkle proof for audit trail |
| `GET` | `/v1/compliance/fema/{session_id}` | JWT | FEMA record PDF/CSV download |
| `GET` | `/v1/compliance/gst/{session_id}` | JWT | GST record PDF/CSV download |
| `POST` | `/v1/compliance/export` | JWT | Bulk compliance export (ZIP) |
| `GET` | `/v1/treasury/dashboard` | JWT | INR/USDC balances + FX rate |
| `GET` | `/v1/treasury/fx-exposure` | JWT | Open FX positions |
| `GET` | `/v1/treasury/liquidity-forecast` | JWT | 30-day runway forecast |
| `GET` | `/health` | None | DB + Redis + Algorand health check |
| `GET` | `/metrics` | Internal | Prometheus metrics |

### Sample Request & Response

**Upload RFQ:**
```json
POST /v1/marketplace/rfq
{
  "raw_text": "We require 500 MT of HR Coil (HSN 7208), budget ₹45,000–₹50,000/MT, delivery by April 30 to Mumbai.",
  "document_type": "free_text"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "rfq_id": "3f7c4d...",
    "parsed_fields": {
      "product": "HR Coil",
      "hsn_code": "7208",
      "quantity": "500 MT",
      "budget_min": 45000,
      "budget_max": 50000,
      "delivery_window": "2026-04-30",
      "geography": "Mumbai"
    },
    "matches": [
      { "match_id": "a1b2...", "seller_name": "IndiaSteel Ltd", "score": 0.94, "rank": 1 },
      { "match_id": "c3d4...", "seller_name": "MetalCorp India", "score": 0.89, "rank": 2 }
    ],
    "status": "MATCHED"
  }
}
```

**SSE negotiation stream:**
```
data: {"event":"offer",  "round":1, "proposer":"BUYER",  "price":46000, "confidence":0.85}
data: {"event":"offer",  "round":2, "proposer":"SELLER", "price":49000, "confidence":0.79}
data: {"event":"offer",  "round":3, "proposer":"BUYER",  "price":47500, "confidence":0.82}
data: {"event":"offer",  "round":4, "proposer":"SELLER", "price":48200, "confidence":0.76}
data: {"event":"agreed", "final_price":47800, "session_id":"3f7c4d..."}
```

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.115 + Python 3.12 |
| ASGI Server | Gunicorn + Uvicorn workers (4 workers production) |
| Database | PostgreSQL 16 + pgvector 0.7 |
| ORM | SQLAlchemy 2.x (async, asyncpg) |
| Migrations | Alembic (12 migrations) |
| Cache / Rate Limiting | Redis 7.0 |
| LLM | Groq (llama-3.3-70b) via pluggable `IAgentDriver` |
| Blockchain | Algorand TestNet (algosdk 2.x + AlgoKit 3.x) |
| Smart Contracts | Algorand Python (Puya) — compiled offline |
| Validation | Pydantic v2 |
| Logging | structlog (JSON) |
| Metrics | Prometheus client |
| Reverse Proxy | Caddy 2.x (TLS + security headers) |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| State | TanStack Query |
| Wallet | Pera Connect (Algorand) |
| Mock API | MSW (dev only, disabled in prod) |
| Build Output | Standalone (Docker-optimized) |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions (CI: lint/build, CD: GHCR + EC2 deploy) |
| Container Registry | GitHub Container Registry (GHCR) |
| Cloud | AWS EC2 (ap-south-1 — Mumbai) |
| Database Cloud | Supabase PostgreSQL |
| IaC | Terraform (ECS, ElastiCache, RDS modules) |
| Observability | Grafana + Prometheus dashboards |

---

## Codebase Statistics

| Layer | Files | Lines of Code |
|-------|------:|-------------:|
| Backend (Python) | 201 | 23,901 |
| Backend Tests | 38 | 5,468 |
| Frontend (TypeScript/TSX) | 106 | 11,494 |
| SQL Migrations | 2 | 400 |
| Smart Contracts (TEAL) | 5 | 635 |
| Infrastructure | 10 | 905 |
| **Total** | **362** | **42,803** |

**Bounded contexts**: 10
**API endpoints**: 60+
**DB migrations**: 12
**Test files**: 38

---

## Quick Start (Local Dev)

### Prerequisites

- Docker + Docker Compose
- Python 3.12 (for local backend dev)
- Node.js 20 (for local frontend dev)
- A Groq API key (free at console.groq.com)

### 1. Clone the repo

```bash
git clone https://github.com/AdityaWagh19/Cadencia-A2A-Platform.git
cd Cadencia-A2A-Platform
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set GROQ_API_KEY and JWT keys at minimum
```

### 3. Start all services

```bash
# From repo root (starts backend + frontend + postgres + redis + algorand localnet)
docker compose -f backend/docker-compose.yml up --build
```

### 4. Run migrations

```bash
docker exec cadencia-backend alembic upgrade head
```

### 5. Seed demo data

```bash
docker exec cadencia-backend python scripts/seed_demo_data.py
```

### 6. Access the platform

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Metrics | http://localhost:8000/metrics |

---

## Deployment

### GitHub Actions CI/CD

```
Push to main  ──▶ CI (lint + type check + build)
git tag v*.*.*──▶ CD (build images → push to GHCR → deploy to EC2)
```

**Required GitHub Secrets:**

| Secret | Purpose |
|--------|---------|
| `EC2_HOST` | EC2 Elastic IP address |
| `EC2_USER` | SSH user (`ubuntu`) |
| `EC2_SSH_KEY` | Contents of `.pem` key file |
| `DATABASE_URL` | Supabase PostgreSQL pooler URL |
| `JWT_PRIVATE_KEY` | RSA private key for JWT signing |
| `GROQ_API_KEY` | LLM provider API key |
| `ALGORAND_ESCROW_CREATOR_MNEMONIC` | 25-word Algorand mnemonic |

**Deploy a release:**

```bash
git tag v1.0.0
git push origin v1.0.0
# GitHub Actions builds images → pushes to ghcr.io → SSHes into EC2 → docker compose up
```

### Docker Images

```bash
docker pull ghcr.io/adityawagh19/cadencia-a2a-platform/backend:latest
docker pull ghcr.io/adityawagh19/cadencia-a2a-platform/frontend:latest
```

---

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Required | PostgreSQL async URL | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | Required | Redis connection string | `redis://localhost:6379/0` |
| `JWT_PRIVATE_KEY` | Required | RS256 RSA private key (PEM) | Never commit — use env injection |
| `JWT_PUBLIC_KEY` | Required | RS256 RSA public key (PEM) | Paired with private key |
| `GROQ_API_KEY` | Required | LLM provider API key | `gsk_...` |
| `ALGORAND_NETWORK` | Required | Algorand target network | `testnet` \| `mainnet` |
| `ALGORAND_ALGOD_ADDRESS` | Required | Algorand node URL | `https://testnet-api.4160.nodely.dev` |
| `ALGORAND_ESCROW_CREATOR_MNEMONIC` | Required | 25-word mnemonic | Never commit |
| `CORS_ALLOWED_ORIGINS` | Required | Allowed CORS origins | `https://yourdomain.com` |
| `APP_ENV` | Required | Environment | `development` \| `production` |
| `ESCROW_DRY_RUN_ENABLED` | Required | Dry-run all blockchain calls | `true` (always in non-production) |
| `AUDIT_RETENTION_YEARS` | Required | Minimum audit retention | `7` |
| `DATA_RESIDENCY_REGION` | Required | AWS data residency region | `ap-south-1` |

---

## Security

| Control | Implementation |
|---------|---------------|
| **Authentication** | RS256 JWT (15-min expiry) + httpOnly refresh cookies (30-day) |
| **API Keys** | HMAC-SHA256 hashed — never stored or logged in plaintext |
| **RBAC** | `require_role()` enforced on every protected route |
| **Rate Limiting** | Redis sliding window: 100 req/60s per enterprise |
| **LLM Security** | Prompt injection detection + 8,000-char hard truncation |
| **Agent Output** | Strict JSON schema validation — invalid outputs never advance negotiation |
| **Blockchain** | Dry-run required before every Algorand call; idempotent submission |
| **Webhooks** | HMAC-SHA256 signed (`X-Cadencia-Signature` header) |
| **TLS** | Caddy + Let's Encrypt; TLS 1.3 only; HSTS (2 years) |
| **Headers** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, CSP |
| **Data** | Zero secrets in VCS; all credentials via environment variables |
| **Audit** | Append-only hash-chained audit log; Merkle proof endpoint |

---

## Testing

### Test Pyramid

```mermaid
flowchart BT
    T1["Unit Tests (Pure Python, zero I/O) - 22 files"]
    T2["Performance Tests (Load/Stress) - 3 files"]
    T3["Integration Tests (Docker DB/Redis) - 6 files"]
    T4["E2E Tests (Algorand localnet + real DB) - 3 files"]
    
    T1 --> T2 --> T3 --> T4
```

### Running Tests

```bash
# Unit tests (no dependencies needed)
cd backend
pip install -e ".[dev]"
pytest tests/unit/ -x --tb=short

# Integration tests (requires Docker)
pytest tests/integration/ --tb=short

# E2E tests (requires full stack + localnet)
docker compose -f docker-compose.yml up --wait
pytest tests/e2e/ -v
```

### Critical Test Cases

| Test | Validates |
|------|-----------|
| `test_budget_guard_rejects_over_ceiling` | Agent never exceeds budget_ceiling |
| `test_stall_detection_triggers_human_review` | Stall → HUMAN_REVIEW after N rounds |
| `test_convergence_detection_agrees_session` | Price gap ≤ 2% → AGREED |
| `test_dry_run_failure_prevents_broadcast` | No on-chain call without successful dry-run |
| `test_frozen_escrow_rejects_release` | Frozen escrow blocks all state transitions |
| `test_audit_log_hash_chain_integrity` | SHA-256 chain unbroken across all entries |
| `test_prompt_injection_rejected_before_llm` | Injection patterns caught before LLM call |
| `test_complete_trade_loop_e2e` | Full RFQ → negotiate → escrow → compliance |

---

## Project Structure

```
Cadencia-A2A-Platform/
├── backend/                        # FastAPI backend (hexagonal architecture)
│   ├── src/                        # 10 bounded domain contexts
│   │   ├── identity/               # Auth, KYC, Enterprise, Users (3,154 LOC)
│   │   ├── marketplace/            # RFQ, NLP, pgvector Matching (2,142 LOC)
│   │   ├── negotiation/            # AI Agents, NeutralEngine, SSE (5,216 LOC)
│   │   ├── settlement/             # Algorand Escrow, Merkle (4,125 LOC)
│   │   ├── compliance/             # FEMA, GST, Audit Log (1,954 LOC)
│   │   ├── treasury/               # FX, Liquidity, Dashboard (1,302 LOC)
│   │   ├── admin/                  # Admin management (1,040 LOC)
│   │   ├── wallet/                 # Algorand wallet (405 LOC)
│   │   ├── health/                 # Health checks (215 LOC)
│   │   └── shared/                 # Infra: DB, Redis, Events, Logging (2,659 LOC)
│   ├── alembic/versions/           # 12 database migrations
│   ├── scripts/                    # seed_demo_data.py, migrate.py
│   ├── tests/                      # 38 test files (unit/integration/e2e)
│   ├── artifacts/                  # Compiled TEAL smart contract artifacts
│   ├── contracts/                  # Puya (Algorand Python) source
│   ├── infra/                      # Terraform + Grafana dashboards
│   ├── docs/                       # PRD + SRS documentation
│   ├── Dockerfile                  # Multi-stage production image
│   ├── docker-compose.yml          # Local dev stack
│   └── docker-compose.prod.yml     # Production stack (Gunicorn + Caddy)
│
├── frontend/                       # Next.js 15 frontend
│   └── src/
│       ├── app/                    # 15 page routes (App Router)
│       ├── components/             # 62 UI components
│       ├── mocks/                  # MSW handlers (dev only)
│       ├── context/                # Auth + Wallet contexts
│       └── lib/                    # API client, utils
│
├── .github/workflows/              # CI (lint+build) + CD (GHCR+EC2)
├── docker-compose.cloud.yml        # Full-stack cloud deployment
├── aws_deployment_audit.md         # AWS deployment readiness audit
└── deployment_plan.md              # Step-by-step AWS deployment guide
```

---

## Product Roadmap

| Phase | Status | Deliverable |
|-------|--------|-------------|
| Phase 0 — Foundation | Complete | Docker stack, DB migrations, `/health` |
| Phase 1 — Identity & Auth | Complete | JWT, KYC state machine, API keys, rate limiting |
| Phase 2 — Algorand Escrow | Complete | Full escrow lifecycle on localnet |
| Phase 3 — Audit | Complete | Hash-chained AuditLog, Merkle proof endpoint |
| Phase 4 — Negotiation Engine | Complete | LLM agents, NeutralEngine, SSE stream, human override |
| Phase 5 — Marketplace | Complete | RFQ upload, NLP, pgvector matching, session handoff |
| Phase 6 — Compliance | Complete | FEMA + GST records, PDF/CSV export, treasury dashboard |
| Phase 7 — Production Hardening | Complete | Gunicorn + Caddy, Pydantic hardening, Prometheus |
| **AWS Deployment** | In Progress | EC2 launch, GitHub CI/CD, production secrets |

---

## Documentation

| Document | Link |
|----------|------|
| Product Requirements Document (PRD) | [`backend/docs/cadencia-prd.md`](backend/docs/cadencia-prd.md) |
| Software Requirements Specification (SRS) | [`backend/docs/cadencia-srs.md`](backend/docs/cadencia-srs.md) |
| AWS Deployment Audit | [`aws_deployment_audit.md`](aws_deployment_audit.md) |
| Deployment Plan | [`deployment_plan.md`](deployment_plan.md) |

---

## Contributing

1. Fork the repo and create a branch: `git checkout -b feature/your-feature`
2. Run linting: `ruff check src/` and type checking: `mypy src/`
3. Run tests: `pytest tests/unit/ -x`
4. Open a pull request to `main` — CI runs automatically

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built for Indian MSMEs · Powered by AI · Secured by Algorand**

*Cadencia v3.0 · Production Architecture · April 2026*

</div>
