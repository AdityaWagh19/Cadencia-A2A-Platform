import asyncio, httpx

API = "http://localhost:8001"

ACCOUNTS = [
    {"email": "buyer1@techweavegarments.com", "password": "Test@Cadencia1"},
    {"email": "buyer2@smartelecdevices.com", "password": "Test@Cadencia1"},
    {"email": "buyer3@mediquickpharma.com", "password": "Test@Cadencia1"},
    {"email": "buyer4@autoassemble.com", "password": "Test@Cadencia1"},
    {"email": "buyer5@greenfieldagro.com", "password": "Test@Cadencia1"},
    {"email": "seller1@mahacottonmills.com", "password": "Test@Cadencia1"},
    {"email": "seller2@punpcbtech.com", "password": "Test@Cadencia1"},
    {"email": "seller3@hydlifesciences.com", "password": "Test@Cadencia1"},
    {"email": "seller4@tnautocomponents.com", "password": "Test@Cadencia1"},
    {"email": "seller5@gujaratagrochemicals.com", "password": "Test@Cadencia1"},
    {"email": "admin@cadencia.io", "password": "Admin@1234"},
    # Old demo data
    {"email": "admin@tatasteel.demo", "password": "Demo123!Secure"},
    {"email": "admin@mahindra.demo", "password": "Demo123!Secure"},
    {"email": "admin@jswsteel.demo", "password": "Demo123!Secure"},
    {"email": "admin@sail.demo", "password": "Demo123!Secure"},
    {"email": "admin@vedanta.demo", "password": "Demo123!Secure"},
]

async def main():
    async with httpx.AsyncClient(timeout=15.0) as c:
        print("Checking all known accounts against the live API...")
        print("-" * 72)
        found = []
        for acc in ACCOUNTS:
            r = await c.post(f"{API}/v1/auth/login", json=acc)
            if r.status_code == 200:
                data = r.json().get("data", {})
                ent = data.get("enterprise", {})
                role = ent.get("trade_role", "PLATFORM_ADMIN")
                name = ent.get("legal_name", "Platform Admin")
                found.append({"email": acc["email"], "name": name, "role": role})
                print(f"  [EXISTS] {role:15s} | {name:35s} | {acc['email']}")
            elif r.status_code == 401:
                print(f"  [NONE]   {'':15s} | {'':35s} | {acc['email']}")
            else:
                print(f"  [ERR {r.status_code}]  {acc['email']}")

        print("-" * 72)
        print(f"Total existing accounts found: {len(found)}")

asyncio.run(main())
