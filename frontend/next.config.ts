import type { NextConfig } from "next";

// Hard error: MSW must never be active in production builds
if (process.env.NODE_ENV === 'production' && process.env.NEXT_PUBLIC_API_MOCKING === 'true') {
  throw new Error(
    'NEXT_PUBLIC_API_MOCKING must not be true in production builds. Remove it from your env.'
  );
}

// Internal backend URL — used server-side by Next.js proxy rewrites.
// In Docker: http://backend:8000 (Docker internal network, baked at build time).
// Local dev outside Docker: set NEXT_INTERNAL_BACKEND_URL=http://localhost:8000
const BACKEND_INTERNAL_URL =
  process.env.NEXT_INTERNAL_BACKEND_URL ?? 'http://backend:8000';

const nextConfig: NextConfig = {
  output: 'standalone',

  // Proxy all /v1/* API requests through Next.js to avoid CORS.
  // Browser → localhost:3000/v1/... → (Next.js rewrites) → backend:8000/v1/...
  async rewrites() {
    return [
      {
        source: '/v1/:path*',
        destination: `${BACKEND_INTERNAL_URL}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
