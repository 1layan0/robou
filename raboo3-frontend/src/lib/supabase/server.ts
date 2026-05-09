import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() ?? '';
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY?.trim() ?? '';

/**
 * Server-only Supabase client with service_role. Use for admin operations (e.g. auth.admin.updateUserById).
 * Never expose SUPABASE_SERVICE_ROLE_KEY to the client.
 */
export function getSupabaseAdmin(): SupabaseClient | null {
  if (url.length === 0 || serviceRoleKey.length === 0) return null;
  return createClient(url, serviceRoleKey, { auth: { persistSession: false, autoRefreshToken: false } });
}
