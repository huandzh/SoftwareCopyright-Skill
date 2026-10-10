#!/usr/bin/env python3
"""Shared helpers for the software copyright materials skill."""

from __future__ import annotations

import json
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Iterable


EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".output",
    "coverage",
    "target",
    "vendor",
    "软件著作权申请资料",
    "software-copyright-materials",
}

KNOWN_CONFIG_FILES = {
    ".babelrc",
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.yaml",
    ".eslintrc.yml",
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.yaml",
    ".prettierrc.yml",
    ".swcrc",
    "angular.json",
    "app.json",
    "astro.config.mjs",
    "astro.config.ts",
    "babel.config.js",
    "babel.config.json",
    "Cargo.lock",
    "Cargo.toml",
    "composer.json",
    "docker-compose.yaml",
    "docker-compose.yml",
    "eslint.config.cjs",
    "eslint.config.js",
    "eslint.config.mjs",
    "go.mod",
    "go.sum",
    "jsconfig.json",
    "lerna.json",
    "manifest.json",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "nuxt.config.js",
    "nuxt.config.ts",
    "nx.json",
    "package-lock.json",
    "package.json",
    "playwright.config.js",
    "playwright.config.ts",
    "postcss.config.cjs",
    "postcss.config.js",
    "prettier.config.cjs",
    "prettier.config.js",
    "prettier.config.mjs",
    "project.json",
    "pyproject.toml",
    "rollup.config.js",
    "rollup.config.mjs",
    "rollup.config.ts",
    "svelte.config.js",
    "stylelintrc.json",
    "tailwind.config.js",
    "tailwind.config.ts",
    "tsconfig.app.json",
    "tsconfig.json",
    "tsconfig.node.json",
    "tslint.json",
    "turbo.json",
    "vite.config.js",
    "vite.config.mjs",
    "vite.config.ts",
    "vitest.config.js",
    "vitest.config.ts",
    "webpack.config.js",
    "webpack.config.ts",
    "workspace.json",
    ".env.example",
}

FRONTEND_EXTS = {
    ".vue",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html",
    ".svelte",
    ".astro",
}

LOCK_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "bun.lock",
}

# Source discovery intentionally uses a denylist plus content detection instead
# of an extension allowlist. New languages and engine-specific scripts should be
# inventoried automatically; the model/user selection gate decides relevance.
DOCUMENT_EXTS = {
    ".adoc",
    ".doc",
    ".docx",
    ".md",
    ".odt",
    ".pdf",
    ".rst",
    ".rtf",
    ".txt",
    ".wps",
}

BINARY_EXTS = {
    ".7z",
    ".a",
    ".avi",
    ".bin",
    ".bmp",
    ".class",
    ".db",
    ".dll",
    ".dmg",
    ".eot",
    ".exe",
    ".flac",
    ".gif",
    ".gz",
    ".ico",
    ".iso",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lib",
    ".lockb",
    ".mov",
    ".mp3",
    ".mp4",
    ".o",
    ".obj",
    ".ogg",
    ".otf",
    ".pdb",
    ".png",
    ".pyc",
    ".rar",
    ".so",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".ttf",
    ".wav",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".xls",
    ".xlsx",
    ".zip",
}

NON_SOURCE_TEXT_EXTS = {
    ".csv",
    ".log",
    ".tsv",
}

DOCUMENT_FILE_PREFIXES = (
    "changelog",
    "code_of_conduct",
    "contributing",
    "license",
    "readme",
    "security",
)

DOCUMENT_DIR_NAMES = {
    "doc",
    "docs",
    "documentation",
    "spec",
    "specs",
    "设计文档",
    "需求文档",
}

DOCUMENT_NAME_HINTS = (
    "architecture",
    "design",
    "manual",
    "prd",
    "requirement",
    "设计",
    "需求",
    "手册",
    "文档",
    "架构",
    "说明",
)

