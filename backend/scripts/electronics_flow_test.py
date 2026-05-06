#!/usr/bin/env python3
"""
Cadencia A2A Platform — Electronics Industry Full Flow Test
============================================================
Industry   : Electronics / Copper Wire & Components
Buyer      : Quantum PCB Tech Pvt Ltd (Noida, India)
RFQ        : 10,000 × 100m copper wire rolls — budget INR 800-1200/roll

Keyword-score engineering (clean DB + keyword fallback):
  Composite = 0.50 × commodity_score + 0.30 × geo_score + 0.20 × value_score
  geo_score = 0.5  ("in" substring found in "noida, india")
  value_score = 0   (per-unit budget 800-1200 vs seller total-order ranges 100k+, no overlap)

  Seller 1  Exactron Wire Systems      commodity=1.0 (exact)      → 65%
  Seller 2  ConnektCu Cables Ltd       commodity=0.8 (substring)  → 55%
  Seller 3  CopperKing Refinery        commodity=0.7 (related-term via copper→copper cathode) → 50%
  Seller 4  DigiParts Electronic Hub   commodity=0.5 (2-word overlap: electronic+components)  → 40%
  Seller 5  WireHarness Solutions      commodity=0.4 (1-word overlap: wire)                   → 35%
  Seller 6  SteelTech Precision        commodity=0.0 (no overlap)  → NO MATCH (filtered)

ZOPA analysis (buyer ceiling = INR 900, max they'll pay):
  Exactron  catalogue 680 → floor 748  → ZOPA ✓ (152 INR range)
  ConnektCu catalogue 720 → floor 792  → ZOPA ✓ (108 INR range)
  CopperKing catalogue 760 → floor 836 → ZOPA ✓ (64 INR range)
  DigiParts  catalogue 780 → floor 858 → ZOPA ✓ (42 INR range, tight)
  WireHarness catalogue 650 → floor 715 → ZOPA ✓ (185 INR range)
  SteelTech  catalogue 2500 → floor 2750 → NO ZOPA ✓ (correctly walks away)

Run:
    docker cp backend/scripts/electronics_flow_test.py cadencia-a2a-platform-test-backend-1:/app/scripts/electronics_flow_test.py
    docker compose -f docker-compose.local.yml exec backend python scripts/electronics_flow_test.py
"""

from __future__ import annotations

import sys
import time
import uuid

import httpx

BASE_URL    = "http://localhost:8000"
ADMIN_EMAIL = "admin@cadencia.io"
ADMIN_PASSWORD = "Admin@1234"

BOLD  = "\033[1m"; GREEN = "\033[32m"; CYAN  = "\033[36m"
YLW   = "\033[33m"; RED   = "\033[31m"; RST   = "\033[0m"

def h(t):    print(f"\n{BOLD}{CYAN}{'='*72}{RST}\n{BOLD}{CYAN}  {t}{RST}\n{BOLD}{CYAN}{'='*72}{RST}")
def ok(t):   print(f"  {GREEN}✓{RST} {t}")
def info(t): print(f"  {CYAN}→{RST} {t}")
def warn(t): print(f"  {YLW}⚠{RST} {t}")
def err(t):  print(f"  {RED}✗{RST} {t}")

def _r(method, path, token=None, **kw):
    hd = kw.pop("headers", {})
    if token: hd["Authorization"] = f"Bearer {token}"
    timeout = kw.pop("timeout", 360)  # 360s for LLM-heavy requests
    return getattr(httpx, method)(f"{BASE_URL}{path}", headers=hd, timeout=timeout, **kw)

def post(p, token=None, **kw): return _r("post", p, token, **kw)
def get(p,  token=None, **kw): return _r("get",  p, token, **kw)
def put(p,  token=None, **kw): return _r("put",  p, token, **kw)

def chk(r, label):
    if r.status_code not in (200, 201, 202, 204):
        err(f"{label} → {r.status_code}: {r.text[:400]}"); sys.exit(1)
    if r.status_code == 204: return {}
    d = r.json()
    if not d.get("success", True): err(f"{label} → {d}"); sys.exit(1)
    return d.get("data", d)

def admin_login():
    return chk(post("/v1/auth/admin-login",
                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}),
               "admin-login")["access_token"]

def register(p):
    d = chk(post("/v1/auth/register", json=p), "register")
    return d["access_token"], d["enterprise_id"]

