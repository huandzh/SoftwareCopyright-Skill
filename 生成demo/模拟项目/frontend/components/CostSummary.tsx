"use client";

import type { ProjectCost } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

interface CostSummaryProps {
  cost?: ProjectCost;
}

// 计费项中文名
const ITEM_LABEL: Record<string, string> = {
  "llm_tokens": "语言模型调用",
  "image_generation": "图片生成",
  "video_generation": "视频生成",
  "voice_synthesis": "语音合成",
  "sfx_search": "音效检索",
  "storage": "素材存储"
};

/**
 * 项目成本面板。
 * 展示当前项目的累计成本、各项占比和预计剩余成本。
 */
export function CostSummary({ cost }: CostSummaryProps) {
  if (!cost) {
    return (
      <section className="rounded border border-slate-800 p-4 text-sm text-slate-400">
        暂无成本数据。
      </section>
    );
  }

  const items = Object.entries(cost.items).sort((a, b) => b[1] - a[1]);

  return (
    <section className="rounded border border-slate-800">
      <header className="flex items-center justify-between border-b border-slate-800 px-4 py-2">
        <h2 className="text-sm font-medium">成本</h2>
        <span className="text-sm text-slate-200">{formatCurrency(cost.total)}</span>
      </header>
      <ul className="divide-y divide-slate-900">
        {items.map(([key, amount]) => (
          <li key={key} className="flex items-center justify-between px-4 py-2 text-xs">
            <span className="text-slate-400">{ITEM_LABEL[key] ?? key}</span>
            <span className="text-slate-200">{formatCurrency(amount)}</span>
          </li>
        ))}
      </ul>
      <p className="px-4 py-3 text-xs text-slate-500">
        预计剩余生成成本约 {formatCurrency(cost.estimatedRemaining)}。
      </p>
    </section>
  );
}
