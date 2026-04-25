#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# Cadencia — User Seed Script
# Creates 5 buyers, 5 sellers, and 1 admin account via the API.
# Also sets up seller capability profiles and catalogue items.
#
# Usage:
#   chmod +x cadencia-user-seed.sh
#   ./cadencia-user-seed.sh
#
# Prerequisites:
#   - Backend running on http://localhost:8000
#   - curl and jq installed
#
# Default credentials:
#   All users:  Password = Cadencia@2026
#   Admin:      admin@cadencia.io / Admin@1234
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
PASSWORD="Cadencia@2026"
ADMIN_EMAIL="admin@cadencia.io"
ADMIN_PASSWORD="Admin@1234"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

success() { echo -e "${GREEN}[OK]${NC} $1"; }
info()    { echo -e "${CYAN}[..]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!!]${NC} $1"; }
fail()    { echo -e "${RED}[FAIL]${NC} $1"; }

# ── Health check ───────────────────────────────────────────────────────────

info "Checking backend health at $API_URL..."
HEALTH=$(curl -sf "$API_URL/health" 2>/dev/null || echo "")
if [ -z "$HEALTH" ]; then
  fail "Backend is not reachable at $API_URL"
  echo "  Start the backend first, then re-run this script."
  exit 1
fi
success "Backend is healthy"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# BUYER ENTERPRISES (5)
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${CYAN}━━━ Registering 5 Buyer Enterprises ━━━${NC}"

# Buyer 1: Tata Steel
info "Registering Buyer 1: Tata Steel Procurement Ltd..."
curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "Tata Steel Procurement Ltd",
      "pan": "AAACT1234A",
      "gstin": "27AAACT1234A1Z5",
      "trade_role": "BUYER",
      "commodities": ["HR Coil", "CR Coil", "Steel Plates"],
      "industry_vertical": "Steel Manufacturing",
      "geography": "IN",
      "min_order_value": 500000,
      "max_order_value": 50000000,
      "address": {
        "address_type": "REGISTERED_OFFICE",
        "address_line1": "Bombay House, 24 Homi Mody Street",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400001"
      },
      "years_in_operation": 115,
      "annual_turnover_inr": 250000000000
    },
    "user": {
      "email": "buyer1@tatasteel.com",
      "password": "'"$PASSWORD"'",
      "full_name": "Rahul Sharma",
      "role": "ADMIN"
    }
  }' > /dev/null && success "Tata Steel Procurement Ltd" || warn "Tata Steel (may already exist)"

# Buyer 2: Hindalco Industries
info "Registering Buyer 2: Hindalco Industries Ltd..."
curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "Hindalco Industries Ltd",
      "pan": "AABCH5678B",
      "gstin": "27AABCH5678B1Z3",
      "trade_role": "BUYER",
      "commodities": ["Aluminium Ingots", "Copper Cathodes", "Steel Billets"],
      "industry_vertical": "Non-Ferrous Metals",
      "geography": "IN",
      "min_order_value": 1000000,
      "max_order_value": 100000000,
      "address": {
        "address_type": "REGISTERED_OFFICE",
        "address_line1": "Century Bhavan, Dr Annie Besant Road",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400030"
      },
      "years_in_operation": 65,
      "annual_turnover_inr": 195000000000
    },
    "user": {
      "email": "buyer2@hindalco.com",
      "password": "'"$PASSWORD"'",
      "full_name": "Priya Menon",
      "role": "ADMIN"
    }
  }' > /dev/null && success "Hindalco Industries Ltd" || warn "Hindalco (may already exist)"

# Buyer 3: Ambuja Cements
info "Registering Buyer 3: Ambuja Cements Ltd..."
curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "Ambuja Cements Ltd",
      "pan": "AABCA9012C",
      "gstin": "24AABCA9012C1Z1",
      "trade_role": "BUYER",
      "commodities": ["Steel TMT Bars", "Wire Rods", "Steel Plates"],
      "industry_vertical": "Construction Materials",
      "geography": "IN",
      "min_order_value": 200000,
      "max_order_value": 20000000,
      "address": {
        "address_type": "REGISTERED_OFFICE",
        "address_line1": "Elegant Business Park, MIDC Cross Road B",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "pincode": "380015"
      },
      "years_in_operation": 40,
      "annual_turnover_inr": 33000000000
    },
    "user": {
      "email": "buyer3@ambujacements.com",
      "password": "'"$PASSWORD"'",
      "full_name": "Vikram Desai",
      "role": "ADMIN"
    }
  }' > /dev/null && success "Ambuja Cements Ltd" || warn "Ambuja Cements (may already exist)"

