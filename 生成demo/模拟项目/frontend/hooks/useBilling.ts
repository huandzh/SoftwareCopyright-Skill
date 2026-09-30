"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchBillingSummary } from "@/lib/api";
import type { BillingSummary } from "@/lib/types";

/**
 * 计费数据钩子。
 * 页面只在需要时拉取，避免进入工作区就产生额外请求。
 */
export function useBilling(autoLoad = true) {
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setSummary(await fetchBillingSummary());
    } catch (err) {
      setError(err instanceof Error ? err.message : "计费信息加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (autoLoad) {
      void refresh();
    }
  }, [autoLoad, refresh]);

  const usedRatio = summary && summary.budget > 0 ? summary.total / summary.budget : 0;

  return { summary, loading, error, refresh, usedRatio };
}
