"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { ExportDialog } from "@/components/dialogs/ExportDialog";
import { exportProject } from "@/lib/api";
import { FRAME_RATES, RESOLUTIONS } from "@/lib/constants";

/**
 * 成片导出页面。
 * 展示导出前的检查清单，并允许调整分辨率、帧率与字幕输出。
 */
export default function ExportPage() {
  const params = useParams<{ id: string }>();
  const projectId = String(params?.id ?? "");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [message, setMessage] = useState("");
  const [resolution, setResolution] = useState(RESOLUTIONS[1].key);
  const [frameRate, setFrameRate] = useState<number>(FRAME_RATES[2]);

  async function handleExport(form: Record<string, string | number | boolean>) {
    setMessage("");
    try {
      const result = await exportProject(projectId);
      setDownloadUrl(result.downloadUrl);
      setMessage(
        "已提交导出任务：" +
          String(form.resolution) +
          " / " +
          String(form.frameRate) +
          "fps" +
          (form.subtitle ? " / 含字幕" : ""),
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "导出失败，请稍后重试");
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-6 py-8">
      <header>
        <h1 className="text-xl font-semibold">导出成片</h1>
        <p className="mt-1 text-sm text-slate-400">
          导出前请确认镜头顺序、配音与字幕；导出过程中不能删除素材。
        </p>
      </header>

      <section className="rounded border border-slate-800 p-4 text-sm">
        <label className="flex items-center justify-between gap-3 py-1">
          分辨率
          <select
            value={resolution}
            onChange={(event) => setResolution(event.target.value)}
            className="rounded border border-slate-700 bg-slate-900 px-3 py-1"
          >
            {RESOLUTIONS.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}（{item.width}×{item.height}）
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center justify-between gap-3 py-1">
          帧率
          <select
            value={frameRate}
            onChange={(event) => setFrameRate(Number(event.target.value))}
            className="rounded border border-slate-700 bg-slate-900 px-3 py-1"
          >
            {FRAME_RATES.map((rate) => (
              <option key={rate} value={rate}>
                {rate} fps
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="rounded bg-sky-600 px-4 py-2 text-sm"
        >
          导出成片
        </button>
        {downloadUrl ? (
          <a href={downloadUrl} className="text-sm text-sky-400 underline">
            下载成片
          </a>
        ) : null}
      </div>

      {message ? <p className="text-sm text-slate-300">{message}</p> : null}

      <ExportDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onConfirm={handleExport}
      />
    </main>
  );
}
