import { http, HttpResponse } from 'msw';

export const sellerProfileHandlers = [
  // GET seller profile
  http.get('*/v1/marketplace/capability-profile', () => HttpResponse.json({
    status: 'success',
    data: {
      industry: 'Steel Manufacturing',
      geographies: ['Maharashtra', 'Gujarat', 'Karnataka'],
      products: ['HR Coil', 'Cold Rolled', 'Wire Rod'],
      min_order_value: 100000,
      max_order_value: 50000000,
      description: 'Leading HR Coil manufacturer with 2MT/day capacity. ISO 9001 certified. Pan-India delivery within 30 days. Competitive bulk pricing.',
      embedding_status: 'active',
      last_embedded: '2026-04-03T20:00:00Z',
    },
  })),

  // PUT update profile
  http.put('*/v1/marketplace/capability-profile', () => HttpResponse.json({
    status: 'success',
    data: {
      message: 'Seller profile updated successfully',
      embedding_status: 'queued',
    },
  })),

  // POST trigger embeddings
  http.post('*/v1/marketplace/capability-profile/embeddings', () => HttpResponse.json({
    status: 'success',
    data: {
      message: 'Embeddings recomputation queued. Profile will be active for matching in ~30 seconds.',
    },
  })),

  // ── Catalogue endpoints ─────────────────────────────────────────────────

  http.get('*/v1/marketplace/catalogue', () => HttpResponse.json({
    status: 'success',
    data: [
      {
        id: 'cat-001',
        product_name: 'TMT Bar Fe500D',
        hsn_code: '72142000',
        product_category: 'TMT_BAR',
        grade: 'Fe500D',
        unit: 'MT',
        price_per_unit_inr: 45000,
        bulk_pricing_tiers: [
          { min_qty: 1, max_qty: 10, price_per_unit_inr: 45000 },
          { min_qty: 10, max_qty: 50, price_per_unit_inr: 43000 },
          { min_qty: 50, max_qty: null, price_per_unit_inr: 41000 },
        ],
        moq: 1,
        max_order_qty: 500,
        lead_time_days: 7,
        in_stock_qty: 50,
        is_active: true,
        certifications: ['BIS', 'ISO 9001'],
        created_at: '2026-04-01T10:00:00Z',
        updated_at: '2026-04-15T10:00:00Z',
      },
      {
        id: 'cat-002',
        product_name: 'HR Coil IS 2062',
        hsn_code: '72083690',
        product_category: 'HR_COIL',
        grade: 'E250',
        unit: 'MT',
        price_per_unit_inr: 52000,
        bulk_pricing_tiers: null,
        moq: 5,
        max_order_qty: 200,
        lead_time_days: 14,
        in_stock_qty: 0,
        is_active: true,
        certifications: ['ISO 9001'],
        created_at: '2026-04-05T10:00:00Z',
        updated_at: '2026-04-15T10:00:00Z',
      },
    ],
  })),

  http.post('*/v1/marketplace/catalogue', async ({ request }) => {
    const body = await request.json() as Record<string, any>;
    return HttpResponse.json({
      status: 'success',
      data: { id: 'cat-new', ...body, is_active: true, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    }, { status: 201 });
  }),

  http.put('*/v1/marketplace/catalogue/:id', async ({ request }) => {
    const body = await request.json() as Record<string, any>;
    return HttpResponse.json({ status: 'success', data: { ...body, updated_at: new Date().toISOString() } });
  }),

  http.delete('*/v1/marketplace/catalogue/:id', () => HttpResponse.json({
    status: 'success',
    data: { message: 'Catalogue item deactivated' },
  })),

  // ── Capacity profile ──────────────────────────────────────────────────

  http.get('*/v1/marketplace/capacity-profile', () => HttpResponse.json({
    status: 'success',
    data: {
      id: 'cap-001',
      enterprise_id: 'ent-001',
      monthly_production_capacity_mt: 500,
      current_utilization_pct: 65,
      available_capacity_mt: 175,
      num_production_lines: 3,
      shift_pattern: 'DOUBLE_SHIFT',
      avg_dispatch_days: 3,
      max_delivery_radius_km: 1500,
      has_own_transport: true,
      preferred_transport_modes: ['ROAD', 'RAIL'],
      ex_works_available: true,
      created_at: '2026-04-01T10:00:00Z',
      updated_at: '2026-04-15T10:00:00Z',
    },
  })),

  http.put('*/v1/marketplace/capacity-profile', async ({ request }) => {
    const body = await request.json() as Record<string, any>;
    return HttpResponse.json({
      status: 'success',
      data: { id: 'cap-001', enterprise_id: 'ent-001', ...body, available_capacity_mt: body.monthly_production_capacity_mt * (1 - body.current_utilization_pct / 100) },
    });
  }),

  // ── Pincode lookup ────────────────────────────────────────────────────

  http.get('*/v1/marketplace/pincode/:pincode', ({ params }) => {
    const pincodeMap: Record<string, any> = {
      '110001': { pincode: '110001', city: 'New Delhi', state: 'Delhi', latitude: 28.6139, longitude: 77.209 },
      '400001': { pincode: '400001', city: 'Mumbai', state: 'Maharashtra', latitude: 18.9388, longitude: 72.8354 },
      '560001': { pincode: '560001', city: 'Bengaluru', state: 'Karnataka', latitude: 12.9716, longitude: 77.5946 },
    };
    const data = pincodeMap[params.pincode as string];
    if (data) return HttpResponse.json({ status: 'success', data });
    return HttpResponse.json({ status: 'error', message: 'Pincode not found' }, { status: 404 });
  }),
];
