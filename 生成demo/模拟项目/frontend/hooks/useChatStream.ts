"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelGeneration,
  openChatStream,
  sendChatMessage,
} from "@/lib/sse";
import type { ChatMessage } from "@/lib/types";

/**
 * 对话流钩子。
 * 维护消息列表、流式增量文本和中断状态，供工作区对话面板使用。
 */
export function useChatStream(projectId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [taskId, setTaskId] = useState("");
  const closeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!projectId) {
      return;
    }
    const close = openChatStream(projectId, {
      onMessage: (message) => {
        setMessages((previous) => {
          // 同一消息可能先推送占位再推送完整内容，这里做去重与覆盖
          const index = previous.findIndex((item) => item.id === message.id);
          if (index < 0) {
            return [...previous, message];
          }
          const next = [...previous];
          next[index] = message;
          return next;
        });
      },
      onDelta: (messageId, text) => {
        setMessages((previous) =>
          previous.map((item) =>
            item.id === messageId ? { ...item, content: item.content + text } : item,
          ),
        );
      },
      onDone: () => {
        setStreaming(false);
      },
      onError: (message) => {
        setMessages((previous) => [
          ...previous,
          {
            id: "local-error-" + Date.now(),
            role: "system",
            content: message,
            createdAt: new Date().toISOString(),
          },
        ]);
      },
    });
    closeRef.current = close;
    return () => {
      close();
      closeRef.current = null;
    };
  }, [projectId]);

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content) {
        return;
      }
      setMessages((previous) => [
        ...previous,
        {
          id: "local-user-" + Date.now(),
          role: "user",
          content,
          createdAt: new Date().toISOString(),
        },
      ]);
      setStreaming(true);
      try {
        await sendChatMessage(projectId, content);
      } catch (error) {
        setStreaming(false);
        setMessages((previous) => [
          ...previous,
          {
            id: "local-fail-" + Date.now(),
            role: "system",
            content: error instanceof Error ? error.message : "发送失败",
            createdAt: new Date().toISOString(),
          },
        ]);
      }
    },
    [projectId],
  );

  const stop = useCallback(async () => {
    if (taskId) {
      await cancelGeneration(projectId, taskId);
    }
    setStreaming(false);
  }, [projectId, taskId]);

  return { messages, streaming, send, stop, setTaskId };
}
