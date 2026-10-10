#!/usr/bin/env python3
"""Remove source-code comments from extracted code material.

The code material must contain no comments, but it must still be traceable to
the real project source. This module therefore removes comments with a
language-aware scanner instead of blind text replacement:

- whole-line comments are dropped; trailing comments are removed while the rest
  of the line is kept;
- comment markers inside string literals, template literals, regex literals and
  URLs such as ``https://example.com`` are preserved;
- Python docstrings (and any other statement that is only a string literal) are
  removed as well: a bare triple-quoted string is documentation, and in a
  printed listing it reads exactly like a comment, so 代码材料 must not keep it.
  Regular string literals — including triple-quoted strings that are *assigned*
  to a name — are still preserved;
- unknown languages are returned unchanged and reported as unsupported so the
  material is never silently rewritten by a guess.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StripResult:
    """Result of one comment-removal pass."""

    text: str
    supported: bool
    comment_only_lines: int
    inline_comment_lines: int
    # 独立字符串语句（Python 文档字符串/块注释）单独计数，方便登记材料说明口径
    docstring_lines: int = 0
    # Python 语法解析失败时为 True：此时只能保证 # 注释被移除，文档字符串要靠人工复核
    docstring_strip_failed: bool = False


HASH_SUFFIXES = frozenset({
    ".awk",
    ".bash",
    ".cfg",
    ".cmake",
    ".coffee",
    ".conf",
    ".cr",
    ".dockerfile",
    ".env",
    ".ex",
    ".exs",
    ".gd",
    ".gdscript",
    ".gemspec",
    ".ini",
    ".jl",
    ".ksh",
    ".mk",
    ".nix",
    ".pl",
    ".pm",
    ".properties",
    ".ps1",
    ".psm1",
    ".r",
    ".sh",
    ".tcl",
    ".tf",
    ".tfvars",
    ".toml",
    ".yaml",
    ".yml",
    ".zsh",
})

# Python needs its own pass: 三引号字符串 + 独立字符串语句（文档字符串）都要处理。
PYTHON_SUFFIXES = frozenset({".py", ".pyi", ".pyw"})

JS_SUFFIXES = frozenset({".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".ts", ".tsx"})

SLASH_SUFFIXES = frozenset({
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".cxx",
    ".dart",
    ".frag",
    ".glsl",
    ".gml",
    ".go",
    ".gradle",
    ".groovy",
    ".h",
    ".hh",
    ".hlsl",
    ".hpp",
    ".hxx",
    ".java",
    ".kt",
    ".kts",
    ".proto",
    ".rs",
    ".sc",
    ".scala",
    ".sv",
    ".swift",
    ".thrift",
    ".v",
    ".vert",
    ".wgsl",
    ".zig",
})

CSS_SUFFIXES = frozenset({".css"})
STYLE_SUFFIXES = frozenset({".scss", ".less", ".sass", ".styl"})
SQL_SUFFIXES = frozenset({".ddl", ".mysql", ".pgsql", ".psql", ".sql"})
LUA_SUFFIXES = frozenset({".lua"})
PHP_SUFFIXES = frozenset({".php", ".php5", ".php7", ".phtml"})
RUBY_SUFFIXES = frozenset({".rake", ".rb", ".ru"})
JSONC_SUFFIXES = frozenset({".json5", ".jsonc"})
MARKUP_SUFFIXES = frozenset({
    ".astro",
    ".ejs",
    ".erb",
    ".handlebars",
    ".hbs",
    ".htm",
    ".html",
    ".j2",
    ".jinja",
    ".jinja2",
    ".liquid",
    ".mdx",
    ".njk",
    ".php",
    ".php5",
    ".php7",
    ".phtml",
    ".svelte",
    ".svg",
    ".twig",
    ".vue",
    ".xaml",
    ".xhtml",
    ".xml",
})

REGEX_LEADING_CHARS = "=(,:[!&|?{};+-*%~^<>"

REGEX_LEADING_KEYWORDS = re.compile(
    r"(?:^|[^\w$])(?:return|typeof|instanceof|case|in|of|new|delete|void|do|else|yield|await)$"
)

MARKUP_REGION_RE = re.compile(
    r"<!--.*?-->"
    r"|<script\b[^>]*>(?P<script>.*?)</script\s*>"
    r"|<style\b[^>]*>(?P<style>.*?)</style\s*>"
    r"|<\?php(?P<php>.*?)\?>",
    re.S | re.I,
)


def comment_stripping_supported(suffix: str) -> bool:
    return _language(suffix) is not None


def _language(suffix: str) -> str | None:
    suffix = suffix.lower()
    if suffix in MARKUP_SUFFIXES:
        return "markup"
    if suffix in PYTHON_SUFFIXES:
        return "python"
    if suffix in HASH_SUFFIXES:
        return "hash"
    if suffix in JS_SUFFIXES:
        return "js"
    if suffix in SLASH_SUFFIXES:
        return "slash"
    if suffix in CSS_SUFFIXES:
        return "css"
    if suffix in STYLE_SUFFIXES:
        return "style"
    if suffix in SQL_SUFFIXES:
        return "sql"
    if suffix in LUA_SUFFIXES:
        return "lua"
    if suffix in PHP_SUFFIXES:
        return "php"
    if suffix in RUBY_SUFFIXES:
        return "ruby"
    if suffix in JSONC_SUFFIXES:
        return "jsonc"
    return None


def _looks_like_url_scheme(current: list[str]) -> bool:
    """True when ``//`` continues a scheme such as ``https://``."""
    return len(current) >= 2 and current[-1] == ":" and current[-2].isalnum()


