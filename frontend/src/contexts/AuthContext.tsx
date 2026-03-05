'use client';

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

type User = {
  firstName: string;
  lastName: string;
  email: string;
  phone?: string | null;
};

type AuthContextType = {
  user: User | null;
  login: (user: User) => void;
  logout: () => void;
  deleteAccount: () => void;
  updateProfile: (partial: Partial<User>) => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const STORAGE_KEY = 'robou_auth_user';

/** يقرأ المستخدم المحفوظ من localStorage (للاستخدام عند تسجيل الدخول للحفاظ على التعديلات) */
export function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as any;
    if (!parsed || typeof parsed.email !== 'string') return null;
    if (parsed.firstName && parsed.lastName !== undefined) {
      return {
        firstName: parsed.firstName,
        lastName: parsed.lastName,
        email: parsed.email,
        phone: parsed.phone ?? '',
      };
    }
    const baseName =
      typeof parsed.name === 'string' && parsed.name.trim()
        ? parsed.name
        : (parsed.email as string).split('@')[0] || '';
    const parts = baseName.trim().split(/\s+/);
    return {
      firstName: parts[0] || baseName || 'User',
      lastName: parts[1] || '',
      email: parsed.email,
      phone: parsed.phone ?? '',
    };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  // Load user from localStorage on first mount (client-side only)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as any;
        if (parsed && typeof parsed.email === 'string') {
          // دعم البيانات القديمة التي كانت تستخدم حقل name واحد
          if (!parsed.firstName || !parsed.lastName) {
            const baseName: string =
              typeof parsed.name === 'string' && parsed.name.trim()
                ? parsed.name
                : parsed.email.split('@')[0] || '';
            const parts = baseName.trim().split(/\s+/);
            const firstName = parts[0] || baseName || 'User';
            const lastName = parts[1] || '';
            setUser({
              firstName,
              lastName,
              email: parsed.email,
              phone: parsed.phone ?? '',
            });
          } else {
            setUser({
              firstName: parsed.firstName,
              lastName: parsed.lastName,
              email: parsed.email,
              phone: parsed.phone ?? '',
            });
          }
        }
      }
    } catch {
      // ignore parsing/storage errors
    }
  }, []);

  // حفظ المستخدم في localStorage عند تغييره (عند تسجيل الخروج لا نمسح التخزين لاستعادة التعديلات عند الدخول بنفس الإيميل)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      if (user) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
      }
    } catch {
      // ignore storage errors
    }
  }, [user]);

  const login = useCallback((nextUser: User) => {
    setUser(nextUser);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
  }, []);

  const deleteAccount = useCallback(() => {
    setUser(null);
    try {
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // ignore
    }
  }, []);

  const updateProfile = useCallback((partial: Partial<User>) => {
    setUser((prev) => (prev ? { ...prev, ...partial } : prev));
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, deleteAccount, updateProfile }}>
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

