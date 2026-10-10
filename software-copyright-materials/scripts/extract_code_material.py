#!/usr/bin/env python3
"""Extract real source code and create Markdown draft pages."""

from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path
from typing import Any

from common import (
    CODE_LINES_PER_PAGE,
    CODE_MAX_COLUMNS,
    CODE_SLICE_PAGE_CHOICES,
    CODE_SLICE_PAGES_DEFAULT,
    FRONTEND_EXTS,
    code_split_draft_names,
    ensure_dir,
    is_source_candidate,
    known_code_drafts,
    read_json,
    read_text,
    rel,
    safe_filename,
    write_json,
)
from code_comments import StripResult, strip_source_comments
import workdir_lock


# Used only to estimate how much source is needed for the first/last N-page sets.
# Final DOCX pagination is performed by Word's layout engine without hard page breaks.
LINES_PER_PAGE = CODE_LINES_PER_PAGE
SLICE_PAGES = CODE_SLICE_PAGES_DEFAULT
MAX_CODE_COLUMNS = CODE_MAX_COLUMNS


def category_weight(path: Path, project: Path) -> tuple[int, str]:
    r = rel(path, project).lower()
    name = path.name.lower()
    priority = 80
    if name in {"main.ts", "main.js", "main.tsx", "main.jsx", "app.vue", "app.tsx"} or r in {
        "src/app/page.tsx",
        "src/app/layout.tsx",
        "app/page.tsx",
        "app/layout.tsx",
    } or r.endswith("/src/app/page.tsx") or r.endswith("/src/app/layout.tsx"):
        priority = 0
    elif path.suffix.lower() in {".css", ".scss", ".sass", ".less"}:
        priority = 90
    elif "/router/" in r or "/routes/" in r or "router." in r or "routes." in r:
        priority = 10
    elif "/pages/" in r or "/views/" in r or "/app/" in r or "/screens/" in r:
        priority = 20
    elif "/api/" in r or "/apis/" in r or "/services/" in r or "request." in r:
        priority = 30
    elif "/store/" in r or "/stores/" in r or "/pinia/" in r or "/redux/" in r:
        priority = 40
    elif "/components/" in r:
        priority = 50
    elif "/utils/" in r or "/lib/" in r or "/hooks/" in r or "/composables/" in r:
        priority = 60
    elif path.suffix.lower() not in FRONTEND_EXTS:
        if any(part in r for part in ("/backend/app/", "/server/", "/api/", "/services/", "/models/", "/schemas/", "/workers/")):
            priority = 70
        elif name in {"docker-compose.yml", "docker-compose.yaml", "pyproject.toml"} or path.suffix.lower() in {".toml", ".yml", ".yaml"}:
            priority = 95
        else:
            priority = 100
    return priority, r


def should_skip_file(path: Path) -> bool:
    return not is_source_candidate(path)


def selected_line_estimate(item: dict[str, Any]) -> int:
    try:
        total = int(item.get("material_line_count") or item.get("line_count") or 0)
    except (TypeError, ValueError):
        total = 0
    return total + 1 if total > 0 else 0


def available_pages_from_selection(selection_path: Path | None, lines_per_page: int) -> tuple[int, int, int]:
    if selection_path is None or not selection_path.exists():
        return 0, 0, 0
    data = read_json(selection_path)
    items = data.get("files") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return 0, 0, 0
    available_lines = sum(selected_line_estimate(item) for item in items if isinstance(item, dict))
    unselected = sum(1 for item in items if isinstance(item, dict) and not item.get("selected") and selected_line_estimate(item) > 0)
    pages = (available_lines + lines_per_page - 1) // lines_per_page if available_lines else 0
    return available_lines, pages, unselected


def marker_for(path: Path, project: Path) -> str:
    return f"// File: {rel(path, project)}"


def display_width(text: str) -> int:
    """Return deterministic monospace display columns for Latin and CJK text."""
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width


def wrap_display_line(line: str, max_columns: int = MAX_CODE_COLUMNS) -> list[str]:
    """Wrap one source line without dropping characters or relying on Word wrapping."""
    if max_columns < 8:
        raise ValueError("max_columns must be at least 8")
    expanded = line.expandtabs(4)
    if not expanded:
        return [""]
    segments: list[str] = []
    current: list[str] = []
    current_width = 0
    for char in expanded:
        char_width = 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        if current and current_width + char_width > max_columns:
            segments.append("".join(current))
            current = []
            current_width = 0
        current.append(char)
        current_width += char_width
    if current:
        segments.append("".join(current))
    return segments


def source_code_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def material_code_lines(text: str, max_columns: int = MAX_CODE_COLUMNS) -> list[str]:
    lines: list[str] = []
    for source_line in source_code_lines(text):
        lines.extend(wrap_display_line(source_line, max_columns))
    return lines


