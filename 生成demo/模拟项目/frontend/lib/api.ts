import type {
  AssetCategory,
  BillingSummary,
  CandidateAsset,
  CreateProjectPayload,
  LoginPayload,
  ProjectDetail,
  ProjectSummary,
  RegisterPayload,
} from "./types";

// 接口根地址：开发环境默认走本地 FastAPI 服务
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";

export class ApiRequestError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(BASE_URL + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    // 会话 Cookie 由后端 HttpOnly 下发，前端不接触令牌
    credentials: "include",
  });

  if (!response.ok) {
    const text = await response.text();
    let code = "request_failed";
    let message = text || "请求失败，请稍后重试";
    try {
      const payload = JSON.parse(text) as { code?: string; message?: string };
      code = payload.code ?? code;
      message = payload.message ?? message;
    } catch {
      // 非 JSON 响应直接使用原始文本
    }
    throw new ApiRequestError(code, message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function fetchProjects(): Promise<ProjectSummary[]> {
  return request<ProjectSummary[]>("/projects");
}

export function fetchProject(projectId: string): Promise<ProjectDetail> {
  return request<ProjectDetail>("/projects/" + projectId);
}

export function createProject(payload: CreateProjectPayload): Promise<ProjectSummary> {
  return request<ProjectSummary>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProject(
  projectId: string,
  payload: Partial<CreateProjectPayload>,
): Promise<ProjectSummary> {
  return request<ProjectSummary>("/projects/" + projectId, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function archiveProject(projectId: string): Promise<void> {
  return request<void>("/projects/" + projectId, { method: "DELETE" });
}

export function fetchProjectAssets(projectId: string): Promise<AssetCategory[]> {
  return request<AssetCategory[]>("/projects/" + projectId + "/assets");
}

export function fetchGlobalAssets(keyword = ""): Promise<AssetCategory[]> {
  const query = keyword ? "?keyword=" + encodeURIComponent(keyword) : "";
  return request<AssetCategory[]>("/assets" + query);
}

export function fetchCandidates(projectId: string): Promise<CandidateAsset[]> {
  return request<CandidateAsset[]>("/projects/" + projectId + "/candidates");
}

export function pickCandidate(projectId: string, candidateId: string): Promise<void> {
  return request<void>("/projects/" + projectId + "/candidates/" + candidateId + "/pick", {
    method: "POST",
  });
}

export function revokeCandidate(projectId: string, candidateId: string): Promise<void> {
  return request<void>("/projects/" + projectId + "/candidates/" + candidateId + "/revoke", {
    method: "POST",
  });
}

export function deleteAsset(assetId: string): Promise<void> {
  return request<void>("/assets/" + assetId, { method: "DELETE" });
}

export function reuseAsset(assetId: string, targetProjectId: string): Promise<void> {
  return request<void>("/assets/" + assetId + "/reuse", {
    method: "POST",
    body: JSON.stringify({ targetProjectId }),
  });
}

export function exportProject(projectId: string): Promise<{ downloadUrl: string }> {
  return request<{ downloadUrl: string }>("/projects/" + projectId + "/export", {
    method: "POST",
  });
}

export function fetchBillingSummary(): Promise<BillingSummary> {
  return request<BillingSummary>("/billing/summary");
}

export function login(payload: LoginPayload): Promise<void> {
  return request<void>("/auth/login", { method: "POST", body: JSON.stringify(payload) });
}

export function register(payload: RegisterPayload): Promise<void> {
  return request<void>("/auth/register", { method: "POST", body: JSON.stringify(payload) });
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}
