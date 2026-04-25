# Onboarding & Negotiation Engine Activation Plan

## Current State Assessment

### What Exists
- **Actual Negotiation Engine**: Full 4-layer pipeline in `/backend/src/negotiation/` — Valuation, Strategy (8 game-theory strategies), LLM Advisory, Guardrail Veto. Production-ready code with Bayesian opponent modeling, convergence detection, stall handling, and SSE streaming.
- **Demo Mode Active**: `LLM_PROVIDER=stub` returns hardcoded 2% concession per round. Frontend uses MSW mock handlers (`/frontend/src/mocks/handlers/negotiation.ts`). Seed script creates fake enterprises.
- **Marketplace Matching**: pgvector cosine similarity between RFQ embeddings and seller capability profiles. Returns top-10 matches ranked by similarity score.
- **Registration Flow**: 3-step form capturing legal name, PAN, GSTIN, trade role, commodities list, order value range, industry vertical, and a free-text "geography" field (defaults to "IN").

### Critical Gaps Blocking Production

| Gap | Why It Matters |
|-----|---------------|
| No precise location (city, pincode, coordinates) | Cannot compute delivery timelines or logistics feasibility |
| No production/manufacturing capacity | Cannot validate if seller can fulfill order volume |
| No product catalogue with unit pricing | Negotiation engine has no price anchors; buyers cannot browse offerings |
| No lead time or manufacturing timeline data | Cannot determine if delivery window is achievable |
| No delivery radius or logistics capability | No way to match buyers with geographically feasible sellers |
| No MOQ/max capacity per product | Risk of assigning impossible orders to small manufacturers |
| No warehouse/facility location | Delivery distance calculation impossible |
| Geography field is free-text "IN" | Useless for any distance or time computation |

---

## Part 1: Enhanced Seller Onboarding

### 1.1 Seller Registration — New Fields

Add to `EnterpriseCreateRequest` and `Enterprise` domain model:

**Location & Facility (required for sellers)**
| Field | Type | Validation | Purpose |
|-------|------|-----------|---------|
| `facility_address_line1` | string | min 5 chars | Street address of primary manufacturing/warehouse |
| `facility_address_line2` | string | optional | Additional address line |
| `city` | string | min 2 chars | City name (e.g., "Raipur", "Jamshedpur") |
| `state` | string | enum of 36 Indian states/UTs | State (cross-validated against GSTIN prefix) |
| `pincode` | string | regex `^\d{6}$` | 6-digit Indian postal code |
| `latitude` | float | -90 to 90, optional | Auto-filled from pincode or manual pin on map |
| `longitude` | float | -180 to 180, optional | Auto-filled from pincode or manual pin on map |
| `facility_type` | enum | MANUFACTURING_PLANT, WAREHOUSE, TRADING_OFFICE, INTEGRATED | Type of facility |

**Production Capacity (required for sellers)**
| Field | Type | Validation | Purpose |
|-------|------|-----------|---------|
| `monthly_production_capacity_mt` | decimal | > 0 | Maximum output in metric tons per month |
| `current_utilization_pct` | integer | 0-100, optional | Current plant utilization (helps estimate available capacity) |
| `available_capacity_mt` | decimal | computed or manual | = monthly_capacity * (1 - utilization/100), or manually entered |
| `num_production_lines` | integer | >= 1, optional | Number of active production lines |
| `shift_pattern` | enum | SINGLE_SHIFT, DOUBLE_SHIFT, TRIPLE_SHIFT, CONTINUOUS | Operating schedule |

**Logistics & Delivery**
| Field | Type | Validation | Purpose |
|-------|------|-----------|---------|
| `max_delivery_radius_km` | integer | 50-5000, optional | Maximum distance seller is willing to deliver |
| `avg_dispatch_days` | integer | 1-90 | Average days from order confirmation to dispatch |
| `has_own_transport` | boolean | default false | Whether seller has own fleet |
| `preferred_transport_modes` | list[enum] | ROAD, RAIL, SEA, AIR | Available transport modes |
| `ex_works_available` | boolean | default true | Whether buyer can arrange own pickup |

**Business Terms**
| Field | Type | Validation | Purpose |
|-------|------|-----------|---------|
| `payment_terms_accepted` | list[enum] | ADVANCE, LC_AT_SIGHT, LC_30, LC_60, NET_30, NET_60, NET_90 | Accepted payment methods |
| `credit_period_days` | integer | 0-180, optional | Max credit period offered |
| `minimum_order_value_inr` | decimal | >= 0 | Minimum order value in INR |
| `annual_turnover_inr` | decimal | optional | Annual business turnover (trust signal) |
| `years_in_operation` | integer | >= 0 | Years the business has been operating |

