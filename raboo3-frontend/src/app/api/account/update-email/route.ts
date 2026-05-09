import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { getSupabaseAdmin } from '@/lib/supabase/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

/**
 * POST /api/account/update-email
 * Server-only: uses SUPABASE_SERVICE_ROLE_KEY to update auth.users email immediately (no confirmation).
 * Then syncs public.users.email. Client sends Authorization: Bearer <access_token>.
 */
export async function POST(request: Request) {
  try {
    const authHeader = request.headers.get('authorization');
    const token = authHeader?.startsWith('Bearer ') ? authHeader.slice(7) : null;
    if (!token) {
      return NextResponse.json({ error: 'Missing or invalid Authorization header' }, { status: 401 });
    }

    const body = await request.json();
    const newEmail = typeof body?.newEmail === 'string' ? body.newEmail.trim() : '';
    if (!newEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail)) {
      return NextResponse.json({ error: 'Valid newEmail required' }, { status: 400 });
    }

    const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() ?? '';
    const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim() ?? '';
    if (!url || !anonKey) {
      return NextResponse.json({ error: 'Server Supabase config missing' }, { status: 500 });
    }

    const anon = createClient(url, anonKey, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data: { user }, error: userError } = await anon.auth.getUser(token);
    if (userError || !user) {
      return NextResponse.json({ error: userError?.message ?? 'Invalid or expired token' }, { status: 401 });
    }

    const admin = getSupabaseAdmin();
    if (!admin) {
      return NextResponse.json({ error: 'Server admin client not configured (SUPABASE_SERVICE_ROLE_KEY)' }, { status: 500 });
    }

    const { error: authUpdateError } = await admin.auth.admin.updateUserById(user.id, {
      email: newEmail,
      email_confirm: true,
    });
    if (authUpdateError) {
      return NextResponse.json({ error: authUpdateError.message }, { status: 400 });
    }

    const now = new Date().toISOString();
    const { error: tableError } = await admin.from('users').update({ email: newEmail, updated_at: now }).eq('id', user.id);
    if (tableError) {
      return NextResponse.json({ error: tableError.message }, { status: 500 });
    }

    return NextResponse.json({ ok: true, email: newEmail });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Update failed';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