# Buyer 4: Mahindra Auto Components
info "Registering Buyer 4: Mahindra Auto Components Pvt Ltd..."
curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "Mahindra Auto Components Pvt Ltd",
      "pan": "AACCM3456D",
      "gstin": "27AACCM3456D1Z7",
      "trade_role": "BUYER",
      "commodities": ["CR Coil", "HR Coil", "Steel Sheets"],
      "industry_vertical": "Automotive",
      "geography": "IN",
      "min_order_value": 100000,
      "max_order_value": 15000000,
      "address": {
        "address_type": "REGISTERED_OFFICE",
        "address_line1": "Mahindra Towers, Worli",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400018"
      },
      "years_in_operation": 30,
      "annual_turnover_inr": 8500000000
    },
    "user": {
      "email": "buyer4@mahindra.com",
      "password": "'"$PASSWORD"'",
      "full_name": "Anita Kulkarni",
      "role": "ADMIN"
    }
  }' > /dev/null && success "Mahindra Auto Components Pvt Ltd" || warn "Mahindra (may already exist)"

# Buyer 5: Godrej & Boyce
info "Registering Buyer 5: Godrej & Boyce Mfg Co Ltd..."
curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "Godrej and Boyce Mfg Co Ltd",
      "pan": "AABCG7890E",
      "gstin": "27AABCG7890E1Z9",
      "trade_role": "BUYER",
      "commodities": ["Steel Sheets", "Steel Pipes", "HR Coil"],
      "industry_vertical": "Consumer Durables",
      "geography": "IN",
      "min_order_value": 50000,
      "max_order_value": 10000000,
      "address": {
        "address_type": "REGISTERED_OFFICE",
        "address_line1": "Godrej One, Pirojshanagar, Vikhroli East",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400079"
      },
      "years_in_operation": 127,
      "annual_turnover_inr": 14000000000
    },
    "user": {
      "email": "buyer5@godrej.com",
      "password": "'"$PASSWORD"'",
      "full_name": "Suresh Nair",
      "role": "ADMIN"
    }
  }' > /dev/null && success "Godrej and Boyce Mfg Co Ltd" || warn "Godrej (may already exist)"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# SELLER ENTERPRISES (5)
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${CYAN}━━━ Registering 5 Seller Enterprises ━━━${NC}"

# Seller 1: JSW Steel
info "Registering Seller 1: JSW Steel Ltd..."
SELLER1_RESP=$(curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "JSW Steel Ltd",
      "pan": "AABCJ1234F",
      "gstin": "29AABCJ1234F1Z1",
      "trade_role": "SELLER",
      "commodities": ["HR Coil", "CR Coil", "Steel Plates", "TMT Bars"],
      "industry_vertical": "Steel Manufacturing",
      "geography": "IN",
      "min_order_value": 100000,
      "max_order_value": 200000000,
      "address": {
        "address_type": "FACILITY",
        "address_line1": "JSW Centre, Bandra Kurla Complex",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400051"
      },
      "facility_type": "INTEGRATED",
      "years_in_operation": 42,
      "annual_turnover_inr": 166000000000,
      "quality_certifications": ["ISO 9001:2015", "ISO 14001:2015", "BIS"],
      "test_certificate_available": true,
      "third_party_inspection_allowed": true
    },
    "user": {
      "email": "seller1@jswsteel.com",
      "password": "'"$PASSWORD"'",
      "full_name": "Rajesh Iyer",
      "role": "ADMIN"
    }
  }' 2>/dev/null || echo '{}')
SELLER1_TOKEN=$(echo "$SELLER1_RESP" | python -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null || echo "")
[ -n "$SELLER1_TOKEN" ] && success "JSW Steel Ltd" || warn "JSW Steel (may already exist)"

