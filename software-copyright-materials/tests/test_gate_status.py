from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import (  # noqa: E402
    confirmation_payload_sha256,
    draft_snapshot,
)
from confirm_stage import gate_status  # noqa: E402


class GateStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parent / ".tmp-gate-status"
        if self.root.exists():
            shutil.rmtree(self.root)
        (self.root / "草稿").mkdir(parents=True)
        self.write_json(
            self.root / "软件名称确认.json",
            {"software_name": "示例软件", "version": "V1.0", "software_name_confirmed": True},
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        payload["confirmed_at"] = "2026-01-01T00:00:00+00:00"
        payload["confirmation_note"] = "测试"
        payload["confirmed_content_sha256"] = confirmation_payload_sha256(payload)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def rows(self) -> dict[str, dict]:
        return {row["stage"]: row for row in gate_status(self.root)}

    def test_missing_gates_are_reported_with_the_reconfirm_command(self) -> None:
        row = self.rows()["markdown"]

        self.assertEqual(row["state"], "missing")
        self.assertIn("--stage markdown", row["command"])

    def test_confirmed_gate_is_ok(self) -> None:
        self.assertEqual(self.rows()["software-name"]["state"], "ok")

    def test_editing_a_draft_after_confirmation_reports_which_file_changed(self) -> None:
        manual = self.root / "草稿" / "操作手册.md"
        manual.write_text("第一版\n", encoding="utf-8")
        self.write_json(
            self.root / "草稿" / "最终生成确认.json",
            {"markdown_confirmed": True, "draft_file_sha256": draft_snapshot(self.root)},
        )
        # 这个最小工作目录里业务理解等草稿并不齐，所以 markdown 可能是 ok 也可能是 blocked；
        # 关键是「确认之后又改了草稿」必须被发现。
        self.assertIn(self.rows()["markdown"]["state"], {"ok", "blocked"})

        manual.write_text("改过一版\n", encoding="utf-8")

        row = self.rows()["markdown"]
        self.assertEqual(row["state"], "stale")
        self.assertTrue(any("草稿/操作手册.md" in reason for reason in row["reasons"]))

    def test_application_md_change_is_reported_for_the_fields_gate(self) -> None:
        app_md = self.root / "草稿" / "申请表信息.md"
        app_md.write_text("➤软件全称：示例软件\n", encoding="utf-8")
        from common import file_sha256

        self.write_json(
            self.root / "草稿" / "申请表字段确认.json",
            {"application_fields_confirmed": True, "application_md_sha256": file_sha256(app_md)},
        )
        self.assertEqual(self.rows()["application-fields"]["state"], "ok")

        app_md.write_text("➤软件全称：示例软件\n➤版本号：V1.0\n", encoding="utf-8")

        row = self.rows()["application-fields"]
        self.assertEqual(row["state"], "stale")
        self.assertTrue(any("申请表信息.md" in reason for reason in row["reasons"]))


if __name__ == "__main__":
    unittest.main()
