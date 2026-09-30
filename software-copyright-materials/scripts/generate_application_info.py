#!/usr/bin/env python3
"""Generate the Markdown draft for application form information."""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
from pathlib import Path
from typing import Any

from common import (
    MAIN_FUNCTION_DETAIL_FIELD,
    MAIN_FUNCTION_LONG_MAX,
    MAIN_FUNCTION_LONG_MIN,
    MAIN_FUNCTION_MODE_FIELD,
    MAIN_FUNCTION_SHORT_LIMIT,
    TECHNICAL_CHARACTERISTIC_TAGS,
    ensure_dir,
    read_json,
    read_text,
    split_tag_values,
)


MAIN_FUNCTION_SHORT_MODE = "短版（≤200字）"
MAIN_FUNCTION_LONG_MODE = "长版（500~1300字）"
MAIN_FUNCTION_LONG_MODE_KEYS = ("长版", "详细", "500", "1300")


FIELD_ORDER = [
    "软件全称",
    "软件简称",
    "版本号",
    "软件分类",
    "开发完成日期",
    "开发方式",
    "软件说明",
    "发表状态",
    "首次发表日期",
    "著作权人",
    "权利范围",
    "权利取得方式",
    "开发的硬件环境",
    "运行的硬件环境",
    "开发该软件的操作系统",
    "软件开发环境 / 开发工具",
    "该软件的运行平台 / 操作系统",
    "软件运行支撑环境 / 支持软件",
    "编程语言",
    "源程序量",
    "开发目的",
    "面向领域 / 行业",
    "软件的主要功能",
    MAIN_FUNCTION_MODE_FIELD,
    MAIN_FUNCTION_DETAIL_FIELD,
    "软件的技术特点",
    "页数",
]


def effective_len(value: str) -> int:
    return len(str(value or "").replace(" ", "").replace("\n", ""))


def clean_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("`", "").replace("#", "").strip()
    return text


def trim_effective(value: str, max_chars: int) -> str:
    if effective_len(value) <= max_chars:
        return value
    result: list[str] = []
    count = 0
    for char in value:
        if char not in (" ", "\n"):
            count += 1
        if count > max_chars:
            break
        result.append(char)
    return "".join(result).rstrip("，。；、 ") + "。"


def business_feature_pairs(business: dict[str, Any] | None) -> list[tuple[str, str]]:
    if not business:
        return []
    features = business.get("business_features") or []
    details = business.get("business_feature_details") or {}
    if not isinstance(features, list):
        return []
    if not isinstance(details, dict):
        details = {}
    pairs: list[tuple[str, str]] = []
    for feature in features:
        name = clean_text(feature)
        if not name:
            continue
        detail = clean_text(details.get(name))
        pairs.append((name, detail))
    return pairs


def summarize_business_features(software_name: str, business: dict[str, Any] | None) -> str:
    pairs = business_feature_pairs(business)
    if not business or not pairs:
        return ""

    industry = clean_text(business.get("industry"))
    target_users = business.get("target_users") or []
    if isinstance(target_users, list):
        target_text = "、".join(clean_text(item) for item in target_users if clean_text(item))
    else:
        target_text = clean_text(target_users)
    core_value = clean_text(business.get("core_value"))
    product_positioning = clean_text(business.get("product_positioning"))
    operation_flow = business.get("operation_flow") or []
    if isinstance(operation_flow, list):
        flow_steps = [clean_text(item).rstrip("。") for item in operation_flow if clean_text(item)]
        flow_text = "，再".join(flow_steps)
    else:
        flow_text = clean_text(operation_flow)

    feature_names = "、".join(name for name, _ in pairs[:8])
    parts: list[str] = []
    if product_positioning:
        parts.append(product_positioning.rstrip("。") + "。")
    else:
        scope = f"面向{industry}" if industry else "面向实际业务场景"
        users = f"，服务于{target_text}" if target_text else ""
        parts.append(f"{software_name}是一套{scope}{users}的应用软件。")
    parts.append(f"软件主要提供{feature_names}等功能。")
    if core_value:
        parts.append(core_value.rstrip("。") + "。")

    for name, detail in pairs[:8]:
        if detail:
            detail = detail.rstrip("。")
            if detail.startswith(("用户", "系统")):
                parts.append(f"在{name}功能中，{detail}。")
            else:
                parts.append(f"{name}功能主要{detail}。")
        else:
            parts.append(f"{name}功能支持用户完成相关业务操作，并在处理完成后返回对应结果。")

    if flow_text:
        parts.append(f"用户通常先{flow_text}，系统在关键步骤提供状态反馈和结果展示。")

    result = "".join(parts)
    while effective_len(result) < MAIN_FUNCTION_LONG_MIN:
        result += (
            f"围绕{feature_names}等核心功能，软件将用户输入、过程处理、结果查看和资料管理组织在连续的操作流程中，"
            "用户可以根据页面提示逐步完成业务处理，系统保存必要的数据记录并提供清晰的反馈信息，"
            "便于用户后续继续查看、复核和调整相关内容。"
        )
    return trim_effective(result, MAIN_FUNCTION_LONG_MAX)