# Seller 2: SAIL
info "Registering Seller 2: Steel Authority of India Ltd..."
SELLER2_RESP=$(curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "Steel Authority of India Ltd",
      "pan": "AABCS5678G",
      "gstin": "07AABCS5678G1Z5",
      "trade_role": "SELLER",
      "commodities": ["HR Coil", "Steel Plates", "Steel Billets", "Wire Rods"],
      "industry_vertical": "Steel Manufacturing",
      "geography": "IN",
      "min_order_value": 500000,
      "max_order_value": 500000000,
      "address": {
        "address_type": "FACILITY",
        "address_line1": "Ispat Bhavan, Lodhi Road",
        "city": "New Delhi",
        "state": "Delhi",
        "pincode": "110003"
      },
      "facility_type": "INTEGRATED",
      "years_in_operation": 51,
      "annual_turnover_inr": 104000000000,
      "quality_certifications": ["ISO 9001:2015", "ISO 14001:2015", "BIS", "NABL"],
      "test_certificate_available": true,
      "third_party_inspection_allowed": true
    },
    "user": {
      "email": "seller2@sail.in",
      "password": "'"$PASSWORD"'",
      "full_name": "Deepak Verma",
      "role": "ADMIN"
    }
  }' 2>/dev/null || echo '{}')
SELLER2_TOKEN=$(echo "$SELLER2_RESP" | python -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null || echo "")
[ -n "$SELLER2_TOKEN" ] && success "Steel Authority of India Ltd" || warn "SAIL (may already exist)"

# Seller 3: Jindal Stainless
info "Registering Seller 3: Jindal Stainless Ltd..."
SELLER3_RESP=$(curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "Jindal Stainless Ltd",
      "pan": "AABCJ9012H",
      "gstin": "06AABCJ9012H1Z3",
      "trade_role": "SELLER",
      "commodities": ["CR Coil", "Steel Sheets", "Steel Pipes"],
      "industry_vertical": "Stainless Steel",
      "geography": "IN",
      "min_order_value": 200000,
      "max_order_value": 100000000,
      "address": {
        "address_type": "FACILITY",
        "address_line1": "Jindal Centre, 12 Bhikaiji Cama Place",
        "city": "New Delhi",
        "state": "Delhi",
        "pincode": "110066"
      },
      "facility_type": "MANUFACTURING_PLANT",
      "years_in_operation": 50,
      "annual_turnover_inr": 35000000000,
      "quality_certifications": ["ISO 9001:2015", "ISO 45001:2018"],
      "test_certificate_available": true,
      "third_party_inspection_allowed": true
    },
    "user": {
      "email": "seller3@jindalstainless.com",
      "password": "'"$PASSWORD"'",
      "full_name": "Meera Joshi",
      "role": "ADMIN"
    }
  }' 2>/dev/null || echo '{}')
SELLER3_TOKEN=$(echo "$SELLER3_RESP" | python -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null || echo "")
[ -n "$SELLER3_TOKEN" ] && success "Jindal Stainless Ltd" || warn "Jindal Stainless (may already exist)"

# Seller 4: Essar Steel
info "Registering Seller 4: Essar Steel India Ltd..."
SELLER4_RESP=$(curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "Essar Steel India Ltd",
      "pan": "AABCE3456J",
      "gstin": "24AABCE3456J1Z7",
      "trade_role": "SELLER",
      "commodities": ["HR Coil", "Steel Billets", "Steel Plates", "Steel Pipes"],
      "industry_vertical": "Steel Manufacturing",
      "geography": "IN",
      "min_order_value": 300000,
      "max_order_value": 150000000,
      "address": {
        "address_type": "FACILITY",
        "address_line1": "Essar House, 11 Keshavrao Khadye Marg",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400034"
      },
      "facility_type": "INTEGRATED",
      "years_in_operation": 55,
      "annual_turnover_inr": 45000000000,
      "quality_certifications": ["ISO 9001:2015", "BIS", "API"],
      "test_certificate_available": true,
      "third_party_inspection_allowed": false
    },
    "user": {
      "email": "seller4@essarsteel.com",
      "password": "'"$PASSWORD"'",
      "full_name": "Arjun Kapoor",
      "role": "ADMIN"
    }
  }' 2>/dev/null || echo '{}')