def _regex_allowed(current: list[str]) -> bool:
    """Decide whether ``/`` starts a regex literal instead of division."""
    tail = "".join(current).rstrip()
    if not tail:
        return True
    if tail[-1] in REGEX_LEADING_CHARS:
        return True
    return bool(REGEX_LEADING_KEYWORDS.search(tail))


def _scan(
    text: str,
    *,
    line_tokens: tuple[str, ...] = (),
    block_pairs: tuple[tuple[str, str], ...] = (),
    string_delims: tuple[str, ...] = ('"', "'"),
    multiline_delims: tuple[str, ...] = (),
    triple_quotes: bool = False,
    backslash_escapes: bool = True,
    doubled_quote: bool = False,
    regex_literals: bool = False,
    url_guard: bool = False,
    ruby_block: bool = False,
) -> str:
    """Drop comments while keeping string contents and line structure."""
    lines: list[str] = []
    current: list[str] = []
    index = 0
    length = len(text)
    in_block: str | None = None
    in_string: str | None = None
    string_multiline = False

    def flush() -> None:
        lines.append("".join(current).rstrip())
        current.clear()

    while index < length:
        char = text[index]

        if in_block is not None:
            if text.startswith(in_block, index):
                index += len(in_block)
                in_block = None
            else:
                if char == "\n":
                    flush()
                index += 1
            continue

        if in_string is not None:
            if doubled_quote and char == in_string and text.startswith(in_string * 2, index):
                current.append(in_string * 2)
                index += len(in_string) * 2
                continue
            if text.startswith(in_string, index):
                current.append(in_string)
                index += len(in_string)
                in_string = None
                string_multiline = False
                continue
            if backslash_escapes and char == "\\":
                current.append(char)
                if index + 1 < length:
                    current.append(text[index + 1])
                    index += 2
                else:
                    index += 1
                continue
            if char == "\n":
                flush()
                if not string_multiline:
                    in_string = None
                index += 1
                continue
            current.append(char)
            index += 1
            continue

        if char == "\n":
            flush()
            index += 1
            continue

        if ruby_block and not "".join(current).strip() and text.startswith("=begin", index):
            in_block = "=end"
            index += len("=begin")
            continue

        block_started = False
        for start, end in block_pairs:
            if text.startswith(start, index):
                in_block = end
                index += len(start)
                block_started = True
                break
        if block_started:
            continue

        line_comment = False
        for token in line_tokens:
            if not text.startswith(token, index):
                continue
            if url_guard and token == "//" and _looks_like_url_scheme(current):
                continue
            while index < length and text[index] != "\n":
                index += 1
            line_comment = True
            break
        if line_comment:
            continue

        delimiter: str | None = None
        if char in string_delims:
            delimiter = char * 3 if triple_quotes and text.startswith(char * 3, index) else char
        elif char in multiline_delims:
            delimiter = char

        if delimiter is not None:
            in_string = delimiter
            string_multiline = delimiter in multiline_delims or len(delimiter) == 3
            current.append(delimiter)
            index += len(delimiter)
            continue

        if regex_literals and char == "/" and _regex_allowed(current):
            cursor = index + 1
            in_class = False
            closed = False
            while cursor < length and text[cursor] != "\n":
                probe = text[cursor]
                if probe == "\\":
                    cursor += 2
                    continue
                if probe == "[":
                    in_class = True
                elif probe == "]":
                    in_class = False
                elif probe == "/" and not in_class:
                    closed = True
                    break
                cursor += 1
            if closed:
                current.append(text[index : cursor + 1])
                index = cursor + 1
                continue

        current.append(char)
        index += 1

    if current:
        flush()
    result = "\n".join(lines)
    if text.endswith("\n"):
        # Keep the trailing newline so embedded regions never shift the lines
        # that follow them in markup files.
        result += "\n"
    return result


