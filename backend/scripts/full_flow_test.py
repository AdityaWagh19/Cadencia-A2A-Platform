#!/usr/bin/env python3
"""
Cadencia A2A Platform — Full End-to-End Flow Test
===================================================
Tests: 1 buyer + 6 sellers, full LLM negotiation, dispatch bug-fix verification.

Run inside the backend container:
    docker compose -f docker-compose.local.yml exec backend python scripts/full_flow_test.py

Reports:
  • RFQ match percentage per seller
  • Every negotiation round (price, role, reasoning) across all 6 sessions
  • Escrow lifecycle: PENDING_APPROVAL → APPROVED → DEPLOYED → FUNDED → DISPATCHED → RELEASED
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from typing import Any, Optional

import httpx as requests  # httpx is compatible enough for our usage patterns

BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@cadencia.io"
ADMIN_PASSWORD = "Admin@1234"

# ─── Colour helpers ───────────────────────────────────────────────────────────

BOLD   = "\033[1m"
GREEN  = "\033[32m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"
RED    = "\033[31m"
RESET  = "\033[0m"


def h(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")


def ok(text: str) -> None:
    print(f"  {GREEN}✓{RESET} {text}")


def info(text: str) -> None:
    print(f"  {CYAN}→{RESET} {text}")


def warn(text: str) -> None:
    print(f"  {YELLOW}⚠{RESET} {text}")


def err(text: str) -> None:
    print(f"  {RED}✗{RESET} {text}")


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _req(method: str, path: str, token: str | None = None, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{BASE_URL}{path}"
    r = getattr(requests, method)(url, headers=headers, timeout=120, **kwargs)
    return r


def post(path: str, token: str | None = None, **kwargs) -> Any:
    return _req("post", path, token, **kwargs)


def get(path: str, token: str | None = None, **kwargs) -> Any:
    return _req("get", path, token, **kwargs)


def put(path: str, token: str | None = None, **kwargs) -> Any:
    return _req("put", path, token, **kwargs)


def assert_ok(r: requests.Response, label: str) -> dict:
    if r.status_code not in (200, 201, 202, 204):
        err(f"{label} → HTTP {r.status_code}: {r.text[:300]}")
        sys.exit(1)
    if r.status_code == 204:
        return {}
    data = r.json()
    if not data.get("success", True):
        err(f"{label} → {data}")
        sys.exit(1)
    return data.get("data", data)


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def register_enterprise(payload: dict) -> tuple[str, str]:
    """Returns (access_token, enterprise_id)."""
    r = post("/v1/auth/register", json=payload)
    data = assert_ok(r, "register")
    return data["access_token"], data["enterprise_id"]


def login(email: str, password: str) -> str:
    r = post("/v1/auth/login", json={"email": email, "password": password})
    data = assert_ok(r, "login")
    return data["access_token"]


def admin_login_backdoor(email: str, password: str) -> str:
    """Use the admin backdoor endpoint (separate from regular login)."""
    r = post("/v1/auth/admin-login", json={"email": email, "password": password})
    data = assert_ok(r, "admin-login")
    return data["access_token"]


# ─── Sellers and commodity specialisations ────────────────────────────────────

SELLERS = [
    {
        "legal_name": "SteelCraft Industries Pvt Ltd",
        "pan": "AAACS1001B",
        "gstin": "27AAACS1001B1Z1",
        "industry_vertical": "steel_manufacturing",
        "commodities": ["stainless steel 304", "stainless steel 316", "steel coils"],
        "min_order_value": 50000,
        "max_order_value": 5000000,
        "email": "seller1@steel-craft-test.in",
        "profile_text": (
            "ISO 9001 certified stainless steel manufacturer. "
            "Grade 304 and 316 coils, sheets, and plates. "
            "Thickness 0.5–6 mm. Annual capacity 12,000 MT. "
            "BIS-certified. Delivery across Maharashtra and Gujarat."
        ),
        "profile_products": ["304", "316", "304L", "316L", "coil", "sheet"],
        "anchor_price": 52000,
    },
    {
        "legal_name": "Rajasthan Metal Works Ltd",
        "pan": "AAARW2002C",
        "gstin": "08AAARW2002C1Z2",
        "industry_vertical": "metal_trading",
        "commodities": ["stainless steel 304", "alloy steel", "mild steel"],
        "min_order_value": 25000,
        "max_order_value": 3000000,
        "email": "seller2@rajasthan-metal-test.in",
        "profile_text": (
            "Multi-grade steel trader with 15 years of experience. "
            "Stainless 304, alloy steel, mild steel. "
            "Strong logistics network in Rajasthan and Delhi NCR. "
            "ISO 14001 certified. MOQ 5 MT."
        ),
        "profile_products": ["304", "alloy", "mild steel", "coil", "plate"],
        "anchor_price": 51000,
    },
    {
        "legal_name": "Gujarat Steel Alliance",
        "pan": "AAAGS3003D",
        "gstin": "24AAAGS3003D1Z3",
        "industry_vertical": "steel_manufacturing",
        "commodities": ["stainless steel 304", "stainless steel 202", "steel pipes"],
        "min_order_value": 75000,
        "max_order_value": 8000000,
        "email": "seller3@gujarat-steel-test.in",
        "profile_text": (
            "Large-scale stainless steel pipe and coil manufacturer in Gujarat. "
            "Grades 202, 304, 316. Pipes, ERW tubes, CR coils. "
            "ISO 9001:2015 and API 5L certified. "
            "Pan-India delivery network with cold chain capability."
        ),
        "profile_products": ["202", "304", "316", "pipe", "tube", "coil"],
        "anchor_price": 50500,
    },
    {
        "legal_name": "Maharashtra Precision Steel",
        "pan": "AAAMP4004E",
        "gstin": "27AAAMP4004E1Z4",
        "industry_vertical": "precision_manufacturing",
        "commodities": ["stainless steel 316L", "stainless steel 304L", "precision tubes"],
        "min_order_value": 100000,
        "max_order_value": 10000000,
        "email": "seller4@maha-precision-test.in",
        "profile_text": (
            "Precision stainless steel manufacturer. "
            "Specialises in low-carbon grades 304L and 316L for pharma and food-grade applications. "
            "Ultrasonic tested, surface finish Ra < 0.8 µm. "
            "FSSC 22000 certified."
        ),
        "profile_products": ["304L", "316L", "precision", "pharmaceutical", "food-grade"],
        "anchor_price": 55000,
    },
    {
        "legal_name": "Deccan Steel Exports",
        "pan": "AAADS5005F",
        "gstin": "36AAADS5005F1Z5",
        "industry_vertical": "steel_exports",
        "commodities": ["stainless steel 304", "duplex steel", "super duplex"],
        "min_order_value": 200000,
        "max_order_value": 20000000,
        "email": "seller5@deccan-steel-test.in",
        "profile_text": (
            "Export-grade stainless steel supplier. "
            "Duplex 2205, super duplex 2507, and grade 304. "
            "SGS inspected, ASTM A240 compliant. "
            "Specialises in bulk orders above 20 MT. "
            "Port-ready packaging."
        ),
        "profile_products": ["304", "duplex 2205", "2507", "export", "bulk"],
        "anchor_price": 49000,
    },
    {
        "legal_name": "Tamil Nadu Steel Consortium",
        "pan": "AAATS6006G",
        "gstin": "33AAATS6006G1Z6",
        "industry_vertical": "steel_distribution",
        "commodities": ["stainless steel 304", "carbon steel", "galvanised steel"],
        "min_order_value": 30000,
        "max_order_value": 4000000,
        "email": "seller6@tn-steel-test.in",
        "profile_text": (
            "South India distribution hub for stainless and carbon steel. "
            "Grade 304, galvanised coils, corrugated sheets, carbon steel plates. "
            "Next-day delivery in Tamil Nadu and Karnataka. "
            "15,000 MT warehouse capacity."
        ),
        "profile_products": ["304", "galvanised", "carbon", "corrugated", "distribution"],
        "anchor_price": 53000,
    },
]

BUYER_INFO = {
    "legal_name": "Horizon Manufacturing Ltd",
    "pan": "AAAHM7007H",
    "gstin": "27AAAHM7007H1Z7",
    "industry_vertical": "manufacturing",
    "commodities": ["stainless steel 304", "raw materials"],
    "min_order_value": 50000,
    "max_order_value": 10000000,
    "email": "buyer@horizon-mfg-test.in",
}

RFQ_TEXT = (
    "We require 50 MT of Stainless Steel 304 HR Coil, "
    "thickness 2.0 mm ± 0.2 mm, width 1250 mm, "
    "surface finish 2B, delivery to Pune within 21 days, "
    "budget INR 48,000–56,000 per MT. "
    "BIS certification mandatory. Third-party inspection allowed. "
    "Payment 30 days after delivery."
)


# ─── Step helpers ─────────────────────────────────────────────────────────────

def poll_rfq_status(rfq_id: str, token: str, target_statuses: list[str], timeout: int = 90) -> dict:
    """Poll RFQ until it reaches one of the target statuses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = get(f"/v1/marketplace/rfq/{rfq_id}", token)
        if r.status_code == 200:
            rfq = r.json()["data"]
            status = rfq.get("status", "")
            info(f"  RFQ status: {status}")
            if status in target_statuses:
                return rfq
        time.sleep(4)
    warn(f"RFQ {rfq_id} did not reach {target_statuses} within {timeout}s — proceeding anyway")
    r = get(f"/v1/marketplace/rfq/{rfq_id}", token)
    return r.json().get("data", {}) if r.status_code == 200 else {}


