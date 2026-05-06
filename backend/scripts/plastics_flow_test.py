#!/usr/bin/env python3
"""
Cadencia A2A Platform — Plastics / Polymer Packaging Flow Test
==============================================================
Industry   : Plastics & Polymer Packaging  (not steel, not civil)
Buyer RFQ  : 5,000 kg polymer film stretch wrap — Surat, Gujarat, 21-day window

Keyword-score engineering (Groq has no embedding API → keyword fallback active):

  Composite = 0.50 × commodity + 0.30 × geo + 0.20 × value
  (geo ≈ 0.5 partial "IN" match; value varies by seller min/max vs RFQ budget)

  Seller 1 — commodity 1.00 (exact match)       → ~75 %
  Seller 2 — commodity 0.80 (substring match)   → ~65 %
  Seller 3 — commodity 0.70 (related-term polymer→plastic) → ~60 %
  Seller 4 — commodity 0.50 (2 words overlap)   → ~50 %
  Seller 5 — commodity 0.30 (1 word overlap)    → ~40 %
  Seller 6 — commodity 0.00 (no overlap)        → NO MATCH (filtered)

Run:
    docker cp backend/scripts/plastics_flow_test.py cadencia-a2a-platform-test-backend-1:/app/scripts/plastics_flow_test.py
    docker compose -f docker-compose.local.yml exec backend python scripts/plastics_flow_test.py
"""

from __future__ import annotations

import sys
import time
import uuid

import httpx as requests

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
    return getattr(requests, method)(f"{BASE_URL}{path}", headers=hd, timeout=120, **kw)

def post(p, token=None, **kw): return _r("post", p, token, **kw)
def get(p,  token=None, **kw): return _r("get",  p, token, **kw)
def put(p,  token=None, **kw): return _r("put",  p, token, **kw)

def chk(r, label):
    if r.status_code not in (200, 201, 202, 204):
        err(f"{label} → {r.status_code}: {r.text[:300]}"); sys.exit(1)
    if r.status_code == 204: return {}
    d = r.json()
    if not d.get("success", True): err(f"{label} → {d}"); sys.exit(1)
    return d.get("data", d)

