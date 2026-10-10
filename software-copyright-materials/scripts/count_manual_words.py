#!/usr/bin/env python3
"""Count an operation manual's length the way Word counts it.

Word 的中文「字数」把**中文标点也算进去**（实测：汉字 21,132 的稿子在 Word 里
显示 23,447 字，差 11%），而草稿里每个截图预留位的提示文字在生成 DOCX 时会被
图片替换掉、不计入最终字数（本次 17 处共 585 字）。所以：

* 草稿期用 :func:`estimate_markdown` 估算「Word 会报多少字」；
* 生成后用 :func:`measure_docx` 直接读 Word 的实测值，写进生成报告。

``Word 字数 ≈ 汉字 + 中文标点 + 英文/数字词``
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import code_layout

HAN_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z0-9]+")
CJK_PUNCT_RE = re.compile(r"[\u3000-\u303f\uff00-\uffef]")
PLACEHOLDER_RE = re.compile(r"【截图预留：[^】]*】")

MANUAL_WORD_LIMIT = 10_000


def estimate_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    han = len(HAN_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    punctuation = len(CJK_PUNCT_RE.findall(text))
    placeholders = PLACEHOLDER_RE.findall(text)
    placeholder_words = sum(
        len(HAN_RE.findall(item)) + len(LATIN_RE.findall(item)) + len(CJK_PUNCT_RE.findall(item))
        for item in placeholders
    )
    total = han + latin + punctuation
    return {
        "file": str(path),
        "han": han,
        "latin_words": latin,
        "cjk_punctuation": punctuation,
        "estimated_word_count": total,
        "placeholder_count": len(placeholders),
        "placeholder_words": placeholder_words,
        "estimated_word_count_without_placeholders": total - placeholder_words,
        "limit": MANUAL_WORD_LIMIT,
        "within_limit": total - placeholder_words <= MANUAL_WORD_LIMIT,
    }


def measure_docx(path: Path) -> dict[str, Any]:
    data = code_layout.word_stats(path)
    data["limit"] = MANUAL_WORD_LIMIT
    if data.get("available"):
        words = int(data.get("words") or 0)
        data["word_count"] = words
        data["within_limit"] = words <= MANUAL_WORD_LIMIT
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="按 Word 口径统计操作手册字数")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--md", help="操作手册 Markdown 草稿")
    group.add_argument("--docx", help="生成好的操作手册 DOCX")
    parser.add_argument("--limit", type=int, default=MANUAL_WORD_LIMIT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.md:
        result = estimate_markdown(Path(args.md))
    else:
        result = measure_docx(Path(args.docx))
    result["limit"] = args.limit
    if "word_count" in result:
        result["within_limit"] = result["word_count"] <= args.limit
    elif "estimated_word_count_without_placeholders" in result:
        result["within_limit"] = result["estimated_word_count_without_placeholders"] <= args.limit

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.md:
        print(
            f"{Path(args.md).name}：汉字 {result['han']} + 中文标点 {result['cjk_punctuation']} + "
            f"英文词 {result['latin_words']} = Word 估算 {result['estimated_word_count']} 字"
        )
        print(
            f"截图预留 {result['placeholder_count']} 处（{result['placeholder_words']} 字，生成时会被图片替换），"
            f"生成后约 {result['estimated_word_count_without_placeholders']} 字，"
            f"上限 {args.limit} 字：{'通过' if result['within_limit'] else '超出'}"
        )
    else:
        if result.get("available"):
            print(
                f"{Path(args.docx).name}：Word 实测 {result['word_count']} 字、{result['pages']} 页，"
                f"上限 {args.limit} 字：{'通过' if result['within_limit'] else '超出'}"
            )
        else:
            print(f"{Path(args.docx).name}：无法取得 Word 字数（{result.get('reason')}）")
            return 1
    return 0 if result.get("within_limit", True) else 2


if __name__ == "__main__":
    sys.exit(main())
