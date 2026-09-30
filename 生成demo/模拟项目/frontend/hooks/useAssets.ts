"use client";

import { useCallback, useEffect, useState } from "react";
import {
  deleteAsset,
  fetchCandidates,
  fetchGlobalAssets,
  fetchProjectAssets,
  pickCandidate,
  reuseAsset,
  revokeCandidate,
} from "@/lib/api";
import type { AssetCategory, CandidateAsset } from "@/lib/types";

/**
 * 素材数据钩子。
 * 传入项目编号时读取项目资产与候选，不传时读取全局素材库。
 */
export function useAssets(projectId: string) {
  const [categories, setCategories] = useState<AssetCategory[]>([]);
  const [candidates, setCandidates] = useState<CandidateAsset[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (projectId) {
        const [assets, pending] = await Promise.all([
          fetchProjectAssets(projectId),
          fetchCandidates(projectId),
        ]);
        setCategories(assets);
        setCandidates(pending);
      } else {
        setCategories(await fetchGlobalAssets());
        setCandidates([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "素材加载失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const pick = useCallback(
    async (candidateId: string) => {
      // 采用后候选转为正式资产，本地先移除再刷新列表
      setCandidates((previous) => previous.filter((item) => item.id !== candidateId));
      await pickCandidate(projectId, candidateId);
      await refresh();
    },
    [projectId, refresh],
  );

  const revoke = useCallback(
    async (candidateId: string) => {
      setCandidates((previous) => previous.filter((item) => item.id !== candidateId));
      await revokeCandidate(projectId, candidateId);
    },
    [projectId],
  );

  const remove = useCallback(
    async (assetId: string) => {
      await deleteAsset(assetId);
      setCategories((previous) =>
        previous.map((category) => ({
          ...category,
          items: category.items.filter((item) => item.id !== assetId),
        })),
      );
    },
    [],
  );

  const reuse = useCallback(
    async (assetId: string) => {
      if (!projectId) {
        throw new Error("请先进入一个项目再复用素材");
      }
      await reuseAsset(assetId, projectId);
    },
    [projectId],
  );

  return { categories, candidates, loading, error, refresh, pickCandidate: pick, revokeCandidate: revoke, deleteAsset: remove, reuseAsset: reuse };
}