def load_selected_files(project: Path, selection_path: Path | None) -> list[dict[str, Any]]:
    if selection_path is None:
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 代码抽取必须先使用 propose_code_selection.py 生成并确认 草稿/代码文件选择.json。"
        )

    data = read_json(selection_path)
    if isinstance(data, dict) and data.get("selection_required") and not data.get("user_confirmed"):
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 代码文件选择尚未确认。请先确认或修改 草稿/代码文件选择.json，"
            "再运行 `python3 <SKILL_DIR>/scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage code-selection --note \"<用户确认内容>\"`。"
        )
    items = data.get("files") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise SystemExit(f"Invalid selection file: {selection_path}")

    selected = []
    for item in items:
        if not isinstance(item, dict) or not item.get("selected"):
            continue
        path_value = item.get("path")
        if not path_value:
            continue
        selected.append(
            {
                "path": str(path_value),
                "selected": True,
            }
        )
    return selected


def collect_code_lines(
    project: Path, selection_path: Path | None, keep_comments: bool = False
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    selected_items = load_selected_files(project, selection_path)
    all_lines: list[str] = []
    manifest_files: list[dict[str, Any]] = []
    comment_stats: dict[str, Any] = {
        "enabled": not keep_comments,
        "comment_only_lines": 0,
        "inline_comment_lines": 0,
        "docstring_lines": 0,
        "docstring_strip_failed_files": [],
        "unsupported_files": [],
    }

    for item in selected_items:
        path = (project / item["path"]).resolve()
        try:
            path.relative_to(project.resolve())
        except ValueError:
            raise SystemExit(f"Selected file is outside project: {path}")
        if should_skip_file(path):
            continue
        raw_text = read_text(path)
        source_lines = raw_text.splitlines()
        stripped = StripResult(text=raw_text, supported=True, comment_only_lines=0, inline_comment_lines=0)
        if not keep_comments:
            stripped = strip_source_comments(raw_text, path.suffix)
            if stripped.supported:
                comment_stats["comment_only_lines"] += stripped.comment_only_lines
                comment_stats["inline_comment_lines"] += stripped.inline_comment_lines
                comment_stats["docstring_lines"] += stripped.docstring_lines
                if stripped.docstring_strip_failed:
                    comment_stats["docstring_strip_failed_files"].append(rel(path, project))
            else:
                comment_stats["unsupported_files"].append(rel(path, project))
        text = stripped.text
        selected_source_lines = source_code_lines(text)
        selected_lines = material_code_lines(text)
        if not selected_source_lines:
            continue
        start = len(all_lines) + 1
        marker = marker_for(path, project)
        marker_lines = wrap_display_line(marker)
        all_lines.extend(marker_lines)
        all_lines.extend(selected_lines)
        end = len(all_lines)
        source_end_line = len(source_lines)
        manifest_files.append(
            {
                "path": rel(path, project),
                "source_line_count": len(source_lines),
                "blank_line_count": len(source_lines) - len(selected_source_lines),
                "comment_only_line_count": stripped.comment_only_lines,
                "inline_comment_line_count": stripped.inline_comment_lines,
                "docstring_line_count": stripped.docstring_lines,
                "comment_stripping_supported": stripped.supported,
                "selected_line_start": 1,
                "selected_line_end": source_end_line,
                "selected_line_count": len(selected_source_lines),
                "material_line_count": len(marker_lines) + len(selected_lines),
                "material_line_start": start,
                "material_line_end": end,
            }
        )
    comment_stats["unsupported_files"] = sorted(set(comment_stats["unsupported_files"]))
    comment_stats["docstring_strip_failed_files"] = sorted(set(comment_stats["docstring_strip_failed_files"]))
    return all_lines, manifest_files, comment_stats


def paginate(lines: list[str], lines_per_page: int) -> list[list[str]]:
    return [lines[i : i + lines_per_page] for i in range(0, len(lines), lines_per_page)]


def write_pages_md(path: Path, title: str, software_name: str, version: str, pages: list[tuple[int, list[str]]]) -> None:
    chunks = [f"# {title}", "", f"软件名称：{software_name}", f"版本号：{version}", ""]
    for page_no, page_lines in pages:
        chunks.extend([f"## 第 {page_no} 页", "", "```text"])
        chunks.extend(page_lines)
        chunks.extend(["```", ""])
    path.write_text("\n".join(chunks), encoding="utf-8")


def write_manifest_md(path: Path, manifest: dict[str, Any]) -> None:
    comments = manifest.get("comment_stripping") or {}
    if comments.get("enabled"):
        comment_note = (
            f"已移除整行注释 {comments.get('comment_only_lines', 0)} 行、"
            f"文档字符串/独立字符串语句 {comments.get('docstring_lines', 0)} 行、"
            f"行尾注释 {comments.get('inline_comment_lines', 0)} 处（普通字符串内容保留）"
        )
        unsupported = comments.get("unsupported_files") or []
        if unsupported:
            comment_note += f"；{len(unsupported)} 个文件语言语法未知，未改动：" + "、".join(unsupported[:5])
        parse_failed = comments.get("docstring_strip_failed_files") or []
        if parse_failed:
            comment_note += (
                f"；★ {len(parse_failed)} 个 Python 文件语法解析失败，只能保证 # 注释被移除，"
                "文档字符串需人工复核：" + "、".join(parse_failed[:5])
            )
    else:
        comment_note = "按参数保留源码注释"
    lines = [
        "# 代码提取清单",
        "",
        f"- 软件名称：{manifest['software_name']}",
        f"- 版本号：{manifest['version']}",
        f"- 项目目录：{manifest['project_root']}",
        f"- 源码文件数：{manifest['file_count']}",
        f"- 材料代码行数：{manifest['material_line_count']}",
        f"- 每页行数：{manifest['lines_per_page']}",
        f"- 单行最大显示宽度：{manifest['max_code_columns']} 列",
        f"- 前后页数模式：前 {manifest['slice_pages']} 页 + 后 {manifest['slice_pages']} 页"
        f"（共 {manifest['slice_pages'] * 2} 页，可用 --slice-pages 在 30/40 之间切换）",
        f"- 注释处理：{comment_note}",
        f"- 已选源码估算总页数：{manifest['total_pages']}",
        f"- 实际提交材料页数：{manifest['submitted_page_count']}",
        f"- 目标页数：{manifest['target_pages']}",
        f"- 候选源码可生成页数：{manifest['available_candidate_pages']}",
        f"- 补充状态：{manifest['supplement_status']}",
        f"- 输出模式：{manifest['mode']}",
        "",
        "## 文件来源",
        "",
        "| 文件 | 源码行数 | 移除整行注释 | 移除文档字符串 | 移除行尾注释 | 抽取源码范围 | 抽取源码行数 | 材料物理行数 | 材料行范围 |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for item in manifest["files"]:
        lines.append(
            f"| `{item['path']}` | {item['source_line_count']} | "
            f"{item['comment_only_line_count']} | "
            f"{item.get('docstring_line_count', 0)} | "
            f"{item['inline_comment_line_count']} | "
            f"{item['selected_line_start']}-{item['selected_line_end']} | "
            f"{item['selected_line_count']} | "
            f"{item['material_line_count']} | "
            f"{item['material_line_start']}-{item['material_line_end']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extract(
    project: Path,
    out_dir: Path,
    software_name: str,
    version: str,
    lines_per_page: int,
    selection_path: Path | None,
    slice_pages: int = SLICE_PAGES,
    keep_comments: bool = False,
) -> dict[str, Any]:
    ensure_dir(out_dir)
    slice_pages = max(1, int(slice_pages))
    threshold = slice_pages * 2
    code_lines, files, comment_stats = collect_code_lines(
        project, selection_path, keep_comments=keep_comments
    )
    if not code_lines:
        raise SystemExit("No selected frontend source code files found for extraction.")

    pages = paginate(code_lines, lines_per_page)
    total_pages = len(pages)
    available_lines, available_pages, unselected_count = available_pages_from_selection(selection_path, lines_per_page)
    if total_pages < threshold and available_pages >= threshold and unselected_count > 0:
        raise SystemExit(
            "STOP_FOR_USER\n"
            f"NEXT_ACTION: 当前已选代码只有 {total_pages} 页，但候选源码足够补齐到 {threshold} 页。"
            "请在 草稿/代码文件选择.json 中继续选择补充文件，重新记录 code-selection 门禁后再抽取。"
        )
    for stale_name in known_code_drafts():
        (out_dir / stale_name).unlink(missing_ok=True)
    outputs: list[str] = []

    if total_pages >= threshold:
        # Slice by physical lines instead of pre-cut page groups. The material's
        # last group is usually partial, so cutting ``pages[-slice_pages:]``
        # hands Word a short tail page: measured 2026-10-10, a 55-line slice set
        # ended with a 44-line group and produced a 40-page document whose last
        # page held only 5 lines. Both halves must carry exactly
        # ``slice_pages * lines_per_page`` lines so every page, last page
        # included, is full.
        page_size = slice_pages * lines_per_page
        front_lines = code_lines[:page_size]
        back_lines = code_lines[-page_size:]
        front = [
            (index + 1, page)
            for index, page in enumerate(paginate(front_lines, lines_per_page))
        ]
        back = [
            (slice_pages + 1 + index, page)
            for index, page in enumerate(paginate(back_lines, lines_per_page))
        ]
        front_name, back_name = code_split_draft_names(slice_pages)
        front_path = out_dir / front_name
        back_path = out_dir / back_name
        write_pages_md(front_path, f"代码材料（前{slice_pages}页）", software_name, version, front)
        write_pages_md(back_path, f"代码材料（后{slice_pages}页）", software_name, version, back)
        outputs.extend([front_path.name, back_path.name])
        mode = f"front{slice_pages}_back{slice_pages}"
    else:
        all_path = out_dir / "代码-全部.md"
        all_pages = list(enumerate(pages, start=1))
        write_pages_md(all_path, "代码材料（全部）", software_name, version, all_pages)
        outputs.append(all_path.name)
        mode = "all_under_target_pages"
    supplement_status = (
        f"候选源码可达到前{slice_pages}页/后{slice_pages}页要求"
        if available_pages >= threshold
        else f"候选源码不足{threshold}页，按全部代码材料生成"
    )

    manifest = {
        "software_name": software_name,
        "version": version,
        "project_root": str(project.resolve()),
        "file_count": len(files),
        "material_line_count": len(code_lines),
        "source_line_count": sum(item["source_line_count"] for item in files),
        "selected_source_line_count": sum(item["selected_line_count"] for item in files),
        "lines_per_page": lines_per_page,
        "max_code_columns": MAX_CODE_COLUMNS,
        "slice_pages": slice_pages,
        "comment_stripping": comment_stats,
        "total_pages": total_pages,
        "submitted_page_count": threshold if total_pages >= threshold else total_pages,
        "target_pages": threshold,
        "available_candidate_line_count": available_lines,
        "available_candidate_pages": available_pages,
        "supplement_status": supplement_status,
        "mode": mode,
        "selection_file": str(selection_path) if selection_path else None,
        "outputs": outputs,
        "files": files,
        "safe_software_filename": safe_filename(software_name),
    }
    write_json(out_dir / "代码提取清单.json", manifest)
    write_manifest_md(out_dir / "代码提取清单.md", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--analysis", help="Optional project analysis JSON; retained for workflow traceability")
    parser.add_argument("--software-name", required=True)
    parser.add_argument("--version", default="V1.0")
    parser.add_argument("--out-dir", default="软件著作权申请资料/草稿")
    parser.add_argument("--lines-per-page", type=int, default=LINES_PER_PAGE)
    parser.add_argument(
        "--slice-pages",
        type=int,
        choices=list(CODE_SLICE_PAGE_CHOICES),
        default=SLICE_PAGES,
        help="Pages per half of the code material: 30 (60 pages total) or 40 (80 pages total, default)",
    )
    parser.add_argument(
        "--keep-comments",
        action="store_true",
        help="Keep source comments instead of removing them from the code material",
    )
    parser.add_argument("--selection", help="Editable JSON file created by propose_code_selection.py")
    parser.add_argument(
        "--ignore-lock",
        action="store_true",
        help="Ignore another run holding the workdir lock (only when it is known to be stale)",
    )
    args = parser.parse_args()

    project = Path(args.project)
    if not project.exists():
        raise SystemExit(f"Project not found: {project}")
    if args.analysis and not Path(args.analysis).exists():
        raise SystemExit(f"Analysis JSON not found: {args.analysis}")

    selection = Path(args.selection) if args.selection else None
    if selection and not selection.exists():
        raise SystemExit(f"Selection JSON not found: {selection}")

    with workdir_lock.hold(Path(args.out_dir).parent, "extract_code_material.py", force=args.ignore_lock):
        manifest = extract(
            project,
            Path(args.out_dir),
            args.software_name,
            args.version,
            args.lines_per_page,
            selection,
            slice_pages=args.slice_pages,
            keep_comments=args.keep_comments,
        )
    print(f"OK code drafts: {args.out_dir}")
    print(f"Selected files: {manifest['file_count']}")
    print(f"Mode: {manifest['mode']}")
    print(f"Slice pages: {manifest['slice_pages']} + {manifest['slice_pages']}")
    print(f"Total pages: {manifest['total_pages']}")
    comments = manifest["comment_stripping"]
    if comments.get("enabled"):
        print(
            "Comments removed: "
            f"{comments['comment_only_lines']} comment-only lines, "
            f"{comments['inline_comment_lines']} trailing comments"
        )
    print(f"Outputs: {', '.join(manifest['outputs'])}")


if __name__ == "__main__":
    main()