def trim_to_sentence(value: str, max_chars: int) -> str:
    """Trim to a limit, preferring a full sentence boundary for short fields."""
    text = str(value or "").strip()
    if effective_len(text) <= max_chars:
        return text
    trimmed = trim_effective(text, max_chars)
    boundary = max(trimmed.rfind(mark) for mark in "。；！")
    if boundary >= 40:
        return trimmed[: boundary + 1]
    return trimmed


def summarize_short_features(analysis: dict[str, Any], software_name: str, business: dict[str, Any] | None) -> str:
    """Compose the ≤200 character 主要功能 text required by the current form."""
    if business:
        provided = clean_text(business.get("main_functions_short"))
        if provided and effective_len(provided) <= MAIN_FUNCTION_SHORT_LIMIT:
            return provided
        positioning = clean_text(business.get("product_positioning"))
        industry = clean_text(business.get("industry"))
        core_value = clean_text(business.get("core_value"))
        names: list[str] = []
        for feature in business.get("business_features") or []:
            name = clean_text(feature)
            if name and name not in names:
                names.append(name)
        for module in business.get("manual_modules") or []:
            if isinstance(module, dict):
                title = clean_text(module.get("title"))
                if title and title not in names:
                    names.append(title)
        flow = [clean_text(item).rstrip("。") for item in (business.get("operation_flow") or []) if clean_text(item)]
        parts: list[str] = []
        if positioning:
            parts.append(positioning.rstrip("。") + "。")
        elif industry:
            parts.append(f"{software_name}面向{industry}业务。")
        if names:
            parts.append("软件提供" + "、".join(names[:6]) + "等功能。")
        if core_value:
            parts.append(core_value.rstrip("。") + "。")
        if flow:
            parts.append("主要流程包括" + "、".join(flow[:4]) + "。")
        text = "".join(parts)
        if effective_len(text) >= 60:
            return trim_to_sentence(text, MAIN_FUNCTION_SHORT_LIMIT)
    fallback = summarize_features(analysis, software_name, business)
    return trim_to_sentence(fallback, MAIN_FUNCTION_SHORT_LIMIT)


def summarize_detail_features(analysis: dict[str, Any], software_name: str, business: dict[str, Any] | None) -> str:
    """Long-form backup text (500~1300 characters) for forms that still ask for it."""
    if business:
        provided = clean_text(business.get("main_functions"))
        if MAIN_FUNCTION_LONG_MIN <= effective_len(provided) <= MAIN_FUNCTION_LONG_MAX:
            return provided
    return summarize_features(analysis, software_name, business)


def technical_characteristics_default(business: dict[str, Any] | None) -> str:
    """技术特点 must be chosen from the official tag list, never free text."""
    if business:
        provided = business.get("technical_characteristics")
        tags = provided if isinstance(provided, list) else split_tag_values(provided)
        known = [clean_text(tag) for tag in tags if clean_text(tag) in TECHNICAL_CHARACTERISTIC_TAGS]
        if known:
            return "、".join(known)
    return "待用户确认（请从官网标签中选择：" + "、".join(TECHNICAL_CHARACTERISTIC_TAGS) + "）"


