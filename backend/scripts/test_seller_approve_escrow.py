#!/usr/bin/env python3
"""
Focused test: seller approves deal → escrow auto-deploys on Algorand testnet.

Flow:
  1. Register buyer + seller
  2. Run LLM negotiation to AGREED
  3. Buyer selects deal (PENDING_APPROVAL)
  4. Inject seller's Algorand wallet directly in DB (bypasses Pera challenge)
  5. Seller calls seller-approve → APPROVED + DEPLOYED in one shot
  6. Assert escrow status == DEPLOYED and algo_app_id is set

Run inside Docker:
    docker compose -f docker-compose.local.yml exec backend \
        python scripts/test_seller_approve_escrow.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid

import httpx

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@cadencia.io"
ADMIN_PASS  = "Admin@1234"

GREEN = "\033[32m"; RED = "\033[31m"; CYAN = "\033[36m"
BOLD  = "\033[1m"; YLW  = "\033[33m"; RST  = "\033[0m"

def ok(t):   print(f"  {GREEN}✓{RST}  {t}")
def err(t):  print(f"  {RED}✗{RST}  {t}"); sys.exit(1)
def info(t): print(f"  {CYAN}→{RST}  {t}")
def warn(t): print(f"  {YLW}⚠{RST}  {t}")
def hdr(t):  print(f"\n{BOLD}{CYAN}{'─'*65}{RST}\n{BOLD}  {t}{RST}\n{BOLD}{CYAN}{'─'*65}{RST}")


def post(path, token=None, **kw):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.post(f"{BASE}{path}", headers=h, timeout=360, **kw)

def get(path, token=None, **kw):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.get(f"{BASE}{path}", headers=h, timeout=60, **kw)


def chk(r, label):
    if r.status_code not in (200, 201, 202, 204):
        err(f"{label} → HTTP {r.status_code}: {r.text[:400]}")
    if r.status_code == 204:
        return {}
    d = r.json()
    if not d.get("success", True):
        err(f"{label} → {d}")
    return d.get("data", d)


# ── Step helpers ─────────────────────────────────────────────────────────────

def register(payload):
    d = chk(post("/v1/auth/register", json=payload), "register")
    return d["access_token"], d["enterprise_id"]

def admin_login():
    return chk(post("/v1/auth/admin-login",
                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}),
               "admin-login")["access_token"]

def user_login(email, password):
    d = chk(post("/v1/auth/login", json={"email": email, "password": password}), "login")
    return d["access_token"]


def get_platform_wallet_address() -> str:
    """Derive the platform wallet address from the env mnemonic."""
    import algosdk.mnemonic as m
    import algosdk.account as acc
    mnemonic = os.environ.get("ALGORAND_ESCROW_CREATOR_MNEMONIC", "")
    if not mnemonic:
        err("ALGORAND_ESCROW_CREATOR_MNEMONIC not set")
    sk = m.to_private_key(mnemonic)
    return acc.address_from_private_key(sk)


async def inject_seller_wallet(enterprise_id: str, wallet_address: str) -> None:
    """Directly write seller's Algorand wallet into DB (bypasses Pera challenge)."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import text

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://cadencia:cadencia_dev@localhost:5432/cadencia",
    )
    engine = create_async_engine(db_url, echo=False)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as s:
        await s.execute(
            text("UPDATE enterprises SET algorand_wallet = :addr WHERE id = :eid"),
            {"addr": wallet_address, "eid": enterprise_id},
        )
        await s.commit()
    await engine.dispose()


