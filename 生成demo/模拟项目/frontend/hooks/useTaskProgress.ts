"use client";

import { useCallback, useEffect, useState } from "react";
import type { GenerationEvent } from "@/lib/types";

/**
 * 任务进度钩子。
 * 定时拉取时间线事件，生成过程中使用较短间隔，结束后停止轮询。
 */
export function useTaskProgress(projectId: string, active: boolean) {
  const [events, setEvents] = useState<GenerationEvent[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!projectId) {
      return;
    }
    const base = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";
    try {
      const response = await fetch(base + "/projects/" + projectId + "/tasks", {
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error("任务列表加载失败");
      }
      const tasks = (await response.json()) as Array<{ id: string; status: string }>;
      const latest = tasks[0];
      if (!latest) {
        setEvents([]);
        return;
      }
      const eventsResponse = await fetch(
        base + "/projects/" + projectId + "/tasks/" + latest.id + "/events",
        { credentials: "include" },
      );
      if (eventsResponse.ok) {
        setEvents((await eventsResponse.json()) as GenerationEvent[]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务进度读取失败");
    }
  }, [projectId]);

  useEffect(() => {
    if (!active) {
      return;
    }
    void load();
    // 生成过程中每 3 秒刷新一次，停止后不再轮询
    const timer = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(timer);
  }, [active, load]);

  return { events, error, refresh: load };
}