# Used only to keep obvious source files out of document evidence when their
# names contain words such as "design" or "manual". It is not a discovery gate.
KNOWN_SOURCE_HINT_EXTS = FRONTEND_EXTS | {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".cxx",
    ".dart",
    ".gd",
    ".gml",
    ".go",
    ".h",
    ".hh",
    ".hpp",
    ".java",
    ".kt",
    ".lua",
    ".php",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
}

MAX_SOURCE_FILE_BYTES = 800_000

# Shared code-document layout. The extractor uses the physical-line estimate
# only to choose enough material; Word still performs the final pagination.
#
# CODE_LINES_PER_PAGE must equal the real page capacity of this layout, not a
# conservative guess. The slices are cut at page boundaries, so an estimate
# below the capacity leaves the LAST page of every code document nearly empty:
# measured 2026-10-10 on this project, 55-line slices produced a 40-page
# document whose page 40 carried only 16 lines (below the ">= 50 lines per
# page" rule for program listings).
# Capacity of A4 + 1.8cm margins + 13pt exact line spacing:
#   usable height = 29.7cm - 2 * 1.8cm = 26.1cm = 739.8pt
#   739.8pt / 13pt = 56.9 -> 56 lines per page (confirmed by Word repagination:
#   every page of a 2240-paragraph document holds exactly 56 lines).
CODE_FONT_NAME = "Consolas"
CODE_FONT_SIZE = "8pt"
CODE_LINE_SPACING = "13pt"
CODE_LINES_PER_PAGE = 56
CODE_MAX_COLUMNS = 90

# Code material is submitted as the first N and the last N pages. The default
# for this flavour is 40 + 40 pages; 30 + 30 stays selectable for users who
# need the smaller traditional set.
CODE_SLICE_PAGE_CHOICES = (30, 40)
CODE_SLICE_PAGES_DEFAULT = 40

# Codes are submitted as the first/last 30 pages by the official form text, but
# the intermediate agencies this flavour works with ask for 20 extra pages, so
# the default is 40 + 40. Keep both options so a project can switch back.
CODE_SLICE_PAGE_NOTE = "官网表单写前后各 30 页；本 flavour 走中间代理，默认前后各 40 页（多提供 20 页）"

# Application form field rules. The current official form asks for
# 主要功能 500~1300 字（汉字字符加标点）and 技术特点 ≤100 字（标签不计入），
# so the long text is the default and the ≤200 字 short text is opt-in only.
MAIN_FUNCTION_SHORT_LIMIT = 200
MAIN_FUNCTION_LONG_MIN = 500
MAIN_FUNCTION_LONG_MAX = 1300
MAIN_FUNCTION_DETAIL_FIELD = "软件的主要功能（详细版）"
MAIN_FUNCTION_MODE_FIELD = "主要功能口径"
TECHNICAL_CHARACTERISTIC_LIMIT = 100

# 「主要功能口径」只有短版（≤200 字）是例外：口径缺失、留空或写成别的值时，
# 一律按官网当前要求的长版（500~1300 字）校验，避免短文本被默认放行。
MAIN_FUNCTION_SHORT_MODE_KEYS = ("短版", "短文本", "≤200", "200 字")
MAIN_FUNCTION_LONG_MODE_KEYS = ("长版", "详细", "500", "1300")


def main_function_is_long_mode(mode: Any) -> bool:
    """Return False only when the 口径 field explicitly asks for the short text."""
    text = str(mode or "")
    return not any(key in text for key in MAIN_FUNCTION_SHORT_MODE_KEYS)

