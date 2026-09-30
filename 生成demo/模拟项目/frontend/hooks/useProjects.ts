"use client";

import { useCallback, useEffect, useState } from "react";
import {
  archiveProject,
  createProject,
  fetchProjects,
  updateProject,
} from "@/lib/api";
import type { CreateProjectPayload, ProjectSummary } from "@/lib/types";

/**
 * 项目列表数据钩子。
 * 统一处理加载状态、错误信息与本地列表更新，页面组件不再各自请求。
 */
export function useProjects() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setProjects(await fetchProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : "项目列表加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const create = useCallback(async (payload: CreateProjectPayload) => {
    const created = await createProject(payload);
    // 新建的项目置顶，保持与后端按更新时间排序一致
    setProjects((previous) => [created, ...previous]);
    return created;
  }, []);

  const rename = useCallback(async (projectId: string, name: string) => {
    const updated = await updateProject(projectId, { name });
    setProjects((previous) =>
      previous.map((item) => (item.id === projectId ? { ...item, name: updated.name } : item)),
    );
  }, []);

  const remove = useCallback(async (projectId: string) => {
    await archiveProject(projectId);
    setProjects((previous) => previous.filter((item) => item.id !== projectId));
  }, []);

  return { projects, loading, error, refresh, createProject: create, renameProject: rename, removeProject: remove };
}
