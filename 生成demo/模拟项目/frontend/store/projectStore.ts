import { create } from "zustand";
import type { AgentStatus, ProjectDetail, StageKey } from "@/lib/types";

interface ProjectState {
  projectId: string;
  detail: ProjectDetail | null;
  activeCategory: string;
  sidebarOpen: boolean;
  setProject: (detail: ProjectDetail | null) => void;
  setActiveCategory: (key: string) => void;
  toggleSidebar: () => void;
  applyAgentState: (agentKey: string, state: AgentStatus["state"], summary?: string) => void;
  applyStage: (stage: StageKey) => void;
}

/**
 * 工作区状态。
 * 只保存跨组件共享的工作区状态，列表数据仍由 hooks 管理。
 */
export const useProjectStore = create<ProjectState>((set) => ({
  projectId: "",
  detail: null,
  activeCategory: "character",
  sidebarOpen: true,

  setProject: (detail) =>
    set(() => ({
      detail,
      projectId: detail?.id ?? "",
    })),

  setActiveCategory: (key) => set(() => ({ activeCategory: key })),

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  applyAgentState: (agentKey, state, summary) =>
    set((previous) => {
      if (!previous.detail) {
        return previous;
      }
      const agents = previous.detail.agents.map((agent) =>
        agent.key === agentKey
          ? { ...agent, state, lastSummary: summary ?? agent.lastSummary }
          : agent,
      );
      return { ...previous, detail: { ...previous.detail, agents } };
    }),

  applyStage: (stage) =>
    set((previous) => {
      if (!previous.detail) {
        return previous;
      }
      // 阶段推进时同步更新进度条，后端会在下一条状态消息里给出准确值
      const order: StageKey[] = [
        "draft",
        "scripting",
        "storyboarding",
        "visualizing",
        "composing",
        "dubbing",
        "review",
        "exporting",
        "done",
      ];
      const index = order.indexOf(stage);
      const progress = index <= 0 ? 0 : Math.round((index / (order.length - 1)) * 100);
      return { ...previous, detail: { ...previous.detail, stage, progress } };
    }),
}));