def _scan_markup(text: str) -> str:
    """Strip HTML comments and embedded script/style/php comments."""
    parts: list[str] = []
    position = 0
    for match in MARKUP_REGION_RE.finditer(text):
        parts.append(text[position : match.start()])
        if match.group(0).startswith("<!--"):
            parts.append(re.sub(r"[^\n]", "", match.group(0)))
        else:
            name = next(
                (candidate for candidate in ("script", "style", "php") if match.group(candidate) is not None),
                None,
            )
            if name is None:
                parts.append(match.group(0))
            else:
                inner_start, inner_end = match.span(name)
                parts.append(text[match.start() : inner_start])
                parts.append(_scan_embedded(text[inner_start:inner_end], name))
                parts.append(text[inner_end : match.end()])
        position = match.end()
    parts.append(text[position:])
    return "".join(parts)


def _scan_embedded(inner: str, region: str) -> str:
    if region == "script":
        return _scan(
            inner,
            line_tokens=("//",),
            block_pairs=(("/*", "*/"),),
            multiline_delims=("`",),
            regex_literals=True,
            url_guard=True,
        )
    if region == "style":
        return _scan(inner, block_pairs=(("/*", "*/"),))
    if region == "php":
        return _scan(
            inner,
            line_tokens=("//", "#"),
            block_pairs=(("/*", "*/"),),
            url_guard=True,
        )
    return inner


def _scan_for_language(text: str, language: str) -> str:
    if language == "hash":
        return _scan(text, line_tokens=("#",))
    if language == "js":
        return _scan(
            text,
            line_tokens=("//",),
            block_pairs=(("/*", "*/"),),
            multiline_delims=("`",),
            regex_literals=True,
            url_guard=True,
        )
    if language == "slash":
        return _scan(
            text,
            line_tokens=("//",),
            block_pairs=(("/*", "*/"),),
            url_guard=True,
        )
    if language == "css":
        return _scan(text, block_pairs=(("/*", "*/"),))
    if language == "style":
        return _scan(text, line_tokens=("//",), block_pairs=(("/*", "*/"),), url_guard=True)
    if language == "sql":
        return _scan(
            text,
            line_tokens=("--",),
            block_pairs=(("/*", "*/"),),
            doubled_quote=True,
            backslash_escapes=False,
        )
    if language == "lua":
        return _scan(text, line_tokens=("--",), block_pairs=(("--[[", "]]"),))
    if language == "php":
        return _scan(
            text,
            line_tokens=("//", "#"),
            block_pairs=(("/*", "*/"),),
            url_guard=True,
        )
    if language == "ruby":
        return _scan(text, line_tokens=("#",), ruby_block=True)
    if language == "jsonc":
        return _scan(text, line_tokens=("//",), block_pairs=(("/*", "*/"),), url_guard=True)
    if language == "markup":
        return _scan_markup(text)
    return text


