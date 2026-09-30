// 平台常量：模型档位、分辨率、时长上限与文案

export const MODEL_PROFILES = [
  { key: "fast", label: "快速", hint: "先出草稿，单镜头约 0.18 元" },
  { key: "balanced", label: "均衡", hint: "默认档位，单镜头约 0.42 元" },
  { key: "quality", label: "高质量", hint: "电影质感，单镜头约 0.86 元" },
] as const;

export const RESOLUTIONS = [
  { key: "720p", label: "720p", width: 1280, height: 720 },
  { key: "1080p", label: "1080p", width: 1920, height: 1080 },
  { key: "4k", label: "4K", width: 3840, height: 2160 },
] as const;

export const FRAME_RATES = [24, 25, 30, 60] as const;

export const LIMITS = {
  projectNameMax: 120,
  ideaMin: 4,
  ideaMax: 4000,
  messageMax: 2000,
  shotsPerProject: 200,
  durationSeconds: 600,
} as const;

export const ASSET_CATEGORY_KEYS = [
  "character",
  "scene",
  "prop",
  "storyboard",
  "video",
  "voice",
  "sfx",
  "export",
] as const;

export const STAGE_KEYS = [
  "draft",
  "scripting",
  "storyboarding",
  "visualizing",
  "composing",
  "dubbing",
  "review",
  "exporting",
  "done",
  "failed",
] as const;

export const MESSAGES = {
  emptyProjects: "还没有项目，先新建一个视频项目。",
  emptyAssets: "该分类还没有素材。",
  budgetExceeded: "本月预算已用完，新的生成任务会暂停。",
  generationFailed: "生成失败，可查看时间线了解原因后重试。",
} as const;
