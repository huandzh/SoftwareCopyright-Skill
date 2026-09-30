"use client";

import { useState } from "react";

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (payload: Record<string, string | number | boolean>) => Promise<void> | void;
}

// 表单默认值：与后端默认配置保持一致
const DEFAULTS: Record<string, string | number | boolean> = {
  profile: "balanced",
  resolution: "1080p",
  frameRate: 30,
  subtitle: true,
};

/**
 * 导出成片对话框。
 * 选择分辨率、帧率与字幕方式，确认后进入导出队列。
 */
export function ExportDialog({ open, onClose, onConfirm }: ExportDialogProps) {
  const [form, setForm] = useState(DEFAULTS);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  if (!open) {
    return null;
  }

  function update(key: string, value: string | number | boolean) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }

  async function handleConfirm() {
    setBusy(true);
    setMessage("");
    try {
      await onConfirm(form);
      onClose();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "操作失败，请重试");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <section className="w-full max-w-md rounded border border-slate-700 bg-slate-950 p-5">
        <header className="flex items-center justify-between">
          <h2 className="text-base font-medium">导出成片</h2>
          <button type="button" onClick={onClose} className="text-sm text-slate-400">
            关闭
          </button>
        </header>

        <div className="mt-4 flex flex-col gap-3 text-sm">
          <label className="flex items-center justify-between gap-3">
            模型档位
            <select
              value={String(form.profile)}
              onChange={(event) => update("profile", event.target.value)}
              className="rounded border border-slate-700 bg-slate-900 px-3 py-1"
            >
              <option value="fast">快速</option>
              <option value="balanced">均衡</option>
              <option value="quality">高质量</option>
            </select>
          </label>

          <label className="flex items-center justify-between gap-3">
            输出分辨率
            <select
              value={String(form.resolution)}
              onChange={(event) => update("resolution", event.target.value)}
              className="rounded border border-slate-700 bg-slate-900 px-3 py-1"
            >
              <option value="720p">720p</option>
              <option value="1080p">1080p</option>
              <option value="4k">4K</option>
            </select>
          </label>

          <label className="flex items-center justify-between gap-3">
            帧率
            <input
              type="number"
              min={24}
              max={60}
              value={Number(form.frameRate)}
              onChange={(event) => update("frameRate", Number(event.target.value))}
              className="w-24 rounded border border-slate-700 bg-slate-900 px-3 py-1"
            />
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={Boolean(form.subtitle)}
              onChange={(event) => update("subtitle", event.target.checked)}
            />
            同时输出字幕文件
          </label>

          {message ? <p className="text-xs text-amber-300">{message}</p> : null}
        </div>

        <footer className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-slate-700 px-3 py-2 text-sm"
          >
            取消
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleConfirm()}
            className="rounded bg-sky-600 px-4 py-2 text-sm disabled:opacity-60"
          >
            {busy ? "处理中…" : "确定"}
          </button>
        </footer>
      </section>
    </div>
  );
}
