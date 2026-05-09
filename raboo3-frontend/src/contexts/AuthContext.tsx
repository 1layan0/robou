'use client';

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import type { User as SupabaseUser } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase/client';

type User = {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string | null;
};

type AuthContextType = {
  user: User | null;
  login: (user: User) => void;
  logout: () => Promise<void>;
  deleteAccount: () => Promise<void>;
  updateProfile: (partial: Partial<User>) => void;
  /** جلب البروفايل من Supabase (auth + public.users) وتحديث الـ state */
  refreshProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

type ProfileRow = { first_name: string | null; last_name: string | null; phone: string | null; email: string | null };

function mergeAuthAndProfile(authUser: SupabaseUser, row: ProfileRow | null): User {
  const meta = (authUser.user_metadata ?? {}) as Record<string, unknown>;
  const firstName =
    (row?.first_name ?? (meta.first_name as string) ?? (meta.firstName as string))?.trim() || 'User';
  const lastName = (row?.last_name ?? (meta.last_name as string) ?? (meta.lastName as string))?.trim() ?? '';
  const phone = row?.phone ?? (authUser.phone as string | null) ?? (meta.phone as string | null) ?? null;
  return {
    id: authUser.id,
    firstName,
    lastName,
    email: authUser.email ?? row?.email ?? '',
    phone: phone || null,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const loadUserWithProfile = useCallback(async (authUser: SupabaseUser) => {
    if (!supabase) return;
    const { data: row } = await supabase
      .from('users')
      .select('first_name, last_name, phone, email')
      .eq('id', authUser.id)
      .maybeSingle();
    setUser(mergeAuthAndProfile(authUser, row as ProfileRow | null));
  }, []);

  const loadRef = useRef(loadUserWithProfile);
  loadRef.current = loadUserWithProfile;

  // تهيئة مرة واحدة عند mount — لا نستدعي Auth إذا Supabase غير مضبوط (نتجنب Failed to fetch)
  useEffect(() => {
    if (!supabase) return;
    let cancelled = false;

    const applySession = (session: { user: SupabaseUser } | null) => {
      if (cancelled) return;
      if (session?.user) {
        loadRef.current(session.user);
      } else {
        setUser(null);
      }
    };

    supabase.auth.getSession().then(({ data, error }) => {
      if (error || cancelled) return;
      applySession(data.session ?? null);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      applySession(session);
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, []);

  const login = useCallback((nextUser: User) => {
    setUser(nextUser);
  }, []);

  const logout = useCallback(async () => {
    if (supabase) await supabase.auth.signOut();
    setUser(null);
  }, []);

  const deleteAccount = useCallback(async () => {
    if (supabase) await supabase.auth.signOut();
    setUser(null);
  }, []);

  const updateProfile = useCallback((partial: Partial<User>) => {
    setUser((prev) => (prev ? { ...prev, ...partial } : prev));
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!supabase) return;
    const { data: { user: authUser } } = await supabase.auth.getUser();
    if (!authUser) {
      setUser(null);
      return;
    }
    await loadUserWithProfile(authUser);
  }, [loadUserWithProfile]);

  return (
    <AuthContext.Provider value={{ user, login, logout, deleteAccount, updateProfile, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}