def summarize_features(analysis: dict[str, Any], software_name: str, business: dict[str, Any] | None = None) -> str:
    """Generate the long-form main-function description (500~1300 Chinese characters)."""
    business_summary = summarize_business_features(software_name, business)
    if business_summary:
        return business_summary

    features = analysis.get("feature_candidates") or []
    readme = (analysis.get("readme_excerpt") or "").strip()
    routes = analysis.get("routes") or []

    readable_features = []
    for feature in features:
        name = humanize_feature(str(feature))
        if re.search(r"[A-Za-z]", name):
            continue
        if name and name not in readable_features:
            readable_features.append(name)

    parts: list[str] = []

    # Opening overview paragraph
    feature_list = "、".join(readable_features[:12]) if readable_features else "信息展示、业务处理、数据管理和系统交互"
    parts.append(
        f"{software_name}是一套面向用户业务场景的综合软件系统，"
        f"主要提供{feature_list}等核心功能模块。"
        f"系统通过清晰的操作界面和合理的业务流程设计，帮助用户高效完成日常工作和业务协作。"
    )

    # Module-by-module breakdown
    detail_parts: list[str] = []
    for name in readable_features[:8]:
        skip = {"软件登录", "用户注册", "用户认证", "首页", "数据看板", "系统设置"}
        if name in skip:
            continue
        detail_parts.append(f"{name}模块支持用户进行相关数据的查看、录入和管理操作，提供完整的业务处理能力和结果反馈。")

    if not detail_parts:
        route_display = [r.strip("/") for r in routes[:6] if r != "/" and not r.startswith("/:")]
        if route_display:
            for route_name in route_display[:6]:
                label = route_name.replace("-", " ").replace("_", " ").title()
                detail_parts.append(f"{label}模块支持用户进行相关数据的查看、录入和管理操作，提供完整的业务处理能力和结果反馈。")
        else:
            detail_parts.append("用户可通过系统界面完成数据查询、信息录入、业务处理和结果导出等操作。")
            detail_parts.append("系统支持多角色用户的协同工作，不同权限用户可访问相应的功能模块。")
            detail_parts.append("系统提供数据持久化存储和历史记录追溯能力，保障业务数据的完整性和可审计性。")

    # Limit detail parts to avoid exceeding max length
    combined = "".join(detail_parts)
    if len(combined) + len("".join(parts)) > MAIN_FUNCTION_LONG_MAX:
        while detail_parts and len("".join(detail_parts)) + len("".join(parts)) > MAIN_FUNCTION_LONG_MAX:
            detail_parts.pop()

    parts.extend(detail_parts)

    # Closing paragraph
    if readme:
        first_line = readme.splitlines()[0][:80]
        parts.append(f"系统核心业务围绕{first_line}展开，覆盖从信息采集到结果呈现的完整操作链路。")

    result = "".join(parts)

    while effective_len(result) < MAIN_FUNCTION_LONG_MIN:
        padding = (
            "此外，系统还提供了配套的数据管理、用户操作记录、状态跟踪和系统配置等辅助功能模块，"
            "各个功能模块之间通过统一的界面布局和操作规范协同运行，用户可以在不同模块间灵活切换和处理跨模块的业务流程。"
            "系统整体设计注重业务完整性和操作连续性，能够满足用户日常工作中对信息处理和业务管理的核心需求。"
            "系统界面设计遵循清晰直观的原则，主要操作入口集中展示，用户无需复杂培训即可上手使用。"
            "系统的数据管理能力包括数据的录入、存储、查询、修改和删除等基本操作，同时支持数据批量处理和导入导出功能。"
            "在业务处理方面，系统支持多步骤业务流程的串联执行，各环节之间数据自动流转，减少用户重复录入。"
            "系统还提供了灵活的配置选项，管理员可以根据实际业务需求调整系统参数和功能开关。"
        )
        result += padding

    return trim_effective(result, MAIN_FUNCTION_LONG_MAX)


def humanize_feature(name: str) -> str:
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    value = value.replace("-", " ").replace("_", " ").strip()
    key = value.lower().replace(" ", "")
    mapping = {
        "login": "软件登录",
        "register": "用户注册",
        "auth": "用户认证",
        "home": "首页",
        "dashboard": "数据看板",
        "project": "项目管理",
        "projects": "项目管理",
        "projectsettings": "项目设置",
        "projectssettings": "项目设置",
        "settings": "系统设置",
        "asset": "资源管理",
        "assets": "资源管理",
        "assethub": "资源中心",
        "billing": "费用管理",
        "agentstatusbar": "智能体状态展示",
        "messagebubble": "消息展示",
        "chatpanel": "对话面板",
        "chatinput": "对话输入",
        "assetpanel": "资源面板",
    }
    return mapping.get(key, value.title() if re.search(r"[A-Za-z]", value) else value)


def total_source_line_count(analysis: dict[str, Any], manifest: dict[str, Any]) -> int | str:
    source = analysis.get("source") if isinstance(analysis.get("source"), dict) else {}
    value = source.get("total_line_count") or source.get("line_count")
    if value:
        return int(value)
    fallback = manifest.get("source_line_count") or manifest.get("selected_source_line_count")
    return int(fallback) if fallback else "待用户确认"


def submitted_code_page_count(manifest: dict[str, Any]) -> int | str:
    value = manifest.get("submitted_page_count")
    if value:
        return int(value)
    mode = str(manifest.get("mode") or "")
    match = re.match(r"front(\d+)_back(\d+)", mode)
    if match:
        return int(match.group(1)) + int(match.group(2))
    slice_pages = manifest.get("slice_pages")
    if slice_pages:
        return int(slice_pages) * 2
    total = manifest.get("total_pages")
    if not total:
        return "待用户确认"
    return int(total)


