"""
Find which enterprise has your wallet address and unlink it via API.
Replace WALLET_ADDRESS below with the actual wallet you're trying to link.
"""
import asyncio
import httpx

API = "http://localhost:8001"

# ← PUT YOUR WALLET ADDRESS HERE
WALLET_ADDRESS = "REPLACE_WITH_YOUR_WALLET_ADDRESS"

ALL_ACCOUNTS = [
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
        print("Scanning all enterprises for wallet addresses...")
        print("=" * 70)

        for acc in ALL_ACCOUNTS:
            r = await c.post(f"{API}/v1/auth/login", json={
                "email": acc["email"], "password": acc["password"]
            })
            if r.status_code != 200:
                continue

            data = r.json().get("data", {})
            token = data.get("access_token", "")
            ent = data.get("enterprise", {})
            ent_id = ent.get("id", "")
            name = ent.get("legal_name", acc["label"])

            # Fetch enterprise profile via /me or /enterprises/{id}
            profile_r = await c.get(
                f"{API}/v1/enterprises/{ent_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            wallet = None
            if profile_r.status_code == 200:
                wallet = profile_r.json().get("data", {}).get("algorand_wallet")

            if not wallet:
                wallet = ent.get("algorand_wallet")

            wallet_str = wallet if wallet else "-- none --"
            marker = " ← CONFLICT!" if wallet and wallet == WALLET_ADDRESS else ""
            print(f"  [{acc['label']:8s}] {name:35s} | {wallet_str}{marker}")

            # If this account owns the conflicting wallet, unlink it
            if wallet and wallet == WALLET_ADDRESS:
                print(f"\n  !! Found conflicting wallet on {acc['label']}. Unlinking...")
                del_r = await c.delete(
                    f"{API}/v1/wallet/link",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if del_r.status_code == 200:
                    print(f"  ✓ Wallet unlinked from {acc['label']}! Now retry linking to seller2.")
                else:
                    print(f"  ✗ Unlink failed: {del_r.status_code}: {del_r.text[:200]}")

        print("=" * 70)
        print("Done. If no conflict was found, the wallet address may be a DB")
        print("residue from a previous run. Run the DB clear command below:")
        print()
        print("  docker exec cadencia-a2a-platform-test-db-1 psql -U cadencia -d cadencia \\")
        print("    -c \"UPDATE enterprises SET algorand_wallet = NULL WHERE algorand_wallet = 'YOUR_WALLET';\"")

asyncio.run(main())
