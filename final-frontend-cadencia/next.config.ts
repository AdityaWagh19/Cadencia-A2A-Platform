import type { NextConfig } from "next";

// Hard error: MSW must never be active in production builds
if (process.env.NODE_ENV === 'production' && process.env.NEXT_PUBLIC_API_MOCKING === 'true') {
  throw new Error(
    'NEXT_PUBLIC_API_MOCKING must not be true in production builds. Remove it from your env.'
  );
}

const nextConfig: NextConfig = {
  output: 'standalone',
};

export default nextConfig;