# ─── RFQ ─────────────────────────────────────────────────────────────────────
RFQ_TEXT = (
    "RFQ — Copper Wire & Electronic Components\n"
    "Product: copper wire electronic components (100m rolls, multi-strand, tinned)\n"
    "Quantity: 10,000 rolls\n"
    "Specifications: 0.75mm conductor, PVC insulated, UL listed, RoHS compliant\n"
    "Delivery location: Noida, India (Sector 62 Electronics Hub)\n"
    "Delivery: 30 days from purchase order\n"
    "Budget: INR 800 to INR 1200 per roll\n"
    "Payment terms: 45 days net from delivery\n"
    "Approved supplier list preferred. ISO 9001 / ISI certified supplier mandatory.\n"
)

# ─── Buyer ───────────────────────────────────────────────────────────────────
BUYER = {
    "legal_name": "Quantum PCB Tech Pvt Ltd",
    "pan": "AAAQP1001A",
    "gstin": "09AAAQP1001A1Z1",
    "email": "purchase@quantum-pcb-test.in",
    "trade_role": "BUYER",
    "commodities": ["copper wire", "electronic components", "PCB materials"],
    "industry_vertical": "electronics_manufacturing",
    "min_order_value": 5000000,
    "max_order_value": 100000000,
    "address": {
        "address_type": "FACILITY",
        "address_line1": "A-14, Sector 62, NOIDA",
        "city": "Noida",
        "state": "UP",
        "pincode": "201309",
    },
}

# ─── Sellers ─────────────────────────────────────────────────────────────────
# RFQ product (lowercase): "copper wire electronic components (100m rolls, multi-strand, tinned)"
# product_words (len>2):    copper, wire, electronic, components, 100m, rolls, multi-strand, tinned
# Key words for matching:   copper, wire, electronic, components