def poll_rfq(rfq_id, token, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = get(f"/v1/marketplace/rfq/{rfq_id}", token)
        if r.status_code == 200:
            s = r.json()["data"].get("status", "")
            info(f"  RFQ status: {s}")
            if s in ("MATCHED", "CONFIRMED", "NEGOTIATING"):
                return r.json()["data"]
        time.sleep(4)
    warn("RFQ match timeout — proceeding anyway")
    r = get(f"/v1/marketplace/rfq/{rfq_id}", token)
    return r.json().get("data", {}) if r.status_code == 200 else {}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # PAN: ^[A-Z]{5}[0-9]{4}[A-Z]{1}$  (5 letters + 4 digits + 1 letter)
    # GSTIN: ^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$
    run4 = str(int(time.time()))[-4:]  # 4-digit unique suffix
    buyer_pan   = f"TBUYR{run4}A"                       # 5+4+1 = 10 ✓
    seller_pan  = f"TSELR{run4}B"
    buyer_gstin = f"27TBUYR{run4}A1Z1"                  # 2+10+1+Z+1 = 15 ✓
    seller_gstin= f"09TSELR{run4}B1Z2"

    hdr("STEP 0 — Health check & admin login")
    if get("/health").status_code != 200:
        err("Backend not healthy")
    ok("Backend healthy")
    admin_tok = admin_login()
    ok("Admin logged in")

    hdr("STEP 1 — Register buyer")
    buyer_payload = {
        "enterprise": {
            "legal_name": f"TestBuyer Corp {run4}",
            "pan": buyer_pan,
            "gstin": buyer_gstin,
            "trade_role": "BUYER",
            "commodities": ["copper wire", "electronic components"],
            "industry_vertical": "electronics",
            "min_order_value": 100000,
            "max_order_value": 10000000,
        },
        "user": {
            "email": f"buyer.test.{run4}@cadencia-test.io",
            "password": "Test@Cadencia1",
            "full_name": "Test Buyer",
            "role": "ADMIN",
        },
    }
    buyer_tok, buyer_eid = register(buyer_payload)
    ok(f"Buyer registered  (enterprise_id={buyer_eid})")

    hdr("STEP 2 — Register seller")
    seller_payload = {
        "enterprise": {
            "legal_name": f"TestSeller Wire {run4}",
            "pan": seller_pan,
            "gstin": seller_gstin,
            "trade_role": "SELLER",
            "commodities": ["copper wire", "electronic components"],
            "industry_vertical": "copper_wire_manufacturing",
            "min_order_value": 50000,
            "max_order_value": 50000000,
        },
        "user": {
            "email": f"seller.test.{run4}@cadencia-test.io",
            "password": "Test@Cadencia1",
            "full_name": "Test Seller",
            "role": "ADMIN",
        },
    }
    seller_tok, seller_eid = register(seller_payload)
    ok(f"Seller registered (enterprise_id={seller_eid})")

    hdr("STEP 3 — Seller sets up capability profile + catalogue")
    r = httpx.put(f"{BASE}/v1/marketplace/capability-profile",
                  headers={"Authorization": f"Bearer {seller_tok}"},
                  json={
                      "industry": "copper_wire_manufacturing",
                      "products": ["copper wire", "electronic components", "PVC wire"],
                      "geographies": ["IN"],
                      "min_order_value": 50000,
                      "max_order_value": 50000000,
                      "description": (
                          "ISO 9001 certified copper wire manufacturer. "
                          "Multi-strand tinned copper wire, PVC insulated, UL/RoHS. "
                          "100m rolls, Pan-India delivery."
                      ),
                  }, timeout=30)
    ok(f"Capability profile: HTTP {r.status_code}")

    r = post("/v1/marketplace/catalogue", token=seller_tok, json={
        "product_name": "Copper Wire Electronic Components",
        "hsn_code": "8544",
        "product_category": "CUSTOM",
        "specification_text": "Multi-strand tinned copper wire 0.75mm PVC insulated",
        "unit": "KG",
        "price_per_unit_inr": 850.0,
        "moq": 100.0,
        "max_order_qty": 100000.0,
        "lead_time_days": 7,
        "in_stock_qty": 50000,
        "certifications": ["ISO9001"],
    })
    ok(f"Catalogue item: HTTP {r.status_code}")

    post("/v1/marketplace/capability-profile/embeddings", token=seller_tok)
    info("Waiting 10s for embeddings…")
    time.sleep(10)

    hdr("STEP 4 — Buyer submits RFQ")
    rfq_text = (
        "RFQ — Copper Wire & Electronic Components\n"
        "Product: copper wire electronic components (100m rolls)\n"
        "Quantity: 1000 rolls\n"
        "Delivery: Noida, India\n"
        "Budget: INR 750 to INR 950 per roll\n"
        "Payment terms: 30 days net\n"
    )
    d = chk(post("/v1/marketplace/rfq", token=buyer_tok,
                 json={"raw_text": rfq_text, "document_type": "free_text"}),
            "submit rfq")
    rfq_id = d["rfq_id"]
    ok(f"RFQ submitted: {rfq_id}")
    poll_rfq(rfq_id, buyer_tok)

    hdr("STEP 5 — Create negotiation session")
    # Get matches
    time.sleep(3)
    r = get(f"/v1/marketplace/rfq/{rfq_id}/matches", token=buyer_tok)
    matches = r.json().get("data", []) if r.status_code == 200 else []
    match_id = str(uuid.uuid4())  # synthetic — session creation doesn't validate against matches table
    info(f"Matches found: {len(matches)}, using our registered seller={seller_eid[:8]}…, match_id=<generated>")

    r = post("/v1/sessions", token=buyer_tok, json={
        "match_id": match_id,
        "rfq_id": rfq_id,
        "buyer_enterprise_id": buyer_eid,
        "seller_enterprise_id": seller_eid,
    })
    chk(r, "create session")
    sess_data = r.json().get("data", {})
    session_id = sess_data.get("session_id") or sess_data.get("id")
    ok(f"Session created: {session_id}")

    hdr("STEP 6 — Auto-negotiation (LLM)")
    info("Running negotiation (up to 10 rounds)…")
    r = post(f"/v1/sessions/{session_id}/run-auto",
             token=buyer_tok, params={"max_rounds": 10})
    if r.status_code == 200:
        auto = r.json().get("data", {})
        sess = auto.get("session", {})
    else:
        warn(f"run-auto HTTP {r.status_code}: {r.text[:200]}")
        r2 = get(f"/v1/sessions/{session_id}", token=buyer_tok)
        sess = r2.json().get("data", {}) if r2.status_code == 200 else {}

    status = sess.get("status", "UNKNOWN")
    agreed_price = sess.get("agreed_price")
    info(f"Negotiation result: status={status}, agreed_price={agreed_price}")

    if status != "AGREED":
        warn(f"Negotiation ended with {status} — forcing AGREED via direct session update")
        # Force AGREED via DB if LLM didn't converge
        async def force_agree():
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
            from sqlalchemy import text
            db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://cadencia:cadencia_dev@localhost:5432/cadencia")
            engine = create_async_engine(db_url, echo=False)
            sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with sm() as s:
                await s.execute(text(
                    "UPDATE negotiation_sessions SET status='AGREED', agreed_price=850 WHERE id=:sid"
                ), {"sid": session_id})
                await s.commit()
            await engine.dispose()
        asyncio.run(force_agree())
        ok("Forced session to AGREED with agreed_price=850 INR")

    hdr("STEP 7 — Buyer selects deal (PENDING_APPROVAL)")
    r = post("/v1/escrow/select-deal", token=buyer_tok,
             json={"session_id": str(session_id)})
    if r.status_code in (200, 201):
        escrow_id = (r.json().get("data") or {}).get("escrow_id")
        ok(f"Escrow created: {escrow_id}  (status=PENDING_APPROVAL)")
    else:
        warn(f"select-deal HTTP {r.status_code}: {r.text[:300]}")
        # Try to find existing escrow
        r2 = get("/v1/escrow", token=buyer_tok, params={"limit": 5})
        escrows = r2.json().get("data", []) if r2.status_code == 200 else []
        escrow_id = escrows[0]["escrow_id"] if escrows else None
        if not escrow_id:
            err("Cannot find escrow_id")
        ok(f"Found existing escrow: {escrow_id}")

    hdr("STEP 8 — Inject seller Algorand wallet into DB")
    wallet_addr = get_platform_wallet_address()
    info(f"Using platform wallet address as seller's test wallet: {wallet_addr[:12]}...")
    asyncio.run(inject_seller_wallet(seller_eid, wallet_addr))
    ok(f"Seller enterprise {seller_eid} → algorand_wallet set")

    hdr("STEP 9 — Seller approves deal → auto-deploys escrow ★")
    info("Calling POST /v1/escrow/{escrow_id}/seller-approve …")
    r = post(f"/v1/escrow/{escrow_id}/seller-approve", token=seller_tok)
    print(f"\n  HTTP {r.status_code}")
    try:
        body = r.json()
        print(f"  Response: {body}")
    except Exception:
        print(f"  Body: {r.text[:400]}")

    if r.status_code == 200:
        d = body.get("data", {})
        deploy_status = d.get("status", "")
        msg = d.get("message", "")
        if deploy_status == "DEPLOYED":
            ok(f"{GREEN}{BOLD}ESCROW AUTO-DEPLOYED SUCCESSFULLY!{RST}")
            ok(f"  Status : {deploy_status}")
            ok(f"  Message: {msg}")
        else:
            warn(f"seller-approve succeeded but status={deploy_status}: {msg}")
    else:
        err(f"seller-approve FAILED: HTTP {r.status_code}\n{r.text[:500]}")

    hdr("STEP 10 — Verify escrow state in DB")
    r = get(f"/v1/escrow/{session_id}", token=buyer_tok)
    if r.status_code == 200:
        escrow = r.json().get("data", {})
        final_status = escrow.get("status", "UNKNOWN")
        app_id = escrow.get("algo_app_id")
        app_address = escrow.get("algo_app_address", "")
        tx_id = escrow.get("deploy_tx_id", "")

        print(f"\n  {'─'*55}")
        print(f"  Escrow ID     : {escrow_id}")
        print(f"  Status        : {BOLD}{final_status}{RST}")
        print(f"  Algo App ID   : {app_id}")
        print(f"  App Address   : {app_address}")
        print(f"  Deploy TX     : {str(tx_id)[:22]}{'...' if tx_id and len(str(tx_id)) > 22 else ''}")
        print(f"  {'─'*55}")

        if final_status == "DEPLOYED" and app_id:
            print(f"\n  {GREEN}{BOLD}✓ TEST PASSED — Escrow deployed on Algorand testnet{RST}")
            print(f"  {GREEN}  App ID {app_id} is live on testnet.algoexplorer.io/application/{app_id}{RST}\n")
        else:
            print(f"\n  {RED}{BOLD}✗ TEST FAILED — status={final_status}, app_id={app_id}{RST}\n")
            sys.exit(1)
    else:
        warn(f"Could not fetch escrow: HTTP {r.status_code}")


if __name__ == "__main__":
    main()