# Official 技术特点 multi-select tags. The list is copied from the form the
# project owner submitted; refresh it when the official list changes.
#
# 官网注：技术特点为「汉字字符加标点100个以内，所列15个选择跟软件相关的，
# 不在100个字符」—— 也就是「标签 + 一段说明」都允许，只有说明部分受 100 字
# 限制。说明写软件的技术能力，不要写框架/技术栈名称（Tauri、React、SQLite…），
# 那些是实现细节，不是登记表要看的技术特点。
TECHNICAL_CHARACTERISTIC_STACK_KEYWORDS = (
    "react", "vue", "angular", "svelte", "tauri", "electron", "vite", "next.js",
    "typescript", "javascript", "node.js", "npm", "pnpm", "fastapi", "uvicorn",
    "python", "sqlite", "pandas", "pyinstaller", "webview2", "rust",
)

# 没有「；」分隔符、又不全是官网标签时：长于这个字数就当成一整段说明，
# 否则仍按标签区处理，好让「自研框架、网页应用」这类伪标签继续报错。
TECHNICAL_CHARACTERISTIC_PLAIN_NOTE_MIN = 30
TECHNICAL_CHARACTERISTIC_TAGS = (
    "APP",
    "VR软件",
    "5G软件",
    "人工智能软件",
    "信息安全软件",
    "大数据软件",
    "小程序",
    "云计算软件",
    "医疗软件",
    "地理信息软件",
    "教育软件",
    "智慧城市软件",
    "物联网软件",
    "网页应用",
    "游戏软件",
    "金融软件",
)


def split_technical_characteristics(value: Any) -> tuple[list[str], str]:
    """Split 技术特点 into its leading official tags and the free-text note.

    允许的三种写法：
      - ``大数据软件、信息安全软件``                  → 纯标签
      - ``大数据软件、信息安全软件；离线单机部署，…``   → 标签 + 说明（推荐）
      - ``离线单机部署，数据全部留在本机，…``           → 纯说明（整段较长时按说明处理）

    「；」是标签区与说明区的分隔符，但只有前半段**全部**是官网标签时才这么切；
    否则整段按说明处理（说明里出现「；」不会被误判成标签）。没有分隔符且不是
    官方标签列表时：长文本按说明处理，短文本按标签区处理，这样「自研框架、网页应用」
    仍会被当成不在官网标签列表里报错。
    """
    text = str(value or "").strip()
    if not text:
        return [], ""
    for separator in ("；", ";"):
        if separator in text:
            head, tail = text.split(separator, 1)
            head_tokens = [tag for tag in split_tag_values(head) if tag]
            if head_tokens and all(token in TECHNICAL_CHARACTERISTIC_TAGS for token in head_tokens):
                return head_tokens, tail.strip()
            break
    tokens = [tag for tag in split_tag_values(text) if tag]
    if tokens and all(token in TECHNICAL_CHARACTERISTIC_TAGS for token in tokens):
        return tokens, ""
    if len(text) > TECHNICAL_CHARACTERISTIC_PLAIN_NOTE_MIN:
        return [], text
    return tokens, ""

IDENTITY_FILE_NAME = "软件名称确认.json"
IDENTITY_APPEARANCES = (
    "申请表信息",
    "正式资料文件名",
    "代码 Word 页眉",
    "操作手册标题与页眉",
)

CONFIRMATION_METADATA_KEYS = {
    "user_confirmed",
    "confirmation_note",
    "confirmed_at",
    "confirmed_content_sha256",
}


CODE_DRAFT_RE = re.compile(r"^代码-(?P<part>前(?P<front>\d+)页|后(?P<back>\d+)页|全部)\.md$")
CODE_DOCX_SLICE_RE = re.compile(r"\((?:前|后)(?P<pages>\d+)页\)")


def code_split_draft_names(slice_pages: int) -> tuple[str, str]:
    return (f"代码-前{slice_pages}页.md", f"代码-后{slice_pages}页.md")


def known_code_drafts() -> set[str]:
    """Every code Markdown name the skill may produce in any slice mode."""
    names = {"代码-全部.md"}
    for pages in CODE_SLICE_PAGE_CHOICES:
        names.update(code_split_draft_names(pages))
    return names


