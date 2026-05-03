"""
Close out zero-balance assets from the platform wallet to reduce its minimum balance.

Algorand minimum balance formula:
  0.1 ALGO base + 0.1 ALGO per opted-in asset

The platform wallet has 77 assets → min balance ~7.8 ALGO
Target: ≤49 assets → min balance ≤5 ALGO

This script closes out all assets with zero balance (safe to do with no balance loss).
Assets with non-zero balance are reported but skipped.
"""
import os, sys

MNEMONIC = "blossom artwork cactus reject sick vacuum august will victory donkey common essay spice source syrup approve quiz world replace journey piece world pyramid abstract slice"
ALGOD_ADDRESS = "https://testnet-api.4160.nodely.dev"
ALGOD_TOKEN = ""
TARGET_MIN_BALANCE_ALGO = 5.0

def main():
    import algosdk.mnemonic as algo_mnemonic
    import algosdk.account as account
    from algosdk import transaction
    from algosdk.v2client.algod import AlgodClient

    sk = algo_mnemonic.to_private_key(MNEMONIC)
    addr = account.address_from_private_key(sk)
    algod = AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)

    print(f"Platform wallet: {addr}")

    # Fetch account info
    info = algod.account_info(addr)
    balance = info.get("amount", 0)
    min_balance = info.get("min-balance", 0)
    assets = info.get("assets", [])

    print(f"Balance:      {balance / 1_000_000:.6f} ALGO")
    print(f"Min balance:  {min_balance / 1_000_000:.6f} ALGO  ({len(assets)} assets)")
    print(f"Available:    {(balance - min_balance) / 1_000_000:.6f} ALGO")
    print()

    # How many assets we need to close out to hit target
    BASE_MIN = 100_000  # 0.1 ALGO
    PER_ASSET = 100_000  # 0.1 ALGO per asset
    target_min_microalgo = int(TARGET_MIN_BALANCE_ALGO * 1_000_000)
    max_assets_allowed = (target_min_microalgo - BASE_MIN) // PER_ASSET
    current_assets = len(assets)
    need_to_close = max(0, current_assets - max_assets_allowed)

    print(f"Target min balance: {TARGET_MIN_BALANCE_ALGO} ALGO")
    print(f"Max assets allowed: {max_assets_allowed}")
    print(f"Current assets:     {current_assets}")
    print(f"Need to close out:  {need_to_close} assets")
    print()

    if need_to_close == 0:
        print("[OK] Already at or below target minimum balance. Nothing to do.")
        return

    # Separate zero-balance (safe to close) vs non-zero
    zero_balance_assets = [a for a in assets if a.get("amount", 0) == 0]
    nonzero_balance_assets = [a for a in assets if a.get("amount", 0) > 0]

    print(f"Zero-balance assets (safe to close): {len(zero_balance_assets)}")
    print(f"Non-zero balance assets (skipped):   {len(nonzero_balance_assets)}")

    if nonzero_balance_assets:
        print("\n[WARN] Assets with non-zero balance (cannot auto-close):")
        for a in nonzero_balance_assets:
            print(f"   Asset ID {a['asset-id']}: balance={a['amount']}")

    # Close out zero-balance assets (up to need_to_close)
    to_close = zero_balance_assets[:need_to_close]
    print(f"\nClosing out {len(to_close)} zero-balance assets...")
    print()

    params = algod.suggested_params()
    params.fee = max(params.min_fee, 1000)
    params.flat_fee = True

    closed = 0
    failed = 0
    for i, asset in enumerate(to_close):
        asset_id = asset["asset-id"]
        try:
            # Opt-out: send 0 of the asset, close_asset_to=addr (self-close)
            txn = transaction.AssetTransferTxn(
                sender=addr,
                sp=params,
                receiver=addr,
                amt=0,
                index=asset_id,
                close_assets_to=addr,  # close remainder to self (asset has 0 balance)
            )
            signed = txn.sign(sk)
            tx_id = algod.send_transaction(signed)
            transaction.wait_for_confirmation(algod, tx_id, 10)
            closed += 1
            print(f"  [{i+1}/{len(to_close)}] [OK] Closed asset {asset_id} (tx: {tx_id[:16]}...)")
        except Exception as e:
            failed += 1
            print(f"  [{i+1}/{len(to_close)}] [FAIL] Failed asset {asset_id}: {e}")

    print()
    # Re-fetch and show new state
    info2 = algod.account_info(addr)
    new_balance = info2.get("amount", 0)
    new_min = info2.get("min-balance", 0)
    new_assets = info2.get("assets", [])

    print("=" * 55)
    print("RESULT")
    print("=" * 55)
    print(f"Closed:       {closed} assets ({failed} failed)")
    print(f"Assets now:   {len(new_assets)}")
    print(f"Balance:      {new_balance / 1_000_000:.6f} ALGO")
    print(f"Min balance:  {new_min / 1_000_000:.6f} ALGO")
    print(f"Available:    {(new_balance - new_min) / 1_000_000:.6f} ALGO")

    if new_min / 1_000_000 <= TARGET_MIN_BALANCE_ALGO:
        print(f"\n[OK] Minimum balance is now ≤ {TARGET_MIN_BALANCE_ALGO} ALGO")
    else:
        remaining_needed = max(0, len(new_assets) - max_assets_allowed)
        print(f"\n[WARN] Still {remaining_needed} more assets to close to reach {TARGET_MIN_BALANCE_ALGO} ALGO target.")
        print("  Some assets have non-zero balance and cannot be auto-closed.")
        print("  Top up the wallet via: https://dispenser.testnet.aws.algodev.network/")
        print(f"  Wallet: {addr}")

if __name__ == "__main__":
    main()
