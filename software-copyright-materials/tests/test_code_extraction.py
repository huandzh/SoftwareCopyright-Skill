from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import (  # noqa: E402
    CODE_SLICE_PAGE_CHOICES,
    CODE_SLICE_PAGES_DEFAULT,
    code_docx_name,
    code_output_slice_pages,
    code_split_draft_names,
    known_code_drafts,
)
from extract_code_material import extract  # noqa: E402


class CodeSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parent / ".tmp-code-slice"
        self.project = self.root / "项目"
        self.out_dir = self.root / "草稿"
        (self.project / "src").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def write_source(self, lines: int) -> None:
        body = [f"export const value{index} = {index};" for index in range(lines)]
        (self.project / "src" / "main.ts").write_text("\n".join(body) + "\n", encoding="utf-8")

    def write_selection(self) -> Path:
        selection = self.out_dir / "代码文件选择.json"
        selection.parent.mkdir(parents=True, exist_ok=True)
        selection.write_text(
            json.dumps(
                {
                    "selection_required": True,
                    "user_confirmed": True,
                    "files": [{"path": "src/main.ts", "selected": True, "model_reason": "入口文件"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return selection

    def test_default_slice_is_forty_pages_per_half(self) -> None:
        self.assertEqual(CODE_SLICE_PAGES_DEFAULT, 40)
        self.assertEqual(CODE_SLICE_PAGE_CHOICES, (30, 40))

    def test_default_extraction_writes_front_and_back_forty_pages(self) -> None:
        self.write_source(6000)
        selection = self.write_selection()

        manifest = extract(self.project, self.out_dir, "示例软件", "V1.0", 55, selection)

        self.assertEqual(manifest["slice_pages"], 40)
        self.assertEqual(manifest["mode"], "front40_back40")
        self.assertEqual(manifest["submitted_page_count"], 80)
        self.assertEqual(manifest["outputs"], ["代码-前40页.md", "代码-后40页.md"])
        front = (self.out_dir / "代码-前40页.md").read_text(encoding="utf-8")
        back = (self.out_dir / "代码-后40页.md").read_text(encoding="utf-8")
        self.assertIn("## 第 40 页", front)
        self.assertNotIn("## 第 41 页", front)
        self.assertIn("## 第 41 页", back)

    def test_thirty_page_mode_replaces_stale_forty_page_drafts(self) -> None:
        self.write_source(4000)
        selection = self.write_selection()
        self.out_dir.mkdir(parents=True, exist_ok=True)
        stale = self.out_dir / "代码-前40页.md"
        stale.write_text("# stale\n", encoding="utf-8")

        manifest = extract(
            self.project, self.out_dir, "示例软件", "V1.0", 55, selection, slice_pages=30
        )

        self.assertEqual(manifest["mode"], "front30_back30")
        self.assertEqual(manifest["submitted_page_count"], 60)
        self.assertFalse(stale.exists())
        self.assertTrue((self.out_dir / "代码-前30页.md").is_file())
        self.assertTrue((self.out_dir / "代码-后30页.md").is_file())

    def test_comments_are_removed_from_extracted_material(self) -> None:
        body = ["// 文件级注释", "const inner = '// not a comment'; // trailing"]
        body.extend(f"export const value{index} = {index};" for index in range(6000))
        (self.project / "src" / "main.ts").write_text("\n".join(body) + "\n", encoding="utf-8")
        selection = self.write_selection()

        manifest = extract(self.project, self.out_dir, "示例软件", "V1.0", 55, selection)

        comments = manifest["comment_stripping"]
        self.assertTrue(comments["enabled"])
        self.assertEqual(comments["comment_only_lines"], 1)
        self.assertEqual(comments["inline_comment_lines"], 1)
        material = (self.out_dir / "代码-前40页.md").read_text(encoding="utf-8")
        self.assertNotIn("文件级注释", material)
        self.assertNotIn("trailing", material)
        self.assertIn("'// not a comment'", material)

    def test_keep_comments_flag_preserves_source_comments(self) -> None:
        body = ["// kept comment", "const inner = 1;"]
        body.extend(f"export const value{index} = {index};" for index in range(6000))
        (self.project / "src" / "main.ts").write_text("\n".join(body) + "\n", encoding="utf-8")
        selection = self.write_selection()

        manifest = extract(
            self.project, self.out_dir, "示例软件", "V1.0", 55, selection, keep_comments=True
        )

        self.assertFalse(manifest["comment_stripping"]["enabled"])
        material = (self.out_dir / "代码-前40页.md").read_text(encoding="utf-8")
        self.assertIn("// kept comment", material)

    def test_draft_and_docx_names_follow_the_slice_setting(self) -> None:
        self.assertEqual(code_split_draft_names(40), ("代码-前40页.md", "代码-后40页.md"))
        self.assertEqual(code_split_draft_names(30), ("代码-前30页.md", "代码-后30页.md"))
        self.assertEqual(
            known_code_drafts(),
            {"代码-前30页.md", "代码-后30页.md", "代码-前40页.md", "代码-后40页.md", "代码-全部.md"},
        )
        self.assertEqual(code_docx_name("代码-前40页.md", "示例软件"), "示例软件-代码(前40页).docx")
        self.assertEqual(code_docx_name("代码-全部.md", "示例软件"), "示例软件-代码(全部).docx")
        self.assertIsNone(code_docx_name("操作手册.md", "示例软件"))
        self.assertEqual(code_output_slice_pages("示例软件-代码(后40页).docx"), 40)
        self.assertEqual(code_output_slice_pages("示例软件-代码(前30页).docx"), 30)
        self.assertIsNone(code_output_slice_pages("示例软件-代码(全部).docx"))


if __name__ == "__main__":
    unittest.main()