def _python_string_statement_ranges(text: str) -> tuple[list[tuple[int, int, int, int]], bool]:
    """Return ``(ranges, parsed)`` for every statement that is only a string.

    这些语句在打印出来的代码材料里读起来就是注释（模块/类/函数文档字符串，
    以及用独立字符串充当块注释的写法），所以整段删除；``x = \"\"\"...\"\"\"``
    这种真正被使用的字符串不会被算进来（它不是独立的字符串语句）。

    返回的 range 是 ``(起始行, 起始列, 结束行, 结束列)``，行号从 1 开始、
    列号按字符计（``ast`` 给的是 UTF-8 字节偏移，这里换算过）。
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, TypeError, MemoryError):
        return [], False
    lines = text.split("\n")

    def char_offset(line_number: int, byte_offset: int) -> int:
        if not 1 <= line_number <= len(lines):
            return byte_offset
        raw = lines[line_number - 1].encode("utf-8")
        return len(raw[:byte_offset].decode("utf-8", errors="ignore"))

    ranges: list[tuple[int, int, int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        value = node.value
        is_string = (
            isinstance(value, ast.Constant) and isinstance(value.value, str)
        ) or isinstance(value, ast.JoinedStr)
        if not is_string:
            continue
        start_line = getattr(value, "lineno", None)
        end_line = getattr(value, "end_lineno", start_line)
        start_byte = getattr(value, "col_offset", None)
        end_byte = getattr(value, "end_col_offset", None)
        if start_line is None or end_line is None or start_byte is None or end_byte is None:
            continue
        ranges.append(
            (
                start_line,
                char_offset(start_line, start_byte),
                end_line,
                char_offset(end_line, end_byte),
            )
        )
    return ranges, True


def _python_fallback_docstring_ranges(text: str) -> list[tuple[int, int, int, int]]:
    """Best-effort ranges when the file cannot be parsed by this interpreter.

    只处理「整行以三引号开头、以三引号结束（后面最多跟一个 # 注释）」的写法 ——
    也就是文档字符串最常见的形态；解析失败的文件会在清单里单独列出，提醒人工复核。
    """
    lines = text.split("\n")
    ranges: list[tuple[int, int, int, int]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        match = re.match(r"^(?:[rRuUbBfF]{0,2})(\"\"\"|''')", stripped)
        if not match:
            index += 1
            continue
        delimiter = match.group(1)
        start_col = indent + len(match.group(0)) - len(delimiter)
        cursor = index
        search_from = start_col + len(delimiter)
        closing = -1
        while cursor < len(lines):
            position = lines[cursor].find(delimiter, search_from)
            if position != -1:
                closing = position
                break
            cursor += 1
            search_from = 0
        if closing == -1:
            index += 1
            continue
        tail = lines[cursor][closing + len(delimiter) :].strip()
        if tail and not tail.startswith("#"):
            index += 1
            continue
        ranges.append((index + 1, start_col, cursor + 1, closing + len(delimiter)))
        index = cursor + 1
    return ranges


def _remove_ranges(text: str, ranges: list[tuple[int, int, int, int]]) -> str:
    """Remove the given spans while keeping every line break in place."""
    if not ranges:
        return text
    lines = text.split("\n")
    for start_line, start_col, end_line, end_col in sorted(ranges, reverse=True):
        if not 1 <= start_line <= len(lines) or not 1 <= end_line <= len(lines):
            continue
        if start_line == end_line:
            line = lines[start_line - 1]
            lines[start_line - 1] = line[:start_col] + line[end_col:]
            continue
        lines[start_line - 1] = lines[start_line - 1][:start_col]
        for number in range(start_line + 1, end_line):
            lines[number - 1] = ""
        lines[end_line - 1] = lines[end_line - 1][end_col:]
    return "\n".join(lines)


def _blanked_line_count(before: str, after: str) -> int:
    """Number of non-blank lines that the removal turned into blank lines."""
    return sum(
        1
        for old_line, new_line in zip(before.splitlines(), after.splitlines())
        if old_line.strip() and not new_line.strip()
    )


def _strip_python(text: str) -> tuple[str, int, bool]:
    """Remove docstrings/block strings and ``#`` comments from Python source."""
    ranges, parsed = _python_string_statement_ranges(text)
    if not parsed:
        ranges = _python_fallback_docstring_ranges(text)
    without_docstrings = _remove_ranges(text, ranges)
    docstring_lines = _blanked_line_count(text, without_docstrings)
    # 三引号识别必须打开：否则文档字符串里的 # 会被当成注释，字符串里的内容会被截断。
    stripped = _scan(without_docstrings, line_tokens=("#",), triple_quotes=True)
    return stripped, docstring_lines, not parsed


def _count_changes(before: str, after: str) -> tuple[int, int]:
    comment_only = 0
    inline = 0
    for old_line, new_line in zip(before.splitlines(), after.splitlines()):
        old_stripped = old_line.strip()
        new_stripped = new_line.strip()
        if not old_stripped:
            continue
        if not new_stripped:
            comment_only += 1
        elif old_stripped != new_stripped:
            inline += 1
    return comment_only, inline


def strip_source_comments(text: str, suffix: str) -> StripResult:
    """Return ``text`` without comments when the language syntax is known."""
    language = _language(suffix)
    if language is None or not text.strip():
        return StripResult(
            text=text,
            supported=language is not None,
            comment_only_lines=0,
            inline_comment_lines=0,
        )
    docstring_lines = 0
    docstring_failed = False
    if language == "python":
        stripped, docstring_lines, docstring_failed = _strip_python(text)
    else:
        stripped = _scan_for_language(text, language)
    comment_only, inline = _count_changes(text, stripped)
    if docstring_lines:
        # 被文档字符串整行吃掉的行已经单独计数，不重复算进「整行注释」
        comment_only = max(0, comment_only - docstring_lines)
    return StripResult(
        text=stripped,
        supported=True,
        comment_only_lines=comment_only,
        inline_comment_lines=inline,
        docstring_lines=docstring_lines,
        docstring_strip_failed=docstring_failed,
    )
