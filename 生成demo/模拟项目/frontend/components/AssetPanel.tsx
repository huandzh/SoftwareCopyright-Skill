"use client";

import type { AssetCategory } from "@/lib/types";
import { formatBytes } from "@/lib/format";

interface AssetPanelProps {
  categories: AssetCategory[];
  activeCategory: string;
  onCategoryChange: (key: string) => void;
  onDelete: (assetId: string) => Promise<void> | void;
}

// 分类展示顺序与后端返回的分类保持一致
const DISPLAY_ORDER = ["character", "scene", "prop", "storyboard", "video", "voice", "sfx", "export"];

/**
 * 项目资产面板。
 * 按分类展示项目内的素材，支持查看大小、下载和删除。
 */
export function AssetPanel({
  categories,
  activeCategory,
  onCategoryChange,
  onDelete,
}: AssetPanelProps) {
  const ordered = [...categories].sort(
    (a, b) => DISPLAY_ORDER.indexOf(a.key) - DISPLAY_ORDER.indexOf(b.key),
  );
  const current = ordered.find((item) => item.key === activeCategory) ?? ordered[0];

  return (
    <section className="rounded border border-slate-800">
      <header className="border-b border-slate-800 px-4 py-2">
        <h2 className="text-sm font-medium">项目资产</h2>
      </header>

      <nav className="flex flex-wrap gap-2 px-4 py-3 text-xs">
        {ordered.map((category) => (
          <button
            key={category.key}
            type="button"
            onClick={() => onCategoryChange(category.key)}
            className={
              category.key === current?.key
                ? "rounded-full bg-sky-600/20 px-3 py-1 text-sky-300"
                : "rounded-full bg-slate-800 px-3 py-1 text-slate-300"
            }
          >
            {category.label}（{category.items.length}）
          </button>
        ))}
      </nav>

      <ul className="divide-y divide-slate-900">
        {(current?.items ?? []).map((item) => (
          <li key={item.id} className="flex items-center justify-between gap-3 px-4 py-2">
            <div className="min-w-0">
              <p className="truncate text-sm">{item.name}</p>
              <p className="text-xs text-slate-500">
                {formatBytes(item.sizeBytes)} · {item.source}
              </p>
            </div>
            <div className="flex gap-2">
              <a
                href={item.downloadUrl}
                className="rounded border border-slate-700 px-2 py-1 text-xs"
              >
                下载
              </a>
              <button
                type="button"
                onClick={() => void onDelete(item.id)}
                className="rounded border border-rose-900 px-2 py-1 text-xs text-rose-300"
              >
                删除
              </button>
            </div>
          </li>
        ))}
      </ul>

      {!current?.items.length ? (
        <p className="px-4 py-6 text-center text-xs text-slate-500">
          该分类还没有素材。
        </p>
      ) : null}
    </section>
  );
}
