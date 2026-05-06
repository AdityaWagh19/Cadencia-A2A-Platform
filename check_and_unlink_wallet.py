"""
Check wallet status for all accounts and optionally unlink for seller2.
"""
import asyncio
import httpx

API = "http://localhost:8001"

ACCOUNTS = [
    {"email": "buyer1@techweavegarments.com", "password": "Test@Cadencia1", "label": "buyer1"},
    {"email": "buyer2@smartelecdevices.com", "password": "Test@Cadencia1", "label": "buyer2"},
    {"email": "buyer3@mediquickpharma.com", "password": "Test@Cadencia1", "label": "buyer3"},
    {"email": "buyer4@autoassemble.com", "password": "Test@Cadencia1", "label": "buyer4"},
    {"email": "buyer5@greenfieldagro.com", "password": "Test@Cadencia1", "label": "buyer5"},
    {"email": "seller1@mahacottonmills.com", "password": "Test@Cadencia1", "label": "seller1"},
    {"email": "seller2@punpcbtech.com", "password": "Test@Cadencia1", "label": "seller2"},
    {"email": "seller3@hydlifesciences.com", "password": "Test@Cadencia1", "label": "seller3"},
    {"email": "seller4@tnautocomponents.com", "password": "Test@Cadencia1", "label": "seller4"},
    {"email": "seller5@gujaratagrochemicals.com", "password": "Test@Cadencia1", "label": "seller5"},
]

async def main():
    async with httpx.AsyncClient(timeout=20.0) as c:
        print("=" * 70)
        print("Wallet Status for All Accounts")
        print("=" * 70)

        for acc in ACCOUNTS:
            # Login
            r = await c.post(f"{API}/v1/auth/login", json={
                "email": acc["email"], "password": acc["password"]
            })
            if r.status_code != 200:
                print(f"  [LOGIN FAIL] {acc['label']}")
                continue

            data = r.json().get("data", {})
            token = data.get("access_token", "")
            ent = data.get("enterprise", {})
            ent_id = ent.get("id", "")
            wallet = ent.get("algorand_wallet", None)
            name = ent.get("legal_name", acc["label"])

            wallet_str = wallet if wallet else "-- no wallet --"
            print(f"  [{acc['label']:8s}] {name:35s} | wallet: {wallet_str}")

            # Unlink wallet for seller2 if it has one
            if acc["label"] == "seller2" and wallet:
                print(f"\n  >> seller2 has wallet linked: {wallet}")
                print(f"  >> Unlinking now via DELETE /v1/wallet/link ...")
                headers = {"Authorization": f"Bearer {token}"}
                del_r = await c.delete(f"{API}/v1/wallet/link", headers=headers)
                if del_r.status_code == 200:
                    print(f"  >> [SUCCESS] Wallet unlinked! seller2 can now link a fresh wallet.")
                else:
                    print(f"  >> [FAIL] {del_r.status_code}: {del_r.text[:200]}")
                    # Try enterprise-scoped route
                    del_r2 = await c.delete(
                        f"{API}/v1/enterprises/{ent_id}/wallet",
                        headers=headers
                    )
                    print(f"  >> Enterprise route: {del_r2.status_code}: {del_r2.text[:200]}")

        print("=" * 70)

asyncio.run(main())
