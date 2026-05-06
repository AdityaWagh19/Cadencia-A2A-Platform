'use client';

import dynamic from 'next/dynamic';

// WalletConnect v2 captures crypto.subtle at module init time.
// Must load client-side only (ssr: false) so it always gets the real browser crypto.
// ssr: false is only allowed inside Client Components — hence this wrapper.
const AlgorandWalletProviderClient = dynamic(
  () => import('./AlgorandWalletProvider').then(m => ({ default: m.AlgorandWalletProvider })),
  { ssr: false, loading: () => null }
);

export function WalletProviderWrapper({ children }: { children: React.ReactNode }) {
  return <AlgorandWalletProviderClient>{children}</AlgorandWalletProviderClient>;
}
