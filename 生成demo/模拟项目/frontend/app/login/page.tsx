"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api";

/**
 * 登录与注册页面。
 * 同一个表单支持登录和注册两种模式，注册成功后自动登录并跳转到项目列表。
 */
export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");

    // 注册要求填写昵称，登录只校验邮箱与密码
    if (mode === "register" && !displayName.trim()) {
      setMessage("请先填写昵称，成片列表和素材库会显示这个名称。");
      return;
    }
    if (!email.includes("@")) {
      setMessage("邮箱格式不正确，请重新输入。");
      return;
    }
    if (password.length < 8) {
      setMessage("密码至少 8 位，建议同时包含字母和数字。");
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "register") {
        await register({ email, password, displayName });
      } else {
        await login({ email, password });
      }
      router.push("/");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "提交失败，请稍后再试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center gap-5 px-6">
      <h1 className="text-2xl font-semibold">StudioAgent AI 视频制片平台</h1>
      <p className="text-sm text-slate-400">
        登录后可以创建视频项目，与智能体协作生成剧本、分镜、素材和成片。
      </p>

      <div className="flex rounded border border-slate-800 text-sm">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={mode === "login" ? "flex-1 bg-slate-800 py-2" : "flex-1 py-2 text-slate-400"}
        >
          登录
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          className={mode === "register" ? "flex-1 bg-slate-800 py-2" : "flex-1 py-2 text-slate-400"}
        >
          注册
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        {mode === "register" ? (
          <label className="flex flex-col gap-1 text-sm">
            昵称
            <input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              className="rounded border border-slate-700 bg-slate-900 px-3 py-2"
            />
          </label>
        ) : null}
        <label className="flex flex-col gap-1 text-sm">
          邮箱
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="rounded border border-slate-700 bg-slate-900 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          密码
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded border border-slate-700 bg-slate-900 px-3 py-2"
          />
        </label>

        {message ? <p className="text-sm text-amber-300">{message}</p> : null}

        <button
          type="submit"
          disabled={submitting}
          className="mt-2 rounded bg-sky-600 py-2 text-sm font-medium disabled:opacity-60"
        >
          {submitting ? "正在提交…" : mode === "login" ? "登录" : "注册并登录"}
        </button>
      </form>
    </main>
  );
}
