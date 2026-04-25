import { NextRequest, NextResponse } from 'next/server';

/**
 * Next.js 16 Proxy (Middleware).
 *
 * Auth is managed entirely client-side via in-memory access tokens and
 * httpOnly refresh cookies (path-scoped to /v1/auth/refresh). The proxy
 * cannot reliably determine auth state because:
 *   - Access tokens are in-memory (not available as cookies)
 *   - Refresh cookies are path-scoped and invisible to page navigations
 *
 * All auth guards are handled by the <AuthContext> and individual page
 * components that call useAuth() and redirect to /login when needed.
 *
 * This proxy now simply passes all requests through.
 */
export function proxy(request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next|favicon.ico|api).*)'],
};
