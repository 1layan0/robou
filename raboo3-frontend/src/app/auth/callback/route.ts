import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { defaultLocale } from '@/i18n/config';

const defaultNext = `/${defaultLocale}/reset-password`;

function safeNextPath(raw: string | null): string {
  if (!raw || typeof raw !== 'string') return defaultNext;
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return defaultNext;
  }
  if (!decoded.startsWith('/') || decoded.startsWith('//')) return defaultNext;
  if (!/^\/(ar|en)(\/|$)/.test(decoded)) return defaultNext;
  return decoded;
}

export const dynamic = 'force-dynamic';

/**
 * نقطة دخول PKCE لروابط Supabase (إعادة تعيين كلمة المرور).
 * التبادل على السيرفر يضمن تعيين كوكيز الجلسة مع الرد.
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const nextPath = safeNextPath(url.searchParams.get('next'));

  const oauthError = url.searchParams.get('error');
  if (oauthError) {
    const fail = new URL(nextPath, url.origin);
    fail.searchParams.set('auth_error', oauthError);
    const desc = url.searchParams.get('error_description');
    if (desc) fail.searchParams.set('auth_error_description', desc.slice(0, 300));
    return NextResponse.redirect(fail);
  }

  if (code) {
    const cookieStore = await cookies();
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
            try {
              cookiesToSet.forEach(({ name, value, options }) =>
                cookieStore.set(name, value, options)
              );
            } catch {
              /* RSC / edge */
            }
          },
        },
      }
    );

    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.warn('[auth/callback] exchangeCodeForSession:', error.message);
      }
      const fail = new URL(nextPath, url.origin);
      fail.searchParams.set('auth_error', 'exchange_failed');
      fail.searchParams.set('auth_error_description', error.message.slice(0, 300));
      return NextResponse.redirect(fail);
    }
  }

  return NextResponse.redirect(new URL(nextPath, url.origin));
}
