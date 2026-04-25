$API         = "http://localhost:8001"
$PASS        = "Cadencia@2026"
$ADMIN_EMAIL = "admin@cadencia.io"
$ADMIN_PASS  = "Admin@1234"

function Post-Json($url, $body) {
    $headers = @{ "Content-Type" = "application/json" }
    try {
        return Invoke-RestMethod -Method POST -Uri $url -Headers $headers -Body ($body | ConvertTo-Json -Depth 10)
    } catch {
        try {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            Write-Host "    ERR: $($reader.ReadToEnd())" -ForegroundColor Red
        } catch {
            Write-Host "    ERR: $($_.Exception.Message)" -ForegroundColor Red
        }
        return $null
    }
}

function ok($msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function info($msg) { Write-Host "  [..]  $msg" -ForegroundColor Cyan }
function warn($msg) { Write-Host "  [!!]  $msg" -ForegroundColor Yellow }

# Health check
info "Checking backend at $API ..."
try {
    $h = Invoke-RestMethod "$API/health"
    ok "Backend healthy - status: $($h.status)"
} catch {
    Write-Host "[FAIL] Backend not reachable at $API" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "--- Registering 5 Buyer Enterprises ---" -ForegroundColor Cyan

$buyers = @(
    @{
        enterprise = @{
            legal_name = "Tata Steel Procurement Ltd"
            pan = "AAACT1234A"; gstin = "27AAACT1234A1Z5"
            trade_role = "BUYER"
            commodities = @("HR Coil","CR Coil","Steel Plates")
            industry_vertical = "Steel Manufacturing"; geography = "IN"
            min_order_value = 500000; max_order_value = 50000000
            address = @{ address_type="REGISTERED_OFFICE"; address_line1="Bombay House, 24 Homi Mody Street"; city="Mumbai"; state="Maharashtra"; pincode="400001" }
            years_in_operation = 115; annual_turnover_inr = 250000000000
        }
        user = @{ email="buyer1@tatasteel.com"; password=$PASS; full_name="Rahul Sharma"; role="ADMIN" }
    },
    @{
        enterprise = @{
            legal_name = "Hindalco Industries Ltd"
            pan = "AABCH5678B"; gstin = "27AABCH5678B1Z3"
            trade_role = "BUYER"
            commodities = @("Aluminium Ingots","Copper Cathodes","Steel Billets")
            industry_vertical = "Non-Ferrous Metals"; geography = "IN"
            min_order_value = 1000000; max_order_value = 100000000
            address = @{ address_type="REGISTERED_OFFICE"; address_line1="Century Bhavan, Dr Annie Besant Road"; city="Mumbai"; state="Maharashtra"; pincode="400030" }
            years_in_operation = 65; annual_turnover_inr = 195000000000
        }
        user = @{ email="buyer2@hindalco.com"; password=$PASS; full_name="Priya Menon"; role="ADMIN" }
    },
    @{
        enterprise = @{
            legal_name = "Ambuja Cements Ltd"
            pan = "AABCA9012C"; gstin = "24AABCA9012C1Z1"
            trade_role = "BUYER"
            commodities = @("Steel TMT Bars","Wire Rods","Steel Plates")
            industry_vertical = "Construction Materials"; geography = "IN"
            min_order_value = 200000; max_order_value = 20000000
            address = @{ address_type="REGISTERED_OFFICE"; address_line1="Elegant Business Park, MIDC Cross Road B"; city="Ahmedabad"; state="Gujarat"; pincode="380015" }
            years_in_operation = 40; annual_turnover_inr = 33000000000
        }
        user = @{ email="buyer3@ambujacements.com"; password=$PASS; full_name="Vikram Desai"; role="ADMIN" }
    },
    @{
        enterprise = @{
            legal_name = "Mahindra Auto Components Pvt Ltd"
            pan = "AACCM3456D"; gstin = "27AACCM3456D1Z7"
            trade_role = "BUYER"
            commodities = @("CR Coil","HR Coil","Steel Sheets")
            industry_vertical = "Automotive"; geography = "IN"
            min_order_value = 100000; max_order_value = 15000000
            address = @{ address_type="REGISTERED_OFFICE"; address_line1="Mahindra Towers, Worli"; city="Mumbai"; state="Maharashtra"; pincode="400018" }
            years_in_operation = 30; annual_turnover_inr = 8500000000
        }
        user = @{ email="buyer4@mahindra.com"; password=$PASS; full_name="Anita Kulkarni"; role="ADMIN" }
    },
    @{
        enterprise = @{
            legal_name = "Godrej and Boyce Mfg Co Ltd"
            pan = "AABCG7890E"; gstin = "27AABCG7890E1Z9"
            trade_role = "BUYER"
            commodities = @("Steel Sheets","Steel Pipes","HR Coil")
            industry_vertical = "Consumer Durables"; geography = "IN"
            min_order_value = 50000; max_order_value = 10000000
            address = @{ address_type="REGISTERED_OFFICE"; address_line1="Godrej One, Pirojshanagar, Vikhroli East"; city="Mumbai"; state="Maharashtra"; pincode="400079" }
            years_in_operation = 127; annual_turnover_inr = 14000000000
        }
        user = @{ email="buyer5@godrej.com"; password=$PASS; full_name="Suresh Nair"; role="ADMIN" }
    }
)

foreach ($b in $buyers) {
    info "Registering $($b.enterprise.legal_name) ..."
    $r = Post-Json "$API/v1/auth/register" $b
    if ($r) { ok "$($b.enterprise.legal_name) - $($b.user.email)" }
    else     { warn "$($b.enterprise.legal_name) may already exist" }
}

Write-Host ""
Write-Host "--- Registering 5 Seller Enterprises ---" -ForegroundColor Cyan

$sellers = @(
    @{
        body = @{
            enterprise = @{
                legal_name = "JSW Steel Ltd"
                pan = "AABCJ1234F"; gstin = "29AABCJ1234F1Z1"
                trade_role = "SELLER"
                commodities = @("HR Coil","CR Coil","Steel Plates","TMT Bars")
                industry_vertical = "Steel Manufacturing"; geography = "IN"
                min_order_value = 100000; max_order_value = 200000000
                address = @{ address_type="FACILITY"; address_line1="JSW Centre, Bandra Kurla Complex"; city="Mumbai"; state="Maharashtra"; pincode="400051" }
                facility_type = "INTEGRATED"; years_in_operation = 42; annual_turnover_inr = 166000000000
                quality_certifications = @("ISO 9001:2015","ISO 14001:2015","BIS")
                test_certificate_available = $true; third_party_inspection_allowed = $true
            }
            user = @{ email="seller1@jswsteel.com"; password=$PASS; full_name="Rajesh Iyer"; role="ADMIN" }
        }
        email = "seller1@jswsteel.com"; name = "JSW Steel Ltd"
    },
    @{
        body = @{
            enterprise = @{
                legal_name = "Steel Authority of India Ltd"
                pan = "AABCS5678G"; gstin = "07AABCS5678G1Z5"
                trade_role = "SELLER"
                commodities = @("HR Coil","Steel Plates","Steel Billets","Wire Rods")
                industry_vertical = "Steel Manufacturing"; geography = "IN"
                min_order_value = 500000; max_order_value = 500000000
                address = @{ address_type="FACILITY"; address_line1="Ispat Bhavan, Lodhi Road"; city="New Delhi"; state="Delhi"; pincode="110003" }
                facility_type = "INTEGRATED"; years_in_operation = 51; annual_turnover_inr = 104000000000
                quality_certifications = @("ISO 9001:2015","ISO 14001:2015","BIS","NABL")
                test_certificate_available = $true; third_party_inspection_allowed = $true
            }
            user = @{ email="seller2@sail.in"; password=$PASS; full_name="Deepak Verma"; role="ADMIN" }
        }
        email = "seller2@sail.in"; name = "SAIL"
    },
    @{
        body = @{
            enterprise = @{
                legal_name = "Jindal Stainless Ltd"
                pan = "AABCJ9012H"; gstin = "06AABCJ9012H1Z3"
                trade_role = "SELLER"
                commodities = @("CR Coil","Steel Sheets","Steel Pipes")
                industry_vertical = "Stainless Steel"; geography = "IN"
                min_order_value = 200000; max_order_value = 100000000
                address = @{ address_type="FACILITY"; address_line1="Jindal Centre, 12 Bhikaiji Cama Place"; city="New Delhi"; state="Delhi"; pincode="110066" }
                facility_type = "MANUFACTURING_PLANT"; years_in_operation = 50; annual_turnover_inr = 35000000000
                quality_certifications = @("ISO 9001:2015","ISO 45001:2018")
                test_certificate_available = $true; third_party_inspection_allowed = $true
            }
            user = @{ email="seller3@jindalstainless.com"; password=$PASS; full_name="Meera Joshi"; role="ADMIN" }
        }
        email = "seller3@jindalstainless.com"; name = "Jindal Stainless"
    },
    @{
        body = @{
            enterprise = @{
                legal_name = "Essar Steel India Ltd"
                pan = "AABCE3456J"; gstin = "24AABCE3456J1Z7"
                trade_role = "SELLER"
                commodities = @("HR Coil","Steel Billets","Steel Plates","Steel Pipes")
                industry_vertical = "Steel Manufacturing"; geography = "IN"
                min_order_value = 300000; max_order_value = 150000000
                address = @{ address_type="FACILITY"; address_line1="Essar House, 11 Keshavrao Khadye Marg"; city="Mumbai"; state="Maharashtra"; pincode="400034" }
                facility_type = "INTEGRATED"; years_in_operation = 55; annual_turnover_inr = 45000000000
                quality_certifications = @("ISO 9001:2015","BIS","API")
                test_certificate_available = $true; third_party_inspection_allowed = $false
            }
            user = @{ email="seller4@essarsteel.com"; password=$PASS; full_name="Arjun Kapoor"; role="ADMIN" }
        }
        email = "seller4@essarsteel.com"; name = "Essar Steel"
    },
    @{
        body = @{
            enterprise = @{
                legal_name = "Rashtriya Ispat Nigam Ltd"
                pan = "AABCR7890K"; gstin = "37AABCR7890K1Z5"
                trade_role = "SELLER"
                commodities = @("Steel Billets","Wire Rods","TMT Bars","Steel Plates")
                industry_vertical = "Steel Manufacturing"; geography = "IN"
                min_order_value = 400000; max_order_value = 80000000
                address = @{ address_type="FACILITY"; address_line1="Visakhapatnam Steel Plant, Gangavaram"; city="Visakhapatnam"; state="Andhra Pradesh"; pincode="530031" }
                facility_type = "INTEGRATED"; years_in_operation = 42; annual_turnover_inr = 28000000000
                quality_certifications = @("ISO 9001:2015","ISO 14001:2015","BIS","RDSO")
                test_certificate_available = $true; third_party_inspection_allowed = $true
            }
            user = @{ email="seller5@vizagsteel.com"; password=$PASS; full_name="Lakshmi Reddy"; role="ADMIN" }
        }
        email = "seller5@vizagsteel.com"; name = "Vizag Steel (RINL)"
    }
)

foreach ($s in $sellers) {
    info "Registering $($s.name) ..."
    $r = Post-Json "$API/v1/auth/register" $s.body
    if ($r -and $r.data -and $r.data.access_token) {
        ok "$($s.name) - $($s.email)"
    } else {
        warn "$($s.name) may already exist - attempting login ..."
        $loginR = Post-Json "$API/v1/auth/login" @{ email=$s.email; password=$PASS }
        if ($loginR -and $loginR.data -and $loginR.data.access_token) {
            ok "Logged in as $($s.email)"
        } else {
            warn "Could not get token for $($s.name)"
        }
    }
}

Write-Host ""
Write-Host "--- Verifying Admin Account ---" -ForegroundColor Cyan
info "Attempting admin login ..."
$adminR = Post-Json "$API/v1/auth/admin-login" @{ email=$ADMIN_EMAIL; password=$ADMIN_PASS }
if ($adminR -and $adminR.data -and $adminR.data.access_token) {
    ok "Admin verified: $ADMIN_EMAIL"
} else {
    warn "Admin login failed - check CADENCIA_ADMIN_EMAIL / CADENCIA_ADMIN_PASSWORD in backend/.env"
}

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Green
Write-Host "  Cadencia Local Seed Complete" -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  BUYER ACCOUNTS   password: $PASS" -ForegroundColor Yellow
Write-Host "    buyer1@tatasteel.com         Rahul Sharma     (Tata Steel)"
Write-Host "    buyer2@hindalco.com          Priya Menon      (Hindalco)"
Write-Host "    buyer3@ambujacements.com     Vikram Desai     (Ambuja Cements)"
Write-Host "    buyer4@mahindra.com          Anita Kulkarni   (Mahindra Auto)"
Write-Host "    buyer5@godrej.com            Suresh Nair      (Godrej and Boyce)"
Write-Host ""
Write-Host "  SELLER ACCOUNTS  password: $PASS" -ForegroundColor Yellow
Write-Host "    seller1@jswsteel.com         Rajesh Iyer      (JSW Steel)"
Write-Host "    seller2@sail.in              Deepak Verma     (SAIL)"
Write-Host "    seller3@jindalstainless.com  Meera Joshi      (Jindal Stainless)"
Write-Host "    seller4@essarsteel.com       Arjun Kapoor     (Essar Steel)"
Write-Host "    seller5@vizagsteel.com       Lakshmi Reddy    (Vizag Steel / RINL)"
Write-Host ""
Write-Host "  ADMIN ACCOUNT" -ForegroundColor Yellow
Write-Host "    $ADMIN_EMAIL    $ADMIN_PASS"
Write-Host ""
Write-Host "  Frontend : http://localhost:3001" -ForegroundColor Cyan
Write-Host "  Backend  : http://localhost:8001" -ForegroundColor Cyan
Write-Host "  API Docs : http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host ""
