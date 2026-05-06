#!/usr/bin/env python3
"""
Cadencia A2A Platform — Pharma Industry Flow Test
==================================================
Industry  : Pharmaceutical / Active Pharmaceutical Ingredients (API)
Buyer RFQ : 500 kg Paracetamol IP API — Hyderabad, 15-day delivery window

Seller spectrum (designed for HIGH score variation):
  Seller 1 — Exact match: Analgesics API specialist (Paracetamol, Ibuprofen)
  Seller 2 — Good match : Broad-spectrum pharma API (multiple therapeutics)
  Seller 3 — Medium     : Pharmaceutical excipients (same sector, wrong product type)
  Seller 4 — Low        : Lab chemicals / analytical reagents (pharma-adjacent)
  Seller 5 — Very low   : Nutraceuticals / health supplements (FSSAI, not IP-grade)
  Seller 6 — Near zero  : Veterinary pharmaceuticals (animal health, not human API)

Scoring factors active:
  ✓ Semantic (pgvector cosine) — 25%
  ✓ Delivery feasibility       — 20%   (buyer has address + delivery window)
  ✓ Capacity                   — 15%
  ✓ Price competitiveness      — 15%   (catalogue items + budget in RFQ)
  ✓ Proximity                  — 10%
  ✓ Payment terms              — 10%
  ✓ Certification               — 5%

Run:
    docker cp backend/scripts/pharma_flow_test.py cadencia-a2a-platform-test-backend-1:/app/scripts/pharma_flow_test.py
    docker compose -f docker-compose.local.yml exec backend python scripts/pharma_flow_test.py
"""

from __future__ import annotations

import sys
import time
import uuid

import httpx as requests

BASE_URL    = "http://localhost:8000"
ADMIN_EMAIL = "admin@cadencia.io"
ADMIN_PASSWORD = "Admin@1234"

BOLD   = "\033[1m"; GREEN  = "\033[32m"; CYAN   = "\033[36m"
YELLOW = "\033[33m"; RED    = "\033[31m"; RESET  = "\033[0m"

def h(t):   print(f"\n{BOLD}{CYAN}{'='*72}{RESET}\n{BOLD}{CYAN}  {t}{RESET}\n{BOLD}{CYAN}{'='*72}{RESET}")
def ok(t):  print(f"  {GREEN}✓{RESET} {t}")
def info(t):print(f"  {CYAN}→{RESET} {t}")
def warn(t):print(f"  {YELLOW}⚠{RESET} {t}")
def err(t): print(f"  {RED}✗{RESET} {t}")

def _req(method, path, token=None, **kw):
    hdrs = kw.pop("headers", {})
    if token: hdrs["Authorization"] = f"Bearer {token}"
    return getattr(requests, method)(f"{BASE_URL}{path}", headers=hdrs, timeout=120, **kw)

def post(p, token=None, **kw):  return _req("post",  p, token, **kw)
def get(p,  token=None, **kw):  return _req("get",   p, token, **kw)
def put(p,  token=None, **kw):  return _req("put",   p, token, **kw)

def chk(r, label):
    if r.status_code not in (200, 201, 202, 204):
        err(f"{label} → HTTP {r.status_code}: {r.text[:300]}"); sys.exit(1)
    if r.status_code == 204: return {}
    d = r.json()
    if not d.get("success", True): err(f"{label} → {d}"); sys.exit(1)
    return d.get("data", d)