def comment_stripping_note(manifest: dict[str, Any]) -> str:
    comments = manifest.get("comment_stripping")
    if not isinstance(comments, dict) or not comments:
        return "未记录（按旧版清单生成）"
    if not comments.get("enabled"):
        return "按参数保留源码注释"
    note = (
        f"已移除整行注释 {comments.get('comment_only_lines', 0)} 行、"
        f"行尾注释 {comments.get('inline_comment_lines', 0)} 处（字符串内容保留）"
    )
    unsupported = comments.get("unsupported_files") or []
    if unsupported:
        note += f"；{len(unsupported)} 个文件语言语法未知未改动"
    return note


def build_fields(
    analysis: dict[str, Any],
    manifest: dict[str, Any],
    software_name: str,
    version: str,
    answers: dict[str, str],
    business: dict[str, Any] | None = None,
) -> dict[str, str]:
    frameworks = analysis.get("frameworks") or []
    framework_text = "、".join(frameworks) if frameworks else "前端工程化框架"
    language = analysis.get("language") or "待用户确认"
    project = Path(analysis.get("project_root") or ".")
    hardware_hint = current_hardware_environment()
    dev_os_hint = current_operating_system()
    version_hint = version_confirmation_hint(analysis, version)
    software_name_hint = f"待用户确认（建议：{software_name}；请确认最终软件全称）"

    defaults = {
        "软件全称": software_name_hint,
        "软件简称": "",
        "版本号": version_hint,
        "软件分类": (business.get("software_category") or "应用软件") if business else "应用软件",
        "开发完成日期": "待用户确认（YYYY-MM-DD）",
        "开发方式": (business.get("development_situation") or "单独开发") if business else "单独开发",
        "软件说明": "原创",
        "发表状态": "待用户确认（已发表/未发表）",
        "首次发表日期": "待用户确认（YYYY-MM-DD，未发表则留空）",
        "著作权人": "待用户确认",
        "权利范围": (business.get("rights_scope") or "全部权利") if business else "全部权利",
        "权利取得方式": (business.get("rights_acquisition") or "原始取得") if business else "原始取得",
        "开发的硬件环境": hardware_hint,
        "运行的硬件环境": hardware_hint,
        "开发该软件的操作系统": dev_os_hint,
        "软件开发环境 / 开发工具": f"开发环境: {dev_os_hint}/开发工具: {infer_ide_name(project)}",
        "该软件的运行平台 / 操作系统": infer_runtime_os(analysis),
        "软件运行支撑环境 / 支持软件": infer_runtime_support(analysis, project),
        "编程语言": language,
        "源程序量": str(total_source_line_count(analysis, manifest)),
        "开发目的": (business.get("application_purpose") or f"待用户确认（≤50字符，需说明开发目的，不能只写软件名称）") if business else "待用户确认（≤50字符，需说明开发目的，不能只写软件名称）",
        "面向领域 / 行业": (business.get("industry") or "待用户确认") if business else "待用户确认",
        "软件的主要功能": summarize_short_features(analysis, software_name, business),
        MAIN_FUNCTION_MODE_FIELD: MAIN_FUNCTION_SHORT_MODE,
        MAIN_FUNCTION_DETAIL_FIELD: summarize_detail_features(analysis, software_name, business),
        "软件的技术特点": technical_characteristics_default(business),
        "页数": str(submitted_code_page_count(manifest)),
    }
    defaults.update({k: v for k, v in answers.items() if v})

    # 未发表时首次发表日期应为空，不触发待确认门禁
    publish_status = defaults.get("发表状态", "")
    if "未发表" in publish_status and "已发表" not in publish_status:
        if "待用户确认" in defaults.get("首次发表日期", "") or not defaults.get("首次发表日期", "").strip():
            defaults["首次发表日期"] = ""

    # 主要功能口径为长版时，把备用详细版内容放进官网字段
    mode = defaults.get(MAIN_FUNCTION_MODE_FIELD, "")
    if any(key in mode for key in MAIN_FUNCTION_LONG_MODE_KEYS):
        detail = defaults.get(MAIN_FUNCTION_DETAIL_FIELD, "")
        if detail and "待用户确认" not in detail:
            defaults["软件的主要功能"] = detail
    else:
        short = defaults.get("软件的主要功能", "")
        if short and "待用户确认" not in short:
            defaults["软件的主要功能"] = trim_to_sentence(short, MAIN_FUNCTION_SHORT_LIMIT)

    return defaults


def version_numbers(value: str) -> tuple[int, ...]:
    raw = str(value or "").strip()
    raw = raw.lstrip("vV")
    parts = re.findall(r"\d+", raw)
    return tuple(int(part) for part in parts[:3])