SELLER4_TOKEN=$(echo "$SELLER4_RESP" | python -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null || echo "")
[ -n "$SELLER4_TOKEN" ] && success "Essar Steel India Ltd" || warn "Essar Steel (may already exist)"

# Seller 5: Vizag Steel (Rashtriya Ispat Nigam Ltd)
info "Registering Seller 5: Rashtriya Ispat Nigam Ltd (Vizag Steel)..."
SELLER5_RESP=$(curl -sf -X POST "$API_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise": {
      "legal_name": "Rashtriya Ispat Nigam Ltd",
      "pan": "AABCR7890K",
      "gstin": "37AABCR7890K1Z5",
      "trade_role": "SELLER",
      "commodities": ["Steel Billets", "Wire Rods", "TMT Bars", "Steel Plates"],
      "industry_vertical": "Steel Manufacturing",
      "geography": "IN",
      "min_order_value": 400000,
      "max_order_value": 80000000,
      "address": {
        "address_type": "FACILITY",
        "address_line1": "Visakhapatnam Steel Plant, Gangavaram",
        "city": "Visakhapatnam",
        "state": "Andhra Pradesh",
        "pincode": "530031"
      },
      "facility_type": "INTEGRATED",
      "years_in_operation": 42,
      "annual_turnover_inr": 28000000000,
      "quality_certifications": ["ISO 9001:2015", "ISO 14001:2015", "BIS", "RDSO"],
      "test_certificate_available": true,
      "third_party_inspection_allowed": true
    },
    "user": {
      "email": "seller5@vizagsteel.com",
      "password": "'"$PASSWORD"'",
      "full_name": "Lakshmi Reddy",
      "role": "ADMIN"
    }
  }' 2>/dev/null || echo '{}')
SELLER5_TOKEN=$(echo "$SELLER5_RESP" | python -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null || echo "")
[ -n "$SELLER5_TOKEN" ] && success "Rashtriya Ispat Nigam Ltd" || warn "Vizag Steel (may already exist)"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# SELLER CAPABILITY PROFILES & CATALOGUE ITEMS
# (only if we have tokens from fresh registrations)
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${CYAN}━━━ Setting up Seller Profiles & Catalogues ━━━${NC}"

setup_seller_profile() {
  local TOKEN="$1"
  local SELLER_NAME="$2"
  local PROFILE_JSON="$3"
  local CATALOGUE_JSON="$4"
  local CAPACITY_JSON="$5"

  if [ -z "$TOKEN" ]; then
    # Try logging in instead
    local EMAIL="$6"
    TOKEN=$(curl -sf -X POST "$API_URL/v1/auth/login" \
      -H "Content-Type: application/json" \
      -d '{"email":"'"$EMAIL"'","password":"'"$PASSWORD"'"}' 2>/dev/null \
      | python -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null || echo "")
  fi

  if [ -z "$TOKEN" ]; then
    warn "Skipping profile setup for $SELLER_NAME (no token)"
    return
  fi

  # Capability profile
  curl -sf -X PUT "$API_URL/v1/marketplace/capability-profile" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PROFILE_JSON" > /dev/null 2>&1 && info "  Profile set for $SELLER_NAME" || true

  # Catalogue item
  curl -sf -X POST "$API_URL/v1/marketplace/catalogue" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CATALOGUE_JSON" > /dev/null 2>&1 && info "  Catalogue added for $SELLER_NAME" || true

  # Capacity profile
  curl -sf -X PUT "$API_URL/v1/marketplace/capacity-profile" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CAPACITY_JSON" > /dev/null 2>&1 && info "  Capacity set for $SELLER_NAME" || true

  success "$SELLER_NAME profile complete"
}