SELLERS = [
    # ── 1: EXACT (commodity_score=1.0 → composite 65%) ──────────────────────
    {
        "legal_name": "Exactron Wire Systems Ltd",
        "pan": "AAAEW2001B",
        "gstin": "09AAAEW2001B1Z2",
        "email": "sales@exactron-wire-test.in",
        "industry_vertical": "copper_wire_manufacturing",
        "commodities": ["copper wire electronic components", "PVC insulated wire", "tinned copper wire"],
        # "copper wire electronic components" IS in the RFQ product → EXACT match → 1.0
        "min_order_value": 500000,
        "max_order_value": 50000000,
        "catalogue_price": 680.0,
        "profile_text": (
            "ISO 9001 & ISI certified copper wire manufacturer. "
            "Multi-strand tinned copper wire in PVC insulation, 0.5–6mm conductor. "
            "100m rolls, 500m drums. UL, RoHS, BIS approved. "
            "Annual capacity 5 million metres. Pan-India delivery."
        ),
        "profile_products": ["copper wire", "tinned copper", "pvc wire", "electronic wire", "multi-strand"],
        "expected_score": "65%",
        "expected_commodity": 1.0,
    },
    # ── 2: SUBSTRING (commodity_score=0.8 → composite 55%) ──────────────────
    {
        "legal_name": "ConnektCu Cables Pvt Ltd",
        "pan": "AAACC3002C",
        "gstin": "27AAACC3002C1Z3",
        "email": "info@connectcu-test.in",
        "industry_vertical": "cable_manufacturing",
        "commodities": ["copper wire", "coaxial cable", "flexible cable"],
        # "copper wire" IS a substring of "copper wire electronic components" → 0.8
        "min_order_value": 1000000,
        "max_order_value": 30000000,
        "catalogue_price": 720.0,
        "profile_text": (
            "Multi-product cable manufacturer. Copper wire, coaxial cables, "
            "flexible cables, fire-resistant cables. "
            "ISI marked, IEC 60227 compliant. Supplying to EPC contractors, "
            "OEM electronics manufacturers, and panel builders."
        ),
        "profile_products": ["copper wire", "coaxial cable", "flexible cable", "armoured cable"],
        "expected_score": "55%",
        "expected_commodity": 0.8,
    },
    # ── 3: RELATED-TERM (commodity_score=0.7 → composite 50%) ───────────────
    {
        "legal_name": "CopperKing Refinery Ltd",
        "pan": "AAACR4003D",
        "gstin": "24AAACR4003D1Z4",
        "email": "sales@copperking-test.in",
        "industry_vertical": "copper_refining",
        "commodities": ["copper cathode", "copper rod", "copper ingot"],
        # product_word "copper" → _RELATED_TERMS["copper"]["copper cathode"]=0.9 → capped 0.7
        "min_order_value": 5000000,
        "max_order_value": 200000000,
        "catalogue_price": 760.0,
        "profile_text": (
            "Primary copper refinery. Grade-A copper cathode, continuous cast rods, ingots. "
            "LME-certified purity 99.99%. "
            "Supplies to wire-drawing mills, cable manufacturers, and foundries. "
            "NOT a wire manufacturer — we are the upstream copper supply chain."
        ),
        "profile_products": ["copper cathode", "copper rod", "copper ingot", "refined copper"],
        "expected_score": "50%",
        "expected_commodity": 0.7,
    },
    # ── 4: 2-WORD OVERLAP (commodity_score=0.5 → composite 40%) ─────────────
    {
        "legal_name": "DigiParts Electronic Hub",
        "pan": "AAADP5004E",
        "gstin": "29AAADP5004E1Z5",
        "email": "orders@digiparts-test.in",
        "industry_vertical": "electronic_components_distribution",
        "commodities": ["SMD resistors", "ceramic capacitors", "electronic passive components"],
        # "electronic" AND "components" both in seller_text → overlap_count=2 → 0.5
        "min_order_value": 100000,
        "max_order_value": 10000000,
        "catalogue_price": 780.0,
        "profile_text": (
            "Authorised distributor of passive electronic components. "
            "SMD resistors, ceramic capacitors, inductors, ferrite beads. "
            "Brands: Murata, TDK, Vishay, Yageo. "
            "NOT a wire or cable supplier — electronic components only."
        ),
        "profile_products": ["resistors", "capacitors", "inductors", "electronic components", "smd"],
        "expected_score": "40%",
        "expected_commodity": 0.5,
    },
    # ── 5: 1-WORD OVERLAP (commodity_score=0.4 → composite 35%) ─────────────
    {
        "legal_name": "WireHarness Solutions Ltd",
        "pan": "AAAWH6005F",
        "gstin": "33AAAWH6005F1Z6",
        "email": "sales@wireharness-test.in",
        "industry_vertical": "automotive_wiring",
        "commodities": ["wire harness", "cable assemblies", "automotive harness"],
        # "wire" in "wire harness" → overlap_count=1 → 0.3+0.1=0.4
        "min_order_value": 200000,
        "max_order_value": 5000000,
        "catalogue_price": 650.0,
        "profile_text": (
            "Custom wire harness and cable assembly manufacturer for automotive OEMs. "
            "Harnesses for 2-wheelers, 4-wheelers, commercial vehicles. "
            "IATF 16949 certified. NOT a raw copper wire supplier — "
            "we produce finished harness assemblies."
        ),
        "profile_products": ["wire harness", "cable assembly", "automotive wiring", "connector"],
        "expected_score": "35%",
        "expected_commodity": 0.4,
    },
    # ── 6: NO MATCH (commodity_score=0.0 → filtered) ─────────────────────────
    {
        "legal_name": "SteelTech Precision Mfg Ltd",
        "pan": "AAAST7006G",
        "gstin": "27AAAST7006G1Z7",
        "email": "info@steeltech-precision-test.in",
        "industry_vertical": "precision_steel_fabrication",
        "commodities": ["precision steel tubes", "CNC machined castings", "forged flanges"],
        # No keyword overlap with copper/wire/electronic/components → commodity_score=0 → filtered
        "min_order_value": 1000000,
        "max_order_value": 50000000,
        "catalogue_price": 2500.0,
        "profile_text": (
            "Precision steel fabrication. Seamless steel tubes, CNC machined castings, "
            "forged flanges for oil & gas, power generation. "
            "NO copper wire or electronic components. "
            "Steel and ferrous metals only."
        ),
        "profile_products": ["steel tubes", "cnc machining", "forged parts", "stainless steel"],
        "expected_score": "NO MATCH",
        "expected_commodity": 0.0,
    },
]