def version_less_than_1(value: str) -> bool:
    numbers = version_numbers(value)
    return bool(numbers) and numbers[0] < 1


def normalize_version_label(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return raw if raw.upper().startswith("V") else f"V{raw}"


def project_version_candidate(analysis: dict[str, Any]) -> str:
    value = str((analysis.get("package") or {}).get("version") or "").strip()
    if value and value.upper() != "V1.0":
        return normalize_version_label(value)
    return ""


def version_confirmation_hint(analysis: dict[str, Any], requested_version: str) -> str:
    project_version = project_version_candidate(analysis)
    requested = normalize_version_label(requested_version or "V1.0")
    if project_version and version_less_than_1(project_version):
        return (
            f"待用户确认（项目版本号为 {project_version}，软著首次提交通常建议从 V1.0 开始；"
            f"请确认填写 V1.0 还是 {project_version}）"
        )
    if not project_version and version_less_than_1(requested):
        return (
            f"待用户确认（当前建议版本号为 {requested}，软著首次提交通常建议从 V1.0 开始；"
            f"请确认填写 V1.0 还是 {requested}）"
        )
    if project_version and project_version != requested:
        return f"待用户确认（项目版本号为 {project_version}，当前建议为 {requested}；请确认最终申报版本号）"
    return f"待用户确认（建议：{requested}；请确认最终版本号）"


def format_gb(size: int | None) -> str:
    if not size:
        return ""
    return f"{size / (1024 ** 3):.0f}GB"


def total_memory_bytes() -> int | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None


def current_hardware_environment() -> str:
    parts: list[str] = []
    cpu_count = os.cpu_count()
    machine = platform.machine()
    processor = platform.processor()
    if processor and processor != machine and processor.lower() != "arm":
        parts.append(f"CPU {processor}")
    if cpu_count:
        parts.append(f"CPU {cpu_count}核")
    if machine:
        parts.append(f"架构 {machine}")
    memory = format_gb(total_memory_bytes())
    if memory:
        parts.append(f"内存 {memory}")
    try:
        disk = shutil.disk_usage(Path.home())
        disk_total = format_gb(disk.total)
        if disk_total:
            parts.append(f"硬盘 {disk_total}")
    except OSError:
        pass
    if parts:
        return "、".join(parts)
    return "待用户确认"


def current_operating_system() -> str:
    system = platform.system()
    if system == "Darwin":
        version = platform.mac_ver()[0]
        label = f"macOS {version}" if version else f"macOS（Darwin {platform.release()}）"
    elif system == "Windows":
        label = f"Windows {platform.release()}"
    elif system == "Linux":
        label = f"Linux {platform.release()}"
    else:
        label = f"{system} {platform.release()}".strip() or "待用户确认"
    return label


def infer_ide_name(project: Path) -> str:
    if (project / ".idea").exists():
        return "WebStorm 或 IntelliJ IDEA"
    if (project / ".vscode").exists():
        return "Visual Studio Code"
    if list(project.glob("*.code-workspace")):
        return "Visual Studio Code"
    return "Visual Studio Code"


def infer_runtime_os(analysis: dict[str, Any]) -> str:
    frameworks = set(analysis.get("frameworks") or [])
    deps = set((analysis.get("package") or {}).get("dependency_names") or [])
    if "Electron" in frameworks or "electron" in deps or "Tauri" in frameworks or "@tauri-apps/api" in deps:
        return "Windows 10/11 或 macOS 13及以上版本"
    if frameworks & {"Vue", "React", "Vite", "Next.js", "Nuxt", "Svelte", "Astro", "Angular"}:
        return "Windows 10/11 或 macOS 13及以上版本"
    return "Windows 10/11 或 macOS 13及以上版本"


def project_file(project: Path, relative: str) -> Path | None:
    if not relative:
        return None
    path = project / relative
    return path if path.exists() else None


def load_project_package(project: Path, analysis: dict[str, Any]) -> dict[str, Any]:
    package_path = project_file(project, (analysis.get("package") or {}).get("path") or "")
    if package_path:
        try:
            return read_json(package_path)
        except Exception:
            return {}
    return {}


def read_readme(project: Path) -> str:
    for name in ("README.md", "README.zh.md", "readme.md", "Readme.md"):
        path = project / name
        if path.exists():
            try:
                return read_text(path, limit=12000)
            except Exception:
                return ""
    return ""


def extract_requirement_bullets(text: str) -> list[str]:
    wanted = ("python", "node", "docker", "compose", "postgres", "redis", "chrome", "edge", "safari")
    # Patterns that indicate a feature description rather than a runtime requirement.
    _feature_start = re.compile(r"^(?:[一-鿿]|L\d|P\d|[A-Z]\d\s)")
    bullets: list[str] = []
    for line in text.splitlines():
        match = re.match(r"\s*[-*]\s+(.+)", line)
        if not match:
            continue
        item = match.group(1).strip()
        if any(key in item.lower() for key in wanted) and item not in bullets:
            if len(item) > 80:
                continue
            if _feature_start.match(item) and "（" in item:
                continue
            bullets.append(item)
    return bullets[:8]


def detect_package_manager(project: Path, package_path: str) -> str:
    base = (project / package_path).parent if package_path else project
    checks = [
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "Yarn"),
        ("bun.lock", "Bun"),
        ("bun.lockb", "Bun"),
        ("package-lock.json", "npm"),
    ]
    for filename, manager in checks:
        if (base / filename).exists() or (project / filename).exists():
            return manager
    return "npm"


