"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ProjectCard } from "@/components/ProjectCard";
import { useProjects } from "@/hooks/useProjects";
import { formatDateTime, formatDuration } from "@/lib/format";
import type { ProjectSummary } from "@/lib/types";

// 项目列表的分类标签，用于快速筛选
const FILTERS: Array<{ key: string; label: string }> = [
  { key: "all", label: "全部" },
  { key: "draft", label: "草稿" },
  { key: "scripting", label: "剧本分析" },
  { key: "storyboarding", label: "分镜规划" },
  { key: "visualizing", label: "视觉生成" },
  { key: "composing", label: "视频合成" },
  { key: "dubbing", label: "配音与音效" },
  { key: "done", label: "已完成" },
];

/**
 * 项目列表页。
 * 展示当前账号下的全部视频项目，支持按阶段筛选、关键字搜索和新建项目。
 */
export default function ProjectsPage() {
  const { projects, loading, error, createProject, refresh } = useProjects();
  const [keyword, setKeyword] = useState("");
  const [stage, setStage] = useState("all");
  const [creating, setCreating] = useState(false);

  // 关键字与阶段筛选在客户端完成，避免每次输入都请求后端
  const visible = useMemo(() => {
    const text = keyword.trim().toLowerCase();
    return projects.filter((project: ProjectSummary) => {
      const matchStage = stage === "all" || project.stage === stage;
      if (!matchStage) {
        return false;
      }
      if (!text) {
        return true;
      }
      return (
        project.name.toLowerCase().includes(text) ||
        project.idea.toLowerCase().includes(text)
      );
    });
  }, [projects, keyword, stage]);

  const totalMinutes = useMemo(
    () => projects.reduce((sum, project) => sum + project.durationSeconds, 0) / 60,
    [projects],
  );

  async function handleCreate() {
    // 新建项目只需要一句创意描述，其余交给智能体补全
    setCreating(true);
    try {
      await createProject({
        name: "未命名视频项目",
        idea: "一位年轻导演在雨天拍摄城市夜景的短片",
      });
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">我的视频项目</h1>
          <p className="mt-1 text-sm text-slate-400">
            共 {projects.length} 个项目，累计成片时长约 {formatDuration(totalMinutes * 60)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded border border-slate-700 px-3 py-2 text-sm hover:border-slate-500"
          >
            刷新
          </button>
          <button
            type="button"
            disabled={creating}
            onClick={() => void handleCreate()}
            className="rounded bg-sky-600 px-4 py-2 text-sm font-medium disabled:opacity-60"
          >
            {creating ? "正在创建…" : "新建项目"}
          </button>
        </div>
      </header>

      <section className="flex flex-wrap items-center gap-3">
        <input
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="搜索项目名称或创意描述"
          className="w-72 rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
        />
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setStage(item.key)}
              className={
                item.key === stage
                  ? "rounded-full bg-sky-600/20 px-3 py-1 text-xs text-sky-300"
                  : "rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300"
              }
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      {error ? (
        <p className="rounded border border-rose-800 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">
          {error}
        </p>
      ) : null}

      {loading && !projects.length ? (
        <p className="text-sm text-slate-400">正在加载项目…</p>
      ) : null}

      {!loading && !visible.length ? (
        <p className="rounded border border-slate-800 px-4 py-10 text-center text-sm text-slate-400">
          没有匹配的项目，换个关键字或先新建一个项目。
        </p>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>

      <footer className="text-xs text-slate-500">
        最近更新：{formatDateTime(new Date().toISOString())}
      </footer>
    </main>
  );
}
