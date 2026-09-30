"use client";

import { useState } from "react";
import type { CandidateAsset } from "@/lib/types";

interface CandidatePickerProps {
  candidates: CandidateAsset[];
  onPick: (candidateId: string) => Promise<void> | void;
  onRevoke: (candidateId: string) => Promise<void> | void;
}

// 候选素材按类型区分展示方式
const KIND_LABEL: Record<string, string> = {
  image: "图片",
  video: "视频",
  audio: "音频",
};

/**
 * 候选素材选择面板。
 * 每次生成会返回多张候选，创作者挑一个采用，也可以撤回重新生成。
 */
export function CandidatePicker({ candidates, onPick, onRevoke }: CandidatePickerProps) {
  const [busyId, setBusyId] = useState("");
  const [message, setMessage] = useState("");

  if (!candidates.length) {
    return (
      <section className="rounded border border-slate-800 p-4 text-sm text-slate-400">
        没有待确认的候选素材。
      </section>
    );
  }

  async function handlePick(candidate: CandidateAsset) {
    setMessage("");
    setBusyId(candidate.id);
    try {
      await onPick(candidate.id);
      setMessage("已采用「" + candidate.name + "」，后续镜头会沿用这套设定。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "采用失败，请重试");
    } finally {
      setBusyId("");
    }
  }

  async function handleRevoke(candidate: CandidateAsset) {
    setMessage("");
    setBusyId(candidate.id);
    try {
      await onRevoke(candidate.id);
      setMessage("已撤回，该候选不会进入项目资产。");
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="rounded border border-slate-800">
      <header className="flex items-center justify-between border-b border-slate-800 px-4 py-2">
        <h2 className="text-sm font-medium">待确认候选素材</h2>
        <span className="text-xs text-slate-500">{candidates.length} 个候选</span>
      </header>

      <ul className="grid grid-cols-2 gap-3 p-4">
        {candidates.map((candidate) => (
          <li key={candidate.id} className="flex flex-col gap-2 rounded border border-slate-800 p-3">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>{KIND_LABEL[candidate.kind] ?? candidate.kind}</span>
              <span>评分 {candidate.score}</span>
            </div>
            <p className="text-sm">{candidate.name}</p>
            <p className="text-xs text-slate-500">{candidate.promptHint}</p>
            {/* 候选缩略图地址由后端签发，带过期时间 */}
            <img
              src={candidate.thumbnailUrl}
              alt={candidate.name}
              className="h-24 w-full rounded object-cover"
            />
            <div className="flex gap-2">
              <button
                type="button"
                disabled={busyId === candidate.id}
                onClick={() => void handlePick(candidate)}
                className="flex-1 rounded bg-sky-600 px-2 py-1 text-xs disabled:opacity-60"
              >
                采用
              </button>
              <button
                type="button"
                disabled={busyId === candidate.id}
                onClick={() => void handleRevoke(candidate)}
                className="flex-1 rounded border border-slate-700 px-2 py-1 text-xs disabled:opacity-60"
              >
                撤回
              </button>
            </div>
          </li>
        ))}
      </ul>

      {message ? <p className="px-4 pb-3 text-xs text-slate-300">{message}</p> : null}
    </section>
  );
}
