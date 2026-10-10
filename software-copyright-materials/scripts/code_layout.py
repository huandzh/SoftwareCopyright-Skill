#!/usr/bin/env python3
"""Read real Word pagination and word statistics for a generated DOCX.

OfficeCLI 只暴露总页数，无法回答「每一页是不是都填满了」；中文「字数」也只有
Word 自己给得出。这个模块把 ``word_docx_probe.ps1`` 包成一个可复用的 Python
接口，供正式生成脚本做两道额外门禁：

* ``verify_code_layout``：代码材料必须「总页数 == 文件名页数」且「每页 >= 50 行」；
* ``word_stats``：操作手册的 Word 实测字数必须低于上限（默认 1 万字）。

不可用时（非 Windows、没有 PowerShell、没装 Word）返回 ``available=False`` 与
原因，由调用方写进生成报告，而不是静默通过。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PROBE_SCRIPT = Path(__file__).resolve().parent / "word_docx_probe.ps1"
MIN_CODE_LINES_PER_PAGE = 50


def powershell_host() -> str | None:
    for name in ("pwsh", "powershell"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _parse_json(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def probe(
    docx: Path,
    *,
    mode: str = "stats",
    expected_pages: int | None = None,
    min_lines_per_page: int | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    """Run the Word probe; never raises, always returns a dict with ``available``."""
    result: dict[str, Any] = {"available": False, "reason": "", "docx": str(docx)}
    if mode not in {"stats", "layout"}:
        result["reason"] = f"未知模式：{mode}"
        return result
    if not PROBE_SCRIPT.is_file():
        result["reason"] = f"缺少探针脚本：{PROBE_SCRIPT}"
        return result
    host = powershell_host()
    if host is None:
        result["reason"] = "当前环境没有 PowerShell，无法调用 Word 复核"
        return result
    if not docx.is_file():
        result["reason"] = f"找不到文件：{docx}"
        return result

    command = [
        host, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(PROBE_SCRIPT),
        "-Path", str(docx), "-Mode", mode,
    ]
    if expected_pages:
        command += ["-ExpectedPages", str(int(expected_pages))]
    if min_lines_per_page:
        command += ["-MinLinesPerPage", str(int(min_lines_per_page))]
    try:
        completed = subprocess.run(
            command, text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        result["reason"] = f"Word 复核超时（{timeout}s）"
        return result
    except OSError as exc:
        result["reason"] = f"无法启动 PowerShell：{exc}"
        return result

    payload = _parse_json(completed.stdout) or _parse_json(completed.stderr)
    if payload is None:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        result["reason"] = "Word 复核没有返回可解析结果" + (f"：{detail[-1]}" if detail else "")
        return result
    if not payload.get("success"):
        result["reason"] = str(payload.get("error") or "Word 不可用（未安装 Microsoft Word？）")
        return result
    payload["available"] = True
    payload["reason"] = ""
    return payload


def verify_code_layout(
    docx: Path,
    *,
    expected_pages: int,
    min_lines_per_page: int = MIN_CODE_LINES_PER_PAGE,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Return ``(ok, messages, probe)`` for one code material DOCX."""
    data = probe(
        docx,
        mode="layout",
        expected_pages=expected_pages,
        min_lines_per_page=min_lines_per_page,
    )
    if not data.get("available"):
        return True, [f"`{docx.name}`：当前环境无法用 Word 复核每页行数（{data['reason']}）。"], data

    messages: list[str] = []
    ok = True
    pages = int(data.get("pages") or 0)
    per_page = [int(value) for value in (data.get("perPage") or [])]
    min_lines = min(per_page) if per_page else 0
    last_lines = per_page[-1] if per_page else 0
    if pages != expected_pages:
        ok = False
        messages.append(
            f"`{docx.name}`：Word 实测 {pages} 页，与文件名要求的 {expected_pages} 页不符。"
        )
    if min_lines < min_lines_per_page:
        ok = False
        messages.append(
            f"`{docx.name}`：存在不足 {min_lines_per_page} 行的页（最少 {min_lines} 行，末页 {last_lines} 行），"
            "请重新校准选材量后再生成。"
        )
    if ok:
        messages.append(
            f"`{docx.name}`：Word 复核每页 {min_lines}~{max(per_page)} 行，末页 {last_lines} 行，"
            f"共 {pages} 页（要求每页至少 {min_lines_per_page} 行）。"
        )
    return ok, messages, data


def word_stats(docx: Path) -> dict[str, Any]:
    return probe(docx, mode="stats")


def main() -> int:
    parser = argparse.ArgumentParser(description="用 Word 复核 DOCX 的分页与字数")
    parser.add_argument("--docx", required=True)
    parser.add_argument("--mode", choices=["stats", "layout"], default="stats")
    parser.add_argument("--expected-pages", type=int, default=0)
    parser.add_argument("--min-lines", type=int, default=MIN_CODE_LINES_PER_PAGE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    docx = Path(args.docx)
    if args.mode == "layout" and args.expected_pages:
        ok, messages, data = verify_code_layout(
            docx, expected_pages=args.expected_pages, min_lines_per_page=args.min_lines
        )
        if args.json:
            print(json.dumps({"ok": ok, "messages": messages, "probe": data}, ensure_ascii=False, indent=2))
        else:
            for message in messages:
                print(message)
        return 0 if ok else 1

    data = probe(docx, mode=args.mode)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if data.get("available") else 1


if __name__ == "__main__":
    raise SystemExit(main())