# JSW Steel
setup_seller_profile "$SELLER1_TOKEN" "JSW Steel" \
  '{"industry":"Steel Manufacturing","products":["HR Coil","CR Coil","Steel Plates","TMT Bars"],"geographies":["Maharashtra","Karnataka","Tamil Nadu","Gujarat"],"min_order_value":100000,"max_order_value":200000000,"description":"Indias leading integrated steel manufacturer. 28 MTPA capacity across Vijayanagar, Dolvi, and Salem plants. Full range of flat and long products with BIS and ISO certifications."}' \
  '{"product_name":"Hot Rolled Coil IS 2062 E250","hsn_code":"72083990","product_category":"HR_COIL","grade":"IS 2062 E250 BR","specification_text":"Thickness: 1.6-25mm, Width: 900-2100mm, Coil weight: 10-30 MT","unit":"MT","price_per_unit_inr":42000,"moq":25,"max_order_qty":5000,"lead_time_days":14,"in_stock_qty":800,"certifications":["BIS","ISO 9001"]}' \
  '{"monthly_production_capacity_mt":2300000,"current_utilization_pct":82,"num_production_lines":6,"shift_pattern":"CONTINUOUS","avg_dispatch_days":5,"max_delivery_radius_km":2500,"has_own_transport":true,"preferred_transport_modes":["ROAD","RAIL","SEA"],"ex_works_available":true}' \
  "seller1@jswsteel.com"

# SAIL
setup_seller_profile "$SELLER2_TOKEN" "SAIL" \
  '{"industry":"Steel Manufacturing","products":["HR Coil","Steel Plates","Steel Billets","Wire Rods"],"geographies":["Jharkhand","Chhattisgarh","West Bengal","Odisha","Delhi"],"min_order_value":500000,"max_order_value":500000000,"description":"Maharatna PSU and Indias largest steel producer. 21.4 MTPA crude steel capacity across five integrated steel plants. Government quality standards with NABL accredited labs."}' \
  '{"product_name":"Structural Steel Plate IS 2062 E350","hsn_code":"72085290","product_category":"PLATE","grade":"IS 2062 E350","specification_text":"Thickness: 6-120mm, Width: up to 4200mm, Length: up to 18m","unit":"MT","price_per_unit_inr":48000,"moq":50,"max_order_qty":10000,"lead_time_days":21,"in_stock_qty":1200,"certifications":["BIS","RDSO","NABL"]}' \
  '{"monthly_production_capacity_mt":1780000,"current_utilization_pct":75,"num_production_lines":8,"shift_pattern":"CONTINUOUS","avg_dispatch_days":7,"max_delivery_radius_km":3000,"has_own_transport":true,"preferred_transport_modes":["RAIL","ROAD"],"ex_works_available":true}' \
  "seller2@sail.in"

# Jindal Stainless
setup_seller_profile "$SELLER3_TOKEN" "Jindal Stainless" \
  '{"industry":"Stainless Steel","products":["CR Coil","Steel Sheets","Steel Pipes"],"geographies":["Haryana","Delhi","Odisha","Gujarat"],"min_order_value":200000,"max_order_value":100000000,"description":"Indias largest stainless steel producer. 2.1 MTPA capacity at Jajpur and Hisar plants. Specialized in austenitic, ferritic, and duplex grades."}' \
  '{"product_name":"Stainless Steel CR Coil 304 Grade","hsn_code":"72193300","product_category":"CR_COIL","grade":"AISI 304 / SS 304","specification_text":"Thickness: 0.3-6mm, Width: 600-1550mm, Finish: 2B/BA/No.4","unit":"MT","price_per_unit_inr":185000,"moq":5,"max_order_qty":500,"lead_time_days":10,"in_stock_qty":350,"certifications":["ISO 9001","ASTM","EN 10088"]}' \
  '{"monthly_production_capacity_mt":175000,"current_utilization_pct":78,"num_production_lines":4,"shift_pattern":"TRIPLE_SHIFT","avg_dispatch_days":4,"max_delivery_radius_km":2000,"has_own_transport":false,"preferred_transport_modes":["ROAD","RAIL"],"ex_works_available":true}' \
  "seller3@jindalstainless.com"

