'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Plus, RotateCcw, FileText, ChevronDown } from 'lucide-react';

import { AppShell } from '@/components/layout/AppShell';
import { SectionHeader } from '@/components/shared/SectionHeader';
import { DataTable } from '@/components/shared/DataTable';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { TextareaWithButton } from '@/components/shared/TextareaWithButton';
import { RfqDetailPanel } from '@/components/shared/RfqDetailPanel';
import { Button } from '@/components/ui/button';
import {
  Sheet, SheetContent, SheetHeader, SheetTitle,
} from '@/components/ui/sheet';

import { api } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { ROUTES } from '@/lib/constants';
import type { RFQ, SellerMatch } from '@/types';

const STATUS_OPTIONS = ['All', 'DRAFT', 'PARSED', 'MATCHED', 'NEGOTIATING', 'CONFIRMED'] as const;

export default function MarketplacePage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // ─── State ──────────────────────────────────────────────────────────────────
  const [formExpanded, setFormExpanded] = React.useState(false);
  const [rfqText, setRfqText] = React.useState('');
  const [selectedRfqId, setSelectedRfqId] = React.useState<string | null>(null);
  const [filter, setFilter] = React.useState<string>('All');
  const [mobileSheetOpen, setMobileSheetOpen] = React.useState(false);

  // ─── Fetch all RFQs from API ───────────────────────────────────────────────
  const { data: allRfqs = [], isLoading: rfqsLoading } = useQuery<RFQ[]>({
    queryKey: ['rfqs'],
    queryFn: () => api.get('/v1/marketplace/rfqs').then(r => r.data.data as RFQ[]),
    refetchInterval: 5000,
  });

  // ─── Filter ─────────────────────────────────────────────────────────────────
  const filteredRfqs = React.useMemo(() => {
    if (filter === 'All') return allRfqs;
    return allRfqs.filter(r => r.status === filter);
  }, [allRfqs, filter]);

  // ─── Selected RFQ ──────────────────────────────────────────────────────────
  const selectedRfq = allRfqs.find(r => r.id === selectedRfqId) ?? null;

  // ─── Matches for selected RFQ ──────────────────────────────────────────────
  const { data: matches = [], isLoading: matchesLoading } = useQuery<SellerMatch[]>({
    queryKey: ['rfq', selectedRfqId, 'matches'],
    queryFn: () => api.get(`/v1/marketplace/rfq/${selectedRfqId}/matches`).then(r => r.data.data),
    enabled: !!selectedRfqId && (selectedRfq?.status === 'MATCHED' || selectedRfq?.status === 'NEGOTIATING'),
  });

  // ─── Negotiation sessions for NEGOTIATING RFQs ────────────────────────────
  const { data: negotiations = [] } = useQuery<any[]>({
    queryKey: ['rfq', selectedRfqId, 'negotiations'],
    queryFn: () => api.get('/v1/sessions').then(r => {
      const sessions = r.data.data || [];
      // Filter sessions linked to this RFQ
      return sessions.filter((s: any) => String(s.rfq_id) === selectedRfqId);
    }),
    enabled: !!selectedRfqId && selectedRfq?.status === 'NEGOTIATING',
    refetchInterval: 5000,
  });

  // ─── Polling for DRAFT/PARSED RFQs ────────────────────────────────────────
  React.useEffect(() => {
    const hasPendingRfqs = allRfqs.some(r => ['DRAFT', 'PARSED'].includes(r.status));
    if (!hasPendingRfqs) return;

    const interval = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ['rfqs'] });
    }, 3000);

    return () => clearInterval(interval);
  }, [allRfqs, queryClient]);

  // ─── Submit new RFQ ────────────────────────────────────────────────────────
  const submitMutation = useMutation({
    mutationFn: async (rawText: string) => {
      const res = await api.post('/v1/marketplace/rfq', { raw_text: rawText });
      return res.data.data as { rfq_id: string; status: string };
    },
    onSuccess: (data) => {
      toast.success(`RFQ submitted! ID: ${data.rfq_id}`);
      setRfqText('');
      setFormExpanded(false);
      setSelectedRfqId(data.rfq_id);
      // Invalidate to refetch the full list
      queryClient.invalidateQueries({ queryKey: ['rfqs'] });
    },
    onError: () => {
      toast.error('Failed to submit RFQ');
    },
  });

  // ─── Start all negotiations ────────────────────────────────────────────────
  const startNegotiationsMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/v1/marketplace/rfq/${selectedRfqId}/start-negotiations`);
      return res.data.data as { session_ids: string[]; message: string };
    },
    onSuccess: (data) => {
      toast.success(data.message);
      queryClient.invalidateQueries({ queryKey: ['rfqs'] });
      queryClient.invalidateQueries({ queryKey: ['rfq', selectedRfqId, 'negotiations'] });
    },
    onError: () => {
      toast.error('Failed to start negotiations');
    },
  });

  // ─── Accept best deal (confirm) ──────────────────────────────────────────
  const confirmMutation = useMutation({
    mutationFn: async (match: SellerMatch) => {
      const res = await api.post(`/v1/marketplace/rfq/${selectedRfqId}/confirm`, {
        seller_enterprise_id: match.enterprise_id,
      });
      return res.data.data as { session_id: string };
    },
    onSuccess: (data) => {
      toast.success('Deal accepted! Proceeding to escrow.');
      queryClient.invalidateQueries({ queryKey: ['rfqs'] });
      router.push(`${ROUTES.ESCROW}`);
    },
    onError: () => {
      toast.error('Failed to accept deal');
    },
  });

  // ─── Row click handler ─────────────────────────────────────────────────────
  const handleRowClick = (rfq: RFQ) => {
    setSelectedRfqId(rfq.id);
    // On mobile open sheet
    if (window.innerWidth < 1024) {
      setMobileSheetOpen(true);
    }
  };

  // ─── Refresh all ───────────────────────────────────────────────────────────
  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['rfqs'] });
  };

  // ─── Detail content (reused in desktop panel and mobile sheet) ─────────────
  const detailContent = selectedRfq ? (
    <RfqDetailPanel
      rfq={selectedRfq}
      matches={matches}
      matchesLoading={matchesLoading}
      negotiations={negotiations}
      onStartNegotiations={() => startNegotiationsMutation.mutate()}
      isStartingNegotiations={startNegotiationsMutation.isPending}
      onAcceptDeal={(match) => confirmMutation.mutate(match)}
      isAcceptingDeal={confirmMutation.isPending}
    />
  ) : (
    <div className="flex items-center justify-center h-full py-16">
      <p className="text-sm text-muted-foreground">Select an RFQ to view details</p>
    </div>
  );

  return (
    <AppShell>
      <div className="p-6">

        {/* Section 1: New RFQ Form */}
        <div className="bg-card border border-border rounded-lg p-6 mb-8">
          <SectionHeader
            title="Request for Quotation"
            action={{
              label: formExpanded ? 'Cancel' : 'New RFQ',
              icon: formExpanded ? undefined : Plus,
              onClick: () => setFormExpanded(!formExpanded),
            }}
          />
          {formExpanded && (
            <div className="animate-in fade-in slide-in-from-top-2 duration-200">
              <p className="text-sm text-muted-foreground mb-3">
                Describe your requirement in natural language. AI will parse and match sellers.
              </p>
              <TextareaWithButton
                placeholder="Need 500 metric tons of HR Coil, IS 2062 grade, delivery to Mumbai port within 45 days. Budget: ₹38,000-42,000 per MT."
                buttonText="Submit RFQ"
                value={rfqText}
                onChange={setRfqText}
                onSubmit={() => submitMutation.mutate(rfqText)}
                isLoading={submitMutation.isPending}
              />
            </div>
          )}
        </div>

        {/* Section 2: RFQ List + Detail Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left: RFQ List */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between border-b border-border pb-3 mb-4">
              <h3 className="text-base font-semibold text-foreground">Your RFQs</h3>
              <div className="flex items-center gap-2">
                {/* Filter dropdown */}
                <div className="relative">
                  <select
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="appearance-none bg-muted border border-border rounded-md px-3 py-1.5 pr-8 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
                  >
                    {STATUS_OPTIONS.map(opt => (
                      <option key={opt} value={opt}>{opt === 'All' ? 'All' : opt}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                </div>

                {/* Refresh */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRefresh}
                  className="text-primary hover:bg-secondary"
                >
                  <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                  Refresh
                </Button>
              </div>
            </div>

            <DataTable<RFQ>
              columns={[
                {
                  key: 'id',
                  label: 'RFQ ID',
                  render: (v) => <span className="text-primary font-mono text-xs">{String(v)}</span>,
                },
                {
                  key: 'raw_text',
                  label: 'Description',
                  render: (v) => {
                    const s = String(v);
                    return (
                      <span className="text-foreground" title={s}>
                        {s.length > 40 ? s.slice(0, 40) + '...' : s}
                      </span>
                    );
                  },
                },
                {
                  key: 'status',
                  label: 'Status',
                  render: (v) => <StatusBadge status={String(v)} />,
                },
                {
                  key: 'created_at',
                  label: 'Created',
                  sortable: true,
                  render: (v) => <span className="text-muted-foreground text-xs">{formatDate(String(v))}</span>,
                },
              ]}
              data={filteredRfqs}
              isLoading={rfqsLoading}
              keyExtractor={(row) => row.id}
              onRowClick={handleRowClick}
              emptyState={{ icon: FileText, title: 'No RFQs yet', description: 'Submit your first RFQ above' }}
            />
          </div>

          {/* Right: Detail Panel (desktop) */}
          <div className="hidden lg:block">
            <div className="bg-card border border-border rounded-lg p-5 sticky top-20">
              <h3 className="text-base font-semibold text-foreground border-b border-border pb-3 mb-4">
                {selectedRfq ? `RFQ #${selectedRfq.id}` : 'RFQ Details'}
              </h3>
              {detailContent}
            </div>
          </div>
        </div>

        {/* Mobile Sheet for Detail Panel */}
        <Sheet open={mobileSheetOpen} onOpenChange={setMobileSheetOpen}>
          <SheetContent side="right" className="bg-card border-border w-full sm:max-w-md overflow-y-auto">
            <SheetHeader>
              <SheetTitle className="text-foreground">
                {selectedRfq ? `RFQ #${selectedRfq.id}` : 'RFQ Details'}
              </SheetTitle>
            </SheetHeader>
            <div className="mt-4">
              {detailContent}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </AppShell>
  );
}