### 1.2 Seller Product Catalogue

New domain entity: `CatalogueItem` — each seller lists the products they can supply with pricing and specs.

**CatalogueItem Schema**
| Field | Type | Validation | Purpose |
|-------|------|-----------|---------|
| `id` | UUID | auto-generated | Primary key |
| `enterprise_id` | UUID | FK to enterprises | Owner seller |
| `product_name` | string | min 3, max 200 | e.g., "TMT Bar Fe500D" |
| `hsn_code` | string | regex `^\d{4,8}$` | Harmonized System Nomenclature code |
| `product_category` | enum | HR_COIL, CR_COIL, TMT_BAR, WIRE_ROD, BILLET, SLAB, PLATE, PIPE, SHEET, ANGLE, CHANNEL, BEAM, CUSTOM | Material category |
| `grade` | string | optional | e.g., "E250", "Fe500D", "IS 2062" |
| `specification_text` | string | optional, max 2000 | Detailed specs (thickness, width, length, etc.) |
| `unit` | enum | MT (metric ton), KG, PIECE, BUNDLE, COIL | Pricing unit |
| `price_per_unit_inr` | decimal | > 0 | Base price per unit (e.g., Rs 45,000/MT) |
| `bulk_pricing_tiers` | JSONB | optional | e.g., `[{"min_qty": 10, "max_qty": 50, "price": 44000}, {"min_qty": 50, "price": 42500}]` |
| `moq` | decimal | > 0 | Minimum order quantity in the stated unit |
| `max_order_qty` | decimal | > moq | Maximum single order (based on capacity) |
| `lead_time_days` | integer | 1-180 | Manufacturing + preparation time for this product |
| `in_stock_qty` | decimal | >= 0, optional | Ready stock available for immediate dispatch |
| `is_active` | boolean | default true | Whether currently available |
| `certifications` | list[string] | optional | e.g., ["ISO 9001", "BIS", "RDSO"] |
| `created_at` | datetime | auto | |
| `updated_at` | datetime | auto | |

**Bulk Pricing Tier Schema (JSONB)**
```json
[
  { "min_qty_mt": 1, "max_qty_mt": 10, "price_per_mt_inr": 48000 },
  { "min_qty_mt": 10, "max_qty_mt": 50, "price_per_mt_inr": 45000 },
  { "min_qty_mt": 50, "max_qty_mt": null, "price_per_mt_inr": 42500 }
]
```

### 1.3 Seller Quality & Certifications
| Field | Type | Purpose |
|-------|------|---------|
| `quality_certifications` | list[string] | ISO 9001, BIS, RDSO, NABL, etc. |
| `environmental_certifications` | list[string] | ISO 14001, EMS, etc. |
| `test_certificate_available` | boolean | Whether mill test certificates are provided with shipment |
| `third_party_inspection_allowed` | boolean | Whether buyer can send inspector |

---

## Part 2: Enhanced Buyer Onboarding

### 2.1 Buyer Registration — New Fields

**Location & Delivery (required for buyers)**
| Field | Type | Validation | Purpose |
|-------|------|-----------|---------|
| `delivery_address_line1` | string | min 5 chars | Primary delivery/site address |
| `delivery_address_line2` | string | optional | |
| `city` | string | min 2 chars | Delivery city |
| `state` | string | enum of 36 states/UTs | Delivery state |
| `pincode` | string | regex `^\d{6}$` | Delivery pincode |
| `latitude` | float | optional | Auto-filled from pincode |
| `longitude` | float | optional | Auto-filled from pincode |
| `site_type` | enum | CONSTRUCTION_SITE, FACTORY, WAREHOUSE, RETAIL_STORE, PROJECT_SITE | Type of delivery location |

**Procurement Profile**
| Field | Type | Validation | Purpose |
|-------|------|-----------|---------|
| `typical_order_frequency` | enum | WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY, ONE_TIME | How often they order |
| `annual_procurement_volume_mt` | decimal | optional | Annual volume helps sellers prioritize |
| `preferred_payment_terms` | list[enum] | ADVANCE, LC_AT_SIGHT, LC_30, LC_60, NET_30, NET_60 | Buyer's preferred payment modes |
| `max_acceptable_lead_time_days` | integer | 1-180 | Default maximum delivery window |
| `requires_test_certificate` | boolean | default false | Whether TC is mandatory |
| `requires_third_party_inspection` | boolean | default false | Whether TPI is needed |
| `preferred_brands` | list[string] | optional | Brand preferences (e.g., "JSW", "SAIL", "Tata") |

---

