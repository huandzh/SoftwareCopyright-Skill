import type { ChatMessage } from "./types";

// SSE 事件类型：后端按事件名推送不同载荷
export interface ChatStreamHandlers {
  onMessage: (message: ChatMessage) => void;
  onDelta: (messageId: string, text: string) => void;
  onAgentState?: (agentKey: string, state: string, summary?: string) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

/**
 * 打开项目对话的 SSE 流。
 * 返回关闭函数，组件卸载或用户点击停止时调用。
 */
export function openChatStream(projectId: string, handlers: ChatStreamHandlers): () => void {
  const base = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";
  // 对话流使用 EventSource，浏览器会自动重连；这里保持默认重连策略
  const source = new EventSource(base + "/projects/" + projectId + "/chat/stream", {
    withCredentials: true,
  });

  source.addEventListener("message", (event) => {
    try {
      handlers.onMessage(JSON.parse((event as MessageEvent).data) as ChatMessage);
    } catch {
      handlers.onError?.("对话消息解析失败");
    }
  });

  source.addEventListener("delta", (event) => {
    try {
      const payload = JSON.parse((event as MessageEvent).data) as {
        id: string;
        text: string;
      };
      handlers.onDelta(payload.id, payload.text);
    } catch {
      handlers.onError?.("增量内容解析失败");
    }
  });

  source.addEventListener("agent", (event) => {
    try {
      const payload = JSON.parse((event as MessageEvent).data) as {
        agentKey: string;
        state: string;
        summary?: string;
      };
      handlers.onAgentState?.(payload.agentKey, payload.state, payload.summary);
    } catch {
      // 状态推送失败不影响主流程
    }
  });

  source.addEventListener("error", () => {
    // EventSource 在服务端关闭后会触发 error，这里交给浏览器自动重连
    handlers.onError?.("连接中断，正在重连…");
  });

  source.addEventListener("done", () => {
    handlers.onDone?.();
  });

  return () => {
    source.close();
  };
}

/**
 * 发送一条创作者指令。
 * 使用普通 POST，真正的回复通过上面的 SSE 流返回。
 */
export async function sendChatMessage(projectId: string, content: string): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";
  const response = await fetch(base + "/projects/" + projectId + "/chat/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ content }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "指令发送失败");
  }
}

export async function cancelGeneration(projectId: string, taskId: string): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";
  await fetch(base + "/projects/" + projectId + "/tasks/" + taskId + "/cancel", {
    method: "POST",
    credentials: "include",
  });
}
