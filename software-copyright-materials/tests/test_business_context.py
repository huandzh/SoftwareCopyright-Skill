from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import TECHNICAL_CHARACTERISTIC_LIMIT  # noqa: E402
from generate_business_context import normalize_model_context, write_model_template  # noqa: E402


EVIDENCE = {"software_name": "演示软件", "documents": []}


def minimal_model(**overrides):
    """A model draft that satisfies every field normalize_model_context requires."""
    model = {
        "product_positioning": "面向内容创作者的视频制作平台。",
        "industry": "数字内容创作",
        "target_users": ["内容创作者"],
        "core_value": "把多步骤视频制作集中在一个项目工作区。",
        "business_features": ["项目工作区"],
        "business_feature_details": {"项目工作区": "新建、查看和管理视频项目。"},
        "operation_flow": ["新建项目", "填写创意描述", "生成成片"],
        "application_purpose": "降低视频创作门槛并让过程与成本可追踪",
        "main_functions": "功" * 600,
        "main_functions_short": "",
        "technical_characteristics": ["网页应用", "人工智能软件"],
        "software_technical_option": "应用软件",
        "software_category": "应用软件",
        "manual_modules": [
            {
                "title": "项目工作区",
                "purpose": "集中管理一次视频制作。",
                "usage": "创作者整理自己的项目时。",
                "entry": "登录后进入项目列表。",
                "operation_steps": ["点击新建项目", "填写创意描述"],
                "feedback": ["新项目出现在项目列表顶部"],
            }
        ],
        "system_requirements": [
            {"item": "操作系统", "minimum": "Windows 10", "recommended": "Windows 11"}
        ],
        "faq": [{"question": "如何新建项目？", "answer": "在项目列表点击新建项目。"}],
        "glossary": [{"term": "项目", "definition": "一次视频制作任务。"}],
    }
    model.update(overrides)
    return model


class BusinessContextNoteTests(unittest.TestCase):
    def test_model_note_flows_into_the_business_context(self) -> None:
        note = "以多智能体协作编排为核心：自然语言指令按制作阶段路由到对应角色智能体，生成过程持续反馈并可中断，素材按项目归集、成本按调用项统计。"
        context = normalize_model_context(
            minimal_model(technical_characteristics_note=note), EVIDENCE, ""
        )
        # generate_application_info 读的就是这个键，缺了它「标签；说明」形同虚设。
        self.assertEqual(context["technical_characteristics_note"], note)
        self.assertEqual(context["technical_characteristics"], "网页应用、人工智能软件")

    def test_missing_model_note_stays_empty(self) -> None:
        context = normalize_model_context(minimal_model(), EVIDENCE, "")
        self.assertEqual(context["technical_characteristics_note"], "")

    def test_model_note_over_the_official_limit_is_rejected(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            normalize_model_context(
                minimal_model(technical_characteristics_note="说" * (TECHNICAL_CHARACTERISTIC_LIMIT + 1)),
                EVIDENCE,
                "",
            )
        self.assertIn("technical_characteristics_note", str(caught.exception))

    def test_model_note_naming_a_stack_is_rejected(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            normalize_model_context(
                minimal_model(technical_characteristics_note="前端使用 React 构建界面，后端使用 Python。"),
                EVIDENCE,
                "",
            )
        self.assertIn("react", str(caught.exception))

    def test_model_template_asks_for_the_note(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "业务理解模型稿模板.json"
            write_model_template(path, {"software_name": "演示软件"})
            text = path.read_text(encoding="utf-8")
        self.assertIn("technical_characteristics_note", text)
        self.assertIn("不要写框架/技术栈名称", text)


if __name__ == "__main__":
    unittest.main()
