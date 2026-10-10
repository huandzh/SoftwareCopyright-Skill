#!/usr/bin/env python3
"""Record explicit user confirmations for gated workflow stages."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from typing import Any

from common import (
    IDENTITY_APPEARANCES,
    IDENTITY_FILE_NAME,
    MAIN_FUNCTION_DETAIL_FIELD,
    MAIN_FUNCTION_LONG_MAX,
    MAIN_FUNCTION_LONG_MIN,
    MAIN_FUNCTION_MODE_FIELD,
    MAIN_FUNCTION_SHORT_LIMIT,
    TECHNICAL_CHARACTERISTIC_LIMIT,
    TECHNICAL_CHARACTERISTIC_STACK_KEYWORDS,
    TECHNICAL_CHARACTERISTIC_TAGS,
    confirmation_is_current,
    confirmation_payload_sha256,
    draft_completeness_issues,
    draft_snapshot,
    file_sha256,
    identity_issue,
    identity_mismatch_issues,
    main_function_is_long_mode,
    read_json,
    split_tag_values,
    split_technical_characteristics,
    write_json,
)


SCREENSHOT_METHODS = {"playwright-cli", "user-supplied", "skip"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOFTWARE_NAME_SUFFIXES = ("软件", "平台", "系统", "工具", "程序", "网站", "客户端", "引擎")
FIELD_LIMITS = {
    "开发的硬件环境": 50,
    "运行的硬件环境": 50,
    "开发该软件的操作系统": 50,
    "软件开发环境 / 开发工具": 50,
    "该软件的运行平台 / 操作系统": 50,
    "软件运行支撑环境 / 支持软件": 50,
    "开发目的": 50,
    "面向领域 / 行业": 50,
    "软件的技术特点": TECHNICAL_CHARACTERISTIC_LIMIT,
    "编程语言": 120,
}
ENUM_FIELDS = {
    "软件分类": {"应用软件", "嵌入式软件", "中间件", "系统软件", "其他"},
    "开发方式": {"单独开发", "合作开发", "委托开发", "下达任务开发"},
    "软件说明": {"原创", "修改（含翻译软件、合成软件）"},
    "发表状态": {"已发表", "未发表"},
    "权利范围": {"全部权利", "部分权利"},
    "权利取得方式": {"原始取得", "继受取得"},
}
REQUIRED_FIELDS = (
    "软件全称",
    "版本号",
    "软件分类",
    "开发完成日期",
    "开发方式",
    "软件说明",
    "发表状态",
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
    "软件的技术特点",
    "页数",
)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def write_confirmation(path: Path, data: dict[str, Any], key: str, note: str) -> None:
    data[key] = True
    data["confirmation_note"] = note
    data["confirmed_at"] = timestamp()
    data["confirmed_content_sha256"] = confirmation_payload_sha256(data)
    write_json(path, data)


def pending_application_fields(md_path: Path) -> list[str]:
    if not md_path.exists():
        return [f"缺少 {md_path}"]
    return [line.strip() for line in md_path.read_text(encoding="utf-8").splitlines() if "待用户确认" in line]


def effective_len(value: str) -> int:
    return len(str(value or "").replace(" ", "").replace("\n", ""))


def application_field_value(md_path: Path, field_name: str) -> str:
    prefix = f"➤{field_name}："
    for line in md_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def main_function_issues(md_path: Path) -> list[str]:
    """Validate 主要功能 against the current form limits and the short-text backup."""
    issues: list[str] = []
    short = application_field_value(md_path, "软件的主要功能")
    detail = application_field_value(md_path, MAIN_FUNCTION_DETAIL_FIELD)
    mode = application_field_value(md_path, MAIN_FUNCTION_MODE_FIELD)
    long_mode = main_function_is_long_mode(mode)
    if short and "待用户确认" not in short:
        count = effective_len(short)
        if long_mode:
            if count < MAIN_FUNCTION_LONG_MIN or count > MAIN_FUNCTION_LONG_MAX:
                issues.append(
                    f"➤软件的主要功能：当前 {count} 字；官网当前要求 "
                    f"{MAIN_FUNCTION_LONG_MIN}~{MAIN_FUNCTION_LONG_MAX} 字（汉字字符加标点），"
                    f"{MAIN_FUNCTION_MODE_FIELD}未写短版时必须是长版。"
                )
        elif count > MAIN_FUNCTION_SHORT_LIMIT:
            issues.append(
                f"➤软件的主要功能：当前 {count} 字，超过 {MAIN_FUNCTION_MODE_FIELD}=短版时"
                f"{MAIN_FUNCTION_SHORT_LIMIT} 字的上限。官网当前要求 {MAIN_FUNCTION_LONG_MIN}~"
                f"{MAIN_FUNCTION_LONG_MAX} 字：请改成长版正文，或把该字段换成 ≤{MAIN_FUNCTION_SHORT_LIMIT} 字的短文本。"
            )
    if detail and "待用户确认" not in detail:
        detail_count = effective_len(detail)
        if detail_count < MAIN_FUNCTION_LONG_MIN or detail_count > MAIN_FUNCTION_LONG_MAX:
            issues.append(
                f"➤{MAIN_FUNCTION_DETAIL_FIELD}：当前 {detail_count} 字，备用详细版应为 "
                f"{MAIN_FUNCTION_LONG_MIN}~{MAIN_FUNCTION_LONG_MAX} 字。"
            )
    return issues


def technical_characteristic_issues(md_path: Path) -> list[str]:
    """技术特点 = 官网标签（可选）+ ≤100 字说明；说明里不写技术栈名称。"""
    value = application_field_value(md_path, "软件的技术特点")
    if not value or "待用户确认" in value:
        return []
    tags, note = split_technical_characteristics(value)
    issues: list[str] = []
    unknown = [tag for tag in tags if tag not in TECHNICAL_CHARACTERISTIC_TAGS]
    if unknown:
        issues.append(
            "➤软件的技术特点："
            + "、".join(unknown)
            + " 不在官网标签列表中。允许的标签为："
            + "、".join(TECHNICAL_CHARACTERISTIC_TAGS)
            + "。"
        )
    if note:
        count = effective_len(note)
        if count > TECHNICAL_CHARACTERISTIC_LIMIT:
            issues.append(
                f"➤软件的技术特点：说明部分 {count} 字，超过官网 {TECHNICAL_CHARACTERISTIC_LIMIT} 字上限"
                "（官网注：所列标签不计入这 100 个字符，所以标签写在「；」前面即可）。"
            )
        stack = [keyword for keyword in TECHNICAL_CHARACTERISTIC_STACK_KEYWORDS if keyword in note.lower()]
        if stack:
            issues.append(
                "➤软件的技术特点：说明部分出现了技术栈名称（"
                + "、".join(stack)
                + "），该字段要写软件的技术能力，不是实现框架，请改成业务/技术特点表述。"
            )
    return issues


def application_field_issues(md_path: Path) -> list[str]:
    issues = pending_application_fields(md_path)
    if not md_path.exists():
        return issues

    for field_name in REQUIRED_FIELDS:
        if not application_field_value(md_path, field_name):
            issues.append(f"➤{field_name}：不能为空。")

    issues.extend(main_function_issues(md_path))
    issues.extend(technical_characteristic_issues(md_path))
    for field_name, allowed in ENUM_FIELDS.items():
        value = application_field_value(md_path, field_name)
        if value and "待用户确认" not in value and value not in allowed:
            issues.append(f"➤{field_name}：值“{value}”不在允许范围内（{'/'.join(sorted(allowed))}）。")
    for field_name in ("开发完成日期", "首次发表日期"):
        value = application_field_value(md_path, field_name)
        if value and "待用户确认" not in value:
            try:
                if not DATE_RE.fullmatch(value):
                    raise ValueError
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                issues.append(f"➤{field_name}：必须是有效的 YYYY-MM-DD 日期。")
    if application_field_value(md_path, "发表状态") == "已发表" and not application_field_value(md_path, "首次发表日期"):
        issues.append("➤首次发表日期：发表状态为“已发表”时必须填写。")
    for field_name, limit in FIELD_LIMITS.items():
        value = application_field_value(md_path, field_name)
        if value and "待用户确认" not in value and len(value) > limit:
            issues.append(f"➤{field_name}：当前 {len(value)} 字符，超过 {limit} 字符限制。")
    for field_name in ("源程序量", "页数"):
        value = application_field_value(md_path, field_name)
        if value and "待用户确认" not in value and (not value.isdigit() or int(value) <= 0):
            issues.append(f"➤{field_name}：必须填写大于 0 的纯数字。")
    return issues


def current_confirmation_issue(path: Path, label: str) -> str | None:
    if not path.exists():
        return f"{label}尚未确认"
    data = read_json(path)
    if not data.get("user_confirmed"):
        return f"{label}尚未确认"
    if not confirmation_is_current(data):
        return f"{label}在确认后已被修改，请重新确认"
    return None


def confirm_environment(workdir: Path, note: str) -> Path:
    out_path = workdir / "环境确认.json"
    data = load_json_or_empty(out_path)
    write_confirmation(out_path, data, "environment_confirmed", note)
    return out_path


def confirm_project(workdir: Path, note: str) -> Path:
    out_path = workdir / "项目确认.json"
    data = load_json_or_empty(out_path)
    write_confirmation(out_path, data, "project_confirmed", note)
    return out_path


def confirm_software_name(workdir: Path, note: str, software_name: str, version: str, short_name: str = "") -> Path:
    """Record the highest-priority gate: the exact software name and version."""
    name = str(software_name or "").strip()
    label = str(version or "").strip()
    short = str(short_name or "").strip()
    issues: list[str] = []
    if not name:
        issues.append("缺少 --software-name：必须让用户给出最终软件全称。")
    elif "待用户确认" in name or "建议" in name:
        issues.append(f"软件全称“{name}”仍是建议值；必须由用户确认最终登记名称。")
    elif len(name) > 60:
        issues.append(f"软件全称 {len(name)} 个字符，明显过长，请再次与用户确认最终登记名称。")
    if not label:
        issues.append("缺少 --version：必须让用户确认版本号（如 V1.0 或 1.0）。")
    if name and label and name == label:
        issues.append("软件全称与版本号相同，请检查是否传参错误。")
    if issues:
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 软件全称/版本号未通过确认，请先与用户核对：\n"
            + "\n".join(f"- {item}" for item in issues)
        )
    path = workdir / IDENTITY_FILE_NAME
    data = load_json_or_empty(path)
    data["software_name"] = name
    data["software_short_name"] = short
    data["version"] = label
    data["appears_in"] = list(IDENTITY_APPEARANCES)
    if not name.endswith(SOFTWARE_NAME_SUFFIXES):
        data["name_suffix_hint"] = (
            "软件全称未以“软件/平台/系统”等结尾，正式资料文件名、页眉和申请表都会照此使用，请再次与用户确认。"
        )
    else:
        data.pop("name_suffix_hint", None)
    write_confirmation(path, data, "software_name_confirmed", note)
    return path


def identity_gate_issues(workdir: Path, software_name: str = "", version: str = "") -> list[str]:
    """Return the identity gate issue plus any mismatch with a later draft."""
    issue = identity_issue(workdir)
    if issue:
        return [issue]
    return identity_mismatch_issues(workdir, software_name, version)


def confirm_business(workdir: Path, note: str) -> Path:
    path = workdir / "草稿/业务理解.json"
    if not path.exists():
        raise SystemExit("Missing 草稿/业务理解.json")
    data = read_json(path)
    issues = identity_gate_issues(
        workdir,
        str(data.get("software_name") or ""),
        str(data.get("version") or ""),
    )
    if issues:
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 业务理解与已确认的软件全称/版本号不一致，请先统一：\n"
            + "\n".join(f"- {item}" for item in issues)
        )
    write_confirmation(path, data, "user_confirmed", note)
    return path


def confirm_code_selection(workdir: Path, note: str) -> Path:
    path = workdir / "草稿/代码文件选择.json"
    if not path.exists():
        raise SystemExit("Missing 草稿/代码文件选择.json")
    data = read_json(path)
    files = data.get("files") if isinstance(data, dict) else []
    selected = [item for item in files if isinstance(item, dict) and item.get("selected")]
    if not selected:
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 代码文件选择尚未由模型填写。请先选择至少一个源码文件并填写选择理由，再让用户确认。"
        )
    missing_reason = [item.get("path") for item in selected if not str(item.get("model_reason") or "").strip()]
    if data.get("model_selection_required") and missing_reason:
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 已选源码缺少模型选择理由，请补全 `model_reason` 后再确认。\n"
            + "\n".join(f"- {item}" for item in missing_reason[:20])
        )
    write_confirmation(path, data, "user_confirmed", note)
    return path


def parse_screenshot_method(method: str, note: str) -> str:
    value = (method or note or "").lower()
    if any(key in value for key in ("skip", "no-screenshot", "none", "不截图", "跳过", "暂不", "先不", "不要截图", "无需截图")):
        return "skip"
    if value.strip() == "1" or any(key in value for key in ("playwright", "playwright-cli", "自动截图", "自动")):
        return "playwright-cli"
    if value.strip() == "2" or any(key in value for key in ("user", "manual", "self", "手动", "自己", "用户")):
        return "user-supplied"
    raise SystemExit(
        "STOP_FOR_USER\n"
        "NEXT_ACTION: 请明确截图方式：playwright-cli、user-supplied 或 skip。"
    )


def confirm_screenshot_method(workdir: Path, note: str, method: str) -> Path:
    selected = parse_screenshot_method(method, note)
    out_path = workdir / "截图方式确认.json"
    data = load_json_or_empty(out_path)
    data["screenshot_method"] = selected
    write_confirmation(out_path, data, "screenshot_method_confirmed", note)
    return out_path


def confirm_application_fields(workdir: Path, note: str) -> Path:
    md_path = workdir / "草稿/申请表信息.md"
    issues = identity_gate_issues(
        workdir,
        application_field_value(md_path, "软件全称"),
        application_field_value(md_path, "版本号"),
    )
    issues.extend(application_field_issues(md_path))
    if issues:
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 申请表信息仍有字段未满足要求。请先补全或修正字段，再重新确认。\n"
            + "\n".join(f"- {item}" for item in issues[:20])
        )
    out_path = workdir / "草稿/申请表字段确认.json"
    data = load_json_or_empty(out_path)
    data["application_md_sha256"] = file_sha256(md_path)
    write_confirmation(out_path, data, "application_fields_confirmed", note)
    return out_path


def confirm_markdown(workdir: Path, note: str) -> Path:
    issues = []
    business = workdir / "草稿/业务理解.json"
    selection = workdir / "草稿/代码文件选择.json"
    screenshot = workdir / "截图方式确认.json"
    fields = workdir / "草稿/申请表字段确认.json"

    business_issue = current_confirmation_issue(business, "业务理解")
    if business_issue:
        issues.append(business_issue)
    selection_issue = current_confirmation_issue(selection, "代码文件选择")
    if selection_issue:
        issues.append(selection_issue)
    if not screenshot.exists() or not read_json(screenshot).get("screenshot_method_confirmed"):
        issues.append("截图方式尚未确认")
    elif read_json(screenshot).get("screenshot_method") not in SCREENSHOT_METHODS:
        issues.append("截图方式已失效，请重新选择 Playwright CLI 自动截图、用户自行截图或跳过截图")
    if not fields.exists() or not read_json(fields).get("application_fields_confirmed"):
        issues.append("申请表字段尚未确认")
    else:
        app_md = workdir / "草稿/申请表信息.md"
        if not app_md.exists() or read_json(fields).get("application_md_sha256") != file_sha256(app_md):
            issues.append("申请表信息在确认后已被修改，请重新确认")
    field_issues = application_field_issues(workdir / "草稿/申请表信息.md")
    if field_issues:
        issues.append("申请表信息仍有字段未满足要求")
    issues.extend(
        identity_gate_issues(
            workdir,
            application_field_value(workdir / "草稿/申请表信息.md", "软件全称"),
            application_field_value(workdir / "草稿/申请表信息.md", "版本号"),
        )
    )
    issues.extend(draft_completeness_issues(workdir))

    if issues:
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: Markdown 草稿确认前需要先处理以下事项：\n"
            + "\n".join(f"- {item}" for item in issues)
        )

    out_path = workdir / "草稿/最终生成确认.json"
    data = load_json_or_empty(out_path)
    data["draft_file_sha256"] = draft_snapshot(workdir)
    write_confirmation(out_path, data, "markdown_confirmed", note)
    return out_path


GATE_LABELS = {
    "environment": ("环境确认.json", "环境检查与 OfficeCLI 口径"),
    "project": ("项目确认.json", "项目目录选择"),
    "software-name": (IDENTITY_FILE_NAME, "软件全称 / 简称 / 版本号"),
    "business": ("草稿/业务理解.json", "业务理解"),
    "code-selection": ("草稿/代码文件选择.json", "代码文件选择"),
    "screenshot-method": ("截图方式确认.json", "截图方式"),
    "application-fields": ("草稿/申请表字段确认.json", "申请表字段"),
    "markdown": ("草稿/最终生成确认.json", "Markdown 最终确认"),
}

GATE_OPTIONAL = {"environment", "project"}

GATE_FLAGS = {
    "environment": '--stage environment --note "<用户确认内容>"',
    "project": '--stage project --note "<用户确认内容>"',
    "software-name": '--stage software-name --software-name "<软件全称>" --version "<版本号>" [--short-name "<简称>"]',
    "business": '--stage business --note "<用户确认内容>"',
    "code-selection": '--stage code-selection --note "<用户确认内容>"',
    "screenshot-method": '--stage screenshot-method --method <playwright-cli|user-supplied|skip> --note "<用户选择>"',
    "application-fields": '--stage application-fields --note "<用户确认内容>"',
    "markdown": '--stage markdown --note "<用户确认内容>"',
}


def _changed_entries(recorded: dict[str, str], current: dict[str, str]) -> list[str]:
    """List drafts whose content fingerprint changed since the gate was recorded."""
    changes: list[str] = []
    for key in sorted(set(recorded) | set(current)):
        before = recorded.get(key)
        after = current.get(key)
        if before == after:
            continue
        if before is None:
            changes.append(f"新增 {key}")
        elif after is None:
            changes.append(f"删除 {key}")
        else:
            changes.append(f"修改 {key}")
    return changes


def gate_status(workdir: Path) -> list[dict[str, Any]]:
    """Describe every gate: confirmed / missing / stale, with the reason and the fix.

    内容一改就要重记门禁，而重记哪几个是靠报错反推的 —— 这个视图把「改了什么 →
    哪个门禁失效 → 该跑哪条命令」直接列出来，省掉一轮试错。
    """
    rows: list[dict[str, Any]] = []
    draft_snapshot_now = draft_snapshot(workdir)
    for stage, (relative, label) in GATE_LABELS.items():
        path = workdir / relative
        row: dict[str, Any] = {
            "stage": stage,
            "label": label,
            "file": str(relative),
            "optional": stage in GATE_OPTIONAL,
            "command": f'python <SKILL_DIR>/scripts/confirm_stage.py --workdir {workdir} {GATE_FLAGS[stage]}',
            "state": "missing",
            "reasons": [],
        }
        if not path.is_file():
            row["reasons"].append("确认文件不存在")
            rows.append(row)
            continue
        try:
            data = read_json(path)
        except Exception as exc:  # noqa: BLE001 - 报告用，任何读取失败都要说清楚
            row["state"] = "unreadable"
            row["reasons"].append(f"无法读取：{exc}")
            rows.append(row)
            continue
        if not data.get("user_confirmed") and not data.get("software_name_confirmed") \
                and not data.get("screenshot_method_confirmed") \
                and not data.get("application_fields_confirmed") \
                and not data.get("markdown_confirmed") \
                and not data.get("environment_confirmed") \
                and not data.get("project_confirmed"):
            row["reasons"].append("尚未确认")
            rows.append(row)
            continue
        if not confirmation_is_current(data):
            row["state"] = "stale"
            row["reasons"].append("确认内容指纹已失效（确认后又被改过）")
            rows.append(row)
            continue
        row["state"] = "ok"
        if stage == "markdown":
            changes = _changed_entries(data.get("draft_file_sha256") or {}, draft_snapshot_now)
            if changes:
                row["state"] = "stale"
                row["reasons"].append("确认后以下草稿发生变化：" + "；".join(changes[:8]))
        elif stage == "application-fields":
            recorded = str(data.get("application_md_sha256") or "")
            app_md = workdir / "草稿/申请表信息.md"
            current = file_sha256(app_md) if app_md.is_file() else ""
            if recorded != current:
                row["state"] = "stale"
                row["reasons"].append("草稿/申请表信息.md 在确认后已修改")
        rows.append(row)

    # markdown 是最容易连带失效的门禁：即使指纹还对，也要顺带报出其它阻塞项
    if all(row["state"] == "ok" for row in rows if row["stage"] == "markdown"):
        blockers = draft_completeness_issues(workdir)
        for row in rows:
            if row["stage"] == "markdown" and blockers:
                row["state"] = "blocked"
                row["reasons"].extend(blockers[:5])
    return rows


def print_gate_status(workdir: Path) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    rows = gate_status(workdir)
    print(f"# 门禁状态：{workdir}")
    stale = [
        row for row in rows
        if row["state"] in {"stale", "missing", "unreadable", "blocked"} and not row.get("optional")
    ]
    for row in rows:
        icon = {"ok": "✅", "stale": "⚠️", "missing": "—", "unreadable": "✖", "blocked": "⛔"}[row["state"]]
        suffix = "（可选，未记录不影响生成）" if row.get("optional") and row["state"] != "ok" else ""
        print(f"{icon} {row['stage']}（{row['label']}）{suffix}")
        for reason in row["reasons"]:
            print(f"    - {reason}")
        if row["state"] != "ok" and not row.get("optional"):
            print(f"    重记：{row['command']}")
    if not stale:
        print("\n所有门禁当前有效，可以直接生成正式资料。")
    else:
        print(f"\n有 {len(stale)} 个门禁需要处理：{', '.join(row['stage'] for row in stale)}")
    return 0 if not stale else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", default="软件著作权申请资料")
    parser.add_argument(
        "--stage",
        required=False,
        choices=[
            "environment",
            "project",
            "software-name",
            "business",
            "code-selection",
            "screenshot-method",
            "application-fields",
            "markdown",
        ],
    )
    parser.add_argument("--note", default="用户已确认")
    parser.add_argument(
        "--status",
        action="store_true",
        help="只打印每个门禁的当前状态、失效原因与重记命令，不做任何写入",
    )
    parser.add_argument(
        "--method",
        choices=sorted(SCREENSHOT_METHODS),
        help="Screenshot capture method when --stage screenshot-method",
    )
    parser.add_argument("--software-name", default="", help="Confirmed software full name when --stage software-name")
    parser.add_argument("--version", default="", help="Confirmed version when --stage software-name")
    parser.add_argument("--short-name", default="", help="Optional software short name")
    args = parser.parse_args()

    workdir = Path(args.workdir)
    if args.status:
        raise SystemExit(print_gate_status(workdir))
    if not args.stage:
        raise SystemExit(
            "STOP_FOR_USER\n"
            "NEXT_ACTION: 需要 --stage <门禁名> 才能记录确认；只想查看门禁状态时用 --status。"
        )
    if args.stage == "environment":
        path = confirm_environment(workdir, args.note)
    elif args.stage == "project":
        path = confirm_project(workdir, args.note)
    elif args.stage == "software-name":
        path = confirm_software_name(workdir, args.note, args.software_name, args.version, args.short_name)
    elif args.stage == "business":
        path = confirm_business(workdir, args.note)
    elif args.stage == "code-selection":
        path = confirm_code_selection(workdir, args.note)
    elif args.stage == "screenshot-method":
        path = confirm_screenshot_method(workdir, args.note, args.method or "")
    elif args.stage == "application-fields":
        path = confirm_application_fields(workdir, args.note)
    else:
        path = confirm_markdown(workdir, args.note)

    print(f"OK confirmation recorded: {args.stage}")
    print(path)


if __name__ == "__main__":
    main()