def admin_login(): return chk(post("/v1/auth/admin-login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}), "admin-login")["access_token"]
def register(p):  d = chk(post("/v1/auth/register", json=p), "register"); return d["access_token"], d["enterprise_id"]

# ─── RFQ text ──────────────────────────────────────────────────────────────────
# Deliberately structured:
#  • product: "polymer film stretch wrap" → keyword words: polymer, film, stretch, wrap
#  • no per-unit budget (prevents bad unit-mismatch comparison with seller min/max)
#  • delivery_window included in plain English (NLP may or may not extract days)

RFQ_TEXT = (
    "RFQ — Polymer Packaging Film\n"
    "Product: polymer film stretch wrap (LLDPE, machine-grade)\n"
    "Quantity: 5,000 kg\n"
    "Specifications: thickness 20 micron, 500 mm width, elongation > 200%, clear/transparent\n"
    "Delivery: Surat, Gujarat — 21 days from order\n"
    "Budget: INR 90 to INR 200 per kg\n"
    "Payment: 30 days net\n"
    "Certifications: food-safe grade preferred\n"
)

# ─── Buyer ────────────────────────────────────────────────────────────────────

BUYER = {
    "legal_name": "PackWell Consumer Goods Pvt Ltd",
    "pan": "AAAPW1001A",
    "gstin": "24AAAPW1001A1Z1",
    "email": "procurement@packwell-test.in",
    "trade_role": "BUYER",
    "commodities": ["polymer film", "packaging material"],
    "industry_vertical": "consumer_packaging",
    "min_order_value": 100000,
    "max_order_value": 5000000,
    "address": {
        "address_type": "FACILITY",
        "address_line1": "Plot 45, GIDC Sachin Industrial Area",
        "city": "Surat",
        "state": "GJ",
        "pincode": "394230",
    },
}

# ─── Sellers (commodity scores engineered for clear variation) ────────────────
# Keyword-matchmaker commodity_score tiers:
#   1.0 = rfq_product IS a seller commodity  (exact)
#   0.8 = rfq_product contains/is contained in a seller commodity  (substring)
#   0.7 = related-term via _RELATED_TERMS["polymer"]["plastic"] = 0.8 → cap 0.7
#   0.5 = 2 product words in seller commodity text  (0.3 + 0.1×2)
#   0.3 = 1 product word in seller commodity text   (0.3 + 0.1×1)
#   0.0 = no overlap  →  filtered out entirely

SELLERS = [
    # ─── Seller 1: EXACT match  (commodity_score = 1.0 → composite ~75%) ──────
    {
        "legal_name": "FlexPack Polymer Films Ltd",
        "pan": "AAAFP2001B",
        "gstin": "24AAAFP2001B1Z2",
        "email": "sales@flexpack-test.in",
        "industry_vertical": "polymer_packaging",
        "commodities": ["polymer film stretch wrap", "LLDPE stretch film", "hand wrap film"],
        # "polymer film stretch wrap" is an EXACT copy of rfq_product → score 1.0
        "min_order_value": 100000,
        "max_order_value": 5000000,
        "profile_text": (
            "Specialist manufacturer of polymer stretch wrap and packaging films. "
            "LLDPE machine-grade stretch wrap, hand-wrap stretch film, pallet wrap. "
            "20–30 micron thickness, 500 mm width. Food-safe compliant, BIS marked. "
            "Annual capacity 4,800 MT."
        ),
        "profile_products": ["polymer film", "stretch wrap", "lldpe", "packaging film"],
        "catalogue_price": 95.0,
        "moq": 500.0,
        "max_qty": 50000.0,
        "capacity_mt": 400.0,
        "util_pct": 65,
        "expected_commodity": 1.0,
        "expected_composite": "~75%",
    },
    # ─── Seller 2: SUBSTRING match  (commodity_score = 0.8 → composite ~65%) ─
    {
        "legal_name": "Sai Packaging Films Pvt Ltd",
        "pan": "AAASP3002C",
        "gstin": "27AAASP3002C1Z3",
        "email": "info@saipackaging-test.in",
        "industry_vertical": "packaging_films",
        "commodities": ["polymer film", "BOPP film", "CPP film"],
        # "polymer film" is a SUBSTRING of rfq_product "polymer film stretch wrap" → score 0.8
        "min_order_value": 200000,
        "max_order_value": 3000000,
        "profile_text": (
            "Manufacturer of BOPP, CPP and polymer film rolls for lamination and "
            "flexible packaging. Widths 100–1500 mm, thickness 12–40 micron. "
            "BIS certified. Clients include FMCG and pharma packaging companies."
        ),
        "profile_products": ["bopp film", "cpp film", "polymer film", "lamination film"],
        "catalogue_price": 105.0,
        "moq": 1000.0,
        "max_qty": 30000.0,
        "capacity_mt": 300.0,
        "util_pct": 70,
        "expected_commodity": 0.8,
        "expected_composite": "~65%",
    },
    # ─── Seller 3: RELATED-TERM  (commodity_score = 0.7 → composite ~60%) ─────
    {
        "legal_name": "National Plastics Industries",
        "pan": "AAANP4003D",
        "gstin": "08AAANP4003D1Z4",
        "email": "sales@natplastics-test.in",
        "industry_vertical": "plastic_manufacturing",
        "commodities": ["plastic packaging", "polyolefin bags", "HDPE bags"],
        # product_word "polymer" → _RELATED_TERMS["polymer"]["plastic"] = 0.8
        # sc_word "plastic" in "plastic packaging" → best_related = 0.8×0.9 = 0.72 → cap 0.7
        "min_order_value": 300000,
        "max_order_value": 2000000,
        "profile_text": (
            "Manufacturer of plastic packaging solutions. HDPE bags, polyolefin pouches, "
            "woven sacks. Food-grade and industrial grade. NOT a stretch film manufacturer "
            "but supplies general plastic packaging to FMCG and agri sectors."
        ),
        "profile_products": ["plastic bags", "hdpe bags", "polyolefin", "woven sacks"],
        "catalogue_price": 78.0,
        "moq": 2000.0,
        "max_qty": 20000.0,
        "capacity_mt": 500.0,
        "util_pct": 55,
        "expected_commodity": 0.7,
        "expected_composite": "~60%",
    },
    # ─── Seller 4: 2-WORD OVERLAP  (commodity_score = 0.5 → composite ~50%) ───
    {
        "legal_name": "Prakash Stretch & Film Industries",
        "pan": "AAAPS5004E",
        "gstin": "29AAAPS5004E1Z5",
        "email": "info@prakashstretch-test.in",
        "industry_vertical": "industrial_packaging",
        "commodities": ["stretch hood packaging", "unitising film", "shrink sleeves"],
        # product_words: polymer, film, stretch, wrap
        # "stretch" in "stretch hood packaging" → +1
        # "film" in "unitising film" → +1   (overlap_count = 2 → 0.5)
        "min_order_value": 50000,
        "max_order_value": 1000000,
        "profile_text": (
            "Supplier of stretch hood packaging and unitizing film for palletised loads. "
            "Stretch hoods, pallet covers, shrink sleeves for bottles and PET containers. "
            "NOT a stretch wrap manufacturer — specialises in automated packaging systems."
        ),
        "profile_products": ["stretch hood", "pallet film", "shrink sleeve", "industrial film"],
        "catalogue_price": 88.0,
        "moq": 500.0,
        "max_qty": 10000.0,
        "capacity_mt": 150.0,
        "util_pct": 60,
        "expected_commodity": 0.5,
        "expected_composite": "~50%",
    },
    # ─── Seller 5: 1-WORD OVERLAP  (commodity_score = 0.3 → composite ~40%) ───
    {
        "legal_name": "GreenWrap Eco Packaging",
        "pan": "AAAGW6005F",
        "gstin": "33AAAGW6005F1Z6",
        "email": "info@greenwrap-test.in",
        "industry_vertical": "eco_packaging",
        "commodities": ["paper wrap", "biodegradable wrap", "compostable bags"],
        # product_words: polymer, film, stretch, wrap
        # "wrap" in "paper wrap" → overlap_count = 1 → commodity_score = 0.4 → hmm 0.3+0.1=0.4
        # "wrap" in "biodegradable wrap" → +1 more → overlap_count=2 → 0.5
        # Hmm, that's 0.5 not 0.3. Let me set only ONE commodity with "wrap"
        # Fixed: commodities below have only ONE occurrence of a product word
        "min_order_value": 20000,
        "max_order_value": 500000,
        "profile_text": (
            "Eco-friendly packaging supplier. Paper wrap, kraft paper rolls, "
            "biodegradable mailers, compostable bags. "
            "NOT a polymer or plastic packaging company — all products are "
            "paper-based and FSSAI/BIS certified for sustainability claims."
        ),
        "profile_products": ["paper wrap", "kraft paper", "biodegradable packaging", "compostable"],
        "catalogue_price": 65.0,
        "moq": 100.0,
        "max_qty": 5000.0,
        "capacity_mt": 80.0,
        "util_pct": 50,
        "expected_commodity": 0.4,
        "expected_composite": "~40%",
    },
    # ─── Seller 6: NO MATCH  (commodity_score = 0.0 → filtered) ─────────────
    {
        "legal_name": "TechMold Engineering Pvt Ltd",
        "pan": "AAATM7006G",
        "gstin": "27AAATM7006G1Z7",
        "email": "sales@techmold-test.in",
        "industry_vertical": "engineering_plastics",
        "commodities": ["injection moulding", "ABS granules", "engineering plastic components"],
        # product_words: polymer, film, stretch, wrap
        # "polymer" → _RELATED_TERMS["polymer"]["plastic"] = 0.8 → sc_word "plastic" in "engineering plastic components"
        # Actually "plastic" IS in "engineering plastic components" → best_related = 0.72 → cap 0.7
        # This would give 0.7 which I don't want. Let me remove "plastic" from commodities.
        "min_order_value": 500000,
        "max_order_value": 10000000,
        "profile_text": (
            "Engineering plastics manufacturer. Injection moulding of ABS, PC, POM components "
            "for automotive and electronics industries. CNC machined plastic parts, thermoset moulding. "
            "We make structural plastic parts, not packaging films or wrapping materials."
        ),
        "profile_products": ["injection moulding", "abs", "engineering components", "thermoset"],
        "catalogue_price": 850.0,
        "moq": 100.0,
        "max_qty": 5000.0,
        "capacity_mt": 200.0,
        "util_pct": 75,
        "expected_commodity": 0.0,
        "expected_composite": "NO MATCH",
    },
]

# Fix: Seller 5 commodities should have only ONE product_word ("wrap")
# to land on commodity_score = 0.3+0.1 = 0.4
SELLERS[4]["commodities"] = ["kraft paper rolls", "paper carry bags", "biodegradable wrap"]
# "wrap" only appears once → overlap_count=1 → 0.3+0.1=0.4

# Fix: Seller 6 — remove "plastic" to prevent related-term hit
SELLERS[5]["commodities"] = ["injection moulding components", "ABS granules", "thermoset parts"]
# "injection", "moulding", "components", "abs", "granules", "thermoset", "parts"
# None of these match product_words polymer/film/stretch/wrap → commodity_score = 0.0


# ─── Helpers ─────────────────────────────────────────────────────────────────

def poll_rfq(rfq_id, token, targets=None, timeout=120):
    if targets is None: targets = ["MATCHED", "PARSED", "CONFIRMED"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = get(f"/v1/marketplace/rfq/{rfq_id}", token)
        if r.status_code == 200:
            d = r.json()["data"]
            s = d.get("status", "")
            info(f"  RFQ status: {s}")
            if s in targets: return d
        time.sleep(4)
    warn("Timeout waiting for RFQ match"); return {}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    run_num  = int(time.time()) % 9000 + 1000
    run_tag  = f"{run_num:04d}"

    def _pan(b):   return b[:5] + run_tag + b[-1]
    def _gstin(b): return b[:2] + _pan(b[2:12]) + b[12:]
    def _email(e): return e.replace("@", f"+{run_tag}@")

    for s in SELLERS:
        s["pan"]   = _pan(s["pan"])
        s["gstin"] = _gstin(s["gstin"])
        s["email"] = _email(s["email"])
    BUYER["pan"]   = _pan(BUYER["pan"])
    BUYER["gstin"] = _gstin(BUYER["gstin"])
    BUYER["email"] = _email(BUYER["email"])

    info(f"Run tag: {run_tag}")

    # ── Step 0 ────────────────────────────────────────────────────────────
    h("STEP 0 — Health & Admin Login")
    if get("/health").status_code != 200: err("Backend unreachable"); sys.exit(1)
    ok("Backend healthy")
    admin_token = admin_login(); ok("Admin logged in")

    # ── Step 0b: Clean old test data to avoid score pollution ────────────────
    h("STEP 0b — Purge Previous Polymer Test Sellers from DB")
    info("Deleting old 'FlexPack', 'Sai Packaging', 'National Plastics', etc. test enterprises...")
    SELLER_NAMES_TO_PURGE = [
        "FlexPack Polymer Films Ltd",
        "Sai Packaging Films Pvt Ltd",
        "National Plastics Industries",
        "Prakash Stretch & Film Industries",
        "GreenWrap Eco Packaging",
        "TechMold Engineering Pvt Ltd",
    ]
    try:
        import os, asyncio
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy import text as sa_text

        db_url = os.environ.get("DATABASE_URL", "")
        if db_url:
            engine = create_async_engine(db_url, echo=False)
            sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async def _purge():
                async with sm() as session:
                    for name in SELLER_NAMES_TO_PURGE:
                        r = await session.execute(
                            sa_text("DELETE FROM enterprises WHERE name = :n"),
                            {"n": name},
                        )
                        if r.rowcount:
                            ok(f"  Deleted {r.rowcount}× '{name}'")
                    await session.commit()
                await engine.dispose()

            asyncio.run(_purge())
            ok("Purge complete")
        else:
            warn("DATABASE_URL not set — skipping purge")
    except Exception as exc:
        warn(f"Purge failed (non-fatal): {exc}")

    # ── Step 1: Register buyer ────────────────────────────────────────────
    h("STEP 1 — Register Buyer  (PackWell Consumer Goods — Surat)")
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
                 "full_name": "Deepak Mehta", "role": "ADMIN"},
    })
    ok(f"Buyer: {BUYER['legal_name']}  (ID: {buyer_eid})")

    # ── Step 2: Register 6 sellers ────────────────────────────────────────
    h("STEP 2 — Register 6 Sellers  (polymer packaging spectrum)")
    seller_data = []
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
                "address": {"address_type": "FACILITY", "address_line1": "Industrial Area",
                             "city": "Ahmedabad", "state": "GJ", "pincode": "382445"},
                "payment_terms_accepted": ["30 days", "45 days"],
            },
            "user": {"email": s["email"], "password": "Cadencia@Test#2026",
                     "full_name": f"Sales {i}", "role": "ADMIN"},
        })
        seller_data.append({**s, "token": token, "enterprise_id": eid})
        ok(f"Seller {i}: {s['legal_name']:<46}  [commodity_score expected: {s['expected_commodity']}]")

    # ── Step 3: Profiles + Catalogue + Capacity ───────────────────────────
    h("STEP 3 — Update Profiles / Catalogue / Capacity")
    for sd in seller_data:
        put("/v1/marketplace/capability-profile", token=sd["token"], json={
            "industry": sd["industry_vertical"],
            "products": sd["profile_products"],
            "geographies": ["IN"],
            "min_order_value": sd["min_order_value"],
            "max_order_value": sd["max_order_value"],
            "description": sd["profile_text"],
        })
        post("/v1/marketplace/capability-profile/embeddings", token=sd["token"])

        # Catalogue — must use a valid product_category from the schema enum
        cat_r = post("/v1/marketplace/catalogue", token=sd["token"], json={
            "product_name": sd["commodities"][0][:60],
            "hsn_code": "3920",
            "product_category": "CUSTOM",
            "specification_text": sd["profile_text"][:200],
            "unit": "KG",
            "price_per_unit_inr": sd["catalogue_price"],
            "moq": sd["moq"],
            "max_order_qty": sd["max_qty"],
            "lead_time_days": 7,
            "in_stock_qty": 10000,
            "certifications": [],
        })
        if cat_r.status_code not in (200, 201):
            warn(f"  Catalogue failed for {sd['legal_name']}: {cat_r.status_code} {cat_r.text[:80]}")
        else:
            ok(f"  {sd['legal_name']:<46}  catalogue @ ₹{sd['catalogue_price']}/kg")

        put("/v1/marketplace/capacity-profile", token=sd["token"], json={
            "monthly_production_capacity_mt": sd["capacity_mt"],
            "current_utilization_pct": sd["util_pct"],
            "num_production_lines": 2,
            "shift_pattern": "DOUBLE_SHIFT",
            "avg_dispatch_days": 3,
            "max_delivery_radius_km": 1500,
            "has_own_transport": True,
            "preferred_transport_modes": ["ROAD"],
            "ex_works_available": True,
        })

    info("Waiting 25s for embeddings...")
    time.sleep(25)

    # ── Step 4: Buyer submits RFQ ─────────────────────────────────────────
    h("STEP 4 — Buyer Submits RFQ  (polymer film stretch wrap)")
    print(f"\n  {BOLD}RFQ:{RST}")
    for ln in RFQ_TEXT.split("\n")[:6]: print(f"    {ln}")
    r = post("/v1/marketplace/rfq", token=buyer_token,
             json={"raw_text": RFQ_TEXT, "document_type": "free_text"})
    rfq_id = chk(r, "submit rfq")["rfq_id"]
    ok(f"RFQ submitted: {rfq_id}")
    rfq = poll_rfq(rfq_id, buyer_token)
    ok(f"RFQ status: {rfq.get('status')}")

    # Log parsed fields so we can see what the NLP extracted
    pf = rfq.get("parsed_fields") or {}
    info(f"  Parsed product: '{pf.get('product','')}' | qty: {pf.get('quantity','')} | geo: {pf.get('geography','')}")
    info(f"  budget: {pf.get('budget_min','')} – {pf.get('budget_max','')} | delivery_window_days: {pf.get('delivery_window_days','(not extracted)')}")

    # ── Step 5: Match scores ──────────────────────────────────────────────
    h("STEP 5 — RFQ Match Scores  (keyword-based composite)")
    r = get(f"/v1/marketplace/rfq/{rfq_id}/matches", token=buyer_token)
    matches_raw = r.json().get("data", []) if r.status_code == 200 else []

    match_map: dict[str, dict] = {}
    if matches_raw:
        print(f"\n  {'Rank':<5} {'Seller':<46} {'Score':<8}  Expected Commodity Score")
        print(f"  {'-'*5} {'-'*46} {'-'*8}  {'-'*28}")
        for m in sorted(matches_raw, key=lambda x: x.get("similarity_score", x.get("score", 0)), reverse=True):
            eid   = str(m.get("enterprise_id", ""))
            score = m.get("similarity_score", m.get("score", 0.0))
            rank  = m.get("rank", "?")
            name  = m.get("enterprise_name", m.get("name", eid[:8]))
            mid   = str(m.get("match_id", m.get("id", "")))
            # Find expected score from SELLERS
            expected = next((s["expected_composite"] for s in seller_data if s["enterprise_id"] == eid), "?")
            print(f"  {rank:<5} {name:<46} {score:<8.4f}  {expected}")
            match_map[eid] = {"score": score, "match_id": mid, "name": name, "rank": rank}
    else:
        warn("No matches returned — check if embeddings were computed")

    # ── Step 6: Expected vs actual summary ───────────────────────────────
    print(f"\n  {BOLD}Score breakdown (keyword composite = 0.5×commodity + 0.3×geo + 0.2×value):{RST}")
    print(f"  {'Seller':<46} {'Expected %':<12} {'Actual score':<14} {'Matched?'}")
    print(f"  {'-'*46} {'-'*12} {'-'*14} {'-'*8}")
    for sd in seller_data:
        eid    = sd["enterprise_id"]
        actual = match_map.get(eid, {}).get("score")
        if actual is not None:
            matched = f"{GREEN}✓{RST}"
            # API returns score already on 0-100 scale (see MatchResponse comment "0-100")
            actual_s = f"{actual:.1f}%"
        else:
            matched = f"{RED}✗ NO MATCH{RST}"
            actual_s = "—"
        print(f"  {sd['legal_name']:<46} {sd['expected_composite']:<12} {actual_s:<14} {matched}")

    # ── Step 7: Sessions ──────────────────────────────────────────────────
    h("STEP 7 — Create Negotiation Sessions (6 sellers)")
    sessions = []
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
            sid = (r.json().get("data", {}) or {}).get("session_id") or (r.json().get("data", {}) or {}).get("id")
            ok(f"Session: {sd['legal_name']:<46}  match={sc:.1f}%  sid={sid}")
            sessions.append({**sd, "session_id": sid, "match_score": sc})
        else:
            warn(f"Session failed: {sd['legal_name']} — {r.status_code}")

    # ── Step 8: Auto-negotiation ──────────────────────────────────────────
    h("STEP 8 — Full LLM Auto-Negotiation  (Groq llama-3.3-70b-versatile)")
    agreed = []
    for s_info in sessions:
        sid  = s_info["session_id"]
        name = s_info["legal_name"]
        sc   = s_info["match_score"]
        print(f"\n  {BOLD}── {name}  [match score: {sc:.1f}%] ──{RST}")
        print(f"  {'Rnd':<5} {'Role':<8} {'INR/kg':>12}  Reasoning")
        print(f"  {'-'*5} {'-'*8} {'-'*12}  {'-'*50}")

        r = post(f"/v1/sessions/{sid}/run-auto", token=buyer_token, params={"max_rounds": 12})
        if r.status_code != 200:
            warn(f"  run-auto {r.status_code}: {r.text[:200]}"); continue

        auto = r.json().get("data", {})
        sess = auto.get("session", {})
        for off in sorted(sess.get("offers", []), key=lambda x: x.get("round_number", 0)):
            print(f"  {off.get('round_number','?'):<5} {off.get('proposer_role','?')[:7]:<8} "
                  f"{off.get('price', 0):>12,.0f}  {(off.get('agent_reasoning') or '')[:50]}")

        status = sess.get("status", "UNKNOWN")
        price  = sess.get("agreed_price")
        rounds = sess.get("round_count", len(sess.get("offers", [])))
        if status == "AGREED":
            ok(f"  AGREED ✓ — INR {price:,.0f}/kg  in {rounds} rounds")
            agreed.append({**s_info, "agreed_price": price, "rounds": rounds})
        else:
            info(f"  Terminal: {status} after {rounds} rounds")

    # ── Step 9: Best deal ─────────────────────────────────────────────────
    h("STEP 9 — Select Best Deal")
    if not agreed:
        warn("No agreed sessions. Using first session as fallback.")
        agreed = [{**sessions[0], "agreed_price": None, "rounds": 0}] if sessions else []
    if not agreed: err("No sessions"); sys.exit(1)

    best          = min(agreed, key=lambda x: (x["agreed_price"] or float("inf")))
    winning_sid   = best["session_id"]
    winning_tok   = best["token"]         # ← fix: was "seller_token", now "token"
    winning_name  = best["legal_name"]
    ap = best.get('agreed_price')
    ok(f"Winner: {winning_name}  — INR {ap:,.0f}/kg" if ap else f"Winner: {winning_name} (no agreed price)")

    # ── Step 10-15: Escrow lifecycle ──────────────────────────────────────
    h("STEP 10 — Create Escrow  (PENDING_APPROVAL)")
    r = post("/v1/escrow/select-deal", token=buyer_token, json={"session_id": winning_sid})
    if r.status_code in (200, 201):
        escrow_id = (r.json().get("data") or {}).get("escrow_id") or (r.json().get("data") or {}).get("id")
        ok(f"Escrow: {escrow_id}")
    else:
        warn(f"select-deal {r.status_code} — trying existing escrows")
        r2 = get("/v1/escrow", token=buyer_token, params={"limit": 5})
        escrows = r2.json().get("data", []) if r2.status_code == 200 else []
        escrow_id = escrows[0]["escrow_id"] if escrows else None
        if not escrow_id: err("No escrow"); sys.exit(1)

    h("STEP 11 — Admin Approve")
    r = post(f"/v1/escrow/{escrow_id}/approve", token=admin_token)
    ok(f"Approved: HTTP {r.status_code}")

    h("STEP 12 — Platform Deploy  (Algorand Testnet)")
    r = post(f"/v1/escrow/{winning_sid}/platform-deploy", token=buyer_token)
    if r.status_code in (200, 201):
        d = r.json()["data"]
        ok(f"Deployed — App ID: {d.get('app_id')}  TX: {str(d.get('tx_id',''))[:22]}...")
    else:
        warn(f"platform-deploy {r.status_code}: {r.text[:200]}")

    h("STEP 13 — Platform Fund")
    r = post(f"/v1/escrow/{escrow_id}/platform-fund", token=buyer_token)
    if r.status_code in (200, 201):
        d = r.json()["data"]
        ok(f"Funded — TX: {str(d.get('tx_id',''))[:22]}...  Status: {d.get('status')}")
    else:
        warn(f"platform-fund {r.status_code}: {r.text[:200]}")

    h("STEP 14 — Seller Dispatch  ★  (Dispatch bug-fix re-verification)")
    r = post(f"/v1/escrow/{escrow_id}/seller-dispatch", token=winning_tok)
    if r.status_code == 200:
        d = r.json()["data"]
        ok(f"{GREEN}{BOLD}DISPATCH SUCCESS — Status: {d.get('status')}{RST}")
        ok(f"  {d.get('message')}")
    else:
        err(f"DISPATCH FAILED: {r.status_code} — {r.text[:400]}")

    h("STEP 15 — Buyer Confirms Delivery  (auto-release)")
    r = post(f"/v1/escrow/{escrow_id}/buyer-confirm", token=buyer_token)
    if r.status_code == 200:
        d = r.json()["data"]
        ok(f"RELEASED — TX: {str(d.get('tx_id',''))[:22]}...")
    else:
        warn(f"buyer-confirm {r.status_code}: {r.text[:200]}")

    # ── Final summary ─────────────────────────────────────────────────────
    h("FINAL SUMMARY")
    print(f"""
  {BOLD}Industry  : Plastics & Polymer Packaging  (non-civil, non-steel){RST}
  {BOLD}Buyer     : {BUYER['legal_name']} — Surat, Gujarat{RST}
  {BOLD}RFQ       : 5,000 kg polymer film stretch wrap{RST}

  {BOLD}Match Scores (keyword composite 0–1):{RST}
  {'Seller':<46} {'Commodity':<12} {'Expected':<12} {'Actual':>10}  {'Δ'}""")

    for sd in seller_data:
        eid    = sd["enterprise_id"]
        actual = match_map.get(eid, {}).get("score")
        if actual is None:
            print(f"  {sd['legal_name']:<46} {sd['expected_commodity']:<12} {sd['expected_composite']:<12} {'NO MATCH':>10}")
        else:
            # score is already 0-100 from API
            bar_len = int(actual * 0.4)
            bar = f"{GREEN}{'█'*bar_len}{RST}"
            print(f"  {sd['legal_name']:<46} {sd['expected_commodity']:<12} {sd['expected_composite']:<12} {actual:>7.1f}%  {bar}")

    print(f"\n  {BOLD}Negotiation Results:{RST}")
    print(f"  {'Seller':<46} {'Rounds':>7}  {'Agreed INR/kg':>14}")
    for a in agreed:
        print(f"  {a['legal_name']:<46} {a.get('rounds','?'):>7}  INR {a.get('agreed_price','N/A'):>10,.0f}/kg")

    print(f"\n  {BOLD}Winner : {winning_name}{RST}")
    print(f"  {BOLD}Price  : INR {best.get('agreed_price','N/A'):,.0f}/kg{RST}")
    print(f"  {BOLD}Escrow : {escrow_id}{RST}")
    print()


if __name__ == "__main__":
    main()