def code_docx_name(md_name: str, safe_name: str) -> str | None:
    match = CODE_DRAFT_RE.match(md_name)
    if not match:
        return None
    return f"{safe_name}-代码({match.group('part')}).docx"


def code_output_slice_pages(name: str) -> int | None:
    """Read the required page count from ``...-代码(前40页).docx`` style names."""
    match = CODE_DOCX_SLICE_RE.search(name)
    return int(match.group("pages")) if match else None


def normalize_identity(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def split_tag_values(value: Any) -> list[str]:
    return [part.strip() for part in re.split(r"[、,，;；/|]+", str(value or "")) if part.strip()]


def confirmed_identity(workdir: Path) -> dict[str, Any]:
    """Return the confirmed software name/version block, or ``{}`` when unusable."""
    path = workdir / IDENTITY_FILE_NAME
    if not path.is_file():
        return {}
    try:
        data = read_json(path)
    except Exception:
        return {}
    if not data.get("software_name_confirmed"):
        return {}
    if not confirmation_is_current(data):
        return {}
    return data


def identity_issue(workdir: Path) -> str | None:
    """Describe why the software name gate is not satisfied yet."""
    path = workdir / IDENTITY_FILE_NAME
    if not path.is_file():
        return (
            "软件全称/版本号尚未确认：请先与用户确认软件全称、软件简称和版本号，再运行 "
            'confirm_stage.py --workdir 软件著作权申请资料 --stage software-name '
            '--software-name "<软件全称>" --version "<版本号>"'
        )
    try:
        data = read_json(path)
    except Exception as exc:
        return f"{IDENTITY_FILE_NAME} 无法读取：{exc}"
    if not data.get("software_name_confirmed"):
        return "软件全称/版本号尚未确认：请记录 software-name 门禁"
    if not confirmation_is_current(data):
        return "软件全称/版本号在确认后已被修改：请重新确认 software-name 门禁"
    return None


def identity_mismatch_issues(workdir: Path, software_name: str = "", version: str = "") -> list[str]:
    """Check a later draft against the confirmed software name/version."""
    data = confirmed_identity(workdir)
    if not data:
        return []
    issues: list[str] = []
    confirmed_name = str(data.get("software_name") or "")
    confirmed_version = str(data.get("version") or "")
    if software_name and normalize_identity(software_name) != normalize_identity(confirmed_name):
        issues.append(
            f"当前软件全称“{software_name}”与已确认名称“{confirmed_name}”不一致；"
            "软件全称会同时出现在申请表、正式文件名、代码 Word 页眉、操作手册标题与页眉，请统一后重新确认"
        )
    if version and normalize_identity(version) != normalize_identity(confirmed_version):
        issues.append(
            f"当前版本号“{version}”与已确认版本号“{confirmed_version}”不一致；请统一后重新确认"
        )
    return issues


def is_excluded(path: Path) -> bool:
    # iter_project_files checks every directory entry while descending. Looking
    # at all absolute path parts would wrongly exclude a project merely because
    # one of its parent folders happens to be named "build" or like this skill,
    # "software-copyright-materials".
    if path.name in EXCLUDE_DIRS:
        return True
    name = path.name
    if name.startswith(".") and name not in {".env.example"}:
        return True
    if name in LOCK_FILES:
        return True
    if name.endswith(".map") or name.endswith(".min.js") or name.endswith(".min.css"):
        return True
    return False


def iter_project_files(project: Path, exts: set[str] | None = None) -> Iterable[Path]:
    project = project.resolve()
    for root, dirs, files in os.walk(project):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if not is_excluded(root_path / d)]
        for filename in files:
            path = root_path / filename
            if is_excluded(path):
                continue
            if exts is not None and path.suffix.lower() not in exts:
                continue
            yield path


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def read_text(path: Path, limit: int | None = None) -> str:
    data = path.read_bytes()
    if limit is not None:
        data = data[:limit]
    encodings = ["utf-8", "utf-8-sig", "gb18030", "latin-1"]
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings.insert(0, "utf-16")
    if data.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        encodings.insert(0, "utf-32")
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def file_sha256(path: Path) -> str:
    """Return a stable digest used to invalidate stale user confirmations."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def confirmation_payload_sha256(data: dict[str, Any]) -> str:
    """Hash JSON content while excluding confirmation bookkeeping fields."""
    payload = {key: value for key, value in data.items() if key not in CONFIRMATION_METADATA_KEYS}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def confirmation_is_current(data: dict[str, Any]) -> bool:
    expected = str(data.get("confirmed_content_sha256") or "")
    return bool(expected) and expected == confirmation_payload_sha256(data)


def draft_snapshot(workdir: Path) -> dict[str, str]:
    """Hash user-reviewable drafts plus the selected screenshot inputs."""
    draft_dir = workdir / "草稿"
    if not draft_dir.is_dir():
        return {}
    paths = [
        path
        for path in sorted(draft_dir.rglob("*"))
        if path.is_file()
        and path.name != "最终生成确认.json"
        and path.suffix.lower() in {".md", ".json"}
    ]
    screenshot_confirmation = workdir / "截图方式确认.json"
    if screenshot_confirmation.is_file():
        paths.append(screenshot_confirmation)
    screenshot_manifest = workdir / "截图/截图清单.json"
    if screenshot_manifest.is_file():
        paths.append(screenshot_manifest)
        try:
            entries = read_json(screenshot_manifest).get("screenshots") or []
            for entry in entries:
                if not isinstance(entry, dict) or not entry.get("path"):
                    continue
                image_path = Path(str(entry["path"]))
                if not image_path.is_absolute():
                    image_path = screenshot_manifest.parent / image_path
                if image_path.is_file():
                    paths.append(image_path.resolve())
        except Exception:
            pass
    snapshot: dict[str, str] = {}
    resolved_workdir = workdir.resolve()
    for index, path in enumerate(paths, start=1):
        resolved = path.resolve()
        try:
            key = resolved.relative_to(resolved_workdir).as_posix()
        except ValueError:
            key = f"external-screenshot/{index}-{resolved.name}"
        snapshot[key] = file_sha256(resolved)
    return snapshot


def draft_completeness_issues(workdir: Path) -> list[str]:
    """Validate that every draft needed by the final builder exists and is coherent."""
    draft_dir = workdir / "草稿"
    required = [
        "业务理解.md",
        "业务理解.json",
        "代码文件选择.json",
        "代码提取清单.md",
        "代码提取清单.json",
        "申请表信息.md",
        "操作手册.md",
        "操作手册自检记录.md",
        "操作手册自检记录.json",
    ]
    issues = [f"缺少 草稿/{name}" for name in required if not (draft_dir / name).is_file()]
    manifest_path = draft_dir / "代码提取清单.json"
    if not manifest_path.is_file():
        return issues
    try:
        manifest = read_json(manifest_path)
    except Exception as exc:
        issues.append(f"草稿/代码提取清单.json 无法读取：{exc}")
        return issues
    outputs = manifest.get("outputs") if isinstance(manifest, dict) else None
    if not isinstance(outputs, list) or not outputs:
        issues.append("草稿/代码提取清单.json 未声明代码 Markdown 输出")
        return issues
    declared = {str(name) for name in outputs}
    known = known_code_drafts()
    try:
        declared_slice = int(manifest.get("slice_pages") or 0)
    except (TypeError, ValueError):
        declared_slice = 0
    if declared_slice > 0:
        known.update(code_split_draft_names(declared_slice))
    invalid = sorted(declared - known)
    if invalid:
        issues.append("代码提取清单包含未知输出：" + "、".join(invalid))
    for name in sorted(declared & known):
        if not (draft_dir / name).is_file():
            issues.append(f"缺少清单声明的 草稿/{name}")
    stale = sorted(name for name in known - declared if (draft_dir / name).exists())
    if stale:
        issues.append("存在与当前代码提取模式冲突的旧草稿：" + "、".join(stale))
    review_path = draft_dir / "操作手册自检记录.json"
    if review_path.is_file():
        try:
            review = read_json(review_path)
            rounds = review.get("rounds") if isinstance(review, dict) else None
            last_issues = rounds[-1].get("issues") if isinstance(rounds, list) and rounds else None
            if isinstance(last_issues, list) and last_issues:
                issues.append("操作手册自检仍有未解决问题：" + "；".join(str(item) for item in last_issues[:5]))
        except Exception as exc:
            issues.append(f"草稿/操作手册自检记录.json 无法读取：{exc}")
    return issues


def count_text_lines(path: Path, skip_blank: bool = True) -> int:
    try:
        text = read_text(path)
    except Exception:
        return 0
    if not text:
        return 0
    if skip_blank:
        return sum(1 for line in text.splitlines() if line.strip())
    return len(text.splitlines())


def is_known_config_file(path: Path) -> bool:
    """Return True for well-known config files that shouldn't count as source code."""
    return path.name in KNOWN_CONFIG_FILES