def poll_rfq(rfq_id, token, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = get(f"/v1/marketplace/rfq/{rfq_id}", token)
        if r.status_code == 200:
            d = r.json()["data"]
            s = d.get("status", "")
            info(f"  RFQ status: {s}")
            if s in ("MATCHED", "CONFIRMED", "NEGOTIATING"): return d
        time.sleep(5)
    warn("Timeout waiting for RFQ to match")
    r = get(f"/v1/marketplace/rfq/{rfq_id}", token)
    return r.json().get("data", {}) if r.status_code == 200 else {}


def main():
    # ── Run tag ───────────────────────────────────────────────────────────────
    run_num = int(time.time()) % 9000 + 1000
    run_tag = f"{run_num:04d}"

    def _pan(b):   return b[:5] + run_tag + b[-1]
    def _gstin(b): return b[:2] + _pan(b[2:12]) + b[12:]
    def _email(e): return e.replace("@", f"+{run_tag}@")

    BUYER["pan"]   = _pan(BUYER["pan"])
    BUYER["gstin"] = _gstin(BUYER["gstin"])
    BUYER["email"] = _email(BUYER["email"])
    for s in SELLERS:
        s["pan"]   = _pan(s["pan"])
        s["gstin"] = _gstin(s["gstin"])
        s["email"] = _email(s["email"])

    info(f"Run tag: {run_tag}")

    # ── STEP 0: Health + Admin ────────────────────────────────────────────────
    h("STEP 0 — Health Check & Admin Login")
    if get("/health").status_code != 200: err("Backend down"); sys.exit(1)
    ok("Backend healthy")
    admin_token = admin_login(); ok("Admin logged in")

    # ── STEP 0b: Full DB purge (test isolation) ───────────────────────────────
    h("STEP 0b — Purge All Previous Test Data (test isolation)")
    try:
        import os, asyncio
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy import text as sat

        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            warn("DATABASE_URL not set — skipping purge")
        else:
            engine = create_async_engine(db_url, echo=False)
            sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Delete in correct FK dependency order
            PURGE_STMTS = [
                # Leaf tables first (children before parents)
                "UPDATE escrow_contracts SET algo_app_id = NULL WHERE status IN ('RELEASED','REFUNDED')",
                "DELETE FROM settlements",
                "DELETE FROM offers",
                "DELETE FROM opponent_profiles",
                "DELETE FROM llm_call_logs",
                "DELETE FROM audit_entries",
                "DELETE FROM fema_records",
                "DELETE FROM gst_records",
                "DELETE FROM export_jobs",
                "DELETE FROM escrow_contracts",
                "DELETE FROM negotiation_sessions",
                "DELETE FROM matches",
                "DELETE FROM rfqs",
                "DELETE FROM agent_profiles",
                "DELETE FROM capability_profiles",
                "DELETE FROM seller_capacity_profiles",
                "DELETE FROM catalogue_items",
                "DELETE FROM agent_memory",
                "DELETE FROM broadcasts",
                "DELETE FROM profiles",
                "DELETE FROM api_keys",
                "DELETE FROM addresses",
                "DELETE FROM users",
                "DELETE FROM enterprises",
            ]

            async def _purge():
                async with sm() as session:
                    for stmt in PURGE_STMTS:
                        try:
                            r = await session.execute(sat(stmt))
                            if r.rowcount and r.rowcount > 0:
                                info(f"  {stmt[:60]} → {r.rowcount} rows")
                        except Exception as ex:
                            warn(f"  {stmt[:50]} → {ex}")
                    await session.commit()
                await engine.dispose()

            asyncio.run(_purge())
            ok("DB purged — starting with clean slate")
    except Exception as exc:
        warn(f"Purge error (non-fatal): {exc}")

    # ── STEP 1: Register buyer ────────────────────────────────────────────────
    h("STEP 1 — Register Buyer  (Quantum PCB Tech — Noida, India)")
    buyer_token, buyer_eid = register({
        "enterprise": {
            "legal_name": BUYER["legal_name"],
            "pan": BUYER["pan"], "gstin": BUYER["gstin"],
            "trade_role": "BUYER",
            "commodities": BUYER["commodities"],
            "min_order_value": BUYER["min_order_value"],
            "max_order_value": BUYER["max_order_value"],
            "industry_vertical": BUYER["industry_vertical"],
            "address": BUYER["address"],
        },
        "user": {"email": BUYER["email"], "password": "Cadencia@Test#2026",
                 "full_name": "Vikram Nair", "role": "ADMIN"},
    })
    ok(f"Buyer: {BUYER['legal_name']}  (ID: {buyer_eid})")

    # ── STEP 2: Register 6 sellers ────────────────────────────────────────────
    h("STEP 2 — Register 6 Sellers  (Electronics spectrum)")
    seller_data: list[dict] = []
    for i, s in enumerate(SELLERS, 1):
        token, eid = register({
            "enterprise": {
                "legal_name": s["legal_name"],
                "pan": s["pan"], "gstin": s["gstin"],
                "trade_role": "SELLER",
                "commodities": s["commodities"],
                "min_order_value": s["min_order_value"],
                "max_order_value": s["max_order_value"],
                "industry_vertical": s["industry_vertical"],
                "address": {
                    "address_type": "FACILITY",
                    "address_line1": "Industrial Area Phase 2",
                    "city": "Noida",
                    "state": "UP",
                    "pincode": "201305",
                },
                "payment_terms_accepted": ["30 days", "45 days"],
                "test_certificate_available": True,
            },
            "user": {"email": s["email"], "password": "Cadencia@Test#2026",
                     "full_name": f"Sales Manager {i}", "role": "ADMIN"},
        })
        seller_data.append({**s, "token": token, "enterprise_id": eid})
        ok(f"Seller {i}: {s['legal_name']:<44}  [expected: {s['expected_score']}] (ID: {eid})")

    # ── STEP 3: Profiles, Catalogues, Capacity ────────────────────────────────
    h("STEP 3 — Capability Profiles + Catalogues + Capacity")
    for sd in seller_data:
        # Capability profile
        put("/v1/marketplace/capability-profile", token=sd["token"], json={
            "industry": sd["industry_vertical"],
            "products": sd["profile_products"],
            "geographies": ["IN"],
            "min_order_value": sd["min_order_value"],
            "max_order_value": sd["max_order_value"],
            "description": sd["profile_text"],
        })
        # Trigger embedding recompute
        post("/v1/marketplace/capability-profile/embeddings", token=sd["token"])

        # Catalogue item (price anchor for ZOPA)
        r = post("/v1/marketplace/catalogue", token=sd["token"], json={
            "product_name": sd["commodities"][0][:60],
            "hsn_code": "8544",
            "product_category": "CUSTOM",
            "specification_text": sd["profile_text"][:200],
            "unit": "KG",
            "price_per_unit_inr": sd["catalogue_price"],
            "moq": 100.0,
            "max_order_qty": 100000.0,
            "lead_time_days": 7,
            "in_stock_qty": 50000,
            "certifications": ["ISO9001", "ISI"],
        })
        cat_ok = r.status_code in (200, 201)

        # Capacity profile
        put("/v1/marketplace/capacity-profile", token=sd["token"], json={
            "monthly_production_capacity_mt": 200.0,
            "current_utilization_pct": 60,
            "num_production_lines": 3,
            "shift_pattern": "DOUBLE_SHIFT",
            "avg_dispatch_days": 5,
            "max_delivery_radius_km": 2000,
            "has_own_transport": True,
            "preferred_transport_modes": ["ROAD"],
            "ex_works_available": True,
        })
        ok(f"  {sd['legal_name']:<44}  catalogue ₹{sd['catalogue_price']}/roll {'✓' if cat_ok else '✗'}")

    info("Waiting 25 seconds for embeddings to compute...")
    time.sleep(25)

    # ── STEP 4: Buyer submits RFQ ─────────────────────────────────────────────
    h("STEP 4 — Buyer Submits RFQ  (Copper Wire Electronic Components)")
    print(f"\n{BOLD}  RFQ:{RST}")
    for ln in RFQ_TEXT.split("\n")[:7]: print(f"    {ln}")
    print()
    r = post("/v1/marketplace/rfq", token=buyer_token,
             json={"raw_text": RFQ_TEXT, "document_type": "free_text"})
    rfq_id = chk(r, "submit rfq")["rfq_id"]
    ok(f"RFQ submitted: {rfq_id}")
    rfq = poll_rfq(rfq_id, buyer_token)
    ok(f"RFQ status: {rfq.get('status')}")

    pf = rfq.get("parsed_fields") or {}
    info(f"  Parsed: product='{pf.get('product','')}' | qty={pf.get('quantity','')} | geo={pf.get('geography','')}")
    info(f"  Budget: {pf.get('budget_min','?')} – {pf.get('budget_max','?')} INR/roll")

    # ── STEP 5: Match Scores ──────────────────────────────────────────────────
    h("STEP 5 — RFQ Match Scores  (keyword composite 0-100)")
    r = get(f"/v1/marketplace/rfq/{rfq_id}/matches", token=buyer_token)
    matches_raw = r.json().get("data", []) if r.status_code == 200 else []

    match_map: dict[str, dict] = {}
    matched_seller_eids = set()
    if matches_raw:
        print(f"\n  {'Rank':<5} {'Seller':<44} {'Score':>8}  {'Commodity Score'}")
        print(f"  {'-'*5} {'-'*44} {'-'*8}  {'-'*20}")
        for m in sorted(matches_raw, key=lambda x: x.get("score", 0), reverse=True):
            eid   = str(m.get("enterprise_id", ""))
            score = m.get("score", 0.0)
            rank  = m.get("rank", "?")
            name  = m.get("enterprise_name", m.get("name", eid[:8]))
            mid   = str(m.get("match_id", m.get("id", "")))
            expected = next((s["expected_score"] for s in seller_data if s["enterprise_id"]==eid), "")
            bar_n = int(score * 0.5)
            bar = f"{GREEN}{'█'*bar_n}{RST}"
            print(f"  {rank:<5} {name:<44} {score:>7.1f}%  {bar}")
            match_map[eid] = {"score": score, "match_id": mid, "name": name, "rank": rank}
            matched_seller_eids.add(eid)
    else:
        warn("No matches returned from API")

    # Print full expected vs actual table
    print(f"\n  {BOLD}Expected vs Actual Score per Seller:{RST}")
    print(f"  {'Seller':<44} {'Commodity':<12} {'Expected':>10} {'Actual':>10}")
    print(f"  {'-'*44} {'-'*12} {'-'*10} {'-'*10}")
    for sd in seller_data:
        eid = sd["enterprise_id"]
        actual = match_map.get(eid, {}).get("score")
        actual_s = f"{actual:>9.1f}%" if actual is not None else "  NO MATCH"
        print(f"  {sd['legal_name']:<44} {sd['expected_commodity']:<12} {sd['expected_score']:>10} {actual_s}")

    # ── STEP 6: Create Sessions ───────────────────────────────────────────────
    h("STEP 6 — Create Negotiation Sessions  (all 6 sellers)")
    sessions: list[dict] = []
    for sd in seller_data:
        eid = sd["enterprise_id"]
        mid = match_map.get(eid, {}).get("match_id") or str(uuid.uuid4())
        sc  = match_map.get(eid, {}).get("score", 0.0)
        r = post("/v1/sessions", token=buyer_token, json={
            "match_id": mid,
            "rfq_id": rfq_id,
            "buyer_enterprise_id": buyer_eid,
            "seller_enterprise_id": eid,
        })
        if r.status_code in (200, 201):
            sd_resp = r.json().get("data", {}) or {}
            sid = sd_resp.get("session_id") or sd_resp.get("id")
            ok(f"  {sd['legal_name']:<44}  score={sc:.1f}%  sid={sid}")
            sessions.append({**sd, "session_id": sid, "match_score": sc})
        else:
            warn(f"  Session failed: {sd['legal_name']} — {r.status_code}")

    # ── STEP 7: Full LLM Auto-Negotiation ─────────────────────────────────────
    h("STEP 7 — Full LLM Auto-Negotiation  (Groq llama-3.3-70b-versatile, 2048 tokens)")
    MAX_ROUNDS = 10
    negotiation_results: list[dict] = []
    agreed_sessions: list[dict] = []

    for idx, s_info in enumerate(sessions, 1):
        sid  = s_info["session_id"]
        name = s_info["legal_name"]
        sc   = s_info["match_score"]
        exp  = s_info["expected_score"]

        print(f"\n  {BOLD}{'─'*68}{RST}")
        print(f"  {BOLD}Seller {idx}: {name}{RST}")
        print(f"  Match score: {sc:.1f}%  (expected {exp})  |  Catalogue: ₹{s_info['catalogue_price']}/roll")
        print(f"  {BOLD}{'─'*68}{RST}")
        print(f"  {'Rnd':<5} {'Role':<8} {'INR/roll':>12}  {'Reasoning'}")
        print(f"  {'-'*5} {'-'*8} {'-'*12}  {'-'*52}")

        try:
            r = post(f"/v1/sessions/{sid}/run-auto",
                     token=buyer_token,
                     params={"max_rounds": MAX_ROUNDS})
            if r.status_code != 200:
                warn(f"  run-auto failed: {r.status_code} {r.text[:200]}")
                r2 = get(f"/v1/sessions/{sid}", token=buyer_token)
                sess = r2.json().get("data", {}) if r2.status_code == 200 else {}
            else:
                auto = r.json().get("data", {})
                sess = auto.get("session", {})
        except Exception as exc:
            warn(f"  run-auto exception: {exc}")
            r2 = get(f"/v1/sessions/{sid}", token=buyer_token)
            sess = r2.json().get("data", {}) if r2.status_code == 200 else {}

        offers = sorted(sess.get("offers", []), key=lambda x: x.get("round_number", 0))
        has_stub = any("Stub agent" in (o.get("agent_reasoning") or "") for o in offers)

        for off in offers:
            rnd  = off.get("round_number", "?")
            role = off.get("proposer_role", "?")[:7]
            price = off.get("price", 0)
            conf  = off.get("confidence")
            reason = (off.get("agent_reasoning") or "")[:52]
            stub_flag = " [STUB]" if "Stub agent" in (off.get("agent_reasoning") or "") else ""
            print(f"  {rnd:<5} {role:<8} {price:>12,.0f}  {reason}{stub_flag}")

        status = sess.get("status", "UNKNOWN")
        agreed_price = sess.get("agreed_price")
        rounds = sess.get("round_count", len(offers))

        if status == "AGREED":
            print(f"\n  {GREEN}{BOLD}  ✓ AGREED at INR {agreed_price:,.0f}/roll in {rounds} rounds{RST}")
            agreed_sessions.append({**s_info, "agreed_price": agreed_price, "rounds": rounds, "has_stub": has_stub})
        elif status == "WALK_AWAY":
            print(f"\n  {YLW}  ✗ WALK_AWAY after {rounds} round(s) — no ZOPA{RST}")
        else:
            print(f"\n  {CYAN}  → Terminal: {status} after {rounds} rounds{RST}")

        negotiation_results.append({
            "seller": name,
            "match_score": sc,
            "expected_score": exp,
            "catalogue_price": s_info["catalogue_price"],
            "status": status,
            "agreed_price": agreed_price,
            "rounds": rounds,
            "has_stub": has_stub,
            "offers": offers,
        })

        # Respectful delay between sessions to avoid Groq rate limits
        if idx < len(sessions):
            info(f"  (pausing 4 seconds before next session...)")
            time.sleep(4)

    # ── STEP 8: Select Best Deal ───────────────────────────────────────────────
    h("STEP 8 — Select Best Deal  (lowest agreed price)")
    if not agreed_sessions:
        warn("No sessions reached AGREED. Using first available as fallback.")
        agreed_sessions = [{**sessions[0], "agreed_price": None, "rounds": 0}] if sessions else []
    if not agreed_sessions:
        err("No sessions available"); sys.exit(1)

    best = min(agreed_sessions, key=lambda x: (x.get("agreed_price") or float("inf")))
    ok(f"Winner: {best['legal_name']}  at INR {best.get('agreed_price','N/A')}/roll  ({best.get('rounds','?')} rounds)")
    winning_sid  = best["session_id"]
    winning_tok  = best["token"]
    winning_name = best["legal_name"]

    # ── STEP 9: Escrow Lifecycle ───────────────────────────────────────────────
    h("STEP 9 — Create Escrow  (PENDING_APPROVAL)")
    r = post("/v1/escrow/select-deal", token=buyer_token, json={"session_id": winning_sid})
    if r.status_code in (200, 201):
        escrow_id = (r.json().get("data") or {}).get("escrow_id") or (r.json().get("data") or {}).get("id")
        ok(f"Escrow created: {escrow_id}")
    else:
        warn(f"select-deal {r.status_code}: {r.text[:200]}")
        r2 = get("/v1/escrow", token=buyer_token, params={"limit": 3})
        escrows = r2.json().get("data", []) if r2.status_code == 200 else []
        escrow_id = escrows[0]["escrow_id"] if escrows else None
        if not escrow_id: err("No escrow found"); sys.exit(1)

    h("STEP 10 — Admin Approves Escrow")
    r = post(f"/v1/escrow/{escrow_id}/approve", token=admin_token)
    ok(f"Approved (HTTP {r.status_code})")

    h("STEP 11 — Platform Deploy on Algorand Testnet")
    # Clear any stale released app_ids first
    try:
        import os, asyncio
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy import text as sat
        db_url = os.environ.get("DATABASE_URL", "")
        if db_url:
            engine = create_async_engine(db_url, echo=False)
            sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async def _clear_app_ids():
                async with sm() as s:
                    await s.execute(sat("UPDATE escrow_contracts SET algo_app_id = NULL WHERE status IN ('RELEASED','REFUNDED')"))
                    await s.commit()
                await engine.dispose()
            asyncio.run(_clear_app_ids())
    except Exception as ex:
        warn(f"app_id clear skipped: {ex}")

    r = post(f"/v1/escrow/{winning_sid}/platform-deploy", token=buyer_token)
    if r.status_code in (200, 201):
        d = r.json()["data"]
        ok(f"Deployed — App ID: {d.get('app_id')}  TX: {str(d.get('tx_id',''))[:20]}...")
    else:
        warn(f"platform-deploy {r.status_code}: {r.text[:200]}")

    h("STEP 12 — Platform Fund")
    r = post(f"/v1/escrow/{escrow_id}/platform-fund", token=buyer_token)
    if r.status_code in (200, 201):
        d = r.json()["data"]
        ok(f"Funded — TX: {str(d.get('tx_id',''))[:22]}...  Status: {d.get('status')}")
    else:
        warn(f"platform-fund {r.status_code}: {r.text[:200]}")

    h("STEP 13 — Seller Dispatch  ★  (Bug-fix re-verification)")
    r = post(f"/v1/escrow/{escrow_id}/seller-dispatch", token=winning_tok)
    if r.status_code == 200:
        d = r.json()["data"]
        ok(f"{GREEN}{BOLD}DISPATCH SUCCESS — Status: {d.get('status')}{RST}")
        ok(f"  {d.get('message')}")
    else:
        err(f"DISPATCH FAILED: {r.status_code} — {r.text[:400]}")

    h("STEP 14 — Buyer Confirms Delivery  (auto-release funds)")
    r = post(f"/v1/escrow/{escrow_id}/buyer-confirm", token=buyer_token)
    if r.status_code == 200:
        d = r.json()["data"]
        ok(f"RELEASED — TX: {str(d.get('tx_id',''))[:22]}...")
    else:
        warn(f"buyer-confirm {r.status_code}: {r.text[:200]}")

    # ── Final Report ─────────────────────────────────────────────────────────
    h("FINAL REPORT — Electronics Industry Test")

    print(f"""
  {BOLD}Industry : Electronics / Copper Wire & Components{RST}
  {BOLD}Buyer    : {BUYER['legal_name']} — Noida, India{RST}
  {BOLD}RFQ      : 10,000 × 100m copper wire rolls, budget INR 800-1200/roll{RST}

  {BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RST}
  {BOLD}RFQ MATCH SCORES  (keyword composite, 0–100%){RST}
  {BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RST}

  {'Seller':<44} {'Commodity':>12} {'Expected':>10} {'Actual':>10}  Score bar""")

    for nr in negotiation_results:
        eid = next((s["enterprise_id"] for s in seller_data if s["legal_name"]==nr["seller"]), "")
        actual = match_map.get(eid, {}).get("score")
        exp = nr["expected_score"]
        cd = next((s["expected_commodity"] for s in SELLERS if s["legal_name"].startswith(nr["seller"][:10])), "?")
        if actual is not None:
            bar_n = int(actual * 0.5)
            bar = f"{GREEN}{'█'*bar_n}{RST}"
            actual_s = f"{actual:>9.1f}%"
        else:
            bar = f"{RED}NO MATCH{RST}"
            actual_s = f"{'—':>10}"
        print(f"  {nr['seller']:<44} {str(cd):>12} {exp:>10} {actual_s}  {bar}")

    print(f"""
  {BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RST}
  {BOLD}NEGOTIATION RESULTS  (full LLM, Groq llama-3.3-70b-versatile){RST}
  {BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RST}

  {'Seller':<44} {'Cat. Price':>11} {'Rounds':>7} {'Status':<12} {'Agreed Price':>14}  {'LLM'}""")

    for nr in negotiation_results:
        ap = f"INR {nr['agreed_price']:>8,.0f}/roll" if nr["agreed_price"] else "—"
        status_col = f"{GREEN}{nr['status']:<12}{RST}" if nr["status"]=="AGREED" else f"{YLW}{nr['status']:<12}{RST}"
        llm_col = f"{YLW}+STUB{RST}" if nr["has_stub"] else f"{GREEN}FULL LLM{RST}"
        print(f"  {nr['seller']:<44} ₹{nr['catalogue_price']:>8,.0f}  {nr['rounds']:>7}  {status_col}  {ap:>14}  {llm_col}")

    print(f"""
  {BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RST}
  {BOLD}DETAILED NEGOTIATION ROUNDS{RST}
  {BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RST}""")

    for nr in negotiation_results:
        print(f"\n  {BOLD}{nr['seller']}  [match: {nr['match_score']:.1f}% | cat: ₹{nr['catalogue_price']:.0f}/roll | status: {nr['status']}]{RST}")
        if nr["offers"]:
            print(f"  {'Rnd':<5} {'Role':<8} {'Price':>12} {'Conf':>6}  Reasoning")
            for off in nr["offers"]:
                rnd    = off.get("round_number", "?")
                role   = off.get("proposer_role", "?")[:8]
                price  = off.get("price", 0)
                conf   = f"{off.get('confidence', 0):.2f}" if off.get("confidence") else "  —"
                reason = (off.get("agent_reasoning") or "")[:60]
                stub_f = f" {YLW}[STUB]{RST}" if "Stub agent" in reason else ""
                print(f"  {rnd:<5} {role:<8} {price:>12,.0f} {conf:>6}  {reason}{stub_f}")
        if nr["status"] == "AGREED":
            print(f"  {GREEN}  → AGREED at INR {nr['agreed_price']:,.0f}/roll{RST}")
        elif nr["status"] == "WALK_AWAY":
            print(f"  {YLW}  → WALK_AWAY (no ZOPA — seller floor above buyer ceiling){RST}")

    ap_w = best.get('agreed_price','N/A')
    print(f"""
  {BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RST}
  {BOLD}ESCROW LIFECYCLE{RST}
  {BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RST}

  Winning seller : {winning_name}
  Agreed price   : INR {ap_w}/roll
  Escrow ID      : {escrow_id}
  Lifecycle      : PENDING_APPROVAL → APPROVED → DEPLOYED → FUNDED → DISPATCHED → RELEASED
  Dispatch fix   : {GREEN}CONFIRMED ✓{RST}
""")


if __name__ == "__main__":
    main()