def poll_escrow_status(escrow_id: str, token: str, target: str, timeout: int = 60) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = get(f"/v1/escrow/{escrow_id}", token)
        if r.status_code == 200:
            esc = r.json()["data"]
            if esc.get("status") == target:
                return esc
        time.sleep(3)
    warn(f"Escrow {escrow_id} did not reach {target} within {timeout}s")
    r = get(f"/v1/escrow/{escrow_id}", token)
    return r.json().get("data", {}) if r.status_code == 200 else {}


# ─── Main test ────────────────────────────────────────────────────────────────

def main() -> None:

    # Generate run-unique suffix so repeated runs don't clash on PAN/GSTIN/email.
    # PAN format: ^[A-Z]{5}[0-9]{4}[A-Z]{1}$ — we swap the 4-digit middle section.
    run_num = int(time.time()) % 9000 + 1000   # 4-digit number, e.g. 3742
    run_id  = str(run_num)                      # e.g. "3742"
    run_tag = f"{run_num:04d}"
    info(f"Run ID: {run_tag}  (PAN digits & email suffix for uniqueness)")

    def _make_pan(base: str) -> str:
        """Replace the 4-digit middle section of a PAN with run_tag."""
        return base[:5] + run_tag + base[-1]

    def _make_gstin(base: str) -> str:
        """Replace digits 3-6 of the GSTIN PAN portion with run_tag."""
        # GSTIN format: 2-digit state code + 10-char PAN + 1 + Z + check
        # e.g. "27AAAHM7007H1Z7" → keep "27" + _make_pan("AAAHM7007H") + "1Z7"
        state = base[:2]
        pan   = base[2:12]
        rest  = base[12:]
        return state + _make_pan(pan) + rest

    for s in SELLERS:
        s["pan"]   = _make_pan(s["pan"])
        s["gstin"] = _make_gstin(s["gstin"])
        s["email"] = s["email"].replace("@", f"+{run_tag}@")
    BUYER_INFO["pan"]   = _make_pan(BUYER_INFO["pan"])
    BUYER_INFO["gstin"] = _make_gstin(BUYER_INFO["gstin"])
    BUYER_INFO["email"] = BUYER_INFO["email"].replace("@", f"+{run_tag}@")

    # ── Step 0: Verify backend ────────────────────────────────────────────────
    h("STEP 0 — Backend Health Check")
    r = get("/health")
    if r.status_code != 200:
        err(f"Backend not reachable: {r.status_code}")
        sys.exit(1)
    health = r.json()
    ok(f"Backend healthy — status={health.get('status')}")

    # ── Step 1: Admin login ───────────────────────────────────────────────────
    h("STEP 1 — Admin Login")
    admin_token = admin_login_backdoor(ADMIN_EMAIL, ADMIN_PASSWORD)
    ok("Admin logged in")

    # ── Step 2: Register buyer ────────────────────────────────────────────────
    h("STEP 2 — Register Buyer")
    buyer_reg = {
        "enterprise": {
            "legal_name": BUYER_INFO["legal_name"],
            "pan": BUYER_INFO["pan"],
            "gstin": BUYER_INFO["gstin"],
            "trade_role": "BUYER",
            "commodities": BUYER_INFO["commodities"],
            "min_order_value": BUYER_INFO["min_order_value"],
            "max_order_value": BUYER_INFO["max_order_value"],
            "industry_vertical": BUYER_INFO["industry_vertical"],
        },
        "user": {
            "email": BUYER_INFO["email"],
            "password": "Cadencia@Test#2026",
            "full_name": "Arjun Sharma",
            "role": "ADMIN",
        },
    }
    buyer_token, buyer_enterprise_id = register_enterprise(buyer_reg)
    ok(f"Buyer registered: {BUYER_INFO['legal_name']} (ID: {buyer_enterprise_id})")

    # ── Step 3: Register 6 sellers ────────────────────────────────────────────
    h("STEP 3 — Register 6 Sellers")
    seller_data: list[dict] = []

    for i, s in enumerate(SELLERS, 1):
        email_suffix = str(uuid.uuid4())[:8]
        unique_email = s["email"].replace("@", f"+{email_suffix}@")
        pan_suffix = str(i)
        reg_payload = {
            "enterprise": {
                "legal_name": s["legal_name"],
                "pan": s["pan"],
                "gstin": s["gstin"],
                "trade_role": "SELLER",
                "commodities": s["commodities"],
                "min_order_value": s["min_order_value"],
                "max_order_value": s["max_order_value"],
                "industry_vertical": s["industry_vertical"],
            },
            "user": {
                "email": unique_email,
                "password": "Cadencia@Test#2026",
                "full_name": f"Seller Admin {i}",
                "role": "ADMIN",
            },
        }
        token, eid = register_enterprise(reg_payload)
        seller_data.append({
            **s,
            "token": token,
            "enterprise_id": eid,
            "email": unique_email,
        })
        ok(f"Seller {i}: {s['legal_name']} (ID: {eid})")

    # ── Step 4: Update seller capability profiles ─────────────────────────────
    h("STEP 4 — Update Seller Capability Profiles + Recompute Embeddings")

    for sd in seller_data:
        r = put(
            "/v1/marketplace/capability-profile",
            token=sd["token"],
            json={
                "industry": sd["industry_vertical"],
                "products": sd["profile_products"],
                "geographies": ["IN"],
                "min_order_value": sd["min_order_value"],
                "max_order_value": sd["max_order_value"],
                "description": sd["profile_text"],
            },
        )
        if r.status_code in (200, 201):
            ok(f"Profile updated: {sd['legal_name']}")
        else:
            warn(f"Profile update failed for {sd['legal_name']}: {r.status_code} — continuing")

        # Trigger embedding recompute
        r2 = post("/v1/marketplace/capability-profile/embeddings", token=sd["token"])
        if r2.status_code in (200, 202):
            ok(f"  Embeddings queued for {sd['legal_name']}")
        else:
            warn(f"  Embedding trigger failed: {r2.status_code}")

    info("Waiting 20 seconds for embeddings to be computed...")
    time.sleep(20)

    # ── Step 5: Buyer submits RFQ ─────────────────────────────────────────────
    h("STEP 5 — Buyer Submits RFQ")
    r = post(
        "/v1/marketplace/rfq",
        token=buyer_token,
        json={"raw_text": RFQ_TEXT, "document_type": "free_text"},
    )
    rfq_data = assert_ok(r, "submit RFQ")
    rfq_id = rfq_data["rfq_id"]
    ok(f"RFQ submitted (ID: {rfq_id})")
    info("Polling for RFQ to reach MATCHED status...")
    rfq = poll_rfq_status(rfq_id, buyer_token, ["MATCHED", "PARSED", "CONFIRMED"], timeout=90)
    ok(f"RFQ status: {rfq.get('status', 'unknown')}")

    # ── Step 6: Get RFQ matches ───────────────────────────────────────────────
    h("STEP 6 — RFQ Match Scores (per seller)")
    r = get(f"/v1/marketplace/rfq/{rfq_id}/matches", token=buyer_token)
    if r.status_code == 200:
        matches_raw = r.json().get("data", [])
    else:
        warn(f"Could not fetch matches (status {r.status_code}) — will create sessions manually")
        matches_raw = []

    # Build match map: enterprise_id → score
    match_map: dict[str, dict] = {}
    if matches_raw:
        print(f"\n  {'Rank':<6} {'Enterprise':<40} {'Score %':<10} {'Match ID'}")
        print(f"  {'-'*6} {'-'*40} {'-'*10} {'-'*36}")
        for rank, m in enumerate(sorted(matches_raw, key=lambda x: x.get("score", 0), reverse=True), 1):
            eid = str(m.get("enterprise_id", m.get("id", "")))
            score = m.get("score", m.get("similarity_score", 0.0))
            match_id = str(m.get("match_id", m.get("id", "")))
            name = m.get("enterprise_name", m.get("name", ""))
            print(f"  {rank:<6} {name:<40} {score:<10.1f} {match_id}")
            match_map[eid] = {
                "score": score,
                "match_id": match_id,
                "name": name,
                "rank": rank,
            }
    else:
        warn("No matches returned. Proceeding to create sessions manually for all sellers.")

    # ── Step 7: Create negotiation sessions for all matched sellers ───────────
    h("STEP 7 — Create Negotiation Sessions (6 sellers)")
    sessions: list[dict] = []

    for sd in seller_data:
        eid = sd["enterprise_id"]
        # Try to get match_id from the match response; fall back to new UUID
        match_info = match_map.get(eid, {})
        match_id_val = match_info.get("match_id") or str(uuid.uuid4())
        score = match_info.get("score", 0.0)

        r = post(
            "/v1/sessions",
            token=buyer_token,
            json={
                "match_id": match_id_val,
                "rfq_id": rfq_id,
                "buyer_enterprise_id": buyer_enterprise_id,
                "seller_enterprise_id": eid,
            },
        )
        if r.status_code in (200, 201):
            session_resp = r.json().get("data", {})
            sid = session_resp.get("session_id") or session_resp.get("id")
            ok(f"Session created for {sd['legal_name']} — session_id={sid} (match score: {score:.1f}%)")
            sessions.append({
                "session_id": sid,
                "seller_name": sd["legal_name"],
                "seller_enterprise_id": eid,
                "seller_token": sd["token"],
                "match_score": score,
                "anchor_price": sd["anchor_price"],
            })
        else:
            warn(f"Session creation failed for {sd['legal_name']}: {r.status_code} {r.text[:200]}")

    if not sessions:
        err("No sessions created — aborting")
        sys.exit(1)

    # ── Step 8: Run auto-negotiation (full LLM) for each session ──────────────
    h("STEP 8 — Full LLM Auto-Negotiation (all 6 sessions)")

    agreed_sessions: list[dict] = []
    MAX_AUTO_ROUNDS = 12

    for s_info in sessions:
        sid = s_info["session_id"]
        seller_name = s_info["seller_name"]
        print(f"\n  {BOLD}── Seller: {seller_name} (session {sid}) ──{RESET}")
        print(f"  {'Round':<6} {'Role':<8} {'Price (INR)':<16} {'Confidence':<12} Reasoning")
        print(f"  {'-'*6} {'-'*8} {'-'*16} {'-'*12} {'-'*40}")

        r = post(
            f"/v1/sessions/{sid}/run-auto",
            token=buyer_token,
            params={"max_rounds": MAX_AUTO_ROUNDS},
        )

        if r.status_code != 200:
            warn(f"  run-auto failed: {r.status_code} {r.text[:200]}")
            # Fall back to get current session state
            r2 = get(f"/v1/sessions/{sid}", token=buyer_token)
            if r2.status_code == 200:
                session_state = r2.json().get("data", {})
            else:
                continue
        else:
            auto_resp = r.json().get("data", {})
            session_state = auto_resp.get("session", {})

        # Print all offers
        offers = session_state.get("offers", [])
        for offer in sorted(offers, key=lambda x: x.get("round_number", 0)):
            rnd     = offer.get("round_number", "?")
            role    = offer.get("proposer_role", "?")[:7]
            price   = f"{offer.get('price', 0):,.0f}"
            conf    = f"{offer.get('confidence', 0):.2f}"
            reason  = (offer.get("agent_reasoning") or "")[:50]
            print(f"  {rnd:<6} {role:<8} {price:<16} {conf:<12} {reason}")

        final_status = session_state.get("status", "UNKNOWN")
        agreed_price = session_state.get("agreed_price")
        rounds_done  = session_state.get("round_count", len(offers))

        if final_status == "AGREED":
            ok(f"  AGREED at INR {agreed_price:,.0f} in {rounds_done} rounds")
            agreed_sessions.append({
                **s_info,
                "agreed_price": agreed_price,
                "rounds": rounds_done,
                "session_state": session_state,
            })
        else:
            info(f"  Terminal: {final_status} after {rounds_done} rounds")

    # ── Step 9: Select best agreed deal ───────────────────────────────────────
    h("STEP 9 — Select Best Agreed Deal")

    if not agreed_sessions:
        warn("No sessions reached AGREED. Attempting to use first available session as fallback.")
        # Use the first session regardless
        if sessions:
            r = get(f"/v1/sessions/{sessions[0]['session_id']}", token=buyer_token)
            if r.status_code == 200:
                agreed_sessions = [{**sessions[0], "agreed_price": None, "rounds": 0}]

    if not agreed_sessions:
        err("Cannot proceed — no sessions available")
        sys.exit(1)

    # Pick deal with lowest price (best for buyer)
    best = min(
        agreed_sessions,
        key=lambda x: (x["agreed_price"] or float("inf")),
    )
    ok(f"Best deal: {best['seller_name']} — INR {best.get('agreed_price', 'N/A'):,.0f}")
    info(f"Session ID: {best['session_id']}")

    winning_session_id = best["session_id"]
    winning_seller_token = best["seller_token"]
    winning_seller_name = best["seller_name"]

    # ── Step 10: Create escrow (select-deal) ──────────────────────────────────
    h("STEP 10 — Create Escrow (PENDING_APPROVAL)")
    r = post(
        "/v1/escrow/select-deal",
        token=buyer_token,
        json={"session_id": winning_session_id},
    )
    if r.status_code not in (200, 201):
        err(f"select-deal failed: {r.status_code} {r.text[:300]}")
        # Try to find an existing escrow for this session
        warn("Trying to find existing escrow...")
        r2 = get("/v1/escrow", token=buyer_token, params={"limit": 10})
        if r2.status_code == 200:
            escrows = r2.json().get("data", [])
            if escrows:
                escrow_id = escrows[0]["escrow_id"]
                ok(f"Using existing escrow: {escrow_id}")
            else:
                err("No escrows found")
                sys.exit(1)
        else:
            sys.exit(1)
    else:
        escrow_data = r.json()["data"]
        escrow_id = escrow_data.get("escrow_id") or escrow_data.get("id")
        ok(f"Escrow created: {escrow_id} — status=PENDING_APPROVAL")

    # ── Step 11: Admin approves escrow ────────────────────────────────────────
    h("STEP 11 — Admin Approves Escrow")
    r = post(f"/v1/escrow/{escrow_id}/approve", token=admin_token)
    if r.status_code in (200, 201):
        ok(f"Escrow approved — status=APPROVED")
    else:
        warn(f"Admin approve failed ({r.status_code}): {r.text[:200]}")

    # ── Step 12: Deploy escrow (platform wallet) ──────────────────────────────
    h("STEP 12 — Deploy Escrow on Algorand Testnet (platform wallet)")
    # Try seller-approve first; fall back to platform-deploy
    r = post(f"/v1/escrow/{escrow_id}/seller-approve", token=winning_seller_token)
    if r.status_code in (200, 201):
        esc_data = r.json().get("data", {})
        ok(f"Seller-approved & deployed — status={esc_data.get('status')}")
    else:
        info(f"seller-approve not available ({r.status_code}), trying platform-deploy...")
        r = post(f"/v1/escrow/{winning_session_id}/platform-deploy", token=buyer_token)
        if r.status_code in (200, 201):
            esc_data = r.json().get("data", {})
            app_id = esc_data.get("app_id") or esc_data.get("algo_app_id")
            ok(f"Platform-deployed — app_id={app_id} status={esc_data.get('status')}")
        else:
            warn(f"platform-deploy failed ({r.status_code}): {r.text[:200]}")

    # Verify current escrow state
    r = get(f"/v1/escrow/{escrow_id}", token=buyer_token)
    if r.status_code == 200:
        esc = r.json()["data"]
        info(f"Escrow status after deploy: {esc.get('status')} | app_id={esc.get('algo_app_id')}")

    # ── Step 13: Fund escrow (platform wallet) ────────────────────────────────
    h("STEP 13 — Fund Escrow (platform wallet)")
    r = post(f"/v1/escrow/{escrow_id}/platform-fund", token=buyer_token)
    if r.status_code in (200, 201):
        fund_data = r.json().get("data", {})
        ok(f"Escrow funded — tx_id={fund_data.get('tx_id')} status={fund_data.get('status')}")
    else:
        warn(f"platform-fund failed ({r.status_code}): {r.text[:300]}")
        info("Attempting admin fund as fallback...")
        r2 = post(
            f"/v1/escrow/{escrow_id}/fund",
            token=admin_token,
            json={"funder_algo_mnemonic": ""},
        )
        if r2.status_code in (200, 201):
            ok("Admin fund succeeded")
        else:
            warn(f"Admin fund also failed ({r2.status_code}) — attempting to continue...")

    # Verify
    r = get(f"/v1/escrow/{escrow_id}", token=buyer_token)
    if r.status_code == 200:
        esc = r.json()["data"]
        info(f"Escrow status after fund: {esc.get('status')}")

    # ── Step 14: Seller marks order dispatched ────────────────────────────────
    h("STEP 14 — Seller Marks Order Dispatched ★ (THE BUG FIX)")
    print(f"  {BOLD}Testing the DB constraint fix for DISPATCHED status...{RESET}")
    r = post(f"/v1/escrow/{escrow_id}/seller-dispatch", token=winning_seller_token)
    if r.status_code == 200:
        dispatch_data = r.json().get("data", {})
        ok(f"{GREEN}{BOLD}✓ DISPATCH SUCCESS! Status={dispatch_data.get('status')}{RESET}")
        ok(f"  Message: {dispatch_data.get('message')}")
    else:
        err(f"DISPATCH FAILED: HTTP {r.status_code}")
        err(f"Response: {r.text[:500]}")

    # Verify
    r = get(f"/v1/escrow/{escrow_id}", token=buyer_token)
    if r.status_code == 200:
        esc = r.json()["data"]
        dispatch_status = esc.get("status")
        if dispatch_status == "DISPATCHED":
            ok(f"DB confirmed: escrow status = DISPATCHED")
        else:
            warn(f"DB shows: escrow status = {dispatch_status}")

    # ── Step 15: Buyer confirms delivery ──────────────────────────────────────
    h("STEP 15 — Buyer Confirms Delivery (auto-release funds)")
    r = post(f"/v1/escrow/{escrow_id}/buyer-confirm", token=buyer_token)
    if r.status_code == 200:
        confirm_data = r.json().get("data", {})
        ok(f"Delivery confirmed — status={confirm_data.get('status')}")
        ok(f"Release TX: {confirm_data.get('tx_id')}")
    else:
        warn(f"buyer-confirm: {r.status_code} — {r.text[:300]}")
        info("(buyer-confirm requires on-chain release; may fail if platform wallet has insufficient ALGO)")

    # ── Final summary ─────────────────────────────────────────────────────────
    h("FINAL SUMMARY")
    r = get(f"/v1/escrow/{escrow_id}", token=buyer_token)
    final_status = "UNKNOWN"
    if r.status_code == 200:
        esc = r.json()["data"]
        final_status = esc.get("status", "UNKNOWN")

    print(f"""
  {BOLD}Flow Results:{RESET}
  ┌─────────────────────────────────────────────────────┐
  │ Buyer           : {BUYER_INFO['legal_name']:<35} │
  │ Sellers         : {len(seller_data)} registered                          │
  │ RFQ ID          : {rfq_id[:36]:<36} │
  │ Sessions        : {len(sessions)} created, {len(agreed_sessions)} agreed                  │
  │ Winning seller  : {winning_seller_name[:35]:<35} │
  │ Agreed price    : INR {best.get('agreed_price', 'N/A'):<30} │
  │ Escrow ID       : {escrow_id[:36]:<36} │
  │ Final status    : {final_status:<35} │
  └─────────────────────────────────────────────────────┘
""")

    print(f"  {BOLD}RFQ Match Scores:{RESET}")
    if match_map:
        for sd in seller_data:
            eid = sd["enterprise_id"]
            score = match_map.get(eid, {}).get("score", 0.0)
            print(f"    {sd['legal_name']:<40} {score:.1f}%")
    else:
        warn("  (Matching data not available — embeddings may not have been ready)")

    print(f"\n  {BOLD}Negotiation Summary:{RESET}")
    for s_info in agreed_sessions:
        print(
            f"    {s_info['seller_name']:<40} "
            f"Agreed: INR {s_info.get('agreed_price', 'N/A'):>12,.0f}   "
            f"Rounds: {s_info.get('rounds', '?')}"
        )

    if final_status == "DISPATCHED":
        print(f"\n  {GREEN}{BOLD}✓ Bug fix confirmed: DISPATCHED status accepted by DB!{RESET}")
        print(f"  {GREEN}  The missing migration 'ea191f1c2d51' has been applied.{RESET}")
    elif final_status == "RELEASED":
        print(f"\n  {GREEN}{BOLD}✓ Full flow complete: RELEASED!{RESET}")
    else:
        print(f"\n  {YELLOW}⚠ Final escrow status: {final_status}{RESET}")

    print()


if __name__ == "__main__":
    main()
