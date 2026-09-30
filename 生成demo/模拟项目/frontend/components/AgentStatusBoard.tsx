"use client";

import type { AgentStatus } from "@/lib/types";

interface AgentStatusBoardProps {
  agents: AgentStatus[];
}

// 智能体状态对应的文案与颜色
const STATE_TEXT: Record<string, string> = {
  idle: "待命",
  thinking: "分析中",
  working: "生成中",
  waiting_user: "等待确认",
  blocked: "等待依赖",
  done: "已完成",
  failed: "失败",
};

const STATE_STYLE: Record<string, string> = {
  idle: "text-slate-400",
  thinking: "text-sky-300",
  working: "text-indigo-300",
  waiting_user: "text-amber-300",
  blocked: "text-slate-400",
  done: "text-emerald-300",
  failed: "text-rose-300",
};

/**
 * 智能体协作状态面板。
 * 展示六个制片角色的当前状态、正在处理的对象和最近一次输出摘要。
 */
export function AgentStatusBoard({ agents }: AgentStatusBoardProps) {
  if (!agents.length) {
    return (
      <section className="rounded border border-slate-800 p-4 text-sm text-slate-400">
        还没有开始生成，先在对话里描述你的创意。
      </section>
    );
  }

  return (
    <section className="rounded border border-slate-800">
      <header className="flex items-center justify-between border-b border-slate-800 px-4 py-2">
        <h2 className="text-sm font-medium">智能体协作状态</h2>
        <span className="text-xs text-slate-500">{agents.length} 个角色</span>
      </header>
      <ul className="divide-y divide-slate-900">
        {agents.map((agent) => (
          <li key={agent.key} className="px-4 py-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm">{agent.name}</span>
              <span className={"text-xs " + (STATE_STYLE[agent.state] ?? "text-slate-400")}>
                {STATE_TEXT[agent.state] ?? agent.state}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-400">{agent.duty}</p>
            {agent.currentTask ? (
              <p className="mt-1 text-xs text-slate-500">当前任务：{agent.currentTask}</p>
            ) : null}
            {agent.lastSummary ? (
              <p className="mt-1 text-xs text-slate-500">最近输出：{agent.lastSummary}</p>
            ) : null}
            {agent.state === "failed" && agent.lastError ? (
              <p className="mt-1 text-xs text-rose-300">失败原因：{agent.lastError}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
