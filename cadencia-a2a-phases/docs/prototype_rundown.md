# Cadencia Platform — Prototype Rundown & Codebase Audit

**Date:** April 2026  
**Purpose:** Comprehensive audit and script for demo showdowns, prototyping presentations, and technical deep-dives.

---

## 1. Platform Executive Summary
**Cadencia** is India's first AI-native, agentic B2B trade marketplace for MSMEs (Micro, Small & Medium Enterprises). It automates the entire B2B procurement cycle—from RFQ creation and AI-driven negotiation, all the way to on-chain settlement using Algorand smart contracts.

### Technical Principles Assured in Code:
- **Hexagonal Architecture (Ports & Adapters):** Strict domain boundaries in the backend. 
- **Event-Driven:** Decoupled domains communicating via in-memory events (`src/shared/infrastructure/events/publisher.py`).
- **Data Security:** Row-Level Security (RLS) enabled in PostgreSQL migrations, ensuring multi-tenant data isolation at the DB engine level.
- **AI-Native:** Embedded LLM capabilities (Groq/Llama3) using `pgvector` for semantic RFQ matching.
- **Web3 Integrations:** Algorand smart contract escrow integration utilizing WalletConnect v2 (Pera Wallet).

---

## 2. Technology Stack Audit

### 🏗️ Backend (FastAPI / `cadencia-a2a-phases/`)
- **Framework:** FastAPI with Python 3.12 (Strict typing enforced via Mypy).
- **Database:** PostgreSQL 16 + `pgvector`.
- **ORM:** SQLAlchemy 2.0 (asyncio) + Alembic for migrations.
- **Caching & Brokers:** Redis (for rate-limiting and session state).
- **Blob Storage:** MinIO (S3-compatible, for Agent Memory vault and document storage).
- **Authentication:** Custom JWT-based Auth (RS256 signed tokens, HttpOnly refresh cookies, Bcrypt for passwords with 72-byte truncation fix).
- **Security:** Strict Content-Security-Policies (CSP), OWASP recommended headers.

### 🎨 Frontend (Next.js / `final-frontend-cadencia/`)
- **Framework:** Next.js 16 (App Router) + React.
- **Styling:** Tailwind CSS + ShadcnUI (Premium dark mode aesthetics with glassmorphism).
- **State Management:** React Query (for server state) + Context API (for Auth).
- **Blockchain Wallet:** WalletConnect v2 (`@walletconnect/sign-client`) strictly limited to Pera Wallet integration.
- **API Client:** Axios with recursive 401 interceptors for automatic token rotation.

### 🚀 DevOps & CI/CD (`.github/workflows/`)
- **CI Pipeline:** `ci.yml` runs Ruff linting, Mypy type-checking, pytest, and frontend builds on every commit.
- **CD Pipeline:** `cd.yml` automates Docker image publishing to GitHub Container Registry (GHCR) upon release tags.
- **Local Dev:** Handled entirely by `docker-compose.yml` (Backend, Frontend, Postgres, Redis, MinIO, Migrate).

---

## 3. The "Demo Showdown" Script (Feature Walkthrough)

*Use this flow when presenting the prototype to stakeholders:*

### Step 1: Onboarding & Identity (The Web2 Feel)
* **Action:** Navigate to `http://localhost:3000/register`. Register a new Enterprise (e.g., "Cadencia Corp", Trade Role: "BUYER") and an Admin User.
* **Behind the Scenes:** 
  - Hits `POST /v1/auth/register`.
  - Passwords hashed using `bcrypt` (Passlib).
  - Returns RS256 JWT tokens. The DB triggers Row-Level Security (RLS) setup for this tenant.

### Step 2: KYC & Compliance (Mocked for Proto)
* **Action:** Show the `/compliance` dashboard.
* **Behind the Scenes:** 
  - Represents the integration layer for external KYC providers (e.g., Signzy/Digio).
  - Documents uploaded here go to MinIO.
  - Required before escrow interactions.

### Step 3: Marketplace Discovery (AI Matching)
* **Action:** Navigate to `/marketplace`. Show how a Buyer can upload an RFQ document or type a request.
* **Behind the Scenes:**
  - Groq LLM parses the natural language RFQ into structured JSON.
  - The backend uses `pgvector` to compute similarities and find matching 'SELLER' capability profiles.
  - Emits an `RFQConfirmed` event to trigger notification handlers.

### Step 4: AI Agent Negotiation (The "A2A" Magic)
* **Action:** Open a session in `/negotiations`. Click "Start AI Negotiation".
* **Behind the Scenes:** 
  - The system instantiates AI agents configured with specific "Negotiation Styles" (Aggressive, Moderate, Conservative).
  - Agents exchange proposals (Price, Quantity, Delivery).
  - State tracked via `SessionStatus` (ACTIVE, AGREED, FAILED, TERMINATED).
  - WebSockets (SSE in backend) push real-time chat updates to the React frontend.

### Step 5: Algorand Escrow & Settlement (Web3 Layer)
* **Action:** Once "AGREED", transition to the `/escrow` dashboard. Click "Link Pera Wallet".
* **Behind the Scenes:**
  - Frontend triggers WalletConnect v2 URI creation.
  - User scans QR with Pera Wallet app.
  - The backend generates a challenge nonce (`POST /v1/wallets/challenge`), user signs it, and backend verifies the Ed25519 signature to link the Algorand Address.
  - Real-world flow: Buyer deposits USDC/ALGO into a multi-sig or TEAL smart contract. Funds are locked. Upon physical delivery signals, funds are released to the Seller.

---

## 4. Current Prototype Status

✅ **What is Working & Production-Ready:**
- **Full Dockerized Stack:** 3.6MB optimized frontend build, healthy backend, redis, minio, and pgvector.
- **TypeScript Types:** 100% matched between Frontend interfaces and Backend Pydantic models.
- **Database Migrations:** Clean Alembic history (001 -> ea191).
- **Authentication:** Robust JWT flow, logout, automatic token refresh, Bcrypt edge cases patched.
- **Wallet Integration Stack:** Deprecated WalletConnect v1 removed; clean WalletConnect v2 implementation.

🚧 **What Needs Real Keys / Production Wiring:**
- **Algorand LocalNet:** The `ALGORAND_ALGOD_ADDRESS` is pointing to `localhost:4001`, requires a running Algokit LocalNet for escrow transactions.
- **Groq AI Keys:** `GROQ_API_KEY` needs to be valid in `.env` for the marketplace LLM parsing to work.
- **KYC/On-Ramp APIs:** Currently using `mock` providers.

---

## 5. Defense / Q&A Guide

**Q: Why use Hexagonal Architecture instead of just typical MVC?**
> **A:** Cadencia is a FinTech/TradeFi platform handling money and smart contracts. We need to isolate business rules (Negotiation, Compliance) from technology choices (FastAPI, SQLAlchemy). This ensures if we change our database or web framework, the core logic remains untouched.

**Q: Why Algorand?**
> **A:** Instant finality, fractional penny transaction fees, and robust Layer-1 smart contracts (TEAL). It’s the only chain suitable for high-volume B2B micro and macro transactions without gas wars. We enforce strictly **Pera Wallet** via WalletConnect v2 for the best user experience.

**Q: How does the AI search work?**
> **A:** We aren't just using full-text search. We embed enterprise capabilities into vector embeddings stored in PostgreSQL using the `pgvector` extension. When a new RFQ comes in, the Groq LLM parses it, we embed the requirements, and perform a nearest-neighbor semantic search (cosine similarity) to find the perfect supplier match.

---
*Generated by Antigravity Agent*
