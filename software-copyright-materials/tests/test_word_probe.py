from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import code_layout  # noqa: E402
import count_manual_words  # noqa: E402


class ParseOutputTests(unittest.TestCase):
    def test_noisy_output_still_yields_the_json_envelope(self) -> None:
        text = 'warning: something\n{"success": true, "pages": 40}\ndone\n'

        payload = code_layout._parse_json(text)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["pages"], 40)

    def test_non_json_output_returns_none(self) -> None:
        self.assertIsNone(code_layout._parse_json("no json here"))


class ProbeAvailabilityTests(unittest.TestCase):
    def test_without_powershell_probe_reports_unavailable(self) -> None:
        with patch("code_layout.powershell_host", return_value=None):
            data = code_layout.probe(Path("whatever.docx"), mode="layout")

        self.assertFalse(data["available"])
        self.assertIn("PowerShell", data["reason"])

    def test_layout_check_without_word_passes_but_says_so(self) -> None:
        with patch("code_layout.probe", return_value={"available": False, "reason": "没装 Word"}):
            ok, messages, _ = code_layout.verify_code_layout(Path("front.docx"), expected_pages=40)

        self.assertTrue(ok)
        self.assertIn("无法用 Word 复核每页行数", messages[0])


class LayoutGateTests(unittest.TestCase):
    def _probe(self, pages: int, per_page: list[int]) -> dict:
        return {
            "available": True,
            "pages": pages,
            "perPage": per_page,
            "minPageLines": min(per_page),
            "maxPageLines": max(per_page),
            "lastPageLines": per_page[-1],
        }

    def test_full_pages_pass(self) -> None:
        with patch("code_layout.probe", return_value=self._probe(40, [56] * 40)):
            ok, messages, _ = code_layout.verify_code_layout(Path("front.docx"), expected_pages=40)

        self.assertTrue(ok)
        self.assertIn("末页 56 行", messages[0])

    def test_last_page_almost_empty_fails_even_when_page_count_matches(self) -> None:
        # 实测缺陷：总页数 40 页全绿，第 40 页只有 16 行
        per_page = [56] * 39 + [16]
        with patch("code_layout.probe", return_value=self._probe(40, per_page)):
            ok, messages, _ = code_layout.verify_code_layout(Path("front.docx"), expected_pages=40)

        self.assertFalse(ok)
        self.assertTrue(any("不足 50 行" in message for message in messages))

    def test_page_count_mismatch_fails(self) -> None:
        with patch("code_layout.probe", return_value=self._probe(41, [56] * 41)):
            ok, messages, _ = code_layout.verify_code_layout(Path("front.docx"), expected_pages=40)

        self.assertFalse(ok)
        self.assertTrue(any("与文件名要求的 40 页不符" in message for message in messages))


class ManualWordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parent / ".tmp-manual-words"
        self.root.mkdir(exist_ok=True)
        self.path = self.root / "操作手册.md"

    def tearDown(self) -> None:
        self.path.unlink(missing_ok=True)
        self.root.rmdir()

    def test_estimate_counts_punctuation_and_skips_placeholders(self) -> None:
        self.path.write_text(
            "# 标题\n\n正文，带标点。\n\n【截图预留：请在此处插入\"示例\"页面或操作结果截图。】\n",
            encoding="utf-8",
        )

        result = count_manual_words.estimate_markdown(self.path)

        self.assertEqual(result["placeholder_count"], 1)
        self.assertGreater(result["placeholder_words"], 0)
        self.assertGreater(result["cjk_punctuation"], 0)
        self.assertEqual(
            result["estimated_word_count"] - result["placeholder_words"],
            result["estimated_word_count_without_placeholders"],
        )

    def test_manual_gate_uses_the_word_measurement(self) -> None:
        with patch("code_layout.probe", return_value={"available": True, "words": 9607, "pages": 21}):
            within = count_manual_words.measure_docx(Path("manual.docx"))
        with patch("code_layout.probe", return_value={"available": True, "words": 10001, "pages": 22}):
            over = count_manual_words.measure_docx(Path("manual.docx"))

        self.assertTrue(within["within_limit"])
        self.assertFalse(over["within_limit"])


if __name__ == "__main__":
    unittest.main()
