#!/usr/bin/env python3
"""Remove source-code comments from extracted code material.

The code material must contain no comments, but it must still be traceable to
the real project source. This module therefore removes comments with a
language-aware scanner instead of blind text replacement:

- whole-line comments are dropped; trailing comments are removed while the rest
  of the line is kept;
- comment markers inside string literals, template literals, regex literals and
  URLs such as ``https://example.com`` are preserved;
- unknown languages are returned unchanged and reported as unsupported so the
  material is never silently rewritten by a guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StripResult:
    """Result of one comment-removal pass."""

    text: str
    supported: bool
    comment_only_lines: int
    inline_comment_lines: int


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
    ".py",
    ".pyi",
    ".pyw",
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
    stripped = _scan_for_language(text, language)
    comment_only, inline = _count_changes(text, stripped)
    return StripResult(
        text=stripped,
        supported=True,
        comment_only_lines=comment_only,
        inline_comment_lines=inline,
    )