## Part 3: Delivery Feasibility Engine

### 3.1 The Core Problem

> A buyer in Delhi wants 10 tons of TMT bars within 10 days. A seller in Mumbai has the material. But Mumbai-to-Delhi transit alone takes 5-7 days by road. Manufacturing lead time is 3-5 days. Total: 8-12 days. This deal should NOT be matched.

### 3.2 Distance & Transit Time Calculation

**Approach**: Use pincode-to-pincode distance matrix.

1. **Pincode Geocoding Table**: Maintain a table of ~19,000 Indian pincodes with lat/lng coordinates (publicly available from India Post / data.gov.in).
2. **Haversine Distance**: Calculate straight-line distance between seller facility pincode and buyer delivery pincode.
3. **Road Distance Multiplier**: Apply 1.3x multiplier to haversine distance for approximate road distance (India's road network is ~30% longer than straight-line on average).
4. **Transit Time Estimation**:

| Distance (km) | Mode | Estimated Transit Days |
|---------------|------|----------------------|
| 0-200 | Road | 1-2 days |
| 200-500 | Road | 2-3 days |
| 500-1000 | Road/Rail | 3-5 days |
| 1000-1500 | Road/Rail | 5-7 days |
| 1500-2500 | Rail/Road | 7-10 days |
| 2500+ | Rail/Sea | 10-15 days |

5. **Buffer Days**: Add 1-2 days for loading, documentation, and unloading.

### 3.3 Feasibility Check Formula

```
total_required_days = seller.lead_time_days (manufacturing)
                    + estimated_transit_days (logistics)
                    + buffer_days (loading/unloading/docs)

is_feasible = total_required_days <= buyer.delivery_window_days
```

**This check runs BEFORE matching**, filtering out infeasible sellers from the pgvector similarity results.

### 3.4 Capacity Feasibility Check

```
is_capacity_feasible = (
    buyer.requested_qty_mt <= seller.available_capacity_mt
    AND buyer.requested_qty_mt >= catalogue_item.moq
    AND buyer.requested_qty_mt <= catalogue_item.max_order_qty
)
```

If the buyer wants 100 MT and the seller's max capacity is 10 MT/month, this match is rejected unless the buyer's delivery window spans multiple months.

**Multi-month capacity check**:
```
months_available = buyer.delivery_window_days / 30
can_fulfill = buyer.requested_qty_mt <= (seller.available_capacity_mt * months_available)
```

---

## Part 4: Matching Engine Enhancement

### 4.1 Current Matching (pgvector only)

Current: RFQ embedding vs seller profile embedding → cosine similarity → top 10.

**Problem**: Pure semantic matching ignores logistics, capacity, and pricing feasibility.

### 4.2 Enhanced Multi-Factor Matching

Replace single-score ranking with a **weighted composite score**:

```
match_score = (
    w1 * semantic_similarity          # product/spec match (current pgvector)
  + w2 * delivery_feasibility_score   # 1.0 if comfortably feasible, 0 if impossible
  + w3 * capacity_score               # 1.0 if seller can fulfill 100%, scaled down
  + w4 * price_competitiveness        # how seller's catalogue price compares to buyer budget
  + w5 * location_proximity_score     # closer = higher score (normalized 0-1)
  + w6 * payment_terms_compatibility  # 1.0 if buyer's preferred terms match seller's accepted terms
  + w7 * certification_match          # 1.0 if seller has all required certs
)

Default weights: w1=0.25, w2=0.20, w3=0.15, w4=0.15, w5=0.10, w6=0.10, w7=0.05
```

### 4.3 Hard Filters (must pass before scoring)

These are binary pass/fail checks — a seller failing any of these is excluded entirely:

1. **Delivery feasibility**: `total_required_days <= buyer.delivery_window_days`
2. **Capacity feasibility**: seller can produce the requested quantity within the delivery window
3. **Product availability**: seller has an active catalogue item matching the requested product category
4. **Minimum order**: buyer's quantity >= seller's MOQ for that product
5. **Geographic willingness**: delivery distance <= seller's `max_delivery_radius_km` (if set)

### 4.4 Soft Scoring Factors

After hard filters, remaining sellers are scored:

| Factor | Score Calculation |
|--------|------------------|
| Semantic similarity | Current pgvector cosine score (0-1) |
| Delivery margin | `1 - (total_required_days / delivery_window_days)` — more buffer = higher score |
| Capacity headroom | `min(1.0, seller_available / buyer_requested)` |
| Price competitiveness | `1 - abs(seller_price - buyer_budget_mid) / buyer_budget_mid` clamped 0-1 |
| Proximity | `1 - min(distance_km / 2500, 1.0)` — normalized to max 2500 km |
| Payment compatibility | overlap count between buyer preferred and seller accepted / total buyer preferred |
| Certification match | certs buyer requires that seller has / total buyer requires |

---

## Part 5: Activating the Real Negotiation Engine

### 5.1 Environment Configuration Changes

Switch from demo to production negotiation:

```env
# .env changes for production negotiation
LLM_PROVIDER=google          # or "openai" — NOT "stub"
GEMINI_API_KEY=<key>          # or OPENAI_API_KEY
EMBEDDING_PROVIDER=google     # for pgvector embeddings
NEXT_PUBLIC_API_MOCKING=false # disable frontend MSW mocks
```

### 5.2 Feed Catalogue Data into Negotiation Valuation Layer

The Valuation Layer (`/backend/src/negotiation/infrastructure/valuation.py`) currently computes pricing bounds from `RiskProfile` and `AgentProfile`. Enhance it to use catalogue data:

**Seller side:**
- `reservation_price` = catalogue item's base `price_per_unit_inr` (minimum seller will accept)
- `target_price` = catalogue price + seller's margin target (from `agent_config`)
- `opening_price` = apply bulk pricing tier for buyer's quantity

**Buyer side:**
- `reservation_price` = buyer's `budget_max` from RFQ
- `target_price` = buyer's `budget_min` from RFQ (ideal low price)
- `opening_price` = slightly below target (anchor strategy)

### 5.3 Inject Logistics Context into LLM Advisory Layer

Pass delivery feasibility data to the LLM prompt so the agent can factor in urgency:

```python
logistics_context = {
    "distance_km": 850,
    "estimated_transit_days": 4,
    "manufacturing_lead_days": 7,
    "total_estimated_days": 12,
    "buyer_deadline_days": 15,
    "time_buffer_days": 3,         # how much slack
    "urgency_level": "MODERATE"    # LOW / MODERATE / HIGH / CRITICAL
}
```

Urgency levels affect negotiation strategy:
- **LOW** (>10 days buffer): Normal negotiation, more rounds allowed
- **MODERATE** (5-10 days buffer): Slightly faster convergence
- **HIGH** (2-5 days buffer): Reduce max rounds, push for quick agreement
- **CRITICAL** (<2 days buffer): Aggressive convergence, recommend immediate acceptance

### 5.4 Disable Frontend Mocks

In `/frontend/src/components/providers/MSWProvider.tsx`, the MSW provider is conditionally loaded. For production:

1. Set `NEXT_PUBLIC_API_MOCKING=false` in frontend `.env.production`
2. Verify all API calls hit the real backend endpoints
3. Remove or gate any hardcoded mock data in page components

---

## Part 6: Database Schema Changes

### 6.1 New Tables

**`addresses`** — Reusable address entity (seller facility, buyer delivery site)
```sql
CREATE TABLE addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID NOT NULL REFERENCES enterprises(id) ON DELETE CASCADE,
    address_type VARCHAR(30) NOT NULL,  -- FACILITY, DELIVERY, REGISTERED_OFFICE
    address_line1 VARCHAR(500) NOT NULL,
    address_line2 VARCHAR(500),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    pincode VARCHAR(6) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_primary BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_addresses_enterprise ON addresses(enterprise_id);
CREATE INDEX idx_addresses_pincode ON addresses(pincode);
CREATE INDEX idx_addresses_coords ON addresses(latitude, longitude);
```

**`catalogue_items`** — Seller product catalogue
```sql
CREATE TABLE catalogue_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID NOT NULL REFERENCES enterprises(id) ON DELETE CASCADE,
    product_name VARCHAR(200) NOT NULL,
    hsn_code VARCHAR(8) NOT NULL,
    product_category VARCHAR(50) NOT NULL,
    grade VARCHAR(100),
    specification_text TEXT,
    unit VARCHAR(20) NOT NULL DEFAULT 'MT',
    price_per_unit_inr NUMERIC(18, 4) NOT NULL,
    bulk_pricing_tiers JSONB,
    moq NUMERIC(12, 4) NOT NULL,
    max_order_qty NUMERIC(12, 4) NOT NULL,
    lead_time_days INTEGER NOT NULL,
    in_stock_qty NUMERIC(12, 4) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    certifications TEXT[],
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT chk_moq_positive CHECK (moq > 0),
    CONSTRAINT chk_max_gt_moq CHECK (max_order_qty >= moq),
    CONSTRAINT chk_price_positive CHECK (price_per_unit_inr > 0),
    CONSTRAINT chk_lead_time CHECK (lead_time_days BETWEEN 1 AND 180)
);
CREATE INDEX idx_catalogue_enterprise ON catalogue_items(enterprise_id);
CREATE INDEX idx_catalogue_category ON catalogue_items(product_category);
CREATE INDEX idx_catalogue_active ON catalogue_items(is_active) WHERE is_active = true;
```

**`seller_capacity_profiles`** — Production capacity data
```sql
CREATE TABLE seller_capacity_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID UNIQUE NOT NULL REFERENCES enterprises(id) ON DELETE CASCADE,
    monthly_production_capacity_mt NUMERIC(12, 4) NOT NULL,
    current_utilization_pct INTEGER DEFAULT 0,
    available_capacity_mt NUMERIC(12, 4),
    num_production_lines INTEGER DEFAULT 1,
    shift_pattern VARCHAR(30) DEFAULT 'SINGLE_SHIFT',
    avg_dispatch_days INTEGER NOT NULL DEFAULT 3,
    max_delivery_radius_km INTEGER,
    has_own_transport BOOLEAN DEFAULT false,
    preferred_transport_modes TEXT[],
    ex_works_available BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT chk_capacity_positive CHECK (monthly_production_capacity_mt > 0),
    CONSTRAINT chk_utilization_range CHECK (current_utilization_pct BETWEEN 0 AND 100)
);
```

**`pincode_geocodes`** — Indian pincode lookup (~19,000 rows, seeded once)
```sql
CREATE TABLE pincode_geocodes (
    pincode VARCHAR(6) PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    region VARCHAR(20)  -- NORTH, SOUTH, EAST, WEST, CENTRAL, NORTHEAST
);
CREATE INDEX idx_pincode_state ON pincode_geocodes(state);
CREATE INDEX idx_pincode_coords ON pincode_geocodes(latitude, longitude);
```

### 6.2 Altered Tables

**`enterprises`** — Add columns:
```sql
ALTER TABLE enterprises ADD COLUMN facility_type VARCHAR(30);
ALTER TABLE enterprises ADD COLUMN payment_terms_accepted TEXT[];
ALTER TABLE enterprises ADD COLUMN credit_period_days INTEGER;
ALTER TABLE enterprises ADD COLUMN years_in_operation INTEGER;
ALTER TABLE enterprises ADD COLUMN annual_turnover_inr NUMERIC(18, 2);
ALTER TABLE enterprises ADD COLUMN quality_certifications TEXT[];
ALTER TABLE enterprises ADD COLUMN test_certificate_available BOOLEAN DEFAULT false;
ALTER TABLE enterprises ADD COLUMN third_party_inspection_allowed BOOLEAN DEFAULT false;
```

**`rfqs`** — Add columns for buyer delivery precision:
```sql
ALTER TABLE rfqs ADD COLUMN delivery_pincode VARCHAR(6);
ALTER TABLE rfqs ADD COLUMN delivery_city VARCHAR(100);
ALTER TABLE rfqs ADD COLUMN delivery_state VARCHAR(50);
ALTER TABLE rfqs ADD COLUMN max_acceptable_lead_time_days INTEGER;
ALTER TABLE rfqs ADD COLUMN requires_test_certificate BOOLEAN DEFAULT false;
ALTER TABLE rfqs ADD COLUMN preferred_payment_terms TEXT[];
```

**`matches`** — Add scoring breakdown:
```sql
ALTER TABLE matches ADD COLUMN semantic_score FLOAT;
ALTER TABLE matches ADD COLUMN delivery_feasibility_score FLOAT;
ALTER TABLE matches ADD COLUMN capacity_score FLOAT;
ALTER TABLE matches ADD COLUMN price_score FLOAT;
ALTER TABLE matches ADD COLUMN proximity_score FLOAT;
ALTER TABLE matches ADD COLUMN composite_score FLOAT;
ALTER TABLE matches ADD COLUMN estimated_delivery_days INTEGER;
ALTER TABLE matches ADD COLUMN distance_km INTEGER;
```

---

## Part 7: Frontend Changes

### 7.1 Seller Registration Form — Enhanced Steps

**Current**: 3 steps (Enterprise Info, Account, Review)
**New**: 5 steps

| Step | Content |
|------|---------|
| 1. Enterprise Info | Legal name, PAN, GSTIN, trade role, industry vertical (existing) |
| 2. Facility & Location | Address, city, state, pincode (auto-fill lat/lng), facility type, map pin confirmation |
| 3. Production & Catalogue | Monthly capacity, shift pattern, dispatch days, delivery radius, transport modes. Inline catalogue builder: add products with pricing tiers, MOQ, lead times |
| 4. Account Details | Full name, email, password (existing) |
| 5. Review & Submit | All-in-one summary with edit buttons per section |

### 7.2 Buyer Registration Form — Enhanced Steps

**Current**: 3 steps (Enterprise Info, Account, Review)
**New**: 4 steps

| Step | Content |
|------|---------|
| 1. Enterprise Info | Legal name, PAN, GSTIN, trade role, industry vertical (existing) |
| 2. Delivery Location | Primary delivery address, city, state, pincode, site type, map pin confirmation |
| 3. Account Details | Full name, email, password (existing), procurement preferences (order frequency, volume, payment terms, lead time tolerance) |
| 4. Review & Submit | Summary with edit buttons |

### 7.3 Seller Catalogue Management Page

New page: `/marketplace/catalogue`

- **Product list view**: Table of all catalogue items with inline editing
- **Add product form**: Product name, HSN code, category dropdown, grade, specs, unit, base price
- **Bulk pricing builder**: Dynamic row-add for quantity tiers with price per tier
- **Stock management**: Update in-stock quantity
- **Activate/deactivate toggle**: Per product
- **Bulk import**: CSV upload for initial catalogue population

### 7.4 Enhanced RFQ Submission

Update `/marketplace/page.tsx` to capture:
- Delivery pincode (with city/state auto-fill from pincode table)
- Firm delivery deadline (date picker, converted to `delivery_window_days`)
- Whether test certificate is required
- Preferred payment terms (multi-select)
- Quantity validation against typical market ranges

### 7.5 Match Results Display

Update match results to show:
- Distance from seller to buyer (km)
- Estimated delivery timeline breakdown (manufacturing + transit + buffer)
- Feasibility indicator (green/yellow/red based on buffer days)
- Price range from seller's catalogue
- Seller capacity vs requested quantity
- Composite score breakdown (expandable)

---

## Part 8: Implementation Plan

### Phase 1: Database & Models (3-5 days)

**Priority: CRITICAL — everything else depends on this**

| # | Task | Files Affected |
|---|------|---------------|
| 1.1 | Create Alembic migration for `addresses`, `catalogue_items`, `seller_capacity_profiles`, `pincode_geocodes` tables | `backend/alembic/versions/013_*.py` |
| 1.2 | Add new columns to `enterprises`, `rfqs`, `matches` tables | Same migration |
| 1.3 | Seed `pincode_geocodes` with India Post data (~19K rows) | `backend/scripts/seed_pincodes.py` |
| 1.4 | Create SQLAlchemy models: `AddressModel`, `CatalogueItemModel`, `SellerCapacityProfileModel`, `PincodeGeocodeModel` | `backend/src/marketplace/infrastructure/models.py` |
| 1.5 | Create domain entities: `Address`, `CatalogueItem`, `SellerCapacityProfile` | `backend/src/marketplace/domain/` |
| 1.6 | Create Pydantic schemas for all new entities (create, update, response) | `backend/src/marketplace/api/schemas.py`, `backend/src/identity/api/schemas.py` |
| 1.7 | Update `Enterprise` domain model and `EnterpriseCreateRequest` schema with new fields | `backend/src/identity/domain/enterprise.py`, `backend/src/identity/api/schemas.py` |

### Phase 2: Seller Catalogue API (2-3 days)

| # | Task | Files Affected |
|---|------|---------------|
| 2.1 | CRUD endpoints for catalogue items: POST, GET (list), GET (by id), PUT, DELETE | `backend/src/marketplace/api/router.py` |
| 2.2 | Bulk pricing tier validation (tiers must not overlap, must cover full range) | `backend/src/marketplace/api/schemas.py` |
| 2.3 | CSV bulk import endpoint for catalogue | `backend/src/marketplace/api/router.py` |
| 2.4 | Seller capacity profile CRUD (PUT to create/update, GET to retrieve) | `backend/src/marketplace/api/router.py` |
| 2.5 | Address CRUD with pincode auto-geocoding | `backend/src/identity/api/router.py` |
| 2.6 | Update capability profile embedding to include catalogue data | `backend/src/marketplace/infrastructure/embedding_service.py` |

### Phase 3: Delivery Feasibility Service (2-3 days)

| # | Task | Files Affected |
|---|------|---------------|
| 3.1 | Create `DeliveryFeasibilityService` with haversine distance calc | `backend/src/marketplace/infrastructure/delivery_feasibility.py` (new) |
| 3.2 | Transit time estimator (distance-to-days lookup, transport mode aware) | Same file |
| 3.3 | Total timeline calculator: manufacturing lead time + transit + buffer | Same file |
| 3.4 | Capacity feasibility checker (single-month and multi-month) | Same file |
| 3.5 | Integration tests for distance/time calculations with known city pairs | `backend/tests/unit/test_delivery_feasibility.py` (new) |

### Phase 4: Enhanced Matching Engine (3-4 days)

| # | Task | Files Affected |
|---|------|---------------|
| 4.1 | Add hard filter pipeline (delivery feasibility, capacity, product match, MOQ, radius) | `backend/src/marketplace/infrastructure/pgvector_matchmaker.py` |
| 4.2 | Add soft scoring pipeline (7-factor composite score) | Same file |
| 4.3 | Store scoring breakdown in `matches` table | `backend/src/marketplace/infrastructure/models.py` |
| 4.4 | Update match API response to include score breakdown and delivery estimates | `backend/src/marketplace/api/schemas.py`, `router.py` |
| 4.5 | Update RFQ parsing to extract delivery pincode, timeline, payment terms | `backend/src/marketplace/domain/rfq.py` |
| 4.6 | Add configurable scoring weights (per-enterprise or global config) | `backend/src/marketplace/domain/` |

### Phase 5: Negotiation Engine Activation (2-3 days)

| # | Task | Files Affected |
|---|------|---------------|
| 5.1 | Update `.env` to switch `LLM_PROVIDER` from `stub` to production provider | `backend/.env` |
| 5.2 | Update valuation layer to pull pricing from catalogue + bulk tiers | `backend/src/negotiation/infrastructure/valuation.py` |
| 5.3 | Inject logistics context (distance, transit time, urgency) into LLM prompt | `backend/src/negotiation/infrastructure/llm_agent_driver.py` |
| 5.4 | Add urgency-aware round limits (CRITICAL urgency = fewer rounds) | `backend/src/negotiation/infrastructure/strategy.py` |
| 5.5 | Update session creation to pass delivery feasibility data | `backend/src/negotiation/application/services.py` |
| 5.6 | Verify guardrails use catalogue-based price bounds | `backend/src/negotiation/infrastructure/guardrails.py` |
| 5.7 | End-to-end test: RFQ → match → negotiate → agree | `backend/tests/e2e/test_full_negotiation_flow.py` |

### Phase 6: Frontend — Registration Enhancement (3-4 days)

| # | Task | Files Affected |
|---|------|---------------|
| 6.1 | Update seller registration to 5-step flow with new fields | `frontend/src/app/(auth)/register/page.tsx` |
| 6.2 | Add pincode auto-fill component (city, state from pincode lookup API) | `frontend/src/components/shared/PincodeLookup.tsx` (new) |
| 6.3 | Add map pin component for location confirmation (Leaflet or Google Maps lite) | `frontend/src/components/shared/LocationPicker.tsx` (new) |
| 6.4 | Update buyer registration to 4-step flow with delivery location | Same registration page (conditionally rendered) |
| 6.5 | Update Zod validation schemas for all new fields | Registration page |
| 6.6 | Update MSW mock handlers for new registration fields (dev mode) | `frontend/src/mocks/handlers/auth.ts` |

### Phase 7: Frontend — Catalogue & Matching UI (3-4 days)

| # | Task | Files Affected |
|---|------|---------------|
| 7.1 | Build seller catalogue management page | `frontend/src/app/marketplace/catalogue/page.tsx` (new) |
| 7.2 | Bulk pricing tier builder component | `frontend/src/components/shared/BulkPricingBuilder.tsx` (new) |
| 7.3 | CSV import modal for catalogue | Part of catalogue page |
| 7.4 | Update RFQ submission form with delivery pincode, deadline, payment terms | `frontend/src/app/marketplace/page.tsx` |
| 7.5 | Update match results display with feasibility indicators and score breakdown | `frontend/src/app/marketplace/page.tsx` |
| 7.6 | Add sidebar nav entry for "Catalogue" under marketplace section | `frontend/src/components/layout/Sidebar.tsx` |
| 7.7 | Disable MSW for negotiation endpoints (`NEXT_PUBLIC_API_MOCKING=false`) | `frontend/.env.production` |

### Phase 8: Testing & Validation (2-3 days)

| # | Task | Details |
|---|------|---------|
| 8.1 | Unit tests for delivery feasibility calculations | Distance, transit time, total timeline |
| 8.2 | Unit tests for capacity feasibility (single-month, multi-month) | Edge cases: exact capacity, 0 available, overflow |
| 8.3 | Integration tests for enhanced matching pipeline | Hard filters + soft scoring with known data |
| 8.4 | E2E test: Delhi buyer, Mumbai seller, 10-day window → should NOT match | Validates the core scenario from requirements |
| 8.5 | E2E test: Delhi buyer, Ghaziabad seller, 10-day window → SHOULD match | Same product, nearby city |
| 8.6 | E2E test: Full flow from registration → catalogue → RFQ → match → negotiate → agree | Happy path |
| 8.7 | Load test: 100 sellers, 50 concurrent RFQs → matching latency < 2s | Performance validation |
| 8.8 | Seed script update for realistic demo data with all new fields | `backend/scripts/seed_demo_data.py` |

---

## Part 9: Business Logic Rules Summary

These are the non-obvious rules that the system must enforce:

| Rule | Logic | Where Enforced |
|------|-------|---------------|
| **Delivery window must cover manufacturing + transit + buffer** | `seller.lead_time + transit_days + 2 <= buyer.delivery_window` | Matching hard filter |
| **Seller cannot accept orders beyond capacity** | `order_qty <= seller.available_capacity * (delivery_window / 30)` | Matching hard filter |
| **Order quantity must meet seller's MOQ** | `order_qty >= catalogue_item.moq` | Matching hard filter |
| **Order quantity must not exceed seller's max** | `order_qty <= catalogue_item.max_order_qty` | Matching hard filter |
| **Seller must have matching product category** | At least one active catalogue item matches RFQ product | Matching hard filter |
| **GSTIN state code must match registered state** | First 2 digits of GSTIN = state code | Registration validation |
| **Negotiation price bounds from catalogue** | Seller's reservation price >= catalogue base price for that qty tier | Valuation layer |
| **Urgency affects negotiation rounds** | CRITICAL urgency = max 3 rounds; HIGH = max 5; MODERATE = max 8; LOW = configurable | Strategy layer |
| **Payment terms must have overlap** | At least one common payment term between buyer and seller | Matching soft filter (score=0 if no overlap) |
| **Price per unit uses correct bulk tier** | Quantity-based tier lookup from seller's bulk pricing JSONB | Valuation + matching |
| **Available capacity auto-decrement** | When order confirmed, reduce `available_capacity_mt` | Post-settlement hook |
| **Seller location must be within delivery radius** | If seller sets max_delivery_radius_km, buyer must be within it | Matching hard filter |

---

## Part 10: Risk Considerations

| Risk | Mitigation |
|------|-----------|
| Pincode geocoding data may be incomplete or inaccurate | Use official India Post dataset; allow manual lat/lng override; fallback to city-level matching |
| Transit time estimates are approximations | Use conservative estimates; add configurable buffer; allow seller to override per-order |
| LLM negotiation may produce unreasonable offers | Guardrail layer already validates against budget/margin bounds; catalogue prices add another anchor |
| Seller may not update capacity after fulfilling orders | Auto-decrement on settlement; periodic capacity reconciliation reminders |
| Bulk pricing tiers may have gaps or overlaps | Validate tiers on save: no gaps, no overlaps, contiguous ranges |
| Buyer and seller in same city but different sides of city | Pincode-level precision handles this (each pincode covers ~3-5 km radius) |
| Seller lists incorrect lead times | Track actual delivery performance over time; flag sellers with consistently late deliveries |

---

## Estimated Total Timeline

| Phase | Duration | Dependencies |
|-------|----------|-------------|
| Phase 1: Database & Models | 3-5 days | None |
| Phase 2: Seller Catalogue API | 2-3 days | Phase 1 |
| Phase 3: Delivery Feasibility | 2-3 days | Phase 1 |
| Phase 4: Enhanced Matching | 3-4 days | Phase 2, 3 |
| Phase 5: Negotiation Activation | 2-3 days | Phase 2, 4 |
| Phase 6: Frontend Registration | 3-4 days | Phase 1, 2 |
| Phase 7: Frontend Catalogue & UI | 3-4 days | Phase 2, 6 |
| Phase 8: Testing & Validation | 2-3 days | All phases |
| **Total (with parallelism)** | **~15-20 working days** | Phases 2, 3, 6 can run in parallel |

---

## File Change Summary

| Action | Count | Key Files |
|--------|-------|-----------|
| New backend files | ~8 | delivery_feasibility.py, new models, schemas, migration, seed script |
| Modified backend files | ~12 | Enterprise model, identity schemas/router, marketplace matchmaker/router/schemas, negotiation valuation/strategy/services, env config |
| New frontend files | ~4 | catalogue page, PincodeLookup, LocationPicker, BulkPricingBuilder |
| Modified frontend files | ~6 | registration page, marketplace page, sidebar, MSW handlers, env config |
| New migration | 1 | 013_enhanced_onboarding.py |
| New seed script | 1 | seed_pincodes.py |
