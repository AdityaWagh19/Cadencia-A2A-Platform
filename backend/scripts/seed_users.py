"""Seed the exact buyer/seller enterprises the user requested."""
import asyncio, httpx, sys

API = "http://localhost:8001"

ENTERPRISES = [
    # ── Buyers ──
    {"enterprise": {"legal_name": "TechWeave Garments Pvt Ltd", "pan": "AATWE1234B", "gstin": "27AATWE1234B1ZA", "trade_role": "BUYER", "commodities": ["TEXTILES"], "industry_vertical": "Textiles", "geography": "PAN_INDIA"}, "user": {"email": "buyer1@techweavegarments.com", "password": "Test@Cadencia1", "full_name": "Buyer One", "role": "ADMIN"}},
    {"enterprise": {"legal_name": "SmartElec Devices Ltd", "pan": "BBSED5678C", "gstin": "27BBSED5678C1ZB", "trade_role": "BUYER", "commodities": ["ELECTRONICS"], "industry_vertical": "Electronics", "geography": "PAN_INDIA"}, "user": {"email": "buyer2@smartelecdevices.com", "password": "Test@Cadencia1", "full_name": "Buyer Two", "role": "ADMIN"}},
    {"enterprise": {"legal_name": "MediQuick Pharma Industries", "pan": "CCMQP9012D", "gstin": "36CCMQP9012D1ZC", "trade_role": "BUYER", "commodities": ["PHARMA"], "industry_vertical": "Pharma", "geography": "PAN_INDIA"}, "user": {"email": "buyer3@mediquickpharma.com", "password": "Test@Cadencia1", "full_name": "Buyer Three", "role": "ADMIN"}},
    {"enterprise": {"legal_name": "AutoAssemble Industries Ltd", "pan": "DDAAI4567E", "gstin": "33DDAAI4567E1ZD", "trade_role": "BUYER", "commodities": ["AUTOMOTIVE"], "industry_vertical": "Automotive", "geography": "PAN_INDIA"}, "user": {"email": "buyer4@autoassemble.com", "password": "Test@Cadencia1", "full_name": "Buyer Four", "role": "ADMIN"}},
    {"enterprise": {"legal_name": "GreenField Agro Pvt Ltd", "pan": "EEGFA7890F", "gstin": "03EEGFA7890F1ZE", "trade_role": "BUYER", "commodities": ["AGRICULTURE"], "industry_vertical": "Agriculture", "geography": "PAN_INDIA"}, "user": {"email": "buyer5@greenfieldagro.com", "password": "Test@Cadencia1", "full_name": "Buyer Five", "role": "ADMIN"}},
    # ── Sellers ──
    {"enterprise": {"legal_name": "Maharashtra Cotton Mills Ltd", "pan": "FFMCO1234G", "gstin": "27FFMCO1234G1ZF", "trade_role": "SELLER", "commodities": ["TEXTILES"], "industry_vertical": "Textiles", "geography": "PAN_INDIA"}, "user": {"email": "seller1@mahacottonmills.com", "password": "Test@Cadencia1", "full_name": "Seller One", "role": "ADMIN"}},
    {"enterprise": {"legal_name": "Pune PCB Technologies Pvt Ltd", "pan": "GGPPT5678H", "gstin": "27GGPPT5678H1ZG", "trade_role": "SELLER", "commodities": ["ELECTRONICS"], "industry_vertical": "Electronics", "geography": "PAN_INDIA"}, "user": {"email": "seller2@punpcbtech.com", "password": "Test@Cadencia1", "full_name": "Seller Two", "role": "ADMIN"}},
    {"enterprise": {"legal_name": "Hyderabad Life Sciences Pvt Ltd", "pan": "HHHLS9012I", "gstin": "36HHHLS9012I1ZH", "trade_role": "SELLER", "commodities": ["PHARMA"], "industry_vertical": "Pharma", "geography": "PAN_INDIA"}, "user": {"email": "seller3@hydlifesciences.com", "password": "Test@Cadencia1", "full_name": "Seller Three", "role": "ADMIN"}},
    {"enterprise": {"legal_name": "Tamil Nadu Auto Components Ltd", "pan": "IITNC4567J", "gstin": "33IITNC4567J1ZI", "trade_role": "SELLER", "commodities": ["AUTOMOTIVE"], "industry_vertical": "Automotive", "geography": "PAN_INDIA"}, "user": {"email": "seller4@tnautocomponents.com", "password": "Test@Cadencia1", "full_name": "Seller Four", "role": "ADMIN"}},
    {"enterprise": {"legal_name": "Gujarat Agro Chemicals Corp", "pan": "JJGAC7890K", "gstin": "24JJGAC7890K1ZJ", "trade_role": "SELLER", "commodities": ["AGRICULTURE"], "industry_vertical": "Agriculture", "geography": "PAN_INDIA"}, "user": {"email": "seller5@gujaratagrochemicals.com", "password": "Test@Cadencia1", "full_name": "Seller Five", "role": "ADMIN"}},
]

async def main():
    async with httpx.AsyncClient(timeout=30.0) as c:
        # Health check
        try:
            r = await c.get(f"{API}/health")
            assert r.status_code == 200
            print("[OK] API healthy")
        except Exception as e:
            print(f"[FAIL] API not reachable: {e}")
            sys.exit(1)

        ok = 0
        for ent in ENTERPRISES:
            name = ent["enterprise"]["legal_name"]
            email = ent["user"]["email"]
            r = await c.post(f"{API}/v1/auth/register", json=ent)
            if r.status_code in (200, 201):
                print(f"  [OK] {name} ({email})")
                ok += 1
            elif r.status_code == 409:
                print(f"  [SKIP] {name} already exists")
                ok += 1
            else:
                print(f"  [FAIL] {name}: {r.status_code} -- {r.text[:120]}")

        print(f"\n{'='*50}")
        print(f"Seeded {ok}/{len(ENTERPRISES)} enterprises")
        print(f"Password for all: Test@Cadencia1")

if __name__ == "__main__":
    asyncio.run(main())
