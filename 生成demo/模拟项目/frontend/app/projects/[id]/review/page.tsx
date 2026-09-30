"use client";

import { useParams } from "next/navigation";
import { CandidatePicker } from "@/components/CandidatePicker";
import { GenerationTimeline } from "@/components/GenerationTimeline";
import { useAssets } from "@/hooks/useAssets";
import { useTaskProgress } from "@/hooks/useTaskProgress";

/**
 * 素材确认页面。
 * 把待确认候选与生成时间线放在同一屏，方便创作者一边看过程一边做决定。
 */
export default function ReviewPage() {
  const params = useParams<{ id: string }>();
  const projectId = String(params?.id ?? "");
  const assets = useAssets(projectId);
  const progress = useTaskProgress(projectId, true);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-6 py-8">
      <header>
        <h1 className="text-xl font-semibold">素材确认</h1>
        <p className="mt-1 text-sm text-slate-400">
          逐条确认候选素材；未确认的候选不会进入项目资产。
        </p>
      </header>

      <CandidatePicker
        candidates={assets.candidates}
        onPick={assets.pickCandidate}
        onRevoke={assets.revokeCandidate}
      />

      <section className="rounded border border-slate-800 p-4">
        <h2 className="mb-3 text-sm font-medium">生成时间线</h2>
        <GenerationTimeline events={progress.events} />
        {progress.error ? <p className="mt-2 text-xs text-rose-300">{progress.error}</p> : null}
      </section>
    </main>
  );
}
