"use client";

import Link from "next/link";
import { formatDateTime } from "@/lib/format";
import type { ProjectSummary, StageKey } from "@/lib/types";

// 阶段颜色：完成态用绿色，失败态用红色，其余用中性色
const STAGE_STYLE: Record<StageKey, string> = {
  draft: "bg-slate-800 text-slate-300",
  scripting: "bg-sky-900/40 text-sky-200",
  storyboarding: "bg-sky-900/40 text-sky-200",
  visualizing: "bg-indigo-900/40 text-indigo-200",
  composing: "bg-indigo-900/40 text-indigo-200",
  dubbing: "bg-violet-900/40 text-violet-200",
  review: "bg-amber-900/40 text-amber-200",
  exporting: "bg-teal-900/40 text-teal-200",
  done: "bg-emerald-900/40 text-emerald-200",
  failed: "bg-rose-900/40 text-rose-200",
};

const STAGE_TEXT: Record<StageKey, string> = {
  draft: "草稿",
  scripting: "剧本分析",
  storyboarding: "分镜规划",
  visualizing: "视觉生成",
  composing: "视频合成",
  dubbing: "配音与音效",
  review: "待确认",
  exporting: "导出中",
  done: "已完成",
  failed: "失败",
};

interface ProjectCardProps {
  project: ProjectSummary;
}

/**
 * 项目卡片。
 * 显示项目名称、创意描述摘要、当前阶段、成片时长和最近更新时间。
 */
export function ProjectCard({ project }: ProjectCardProps) {
  const progress = Math.max(0, Math.min(100, project.progress));

  return (
    <Link
      href={"/projects/" + project.id}
      className="flex flex-col gap-3 rounded border border-slate-800 p-4 transition hover:border-sky-700"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-base font-medium">{project.name}</h2>
        <span className={"rounded px-2 py-0.5 text-xs " + STAGE_STYLE[project.stage]}>
          {STAGE_TEXT[project.stage]}
        </span>
      </div>

      <p className="line-clamp-3 text-sm text-slate-400">{project.idea}</p>

      {/* 进度条用后端返回的百分比，前端不自行推算阶段进度 */}
      <div className="h-1.5 w-full rounded bg-slate-800">
        <div className="h-1.5 rounded bg-sky-500" style={{ width: progress + "%" }} />
      </div>

      <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <div className="flex gap-1">
          <dt>成片时长</dt>
          <dd>{project.durationSeconds} 秒</dd>
        </div>
        <div className="flex gap-1">
          <dt>已生成镜头</dt>
          <dd>{project.shotCount}</dd>
        </div>
        <div className="flex gap-1">
          <dt>更新时间</dt>
          <dd>{formatDateTime(project.updatedAt)}</dd>
        </div>
      </dl>

      {project.lastError ? (
        <p className="text-xs text-rose-300">上次失败原因：{project.lastError}</p>
      ) : null}
    </Link>
  );
}
