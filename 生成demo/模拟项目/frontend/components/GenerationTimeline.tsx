"use client";

import type { GenerationEvent } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

interface GenerationTimelineProps {
  events: GenerationEvent[];
}

// 事件类型对应的标记颜色
const DOT_STYLE: Record<string, string> = {
  started: "bg-sky-500",
  progress: "bg-indigo-500",
  waiting: "bg-amber-500",
  succeeded: "bg-emerald-500",
  failed: "bg-rose-500",
  cancelled: "bg-slate-500",
};

/**
 * 生成时间线。
 * 按时间顺序展示一次生成任务的关键节点，便于排查失败原因。
 */
export function GenerationTimeline({ events }: GenerationTimelineProps) {
  if (!events.length) {
    return <p className="text-xs text-slate-500">还没有生成记录。</p>;
  }

  return (
    <ol className="space-y-3">
      {events.map((event) => (
        <li key={event.id} className="flex gap-3">
          <span
            className={
              "mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full " +
              (DOT_STYLE[event.type] ?? "bg-slate-500")
            }
          />
          <div className="min-w-0">
            <p className="text-xs text-slate-300">{event.message}</p>
            <p className="text-xs text-slate-500">
              {formatDateTime(event.createdAt)}
              {event.agentName ? " · " + event.agentName : ""}
              {event.durationMs ? " · " + Math.round(event.durationMs / 1000) + " 秒" : ""}
            </p>
            {event.detail ? (
              <p className="mt-1 whitespace-pre-wrap text-xs text-rose-300">{event.detail}</p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
