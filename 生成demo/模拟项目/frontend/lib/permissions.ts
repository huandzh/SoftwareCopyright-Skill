// 前端权限判断：只用于界面显隐，真正的权限以后端校验为准
import type { ProjectDetail } from "./types";

export interface Capability {
  key: string;
  label: string;
  allowed: boolean;
  reason: string;
}

const FINISHED_STAGES = new Set(["done"]);

export function capabilities(project: ProjectDetail | null, budgetExceeded: boolean): Capability[] {
  const stage = project?.stage ?? "draft";
  return [
    {
      key: "chat",
      label: "发送制片指令",
      allowed: !FINISHED_STAGES.has(stage) && !budgetExceeded,
      reason: budgetExceeded ? "本月预算已用完" : "项目已完成，可复制项目后继续修改",
    },
    {
      key: "pick-candidate",
      label: "采用候选素材",
      allowed: stage === "review" || stage === "visualizing",
      reason: "只有生成候选图或等待确认时可以操作",
    },
    {
      key: "export",
      label: "导出成片",
      allowed: stage === "review" || stage === "done",
      reason: "需要先完成镜头合成与配音",
    },
    {
      key: "delete-asset",
      label: "删除素材",
      allowed: stage !== "exporting",
      reason: "导出过程中不允许删除素材",
    },
  ];
}

export function canEditProject(project: ProjectDetail | null): boolean {
  if (!project) {
    return false;
  }
  // 导出中的项目不允许改创意描述，避免成片与描述不一致
  return project.stage !== "exporting";
}
