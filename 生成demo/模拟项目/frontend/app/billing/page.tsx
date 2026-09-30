"use client";

import { useEffect, useState } from "react";
import { fetchBillingSummary } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import type { BillingSummary } from "@/lib/types";

// 计费项展示名与单位
const ITEM_LABEL: Record<string, string> = {
  "llm_tokens": "语言模型调用",
  "image_generation": "图片生成",
  "video_generation": "视频生成",
  "voice_synthesis": "语音合成",
  "sfx_search": "音效检索",
  "storage": "素材存储"
};

/**
 * 计费与成本页面。
 * 展示本月各项生成成本、预算使用比例和超额提醒。
 */
export default function BillingPage() {
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setSummary(await fetchBillingSummary());
      } catch (err) {
        setError(err instanceof Error ? err.message : "计费信息加载失败");
      }
    }
    void load();
  }, []);

  const usedPercent = summary && summary.budget > 0
    ? Math.min(100, Math.round((summary.total / summary.budget) * 100))
    : 0;

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-5 px-6 py-10">
      <h1 className="text-2xl font-semibold">计费与成本</h1>

      {error ? (
        <p className="rounded border border-rose-800 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">
          {error}
        </p>
      ) : null}

      <section className="rounded border border-slate-800 p-5">
        <p className="text-sm text-slate-400">
          本月已用 {formatCurrency(summary?.total ?? 0)} / 预算{" "}
          {formatCurrency(summary?.budget ?? 0)}
        </p>
        <div className="mt-3 h-2 w-full rounded bg-slate-800">
          <div
            className={usedPercent > 80 ? "h-2 rounded bg-rose-500" : "h-2 rounded bg-sky-500"}
            style={{ width: usedPercent + "%" }}
          />
        </div>
        <p className="mt-2 text-xs text-slate-500">预算使用 {usedPercent}%</p>
      </section>

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
            <th className="py-2">计费项</th>
            <th className="py-2">用量</th>
            <th className="py-2">金额</th>
          </tr>
        </thead>
        <tbody>
          {(summary?.items ?? []).map((item) => (
            <tr key={item.key} className="border-b border-slate-900">
              <td className="py-2">{ITEM_LABEL[item.key] ?? item.key}</td>
              <td className="py-2 text-slate-400">
                {item.quantity} {item.unit}
              </td>
              <td className="py-2 text-slate-300">{formatCurrency(item.amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {summary && summary.total > summary.budget ? (
        <p className="rounded border border-amber-800 bg-amber-950/30 px-4 py-3 text-sm text-amber-200">
          本月成本已超出预算，新的生成任务会先暂停，请调整预算或等待下个计费周期。
        </p>
      ) : null}
    </main>
  );
}