def has_support_term(items: list[str], term: str) -> bool:
    return any(term.lower() in item.lower() for item in items)


def infer_runtime_support(analysis: dict[str, Any], project: Path) -> str:
    """Infer runtime support environment (≤50 chars plain text)."""
    package_info = load_project_package(project, analysis)
    package_path = (analysis.get("package") or {}).get("path") or ""
    deps = set((analysis.get("package") or {}).get("dependency_names") or [])
    frameworks = set(analysis.get("frameworks") or [])

    support: list[str] = []
    readme_requirements = extract_requirement_bullets(read_readme(project))

    if package_info or deps or frameworks & {"Vue", "React", "Vite", "Next.js", "Nuxt", "Svelte", "Astro", "Angular"}:
        if not has_support_term(support, "node"):
            node_engine = str((package_info.get("engines") or {}).get("node") or "").strip()
            support.append(f"Node.js {node_engine}".strip() if node_engine else "Node.js")
        support.append(detect_package_manager(project, package_path))
        support.append("现代浏览器")

    if ((project / "pyproject.toml").exists() or any(project.glob("*/pyproject.toml"))) and not has_support_term(support, "python"):
        support.append("Python")
    if ((project / "requirements.txt").exists() or list(project.glob("*/requirements*.txt"))) and not has_support_term(support, "python"):
        support.append("Python")

    if ((project / "docker-compose.yml").exists() or (project / "docker-compose.yaml").exists() or list(project.glob("docker-compose*.yml"))) and not has_support_term(support, "docker"):
        support.append("Docker")

    compose_text = ""
    for compose in list(project.glob("docker-compose*.yml")) + list(project.glob("docker-compose*.yaml")):
        try:
            compose_text += "\n" + read_text(compose, limit=20000).lower()
        except Exception:
            continue
    if "postgres" in compose_text:
        support.append("PostgreSQL")
    if "redis" in compose_text:
        support.append("Redis")

    # Also incorporate readme requirements into support software
    for req in readme_requirements:
        if not has_support_term(support, req.split()[0].lower()):
            support.append(req)

    # Deduplicate
    unique: list[str] = []
    for item in support:
        clean = str(item).strip().rstrip("；;")
        if clean and clean not in unique:
            unique.append(clean)

    if not unique:
        return "待用户确认"

    # Enforce ≤50 char limit: trim items if needed
    result = "、".join(unique)
    if len(result) > 50:
        trimmed: list[str] = []
        for item in unique:
            candidate = "、".join(trimmed + [item])
            if len(candidate) <= 50:
                trimmed.append(item)
            else:
                break
        result = "、".join(trimmed) if trimmed else unique[0][:50]
    return result


