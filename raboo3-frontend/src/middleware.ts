import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { defaultLocale, isLocale } from './i18n/config';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Skip middleware for static files and API routes
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.startsWith('/favicon') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0];
  const pathnameHasLocale = isLocale(firstSegment);

  // Let next.config rewrites handle "/" -> "/ar"; don't rewrite here to avoid 404
  if (pathname === '/' || pathname === '') {
    return NextResponse.next();
  }

  /* PKCE / استعادة كلمة المرور: بدون بادئة لغة — لا تُحوَّل إلى /ar/auth/callback */
  if (pathname === '/auth/callback' || pathname.startsWith('/auth/')) {
    return NextResponse.next();
  }

  // If path doesn't start with a locale, redirect to default locale
  if (!pathnameHasLocale && firstSegment) {
    return NextResponse.redirect(new URL(`/${defaultLocale}${pathname}`, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Do not run middleware for: api, _next (all Next.js assets), favicon, or paths with a file extension.
     */
    '/((?!api|_next|favicon\\.ico|.*\\..*).*)',
  ],
};

