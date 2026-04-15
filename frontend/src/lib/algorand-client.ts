/**
 * AlgoKit-compatible Algorand client configuration.
 *
 * Follows the Vibekit pattern: a shared algod config used by both the
 * WalletManager and any direct chain queries from the frontend.
 */

import algosdk from 'algosdk';

const ALGOD_SERVER = process.env.NEXT_PUBLIC_ALGOD_SERVER || 'https://testnet-api.4160.nodely.dev';
const ALGOD_PORT = process.env.NEXT_PUBLIC_ALGOD_PORT || '';
const ALGOD_TOKEN = process.env.NEXT_PUBLIC_ALGOD_TOKEN || '';
const NETWORK = process.env.NEXT_PUBLIC_ALGORAND_NETWORK || 'testnet';

let _algodClient: algosdk.Algodv2 | null = null;

/**
 * Get a singleton Algod client for direct chain queries.
 */
export function getAlgodClient(): algosdk.Algodv2 {
  if (_algodClient) return _algodClient;

  _algodClient = new algosdk.Algodv2(
    ALGOD_TOKEN,
    ALGOD_SERVER,
    ALGOD_PORT,
  );

  return _algodClient;
}

/**
 * Get the configured network identifier.
 */
export function getNetwork(): string {
  return NETWORK;
}

/**
 * Get Lora Explorer URL for a transaction or application.
 */
export function getLoraExplorerUrl(id: string | number, type: 'transaction' | 'application'): string {
  return `https://lora.algokit.io/${NETWORK}/${type}/${id}`;
}
