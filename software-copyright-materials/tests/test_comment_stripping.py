from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from code_comments import comment_stripping_supported, strip_source_comments  # noqa: E402


class CommentStrippingTests(unittest.TestCase):
    def strip(self, text: str, suffix: str) -> str:
        return strip_source_comments(text, suffix).text

    def test_typescript_comments_are_removed_but_strings_are_kept(self) -> None:
        source = (
            "// upload helper\n"
            "const endpoint = \"https://api.example.com/v1/upload\"; // keep the URL\n"
            "const label = 'a // b # c';\n"
            "/* block\n"
            "   comment */\n"
            "export function upload() {\n"
            "  return endpoint;\n"
            "}\n"
        )

        stripped = self.strip(source, ".ts")

        self.assertNotIn("upload helper", stripped)
        self.assertNotIn("keep the URL", stripped)
        self.assertNotIn("block", stripped)
        self.assertIn("https://api.example.com/v1/upload", stripped)
        self.assertIn("'a // b # c'", stripped)
        self.assertIn("export function upload()", stripped)

    def test_template_literals_and_regex_literals_keep_their_slashes(self) -> None:
        source = (
            "const tpl = `prefix // not a comment`;\n"
            "const url = `https://example.com//path`;\n"
            "const re = /a\\/\\/b/;\n"
            "const ratio = total / count; // real trailing comment\n"
        )

        stripped = self.strip(source, ".js")

        self.assertIn("`prefix // not a comment`", stripped)
        self.assertIn("`https://example.com//path`", stripped)
        self.assertIn("/a\\/\\/b/", stripped)
        self.assertIn("const ratio = total / count;", stripped)
        self.assertNotIn("real trailing comment", stripped)

    def test_python_comments_are_removed_and_strings_including_docstrings_survive(self) -> None:
        source = (
            "#!/usr/bin/env python3\n"
            "\"\"\"Module docstring.\"\"\"\n"
            "def build():\n"
            "    marker = \"# not a comment\"  # real comment\n"
            "    # whole line comment\n"
            "    return marker\n"
        )

        stripped = self.strip(source, ".py")

        self.assertNotIn("whole line comment", stripped)
        self.assertNotIn("real comment", stripped)
        self.assertNotIn("/usr/bin/env", stripped)
        self.assertIn('"""Module docstring."""', stripped)
        self.assertIn('"# not a comment"', stripped)

    def test_sql_comments_and_escaped_quotes(self) -> None:
        source = (
            "-- report query\n"
            "SELECT 'it''s fine' AS label, /* inline */ 1 AS flag -- trailing\n"
            "FROM t;\n"
        )

        stripped = self.strip(source, ".sql")

        self.assertNotIn("report query", stripped)
        self.assertNotIn("inline", stripped)
        self.assertNotIn("trailing", stripped)
        self.assertIn("'it''s fine'", stripped)

    def test_css_and_scss_rules(self) -> None:
        css = "/* theme */\n.a { color: red; }\n"
        scss = "// theme\n.a { color: red; } // trailing\n"

        self.assertEqual(self.strip(css, ".css"), "\n.a { color: red; }\n")
        self.assertEqual(self.strip(scss, ".scss"), "\n.a { color: red; }\n")

    def test_vue_single_file_component_strips_every_region(self) -> None:
        source = (
            "<template>\n"
            "  <!-- template comment -->\n"
            "  <div :title=\"'// keep'\">{{ title }}</div>\n"
            "</template>\n"
            "<script setup lang=\"ts\">\n"
            "// script comment\n"
            "const title = 'Home';\n"
            "</script>\n"
            "<style scoped>\n"
            "/* style comment */\n"
            ".title { font-weight: 600; }\n"
            "</style>\n"
        )

        stripped = self.strip(source, ".vue")

        self.assertNotIn("template comment", stripped)
        self.assertNotIn("script comment", stripped)
        self.assertNotIn("style comment", stripped)
        self.assertIn("'// keep'", stripped)
        self.assertIn("const title = 'Home';", stripped)
        self.assertIn(".title { font-weight: 600; }", stripped)

    def test_html_text_urls_are_not_treated_as_comments(self) -> None:
        source = "<p>see http://example.com/docs</p>\n<!-- hidden -->\n"
        stripped = self.strip(source, ".html")

        self.assertIn("http://example.com/docs", stripped)
        self.assertNotIn("hidden", stripped)

    def test_c_preprocessor_and_comments(self) -> None:
        source = "#include <stdio.h> // header\nint main() { /* body */ return 0; }\n"
        stripped = self.strip(source, ".c")

        self.assertIn("#include <stdio.h>", stripped)
        self.assertNotIn("header", stripped)
        self.assertNotIn("body", stripped)

    def test_unknown_language_is_left_untouched_and_reported(self) -> None:
        source = "// not a known language\nvalue = 1\n"
        result = strip_source_comments(source, ".futurelang")

        self.assertEqual(result.text, source)
        self.assertFalse(result.supported)
        self.assertFalse(comment_stripping_supported(".futurelang"))
        self.assertTrue(comment_stripping_supported(".ts"))

    def test_markup_stripping_preserves_line_count_and_structure(self) -> None:
        source = (
            "<template>\n"
            "  <!-- gone -->\n"
            "  <div>ok</div>\n"
            "</template>\n"
            "<script setup>\n"
            "// gone\n"
            "const a = 1;\n"
            "</script>\n"
            "<style>\n"
            "/* gone */\n"
            ".a { color: red; }\n"
            "</style>\n"
        )

        stripped = self.strip(source, ".vue")

        self.assertEqual(len(stripped.splitlines()), len(source.splitlines()))
        self.assertIn("<div>ok</div>", stripped)
        self.assertIn("const a = 1;", stripped)
        self.assertIn(".a { color: red; }", stripped)
        self.assertIn("</script>", stripped)
        self.assertIn("</style>", stripped)

    def test_comment_counts_describe_removed_lines(self) -> None:
        source = "// one\nconst a = 1; // trailing\nconst b = 2;\n"
        result = strip_source_comments(source, ".ts")

        self.assertEqual(result.comment_only_lines, 1)
        self.assertEqual(result.inline_comment_lines, 1)
        self.assertEqual(result.text, "\nconst a = 1;\nconst b = 2;\n")


if __name__ == "__main__":
    unittest.main()
