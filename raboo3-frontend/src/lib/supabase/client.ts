import { createBrowserClient } from '@supabase/ssr';
import type { SupabaseClient } from '@supabase/supabase-js';

const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() ?? '';
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim() ?? '';

let browserClient: SupabaseClient | null = null;

/**
 * عميل Supabase للمتصفح (متوافق مع Next.js + كوكيز الجلسة عبر @supabase/ssr).
 * يُستخدم لـ Auth، المفضلة، والبروفايل.
 */
export function getSupabaseBrowser(): SupabaseClient | null {
  if (url.length === 0 || anonKey.length === 0) return null;
  if (!browserClient) {
    browserClient = createBrowserClient(url, anonKey);
  }
  return browserClient;
}

/**
 * نفس المثيل الذي يعيده getSupabaseBrowser — للتوافق مع الكود السابق `import { supabase }`.
 */
export const supabase: SupabaseClient | null = getSupabaseBrowser();