def admin_login(): return chk(post("/v1/auth/admin-login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}), "admin-login")["access_token"]
def register(payload): d = chk(post("/v1/auth/register", json=payload), "register"); return d["access_token"], d["enterprise_id"]

# ─── RFQ text (rich with delivery/budget/qty info for enhanced matching) ───────

RFQ_TEXT = (
    "RFQ — Pharmaceutical API Procurement\n"
    "Product: Paracetamol IP (Acetaminophen) Active Pharmaceutical Ingredient\n"
    "Quantity: 500 kg\n"
    "Grade: IP 2022 (Indian Pharmacopoeia 2022 compliant)\n"
    "Specifications: Particle size D90 < 60 µm, water content ≤ 0.5%, "
    "heavy metals ≤ 10 ppm, residue on ignition ≤ 0.1%\n"
    "Documentation: Certificate of Analysis, Certificate of Origin, GMP certificate mandatory\n"
    "Delivery location: Genome Valley, Hyderabad, Telangana — PIN 500078\n"
    "Delivery window: 15 days from purchase order\n"
    "Budget: INR 480 to INR 580 per kg\n"
    "Payment terms: 30 days net from delivery\n"
    "Third-party inspection allowed: Yes"
)

# ─── Buyer ──────────────────────────────────────────────────────────────────

BUYER = {
    "legal_name": "PharmaCore Formulations Pvt Ltd",
    "pan": "AAAPC0001A",
    "gstin": "36AAAPC0001A1Z0",
    "email": "procurement@pharmacore-test.in",
    "trade_role": "BUYER",
    "commodities": ["paracetamol api", "pharmaceutical ingredients"],
    "industry_vertical": "pharmaceutical_manufacturing",
    "min_order_value": 50000,
    "max_order_value": 10000000,
    "address": {
        "address_type": "FACILITY",
        "address_line1": "Plot 12, Genome Valley, Shameerpet",
        "city": "Hyderabad",
        "state": "TS",
        "pincode": "500078",
    },
}

# ─── Sellers (deliberately differentiated for score variation) ──────────────

SELLERS = [
    # ── Seller 1: EXACT match ─────────────────────────────────────────────
    {
        "legal_name": "Apex Analgesics API Pvt Ltd",
        "pan": "AAAAP1001B",
        "gstin": "36AAAAP1001B1Z1",
        "email": "sales@apex-analgesics-test.in",
        "trade_role": "SELLER",
        "industry_vertical": "pharmaceutical_api",
        "commodities": ["paracetamol api", "acetaminophen", "ibuprofen api", "aspirin api"],
        "min_order_value": 50000,
        "max_order_value": 5000000,
        "payment_terms_accepted": ["30 days", "45 days"],
        "test_certificate_available": True,
        "address": {"address_type": "FACILITY", "address_line1": "IDA Nacharam", "city": "Hyderabad", "state": "TS", "pincode": "500076"},
        "profile_text": (
            "GMP-certified API manufacturer specialising in analgesics and antipyretics. "
            "Paracetamol IP/BP/USP, Ibuprofen, Aspirin. Particle size control D90 < 60 µm. "
            "Annual capacity 2,500 MT. Approved by WHO-GMP, US-FDA. COA, COO, GMP certificate provided. "
            "In-house NABL-accredited analytical lab. Hyderabad-based, same-city delivery within 2 days."
        ),
        "profile_products": ["paracetamol", "acetaminophen", "ibuprofen", "aspirin", "analgesic api", "ip grade"],
        "catalogue_price": 520.0,
        "moq": 10.0,
        "max_order_qty": 5000.0,
        "capacity_mt_month": 200.0,
        "utilisation_pct": 60,
        "anchor_price": 520,
        "expected_score": "~85%",
    },
    # ── Seller 2: GOOD match ──────────────────────────────────────────────
    {
        "legal_name": "GenPharma API Solutions Ltd",
        "pan": "AAAGP2002C",
        "gstin": "27AAAGP2002C1Z2",
        "email": "api@genpharma-test.in",
        "trade_role": "SELLER",
        "industry_vertical": "pharmaceutical_manufacturing",
        "commodities": ["paracetamol api", "metformin hcl", "atorvastatin api", "cardiovascular apis"],
        "min_order_value": 100000,
        "max_order_value": 20000000,
        "payment_terms_accepted": ["30 days", "60 days"],
        "test_certificate_available": True,
        "address": {"address_type": "FACILITY", "address_line1": "Ambernath MIDC", "city": "Pune", "state": "MH", "pincode": "411028"},
        "profile_text": (
            "Multi-therapeutic API manufacturer with 20+ years in regulated markets. "
            "Paracetamol, Metformin, Atorvastatin, Losartan APIs. GMP certified, EDQM CEP available. "
            "IP/BP/USP/EP grade products. 5,000 MT annual capacity. "
            "Exports to EU, US, Australia. COA and COPP furnished with every batch."
        ),
        "profile_products": ["paracetamol", "metformin", "atorvastatin", "api", "pharmaceutical", "gmp"],
        "catalogue_price": 560.0,
        "moq": 50.0,
        "max_order_qty": 10000.0,
        "capacity_mt_month": 400.0,
        "utilisation_pct": 70,
        "anchor_price": 560,
        "expected_score": "~65%",
    },
    # ── Seller 3: MEDIUM match ────────────────────────────────────────────
    {
        "legal_name": "PharmEx Excipients Ltd",
        "pan": "AAAPE3003D",
        "gstin": "24AAAPE3003D1Z3",
        "email": "sales@pharmex-excipients-test.in",
        "trade_role": "SELLER",
        "industry_vertical": "pharma_excipients",
        "commodities": ["microcrystalline cellulose", "lactose monohydrate", "hpmc", "pharmaceutical excipients"],
        "min_order_value": 25000,
        "max_order_value": 3000000,
        "payment_terms_accepted": ["45 days", "60 days"],
        "test_certificate_available": True,
        "address": {"address_type": "WAREHOUSE", "address_line1": "Vatva GIDC", "city": "Ahmedabad", "state": "GJ", "pincode": "382445"},
        "profile_text": (
            "Specialised pharmaceutical excipients supplier. Microcrystalline cellulose (MCC), "
            "lactose monohydrate, HPMC, PVP, croscarmellose sodium. "
            "DMF filed with USFDA. Pharma-grade products, CoA available. "
            "We supply binders, fillers and disintegrants — not active pharmaceutical ingredients. "
            "Serves tablet and capsule formulation plants across India."
        ),
        "profile_products": ["excipients", "mcc", "lactose", "hpmc", "binders", "fillers", "pharmaceutical"],
        "catalogue_price": 280.0,
        "moq": 25.0,
        "max_order_qty": 2000.0,
        "capacity_mt_month": 300.0,
        "utilisation_pct": 55,
        "anchor_price": 280,
        "expected_score": "~40%",
    },
    # ── Seller 4: LOW match ───────────────────────────────────────────────
    {
        "legal_name": "Bioanalytical Reagents India Pvt Ltd",
        "pan": "AAABR4004E",
        "gstin": "29AAABR4004E1Z4",
        "email": "info@bioanalytical-test.in",
        "trade_role": "SELLER",
        "industry_vertical": "laboratory_chemicals",
        "commodities": ["hplc solvents", "analytical standards", "reference standards", "lab reagents"],
        "min_order_value": 5000,
        "max_order_value": 500000,
        "payment_terms_accepted": ["advance", "30 days"],
        "test_certificate_available": True,
        "address": {"address_type": "FACILITY", "address_line1": "Electronic City Phase 1", "city": "Bangalore", "state": "KA", "pincode": "560100"},
        "profile_text": (
            "Supplier of analytical chemistry reagents for pharmaceutical R&D and QC labs. "
            "HPLC grade solvents, USP reference standards, working standards, titration reagents. "
            "NABL accredited. We provide chemical standards used in API testing — "
            "not bulk pharmaceutical ingredients for manufacturing. "
            "Acetonitrile, methanol, buffer solutions, certified reference standards."
        ),
        "profile_products": ["hplc", "reagents", "standards", "solvents", "analytical chemistry", "laboratory"],
        "catalogue_price": 3500.0,
        "moq": 1.0,
        "max_order_qty": 200.0,
        "capacity_mt_month": 5.0,
        "utilisation_pct": 40,
        "anchor_price": 3500,
        "expected_score": "~25%",
    },
    # ── Seller 5: VERY LOW match ──────────────────────────────────────────
    {
        "legal_name": "NatureCure Nutraceuticals Ltd",
        "pan": "AAANC5005F",
        "gstin": "33AAANC5005F1Z5",
        "email": "info@naturecure-nutra-test.in",
        "trade_role": "SELLER",
        "industry_vertical": "nutraceuticals",
        "commodities": ["vitamin c powder", "turmeric extract", "ashwagandha extract", "dietary supplements"],
        "min_order_value": 10000,
        "max_order_value": 2000000,
        "payment_terms_accepted": ["advance", "30 days"],
        "test_certificate_available": False,
        "address": {"address_type": "FACILITY", "address_line1": "Sidco Industrial Estate", "city": "Coimbatore", "state": "TN", "pincode": "641021"},
        "profile_text": (
            "FSSAI-licensed nutraceuticals and health supplement ingredients manufacturer. "
            "Vitamin C (ascorbic acid), Vitamin D3, Turmeric extract (95% curcumin), "
            "Ashwagandha extract, Moringa powder. Food-grade and supplement-grade only. "
            "NOT manufactured under pharmaceutical GMP. Products are for dietary supplements, "
            "not for formulation as pharmaceutical APIs or prescription medicines."
        ),
        "profile_products": ["vitamin", "herbal extract", "nutraceutical", "supplement", "fssai", "food grade"],
        "catalogue_price": 850.0,
        "moq": 5.0,
        "max_order_qty": 500.0,
        "capacity_mt_month": 50.0,
        "utilisation_pct": 45,
        "anchor_price": 850,
        "expected_score": "~12%",
    },
    # ── Seller 6: NEAR ZERO match ─────────────────────────────────────────
    {
        "legal_name": "VetMed Animal Health Pvt Ltd",
        "pan": "AAAVH6006G",
        "gstin": "08AAAVH6006G1Z6",
        "email": "sales@vetmed-test.in",
        "trade_role": "SELLER",
        "industry_vertical": "veterinary_pharma",
        "commodities": ["albendazole veterinary", "ivermectin veterinary", "oxytetracycline", "animal health drugs"],
        "min_order_value": 20000,
        "max_order_value": 1000000,
        "payment_terms_accepted": ["advance", "60 days"],
        "test_certificate_available": False,
        "address": {"address_type": "FACILITY", "address_line1": "Sitapura Industrial Area", "city": "Jaipur", "state": "RJ", "pincode": "302022"},
        "profile_text": (
            "Manufacturer of veterinary pharmaceutical products for livestock and poultry. "
            "Albendazole bolus, Ivermectin pour-on, Oxytetracycline injectable, "
            "de-worming tablets, tick control products. "
            "CVPCEA licensed. Products are for animal use only — not for human pharmaceutical manufacturing. "
            "Our products comply with veterinary pharmacopoeia standards, not Indian Pharmacopoeia for humans."
        ),
        "profile_products": ["veterinary", "animal health", "albendazole", "ivermectin", "livestock", "poultry"],
        "catalogue_price": 420.0,
        "moq": 100.0,
        "max_order_qty": 5000.0,
        "capacity_mt_month": 80.0,
        "utilisation_pct": 50,
        "anchor_price": 420,
        "expected_score": "~5%",
    },
]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def poll_rfq(rfq_id, token, targets, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = get(f"/v1/marketplace/rfq/{rfq_id}", token)
        if r.status_code == 200:
            d = r.json()["data"]
            status = d.get("status", "")
            info(f"  RFQ status: {status}")
            if status in targets:
                return d
        time.sleep(4)
    warn(f"RFQ did not reach {targets} within {timeout}s")
    r = get(f"/v1/marketplace/rfq/{rfq_id}", token)
    return r.json().get("data", {}) if r.status_code == 200 else {}


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
    r = get("/health")
    if r.status_code != 200: err("Backend unreachable"); sys.exit(1)
    ok(f"Backend healthy — {r.json().get('status')}")
    admin_token = admin_login()
    ok("Admin logged in")

    # ── Step 1: Register buyer ────────────────────────────────────────────
    h("STEP 1 — Register Buyer (PharmaCore Formulations — Hyderabad)")
    buyer_token, buyer_eid = register({
        "enterprise": {
            "legal_name": BUYER["legal_name"],
            "pan": BUYER["pan"],
            "gstin": BUYER["gstin"],
            "trade_role": BUYER["trade_role"],
            "commodities": BUYER["commodities"],
            "min_order_value": BUYER["min_order_value"],
            "max_order_value": BUYER["max_order_value"],
            "industry_vertical": BUYER["industry_vertical"],
            "address": BUYER["address"],
        },
        "user": {"email": BUYER["email"], "password": "Cadencia@Test#2026",
                 "full_name": "Rajesh Patel", "role": "ADMIN"},
    })
    ok(f"Buyer: {BUYER['legal_name']} (ID: {buyer_eid})")

    # ── Step 2: Register 6 sellers ────────────────────────────────────────
    h("STEP 2 — Register 6 Sellers (across pharma-adjacent verticals)")
    seller_data = []
    for i, s in enumerate(SELLERS, 1):
        token, eid = register({
            "enterprise": {
                "legal_name": s["legal_name"],
                "pan": s["pan"],
                "gstin": s["gstin"],
                "trade_role": s["trade_role"],
                "commodities": s["commodities"],
                "min_order_value": s["min_order_value"],
                "max_order_value": s["max_order_value"],
                "industry_vertical": s["industry_vertical"],
                "address": s.get("address"),
                "payment_terms_accepted": s.get("payment_terms_accepted", []),
                "test_certificate_available": s.get("test_certificate_available", False),
            },
            "user": {"email": s["email"], "password": "Cadencia@Test#2026",
                     "full_name": f"Sales Manager {i}", "role": "ADMIN"},
        })
        seller_data.append({**s, "token": token, "enterprise_id": eid})
        ok(f"Seller {i}: {s['legal_name']}  [expected score {s['expected_score']}] (ID: {eid})")

    # ── Step 3: Enrich profiles + catalogue + capacity ─────────────────────
    h("STEP 3 — Update Profiles / Catalogue Items / Capacity")
    for sd in seller_data:
        # Capability profile
        r = put("/v1/marketplace/capability-profile", token=sd["token"], json={
            "industry": sd["industry_vertical"],
            "products": sd["profile_products"],
            "geographies": ["IN"],
            "min_order_value": sd["min_order_value"],
            "max_order_value": sd["max_order_value"],
            "description": sd["profile_text"],
        })
        status_code = r.status_code
        ok(f"  Profile: {sd['legal_name']} ({status_code})")

        # Trigger embeddings
        post("/v1/marketplace/capability-profile/embeddings", token=sd["token"])

        # Catalogue item (so price scoring works)
        r = post("/v1/marketplace/catalogue", token=sd["token"], json={
            "product_name": sd["commodities"][0].title(),
            "hsn_code": "2941",
            "product_category": "API",
            "specification_text": sd["profile_text"][:200],
            "unit": "KG",
            "price_per_unit_inr": sd["catalogue_price"],
            "moq": sd["moq"],
            "max_order_qty": sd["max_order_qty"],
            "lead_time_days": 7,
            "in_stock_qty": 2000,
            "certifications": ["GMP"] if sd.get("test_certificate_available") else [],
        })
        if r.status_code in (200, 201):
            ok(f"  Catalogue: {sd['commodities'][0].title()} @ INR {sd['catalogue_price']}/kg")

        # Capacity profile (so capacity scoring works)
        r = put("/v1/marketplace/capacity-profile", token=sd["token"], json={
            "monthly_production_capacity_mt": sd["capacity_mt_month"],
            "current_utilization_pct": sd["utilisation_pct"],
            "num_production_lines": 2,
            "shift_pattern": "DOUBLE_SHIFT",
            "avg_dispatch_days": 3,
            "max_delivery_radius_km": 1500,
            "has_own_transport": True,
            "preferred_transport_modes": ["ROAD"],
            "ex_works_available": True,
        })
        if r.status_code in (200, 201):
            ok(f"  Capacity: {sd['capacity_mt_month']} MT/month, {sd['utilisation_pct']}% utilised")

    info("Waiting 25 seconds for embeddings to compute...")
    time.sleep(25)

    # ── Step 4: Buyer submits RFQ ─────────────────────────────────────────
    h("STEP 4 — Buyer Submits RFQ (Paracetamol IP API)")
    print(f"\n  {BOLD}RFQ text preview:{RESET}")
    for line in RFQ_TEXT.split("\n")[:6]:
        print(f"    {line}")
    print()
    r = post("/v1/marketplace/rfq", token=buyer_token,
             json={"raw_text": RFQ_TEXT, "document_type": "free_text"})
    rfq_data = chk(r, "submit RFQ")
    rfq_id = rfq_data["rfq_id"]
    ok(f"RFQ submitted: {rfq_id}")
    rfq = poll_rfq(rfq_id, buyer_token, ["MATCHED", "PARSED", "CONFIRMED"], timeout=90)
    ok(f"RFQ reached status: {rfq.get('status')}")

    # ── Step 5: Match scores ──────────────────────────────────────────────
    h("STEP 5 — RFQ Match Scores (7-factor composite)")
    r = get(f"/v1/marketplace/rfq/{rfq_id}/matches", token=buyer_token)
    matches_raw = r.json().get("data", []) if r.status_code == 200 else []

    # Build score map: enterprise_id → full match data
    match_map: dict[str, dict] = {}
    if matches_raw:
        print(f"\n  {'Rank':<5} {'Seller':<44} {'Score':<8} {'Semantic':<10} {'Delivery':<10} {'Capacity':<10} {'Price':<8}")
        print(f"  {'-'*5} {'-'*44} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
        for m in sorted(matches_raw, key=lambda x: x.get("score", x.get("composite_score", 0)), reverse=True):
            eid   = str(m.get("enterprise_id", m.get("id", "")))
            score = m.get("score", m.get("composite_score", 0))
            sem   = m.get("semantic_score", "—")
            deli  = m.get("delivery_feasibility_score", "—")
            cap   = m.get("capacity_score", "—")
            price = m.get("price_score", "—")
            rank  = m.get("rank", "?")
            name  = m.get("enterprise_name", m.get("name", ""))
            match_id = str(m.get("match_id", m.get("id", "")))
            print(f"  {rank:<5} {name:<44} {score:<8.2f} {str(sem):<10} {str(deli):<10} {str(cap):<10} {str(price):<8}")
            match_map[eid] = {"score": score, "match_id": match_id, "name": name, "rank": rank, **m}
    else:
        warn("No matches returned from API")

    # ── Step 6: Print expected vs actual scores ───────────────────────────
    print(f"\n  {BOLD}Score comparison (expected vs actual):{RESET}")
    print(f"  {'Seller':<44} {'Expected':<12} {'Actual score':<15}")
    print(f"  {'-'*44} {'-'*12} {'-'*15}")
    for sd in seller_data:
        eid = sd["enterprise_id"]
        actual = match_map.get(eid, {}).get("score", "NO MATCH")
        actual_str = f"{actual:.2f}%" if isinstance(actual, float) else str(actual)
        print(f"  {sd['legal_name']:<44} {sd['expected_score']:<12} {actual_str:<15}")

    # ── Step 7: Create sessions for all matched sellers ───────────────────
    h("STEP 7 — Create Negotiation Sessions")
    sessions = []
    for sd in seller_data:
        eid = sd["enterprise_id"]
        match_info = match_map.get(eid, {})
        match_id_val = match_info.get("match_id") or str(uuid.uuid4())
        score = match_info.get("score", 0.0)
        r = post("/v1/sessions", token=buyer_token, json={
            "match_id": match_id_val,
            "rfq_id": rfq_id,
            "buyer_enterprise_id": buyer_eid,
            "seller_enterprise_id": eid,
        })
        if r.status_code in (200, 201):
            sd_resp = r.json().get("data", {})
            sid = sd_resp.get("session_id") or sd_resp.get("id")
            ok(f"Session: {sd['legal_name']:<44} score={score:.2f}%  sid={sid}")
            sessions.append({**sd, "session_id": sid, "match_score": score})
        else:
            warn(f"Session failed for {sd['legal_name']}: {r.status_code}")

    # ── Step 8: Auto-negotiation with full LLM ────────────────────────────
    h("STEP 8 — Full LLM Auto-Negotiation (Groq llama-3.3-70b-versatile)")
    agreed = []
    for s_info in sessions:
        sid = s_info["session_id"]
        name = s_info["legal_name"]
        expected = s_info["expected_score"]
        print(f"\n  {BOLD}── {name}  [match {s_info['match_score']:.2f}%] ──{RESET}")
        print(f"  {'Rnd':<5} {'Role':<8} {'INR/kg':>12} {'Reasoning (50 chars)':}")
        print(f"  {'-'*5} {'-'*8} {'-'*12} {'-'*50}")

        r = post(f"/v1/sessions/{sid}/run-auto", token=buyer_token, params={"max_rounds": 12})
        if r.status_code != 200:
            warn(f"  run-auto failed: {r.status_code} {r.text[:200]}")
            continue

        auto = r.json().get("data", {})
        sess = auto.get("session", {})
        for off in sorted(sess.get("offers", []), key=lambda x: x.get("round_number", 0)):
            print(f"  {off.get('round_number','?'):<5} {off.get('proposer_role','?')[:7]:<8} "
                  f"{off.get('price', 0):>12,.0f}  {(off.get('agent_reasoning') or '')[:50]}")

        status = sess.get("status", "UNKNOWN")
        price  = sess.get("agreed_price")
        rounds = sess.get("round_count", 0)
        if status == "AGREED":
            ok(f"  AGREED ✓  INR {price:,.0f}/kg  in {rounds} rounds")
            agreed.append({**s_info, "agreed_price": price, "rounds": rounds})
        else:
            info(f"  Terminal: {status} after {rounds} rounds")

    # ── Step 9: Best deal ─────────────────────────────────────────────────
    h("STEP 9 — Select Best Deal (lowest agreed price for buyer)")
    if not agreed:
        warn("No agreed sessions. Using first session as fallback.")
        if sessions:
            agreed = [{**sessions[0], "agreed_price": None, "rounds": 0}]
        else:
            err("No sessions at all"); sys.exit(1)

    best = min(agreed, key=lambda x: (x["agreed_price"] or float("inf")))
    ok(f"Winner: {best['legal_name']} at INR {best.get('agreed_price', 'N/A'):,.0f}/kg")
    winning_sid     = best["session_id"]
    winning_seller  = best["seller_token"]
    winning_name    = best["legal_name"]

    # ── Step 10: Escrow lifecycle ─────────────────────────────────────────
    h("STEP 10 — Escrow: PENDING_APPROVAL")
    r = post("/v1/escrow/select-deal", token=buyer_token, json={"session_id": winning_sid})
    if r.status_code in (200, 201):
        escrow_id = r.json()["data"].get("escrow_id") or r.json()["data"].get("id")
        ok(f"Escrow created: {escrow_id}")
    else:
        warn(f"select-deal: {r.status_code} {r.text[:200]}")
        r2 = get("/v1/escrow", token=buyer_token, params={"limit": 5})
        escrows = r2.json().get("data", []) if r2.status_code == 200 else []
        escrow_id = escrows[0]["escrow_id"] if escrows else None
        if not escrow_id: err("No escrow"); sys.exit(1)

    h("STEP 11 — Admin Approves")
    r = post(f"/v1/escrow/{escrow_id}/approve", token=admin_token)
    ok(f"Approved: {r.status_code}")

    h("STEP 12 — Platform Deploy (Algorand Testnet)")
    r = post(f"/v1/escrow/{winning_sid}/platform-deploy", token=buyer_token)
    if r.status_code in (200, 201):
        d = r.json()["data"]
        ok(f"Deployed — App ID: {d.get('app_id')}  TX: {d.get('tx_id', '')[:20]}...")
    else:
        warn(f"platform-deploy: {r.status_code} {r.text[:200]}")

    h("STEP 13 — Platform Fund")
    r = post(f"/v1/escrow/{escrow_id}/platform-fund", token=buyer_token)
    if r.status_code in (200, 201):
        d = r.json()["data"]
        ok(f"Funded — TX: {d.get('tx_id', '')[:20]}...  Status: {d.get('status')}")
    else:
        warn(f"platform-fund: {r.status_code} {r.text[:200]}")

    h("STEP 14 — Seller Dispatch  ★ (Bug-fix verification)")
    r = post(f"/v1/escrow/{escrow_id}/seller-dispatch", token=winning_seller)
    if r.status_code == 200:
        d = r.json()["data"]
        ok(f"{GREEN}{BOLD}DISPATCH SUCCESS — Status: {d.get('status')}{RESET}")
    else:
        err(f"DISPATCH FAILED: {r.status_code} — {r.text[:400]}")

    h("STEP 15 — Buyer Confirms Delivery")
    r = post(f"/v1/escrow/{escrow_id}/buyer-confirm", token=buyer_token)
    if r.status_code == 200:
        d = r.json()["data"]
        ok(f"RELEASED — TX: {d.get('tx_id', '')[:20]}...")
    else:
        warn(f"buyer-confirm: {r.status_code} — {r.text[:200]}")

    # ── Final summary ─────────────────────────────────────────────────────
    h("FINAL SUMMARY")
    print(f"""
  {BOLD}Industry : Pharmaceutical / Active Pharmaceutical Ingredients (API){RESET}
  {BOLD}RFQ      : 500 kg Paracetamol IP, budget INR 480–580/kg, 15-day delivery, Hyderabad{RESET}

  {BOLD}Match Scores (7-factor composite, 0–100):{RESET}
  {'Seller':<44} {'Expected':>10} {'Actual':>10}   {'Δ'}""")
    for sd in seller_data:
        eid    = sd["enterprise_id"]
        actual = match_map.get(eid, {}).get("score", "NO MATCH")
        actual_s = f"{actual:>8.2f}" if isinstance(actual, float) else f"{'NO MATCH':>8}"
        print(f"  {sd['legal_name']:<44} {sd['expected_score']:>10} {actual_s}   {sd['expected_score']}")

    print(f"\n  {BOLD}Negotiation Results:{RESET}")
    print(f"  {'Seller':<44} {'Rounds':>7}  {'Agreed Price':>14}")
    for a in agreed:
        print(f"  {a['legal_name']:<44} {a.get('rounds', '?'):>7}  INR {a.get('agreed_price', 'N/A'):>10,.0f}/kg")

    print(f"\n  {BOLD}Winner : {winning_name}{RESET}")
    print(f"  {BOLD}Price  : INR {best.get('agreed_price', 'N/A'):,.0f}/kg{RESET}")
    print(f"  {BOLD}Escrow : {escrow_id}{RESET}")
    print()


if __name__ == "__main__":
    main()
