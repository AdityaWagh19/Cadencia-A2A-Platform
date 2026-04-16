import { NetworkId, WalletId, WalletManager } from '@txnlab/use-wallet-react';

const ALGOD_BASE = process.env.NEXT_PUBLIC_ALGOD_SERVER || 'https://testnet-api.4160.nodely.dev';
const ALGOD_PORT = process.env.NEXT_PUBLIC_ALGOD_PORT || '';
const ALGOD_TOKEN = process.env.NEXT_PUBLIC_ALGOD_TOKEN || '';
const NETWORK = (process.env.NEXT_PUBLIC_ALGORAND_NETWORK || 'testnet') as NetworkId;
const WC_PROJECT_ID = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || '';

let _manager: WalletManager | null = null;

export function getWalletManager(): WalletManager {
  if (_manager) return _manager;

  _manager = new WalletManager({
    wallets: [
      {
        id: WalletId.PERA,
        options: { projectId: WC_PROJECT_ID },
      },
      {
        id: WalletId.DEFLY,
        options: { projectId: WC_PROJECT_ID },
      },
    ],
    defaultNetwork: NETWORK,
    networks: {
      [NETWORK]: {
        algod: {
          baseServer: ALGOD_BASE,
          port: ALGOD_PORT,
          token: ALGOD_TOKEN,
        },
      },
    },
  });

  return _manager;
}
