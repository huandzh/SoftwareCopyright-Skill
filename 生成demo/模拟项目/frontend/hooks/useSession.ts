"use client";

import { useCallback, useEffect, useState } from "react";
import { logout } from "@/lib/api";

export interface SessionUser {
  userId: string;
  email: string;
  displayName: string;
  monthlyBudget: number;
}

/**
 * 账号会话钩子。
 * 只保存展示需要的账号信息，令牌由后端 HttpOnly Cookie 保管。
 */
export function useSession() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const base = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";
      try {
        const response = await fetch(base + "/auth/me", { credentials: "include" });
        if (!response.ok) {
          if (!cancelled) {
            setUser(null);
          }
          return;
        }
        const payload = (await response.json()) as {
          user_id: string;
          email: string;
          display_name: string;
          monthly_budget: number;
        };
        if (!cancelled) {
          setUser({
            userId: payload.user_id,
            email: payload.email,
            displayName: payload.display_name,
            monthlyBudget: payload.monthly_budget,
          });
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const signOut = useCallback(async () => {
    await logout();
    setUser(null);
  }, []);

  return { user, loading, signOut };
}
