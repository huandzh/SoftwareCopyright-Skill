import type { Metadata } from "next";
import "./../styles/globals.css";
import { AppShell } from "@/components/AppShell";

// 站点级元信息：标题与描述会显示在浏览器标签和分享卡片上
export const metadata: Metadata = {
  title: "StudioAgent AI 视频制片平台",
  description: "用自然语言驱动多智能体协作，完成从剧本到成片的视频制作流程",
};

/**
 * 应用根布局。
 * 左侧导航由 AppShell 负责，右侧内容区由各个页面填充。
 */
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // html lang 固定为中文，便于浏览器按中文排版
  return (
    <html lang="zh-CN">
      <body className="bg-slate-950 text-slate-100 antialiased">
        {/* 全局外壳：顶部项目切换、左侧导航、底部成本提示 */}
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