def write_application_md(path: Path, fields: dict[str, str], analysis: dict[str, Any], manifest: dict[str, Any], business: dict[str, Any] | None = None) -> None:
    # 兜底：未发表时首次发表日期不应输出"待用户确认"，直接留空
    publish_status = fields.get("发表状态", "")
    if "未发表" in publish_status and "已发表" not in publish_status:
        if "待用户确认" in (fields.get("首次发表日期") or "") or not (fields.get("首次发表日期") or "").strip():
            fields["首次发表日期"] = ""

    lines = ["# 申请表信息", ""]
    for field in FIELD_ORDER:
        lines.append(f"➤{field}：{fields.get(field, '待用户确认')}")
    pending = [field for field in FIELD_ORDER if "待用户确认" in (fields.get(field) or "")]

    # Build warnings for common issues
    warnings: list[str] = []
    soft_name = fields.get("软件全称", "")
    clean_name = str(soft_name).strip()
    raw_name = clean_name
    if "待用户确认" in clean_name and "建议：" in clean_name:
        try:
            raw_name = clean_name.split("建议：")[1].rstrip("）").split("；")[0].strip()
        except (IndexError, ValueError):
            raw_name = clean_name
    recommended_suffixes = ("软件", "平台", "系统")
    if raw_name and not raw_name.endswith(recommended_suffixes):
        warnings.append("软件全称未以「软件」「平台」或「系统」结尾，建议结合实际命名补充软件属性后缀。")

    main_func = fields.get("软件的主要功能", "")
    main_mode = str(fields.get(MAIN_FUNCTION_MODE_FIELD, ""))
    long_mode = any(key in main_mode for key in MAIN_FUNCTION_LONG_MODE_KEYS)
    if main_func and "待用户确认" not in main_func:
        func_len = effective_len(main_func)
        if long_mode:
            if not MAIN_FUNCTION_LONG_MIN <= func_len <= MAIN_FUNCTION_LONG_MAX:
                warnings.append(
                    f"软件的主要功能共 {func_len} 字；{MAIN_FUNCTION_MODE_FIELD}为长版时需为 "
                    f"{MAIN_FUNCTION_LONG_MIN}~{MAIN_FUNCTION_LONG_MAX} 字。"
                )
        elif func_len > MAIN_FUNCTION_SHORT_LIMIT:
            warnings.append(
                f"软件的主要功能共 {func_len} 字，超过官网 {MAIN_FUNCTION_SHORT_LIMIT} 字上限；"
                f"如本次表单需要 {MAIN_FUNCTION_LONG_MIN}~{MAIN_FUNCTION_LONG_MAX} 字，请把"
                f"{MAIN_FUNCTION_MODE_FIELD}改为长版。"
            )
        elif func_len < 120:
            warnings.append(
                f"软件的主要功能仅有 {func_len} 字，建议写到 150~{MAIN_FUNCTION_SHORT_LIMIT} 字，避免功能说明过薄。"
            )
    detail_func = fields.get(MAIN_FUNCTION_DETAIL_FIELD, "")
    if detail_func and "待用户确认" not in detail_func:
        detail_len = effective_len(detail_func)
        if not MAIN_FUNCTION_LONG_MIN <= detail_len <= MAIN_FUNCTION_LONG_MAX:
            warnings.append(
                f"{MAIN_FUNCTION_DETAIL_FIELD}共 {detail_len} 字，应为 "
                f"{MAIN_FUNCTION_LONG_MIN}~{MAIN_FUNCTION_LONG_MAX} 字。"
            )
    tech_tags = split_tag_values(fields.get("软件的技术特点", ""))
    unknown_tags = [tag for tag in tech_tags if tag not in TECHNICAL_CHARACTERISTIC_TAGS]
    if unknown_tags:
        warnings.append(
            "软件的技术特点只能从官网标签中选择，以下内容不是官网标签："
            + "、".join(unknown_tags)
            + "。可选标签："
            + "、".join(TECHNICAL_CHARACTERISTIC_TAGS)
            + "。"
        )

    # Check character limits for fields with ≤50 or ≤100 constraints
    char_limit_fields = {
        "开发的硬件环境": 50,
        "运行的硬件环境": 50,
        "开发该软件的操作系统": 50,
        "软件开发环境 / 开发工具": 50,
        "该软件的运行平台 / 操作系统": 50,
        "软件运行支撑环境 / 支持软件": 50,
        "开发目的": 50,
        "面向领域 / 行业": 50,
        "软件的技术特点": 100,
    }
    for field_name, limit in char_limit_fields.items():
        value = fields.get(field_name, "")
        if value and "待用户确认" not in value and len(value) > limit:
            warnings.append(f"{field_name}共 {len(value)} 字符，超过限制 {limit} 字符。请精简。")

    lines.extend(
        [
            "",
            "## 字段填写口径",
            "",
            "- 软件全称：最高优先级字段。正式资料文件名、代码 Word 页眉、操作手册标题与页眉、申请表都使用同一个名称，必须由用户在生成任何材料前仔细确认，确认后不要改动。",
            "- 软件简称：可选；如有常用简称则填写。",
            "- 版本号：必须由用户确认；如果项目版本小于 V1.0，软著首次提交通常建议使用 V1.0，也可按实际项目版本填写，最终以本字段为准。",
            "- 软件分类：应用软件/嵌入式软件/中间件/系统软件/其他。",
            "- 开发完成日期、首次发表日期：必须使用 YYYY-MM-DD 格式。",
            "- 开发方式：单独开发/合作开发/委托开发/下达任务开发。",
            "- 软件说明：原创 / 修改（含翻译软件、合成软件）。",
            "- 发表状态：已发表或未发表；已发表需附首次发表日期。",
            "- 软件开发环境 / 开发工具：≤50字符，格式 `开发环境: <OS>/开发工具: <IDE名称>`。",
            "- 开发该软件的操作系统：≤50字符，填写实际开发电脑的操作系统版本。",
            "- 该软件的运行平台 / 操作系统：≤50字符，填写软件运行所在的操作系统或浏览器环境。",
            "- 软件运行支撑环境 / 支持软件：≤50字符，直接列出运行依赖（如 Node.js、npm、浏览器），不加格式前缀。",
            "- 开发的硬件环境和运行的硬件环境：≤50字符，可使用检测到的电脑配置作为建议值。",
            "- 源程序量：纯数字（不含'行'字），指全部源程序的总行数。",
            "- 开发目的：≤50字符，用一句话说明目的，不能只写软件名称。",
            "- 面向领域 / 行业：≤50字符。",
            f"- 软件的主要功能：≤{MAIN_FUNCTION_SHORT_LIMIT} 字（官网当前字段限制），默认使用短版；不足 150 字建议补写。",
            f"- {MAIN_FUNCTION_MODE_FIELD}：短版（≤200字）或长版（500~1300字）。表单要求长文本时改为长版，脚本会把详细版内容填进“软件的主要功能”。",
            f"- {MAIN_FUNCTION_DETAIL_FIELD}：500~1300 字备用文本，官网字段只收 200 字时不要填到上面去。",
            "- 软件的技术特点：只能从官网标签中选择，可用标签：" + "、".join(TECHNICAL_CHARACTERISTIC_TAGS) + "。",
            "",
            "## 项目分析摘要",
            "",
            f"- 项目目录：{analysis.get('project_root', '')}",
            f"- 框架：{'、'.join(analysis.get('frameworks') or []) or '未识别'}",
            f"- 源码文件数：{analysis.get('source', {}).get('total_file_count', analysis.get('source', {}).get('file_count', 0))}",
            f"- 源程序量（含空行）：{analysis.get('source', {}).get('total_line_count', analysis.get('source', {}).get('line_count', 0))}",
            f"- 已选源码估算总页数：{manifest.get('total_pages', 0)}",
            f"- 实际提交代码材料页数：{submitted_code_page_count(manifest)}",
            f"- 代码输出模式：{manifest.get('mode', '')}",
            f"- 代码材料前后页数：前 {manifest.get('slice_pages', '未记录')} 页 + 后 {manifest.get('slice_pages', '未记录')} 页",
            f"- 代码注释处理：{comment_stripping_note(manifest)}",
            f"- 业务理解：{'已读取 草稿/业务理解.json' if business else '未提供，使用项目分析兜底'}",
            "",
            "## 待确认字段",
            "",
        ]
    )
    if warnings:
        lines.append("## 字段提醒")
        lines.append("")
        lines.extend(f"- {w}" for w in warnings)
        lines.append("")
    if pending:
        lines.extend(f"- {field}" for field in pending)
    else:
        lines.append("- 无")
    lines.extend(
        [
            "",
            "```text",
            "STOP_FOR_USER",
            "NEXT_ACTION: 请补全并确认申请表字段；确认后运行 confirm_stage.py --stage application-fields。",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def require_confirmed_business(business: dict[str, Any] | None) -> None:
    if business is None:
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 申请表信息必须基于已确认的业务理解生成。请先生成并确认 草稿/业务理解.md。"
        )
    if business.get("confirmation_required") and not business.get("user_confirmed"):
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 业务理解尚未确认。请先确认 草稿/业务理解.md，"
            "再运行 `python3 <SKILL_DIR>/scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage business --note \"<用户确认内容>\"`。"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--code-manifest", required=True)
    parser.add_argument("--software-name", required=True)
    parser.add_argument("--version", default="V1.0")
    parser.add_argument("--answers", help="Optional JSON object with confirmed field values")
    parser.add_argument("--business-context", help="Business context JSON generated before material drafting")
    parser.add_argument("--out-dir", default="软件著作权申请资料/草稿")
    args = parser.parse_args()

    analysis = read_json(Path(args.analysis))
    manifest = read_json(Path(args.code_manifest))
    answers = read_json(Path(args.answers)) if args.answers else {}
    business = read_json(Path(args.business_context)) if args.business_context else None
    require_confirmed_business(business)
    out_dir = ensure_dir(Path(args.out_dir))

    fields = build_fields(analysis, manifest, args.software_name, args.version, answers, business)
    out_path = out_dir / "申请表信息.md"
    write_application_md(out_path, fields, analysis, manifest, business)
    print(f"OK application draft: {out_path}")
    print("STOP_FOR_USER")
    print("NEXT_ACTION: 请补全并确认申请表字段；确认后运行 confirm_stage.py --stage application-fields。")


if __name__ == "__main__":
    main()