# Essar Steel
setup_seller_profile "$SELLER4_TOKEN" "Essar Steel" \
  '{"industry":"Steel Manufacturing","products":["HR Coil","Steel Billets","Steel Plates","Steel Pipes"],"geographies":["Gujarat","Maharashtra","Rajasthan"],"min_order_value":300000,"max_order_value":150000000,"description":"Major flat steel producer with 10 MTPA capacity at Hazira, Gujarat. Specializes in value-added and downstream steel products for oil & gas, automotive, and infrastructure sectors."}' \
  '{"product_name":"API 5L X65 Line Pipe Steel Plate","hsn_code":"72085190","product_category":"PLATE","grade":"API 5L X65 PSL2","specification_text":"Thickness: 6-50mm, Width: 1500-4000mm, Charpy tested at -20C","unit":"MT","price_per_unit_inr":55000,"moq":20,"max_order_qty":3000,"lead_time_days":18,"in_stock_qty":600,"certifications":["API","BIS","ISO 9001","DNV"]}' \
  '{"monthly_production_capacity_mt":830000,"current_utilization_pct":70,"num_production_lines":3,"shift_pattern":"CONTINUOUS","avg_dispatch_days":6,"max_delivery_radius_km":1500,"has_own_transport":true,"preferred_transport_modes":["ROAD","SEA"],"ex_works_available":true}' \
  "seller4@essarsteel.com"

# Vizag Steel
setup_seller_profile "$SELLER5_TOKEN" "Vizag Steel" \
  '{"industry":"Steel Manufacturing","products":["Steel Billets","Wire Rods","TMT Bars","Steel Plates"],"geographies":["Andhra Pradesh","Telangana","Tamil Nadu","Karnataka","Odisha"],"min_order_value":400000,"max_order_value":80000000,"description":"Shore-based integrated steel plant with 7.3 MTPA capacity at Visakhapatnam. Specializes in long products including wire rods and structural steel. RDSO approved for railway-grade steel."}' \
  '{"product_name":"TMT Bar Fe 500D","hsn_code":"72142000","product_category":"TMT_BAR","grade":"Fe 500D IS 1786:2008","specification_text":"Diameter: 8-40mm, Length: 12m standard, Bendability: 3d, UTS/YS ratio >= 1.08","unit":"MT","price_per_unit_inr":38500,"moq":10,"max_order_qty":2000,"lead_time_days":7,"in_stock_qty":2500,"certifications":["BIS","RDSO","ISO 9001"]}' \
  '{"monthly_production_capacity_mt":610000,"current_utilization_pct":85,"num_production_lines":5,"shift_pattern":"CONTINUOUS","avg_dispatch_days":3,"max_delivery_radius_km":1800,"has_own_transport":true,"preferred_transport_modes":["RAIL","ROAD","SEA"],"ex_works_available":true}' \
  "seller5@vizagsteel.com"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# ADMIN ACCOUNT VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${CYAN}━━━ Verifying Admin Account ━━━${NC}"

ADMIN_RESP=$(curl -sf -X POST "$API_URL/v1/auth/admin-login" \
  -H "Content-Type: application/json" \
  -d '{"email":"'"$ADMIN_EMAIL"'","password":"'"$ADMIN_PASSWORD"'"}' 2>/dev/null || echo '{}')
ADMIN_TOKEN=$(echo "$ADMIN_RESP" | python -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" 2>/dev/null || echo "")

if [ -n "$ADMIN_TOKEN" ]; then
  success "Admin account verified: $ADMIN_EMAIL"
else
  warn "Admin login failed (check CADENCIA_ADMIN_EMAIL and CADENCIA_ADMIN_PASSWORD in .env)"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Cadencia User Seed Complete${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  BUYER ACCOUNTS (5):"
echo "    buyer1@tatasteel.com       / $PASSWORD  (Tata Steel)"
echo "    buyer2@hindalco.com        / $PASSWORD  (Hindalco)"
echo "    buyer3@ambujacements.com   / $PASSWORD  (Ambuja Cements)"
echo "    buyer4@mahindra.com        / $PASSWORD  (Mahindra Auto)"
echo "    buyer5@godrej.com          / $PASSWORD  (Godrej & Boyce)"
echo ""
echo "  SELLER ACCOUNTS (5):"
echo "    seller1@jswsteel.com       / $PASSWORD  (JSW Steel)"
echo "    seller2@sail.in            / $PASSWORD  (SAIL)"
echo "    seller3@jindalstainless.com/ $PASSWORD  (Jindal Stainless)"
echo "    seller4@essarsteel.com     / $PASSWORD  (Essar Steel)"
echo "    seller5@vizagsteel.com     / $PASSWORD  (Vizag Steel)"
echo ""
echo "  ADMIN ACCOUNT:"
echo "    $ADMIN_EMAIL     / $ADMIN_PASSWORD"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo ""
