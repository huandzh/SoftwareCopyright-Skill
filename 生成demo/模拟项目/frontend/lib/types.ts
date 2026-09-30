// 平台公共类型定义：前端组件与接口封装共用同一套结构

// 项目所处阶段，与后端 ProjectStage 枚举一一对应
export type StageKey =
  | "draft"
  | "scripting"
  | "storyboarding"
  | "visualizing"
  | "composing"
  | "dubbing"
  | "review"
  | "exporting"
  | "done"
  | "failed";

export interface ProjectSummary {
  id: string;
  name: string;
  idea: string;
  stage: StageKey;
  progress: number;
  durationSeconds: number;
  shotCount: number;
  updatedAt: string;
  lastError?: string;
}

export interface AgentStatus {
  key: string;
  name: string;
  duty: string;
  state: "idle" | "thinking" | "working" | "waiting_user" | "blocked" | "done" | "failed";
  currentTask?: string;
  lastSummary?: string;
  lastError?: string;
}

export interface ProjectCost {
  total: number;
  estimatedRemaining: number;
  items: Record<string, number>;
}

export interface ProjectDetail extends ProjectSummary {
  agents: AgentStatus[];
  cost?: ProjectCost;
  createdAt: string;
  modelProfile: string;
}

export interface ChatAttachment {
  id: string;
  name: string;
  kind: "image" | "video" | "audio";
  url: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
  agentKey?: string;
  agentName?: string;
  attachments?: ChatAttachment[];
  pending?: boolean;
}

export interface AssetItem {
  id: string;
  name: string;
  source: string;
  sizeBytes: number;
  downloadUrl: string;
  createdAt: string;
}

export interface AssetCategory {
  key: string;
  label: string;
  hint: string;
  items: AssetItem[];
}

export interface CandidateAsset {
  id: string;
  name: string;
  kind: "image" | "video" | "audio";
  score: number;
  promptHint: string;
  thumbnailUrl: string;
  createdAt: string;
}

export interface GenerationEvent {
  id: string;
  type: "started" | "progress" | "waiting" | "succeeded" | "failed" | "cancelled";
  message: string;
  detail?: string;
  agentName?: string;
  durationMs?: number;
  createdAt: string;
}

export interface BillingItem {
  key: string;
  quantity: number;
  unit: string;
  amount: number;
}

export interface BillingSummary {
  period: string;
  total: number;
  budget: number;
  items: BillingItem[];
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  displayName: string;
}

export interface CreateProjectPayload {
  name: string;
  idea: string;
  modelProfile?: string;
}

export interface ApiError {
  code: string;
  message: string;
  detail?: string;
}
