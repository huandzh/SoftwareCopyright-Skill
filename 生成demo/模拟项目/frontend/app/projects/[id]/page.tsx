"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { ChatPanel } from "@/components/ChatPanel";
import { AgentStatusBoard } from "@/components/AgentStatusBoard";
import { AssetPanel } from "@/components/AssetPanel";
import { CandidatePicker } from "@/components/CandidatePicker";
import { CostSummary } from "@/components/CostSummary";
import { useChatStream } from "@/hooks/useChatStream";
import { useAssets } from "@/hooks/useAssets";
import { fetchProject } from "@/lib/api";
import type { ProjectDetail, StageKey } from "@/lib/types";

// 顶部步骤条顺序与后端项目阶段一一对应
const STAGE_ORDER: StageKey[] = [
  "draft",
  "scripting",
  "storyboarding",
  "visualizing",
  "composing",
  "dubbing",
  "review",
  "exporting",
  "done",
];

const STAGE_LABEL: Record<StageKey, string> = {
  "draft": "草稿",
  "scripting": "剧本分析",
  "storyboarding": "分镜规划",
  "visualizing": "视觉生成",
  "composing": "视频合成",
  "dubbing": "配音与音效",
  "review": "人工确认",
  "exporting": "导出成片",
  "done": "已完成",
  "failed": "失败"
};

/**
 * 项目工作区。
 * 左侧是与智能体的对话，中间是候选素材与资产，右侧是智能体状态与成本。
 */
export default function ProjectWorkspacePage() {
  const params = useParams<{ id: string }>();
  const projectId = String(params?.id ?? "");
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loadError, setLoadError] = useState("");
  const [activeCategory, setActiveCategory] = useState("character");

  // 对话流通过 SSE 增量写入，避免整页刷新
  const chat = useChatStream(projectId);
  const assets = useAssets(projectId);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        // 进入工作区先拉一次项目详情，拿到阶段、成本与智能体状态
        const detail = await fetchProject(projectId);
        if (!cancelled) {
          setProject(detail);
        }
      } catch (error) {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : "项目加载失败");
        }
      }
    }
    if (projectId) {
      void load();
    }
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const stageIndex = useMemo(() => {
    if (!project) {
      return 0;
    }
    const index = STAGE_ORDER.indexOf(project.stage);
    return index < 0 ? 0 : index;
  }, [project]);

  return (
    <main className="flex w-full flex-col gap-4 px-6 py-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{project?.name ?? "视频项目"}</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            {project?.idea ?? "正在读取创意描述…"}
          </p>
        </div>
        <span className="rounded bg-slate-800 px-3 py-1 text-xs text-slate-300">
          当前阶段：{project ? STAGE_LABEL[project.stage] : "读取中"}
        </span>
      </header>

      {/* 步骤条：已完成阶段高亮，失败阶段标红 */}
      <ol className="flex flex-wrap gap-2 text-xs">
        {STAGE_ORDER.map((stage, index) => (
          <li
            key={stage}
            className={
              index < stageIndex
                ? "rounded-full bg-emerald-900/40 px-3 py-1 text-emerald-200"
                : index === stageIndex
                  ? "rounded-full bg-sky-600/30 px-3 py-1 text-sky-100"
                  : "rounded-full bg-slate-800 px-3 py-1 text-slate-400"
            }
          >
            {index + 1}. {STAGE_LABEL[stage]}
          </li>
        ))}
      </ol>

      {loadError ? (
        <p className="rounded border border-rose-800 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">
          {loadError}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <ChatPanel
          messages={chat.messages}
          streaming={chat.streaming}
          onSend={chat.send}
          onStop={chat.stop}
        />
        <div className="flex flex-col gap-4">
          <AgentStatusBoard agents={project?.agents ?? []} />
          <CandidatePicker
            candidates={assets.candidates}
            onPick={assets.pickCandidate}
            onRevoke={assets.revokeCandidate}
          />
          <AssetPanel
            categories={assets.categories}
            activeCategory={activeCategory}
            onCategoryChange={setActiveCategory}
            onDelete={assets.deleteAsset}
          />
          <CostSummary cost={project?.cost} />
        </div>
      </div>
    </main>
  );
}