def looks_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:8192]
    except Exception:
        return True
    if not chunk:
        return False
    if path.suffix.lower() in BINARY_EXTS:
        return True
    if chunk.startswith((b"PK\x03\x04", b"%PDF-", b"\x1f\x8b", b"\x89PNG", b"GIF8")):
        return True
    if chunk.startswith((b"\xff\xfe", b"\xfe\xff", b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        return False
    if b"\x00" in chunk:
        return True
    control_count = sum(1 for byte in chunk if byte < 32 and byte not in {9, 10, 12, 13})
    return control_count / len(chunk) > 0.02


def is_document_candidate(path: Path, project: Path | None = None) -> bool:
    """Return True for explicit or strongly signalled project documentation."""
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix in DOCUMENT_EXTS or name.startswith(DOCUMENT_FILE_PREFIXES):
        return True
    try:
        display_path = Path(rel(path, project)) if project is not None else path
    except ValueError:
        display_path = path
    directory_names = {part.lower() for part in display_path.parent.parts}
    in_document_directory = bool(directory_names & DOCUMENT_DIR_NAMES)
    hinted_name = any(hint in path.stem.lower() for hint in DOCUMENT_NAME_HINTS)
    return (in_document_directory or (hinted_name and suffix not in KNOWN_SOURCE_HINT_EXTS)) and not looks_binary(path)


def is_source_candidate(path: Path) -> bool:
    """Detect readable source without requiring its language extension to be known."""
    if not path.is_file() or is_known_config_file(path):
        return False
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix in DOCUMENT_EXTS | BINARY_EXTS | NON_SOURCE_TEXT_EXTS:
        return False
    if name.startswith(DOCUMENT_FILE_PREFIXES):
        return False
    try:
        size = path.stat().st_size
    except OSError:
        return False
    if size <= 0 or size > MAX_SOURCE_FILE_BYTES or looks_binary(path):
        return False
    try:
        sample = read_text(path, limit=20_000)
    except Exception:
        return False
    if not sample.strip():
        return False
    if any(len(line) > 3000 for line in sample.splitlines()[:80]):
        return False
    return any(char.isalnum() for char in sample)


def iter_source_files(project: Path) -> Iterable[Path]:
    """Yield source candidates using content detection, not an extension allowlist."""
    for path in iter_project_files(project):
        if is_source_candidate(path):
            yield path


def normalize_title(value: str) -> str:
    value = re.sub(r"[-_]+", " ", value).strip()
    value = re.sub(r"\s+", " ", value)
    return value or "待命名软件"


def safe_filename(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    return value or "软件"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
