import { NextRequest, NextResponse } from 'next/server';

const PUBLIC_ROUTES = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes
  const isPublic = PUBLIC_ROUTES.some(route => pathname.startsWith(route));
  if (isPublic) {
    return NextResponse.next();
  }

  // The app uses in-memory access tokens with httpOnly refresh cookies.
  // The refresh_token cookie is path-scoped to /v1/auth/refresh, so it is
  // NOT visible on normal page navigations. Therefore this middleware acts
  // as a lightweight hint: if a browser sends no cookies at all (brand-new
  // session with no prior login), redirect to /login.  The client-side
  // AuthContext handles the authoritative guard via silent refresh.
  const hasCookies = request.cookies.size > 0;
  const hasAuthHeader = !!request.headers.get('authorization');

  if (!hasCookies && !hasAuthHeader) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next|favicon.ico|api).*)'],
};
