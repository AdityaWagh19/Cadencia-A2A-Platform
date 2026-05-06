'use client';

import { useAuth } from '@/hooks/useAuth';

/**
 * AdminSection — renders children only when the current user is an admin.
 * Unlike AdminGuard, this component does NOT redirect; it simply hides the
 * content. Use this when guarding a section *within* a page that all
 * authenticated users can visit (e.g. the Bulk Export panel on the Compliance
 * page). Use AdminGuard only for full-page access control.
 */
export function AdminSection({ children }: { children: React.ReactNode }) {
  const { isAdmin, isLoading } = useAuth();

  if (isLoading || !isAdmin) return null;

  return <>{children}</>;
}
