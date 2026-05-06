import * as React from 'react';
import { ExternalLink } from 'lucide-react';

const NETWORK = process.env.NEXT_PUBLIC_ALGORAND_NETWORK || 'testnet';
const LORA_BASE = `https://lora.algokit.io/${NETWORK}`;

interface TxExplorerLinkProps {
  txId: string | number;
  type: 'tx' | 'app';
}

export function TxExplorerLink({ txId, type }: TxExplorerLinkProps) {
  const isApp = type === 'app';
  const href = isApp
    ? `${LORA_BASE}/application/${txId}`
    : `${LORA_BASE}/transaction/${txId}`;
  const display = isApp ? `#${txId}` : String(txId).slice(0, 8) + '...';

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 font-mono text-xs text-primary hover:underline hover:text-primary/90"
      title={`View on Lora Explorer: ${txId}`}
    >
      {display}
      <ExternalLink className="h-3 w-3" />
    </a>
  );
}
