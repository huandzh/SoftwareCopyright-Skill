"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// 顶部导航项；key 同时用于高亮判断
const NAV_ITEMS = [
  { href: "/", label: "项目" },
  { href: "/assets", label: "素材库" },
  { href: "/billing", label: "计费" },
  { href: "/login", label: "账号" },
];

/**
 * 全局外壳。
 * 负责顶部导航、页面标题区域和内容容器，页面组件只需要填充 children。
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-3">
          <Link href="/" className="flex items-center gap-2 text-sm font-semibold">
            <span className="inline-block h-2 w-2 rounded-full bg-sky-500" />
            StudioAgent
          </Link>
          <nav className="flex items-center gap-4 text-sm text-slate-300">
            {NAV_ITEMS.map((item) => {
              // 根路径只在完全相等时高亮，避免所有页面都点亮“项目”
              const active =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={active ? "text-sky-400" : "hover:text-slate-100"}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <div className="mx-auto w-full max-w-7xl">{children}</div>
      <footer className="border-t border-slate-900 px-6 py-4 text-xs text-slate-500">
        演示环境：生成结果仅保存在本地部署的存储中，请定期清理不再使用的素材。
      </footer>
    </div>
  );
}
