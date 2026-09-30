"use client";

import { useMemo, useState } from "react";
import { useAssets } from "@/hooks/useAssets";
import { formatBytes } from "@/lib/format";

// 全局素材库分类，与项目资产保持一致
const CATEGORIES = [
  {
    "key": "character",
    "label": "角色",
    "hint": "人物形象与角色设定图"
  },
  {
    "key": "scene",
    "label": "场景",
    "hint": "环境、地点与氛围图"
  },
  {
    "key": "prop",
    "label": "道具",
    "hint": "剧情相关物品与装备"
  },
  {
    "key": "storyboard",
    "label": "分镜",
    "hint": "镜头画面草图与构图"
  },
  {
    "key": "video",
    "label": "视频片段",
    "hint": "已合成的镜头视频"
  },
  {
    "key": "voice",
    "label": "配音",
    "hint": "旁白与台词音频"
  },
  {
    "key": "sfx",
    "label": "音效",
    "hint": "环境音与转场音效"
  },
  {
    "key": "export",
    "label": "成片导出",
    "hint": "最终合成输出文件"
  }
];

/**
 * 全局素材库页面。
 * 汇总当前账号在所有项目里生成过的素材，支持按分类查看、搜索和复用。
 */
export default function GlobalAssetsPage() {
  const { categories, deleteAsset, reuseAsset } = useAssets("");
  const [keyword, setKeyword] = useState("");
  const [active, setActive] = useState("all");

  const rows = useMemo(() => {
    const text = keyword.trim().toLowerCase();
    return categories
      .filter((group) => active === "all" || group.key === active)
      .flatMap((group) =>
        group.items
          .filter((item) => !text || item.name.toLowerCase().includes(text))
          .map((item) => ({ ...item, categoryLabel: group.label })),
      );
  }, [categories, keyword, active]);

  const totalBytes = rows.reduce((sum, item) => sum + item.sizeBytes, 0);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-6 py-10">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">全局素材库</h1>
          <p className="mt-1 text-sm text-slate-400">
            {rows.length} 个素材，占用 {formatBytes(totalBytes)}
          </p>
        </div>
        <input
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="搜索素材名称"
          className="w-64 rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
        />
      </header>

      <nav className="flex flex-wrap gap-2 text-xs">
        <button
          type="button"
          onClick={() => setActive("all")}
          className={
            active === "all"
              ? "rounded-full bg-sky-600/20 px-3 py-1 text-sky-300"
              : "rounded-full bg-slate-800 px-3 py-1 text-slate-300"
          }
        >
          全部
        </button>
        {CATEGORIES.map((category) => (
          <button
            key={category.key}
            type="button"
            title={category.hint}
            onClick={() => setActive(category.key)}
            className={
              active === category.key
                ? "rounded-full bg-sky-600/20 px-3 py-1 text-sky-300"
                : "rounded-full bg-slate-800 px-3 py-1 text-slate-300"
            }
          >
            {category.label}
          </button>
        ))}
      </nav>

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
            <th className="py-2">素材名称</th>
            <th className="py-2">分类</th>
            <th className="py-2">来源项目</th>
            <th className="py-2">大小</th>
            <th className="py-2">操作</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b border-slate-900">
              <td className="py-2">{row.name}</td>
              <td className="py-2 text-slate-400">{row.categoryLabel}</td>
              <td className="py-2 text-slate-400">{row.projectName}</td>
              <td className="py-2 text-slate-400">{formatBytes(row.sizeBytes)}</td>
              <td className="flex gap-2 py-2">
                <button
                  type="button"
                  onClick={() => void reuseAsset(row.id)}
                  className="rounded border border-slate-700 px-2 py-1 text-xs"
                >
                  复用
                </button>
                <button
                  type="button"
                  onClick={() => void deleteAsset(row.id)}
                  className="rounded border border-rose-900 px-2 py-1 text-xs text-rose-300"
                >
                  删除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {!rows.length ? (
        <p className="rounded border border-slate-800 px-4 py-10 text-center text-sm text-slate-400">
          素材库还是空的，先去项目工作区生成一些素材。
        </p>
      ) : null}
    </main>
  );
}
