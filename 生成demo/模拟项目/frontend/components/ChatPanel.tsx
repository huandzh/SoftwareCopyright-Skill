"use client";

import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";

interface ChatPanelProps {
  messages: ChatMessage[];
  streaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}

// 输入框的快捷提示，帮助创作者知道可以怎么说
const QUICK_PROMPTS = [
  "把开场改成都市夜景，镜头慢推",
  "第二个镜头节奏太快，延长两秒",
  "给主角换一套深色风衣",
  "旁白语气再平缓一些",
  "这段配乐换成弦乐",
];

/**
 * 对话工作区。
 * 创作者用自然语言描述修改意见，智能体按当前阶段决定由哪个角色接话。
 */
export function ChatPanel({ messages, streaming, onSend, onStop }: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLDivElement | null>(null);

  // 新消息到达后自动滚到底部，用户手动上滑时不强制跟随
  useEffect(() => {
    const node = listRef.current;
    if (!node) {
      return;
    }
    const nearBottom = node.scrollHeight - node.scrollTop - node.clientHeight < 120;
    if (nearBottom) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || streaming) {
      return;
    }
    onSend(text);
    setDraft("");
  }

  return (
    <section className="flex h-[70vh] flex-col rounded border border-slate-800">
      <header className="flex items-center justify-between border-b border-slate-800 px-4 py-2">
        <h2 className="text-sm font-medium">制片对话</h2>
        <span className="text-xs text-slate-500">
          {streaming ? "智能体正在回复…" : "等待你的下一条指令"}
        </span>
      </header>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 ? (
          <p className="rounded border border-dashed border-slate-800 px-4 py-6 text-sm text-slate-400">
            先描述你想要的内容，例如“做一个 30 秒的城市夜景短片，节奏偏慢，旁白用女声”。
          </p>
        ) : null}

        {messages.map((message) => (
          <article
            key={message.id}
            className={
              message.role === "user"
                ? "ml-auto max-w-[85%] rounded bg-sky-950/50 px-3 py-2 text-sm"
                : "mr-auto max-w-[90%] rounded bg-slate-900 px-3 py-2 text-sm"
            }
          >
            {message.agentKey ? (
              <p className="mb-1 text-xs text-slate-400">{message.agentName}</p>
            ) : null}
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
            {message.attachments?.length ? (
              <ul className="mt-2 flex flex-wrap gap-2">
                {message.attachments.map((item) => (
                  <li
                    key={item.id}
                    className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300"
                  >
                    {item.kind === "image" ? "图片" : item.kind === "video" ? "视频" : "音频"}：
                    {item.name}
                  </li>
                ))}
              </ul>
            ) : null}
            {message.pending ? (
              <p className="mt-1 text-xs text-slate-500">生成中，可随时中断</p>
            ) : null}
          </article>
        ))}
      </div>

      <div className="border-t border-slate-800 px-4 py-2">
        <div className="flex flex-wrap gap-2">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => setDraft(prompt)}
              className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300 hover:bg-slate-700"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-slate-800 p-3">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={3}
          placeholder="描述你想要的画面、节奏或修改意见（Enter 发送，Shift+Enter 换行）"
          onKeyDown={(event) => {
            // Enter 直接发送，需要换行时按住 Shift
            if (event.key === "Enter" && !event.shiftKey) {
              handleSubmit(event);
            }
          }}
          className="flex-1 resize-none rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
        />
        <div className="flex flex-col gap-2">
          <button
            type="submit"
            disabled={streaming}
            className="rounded bg-sky-600 px-4 py-2 text-sm disabled:opacity-60"
          >
            发送
          </button>
          <button
            type="button"
            disabled={!streaming}
            onClick={onStop}
            className="rounded border border-slate-700 px-4 py-2 text-sm disabled:opacity-40"
          >
            停止
          </button>
        </div>
      </form>
    </section>
  );
}
