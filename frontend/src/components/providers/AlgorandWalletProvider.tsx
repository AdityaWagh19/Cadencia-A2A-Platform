'use client';

import { WalletProvider } from '@txnlab/use-wallet-react';
import type { WalletManager } from '@txnlab/use-wallet-react';
import { useState, useEffect, createContext, useContext } from 'react';

/**
 * Tracks whether the Algorand WalletManager has been initialised.
 * Consumers (e.g. CadenciaWalletProvider) check this before calling
 * useWallet(), preventing crashes when the manager isn't ready yet.
 */
const WalletReadyContext = createContext(false);
export const useWalletReady = () => useContext(WalletReadyContext);

export function AlgorandWalletProvider({ children }: { children: React.ReactNode }) {
  const [manager, setManager] = useState<WalletManager | null>(null);

  useEffect(() => {
    let cancelled = false;
    import('@/lib/wallet-config').then(({ getWalletManager }) => {
      if (!cancelled) setManager(getWalletManager());
    }).catch((err) => {
      console.warn('[AlgorandWalletProvider] Wallet SDK failed to load:', err);
    });
    return () => { cancelled = true; };
  }, []);

  // IMPORTANT: Always render children so the app isn't blocked.
  // Before the manager loads, children that need useWallet() should
  // guard themselves via useWalletReady().
  if (!manager) {
    return (
      <WalletReadyContext.Provider value={false}>
        {children}
      </WalletReadyContext.Provider>
    );
  }

  return (
    <WalletReadyContext.Provider value={true}>
      <WalletProvider manager={manager}>{children}</WalletProvider>
    </WalletReadyContext.Provider>
  );
}

