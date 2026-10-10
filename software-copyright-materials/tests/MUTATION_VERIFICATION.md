# 门禁变异验证记录

规矩：**新增门禁必须做变异验证** —— 把它对应的旧行为改回去（或把阈值收紧到已知不满足），
确认它真的变红，并把结果记在这里。永远绿的守护比没有守护更糟：它会让人以为已经查过了。

## 2026-10-10 一批（真实项目 survey-invalid-tool）

| # | 门禁 | 变异方式 | 结果 |
| --- | --- | --- | --- |
| M1 | `tests/test_code_extraction.py::test_slices_carry_full_pages_even_when_material_tail_is_partial` | 把前后切片改回「按预切页分组切」（`pages[:slice_pages]` / `pages[-slice_pages:]`） | ✅ 该测试失败：`代码-后40页.md` 末组只有 55→不满 56 行（复现真实缺陷） |
| M2 | `tests/test_comment_stripping.py` 的文档字符串用例 | 把 Python 分支改回「只删 `#`、不删独立字符串语句」 | ✅ `test_python_comments_and_docstrings_are_removed_while_strings_survive` 失败（docstring 残留） |
| M3 | `tests/test_workflow_integrity.py::test_generated_application_defaults_to_the_long_main_function` | 把 `MAIN_FUNCTION_DEFAULT_MODE` 改回短版 | ✅ 该测试失败：口径显示「短版（≤200字）」而要求长版 |
| M4 | `scripts/code_layout.py`（每页行数门禁） | `--min-lines 60`（真实材料 56 行/页） | ✅ 退出码 1，输出「存在不足 60 行的页（最少 56 行，末页 56 行）」 |
| M5 | `scripts/count_manual_words.py`（手册字数门禁） | `--limit 9000`（真实手册 9607 字） | ✅ 退出码 2，输出「Word 实测 9607 字…超出」 |
| M6 | `scripts/workdir_lock.py`（并发锁） | 持锁状态下再次 `acquire()`；另用死 pid 造陈旧锁 | ✅ 前者 `SystemExit`「正被另一个会话写入」；后者打印「发现陈旧锁，已接管」并写入新锁（见 `tests/test_workdir_lock.py`） |

## 2026-10-10 补记（阈值守卫）

| # | 门禁 | 变异方式 | 结果 |
| --- | --- | --- | --- |
| M7 | `tests/test_officecli_builder.py::test_code_layout_thresholds_stay_consistent_with_the_capacity` | 把 `code_layout.MIN_CODE_LINES_PER_PAGE` 从 50 改成 60（超过版式真实容量 56） | ✅ 该测试失败：`AssertionError: 60 not less than or equal to 56`；改回 50 后恢复 OK |
| M8 | `tests/test_business_context.py`（技术特点说明透传） | 从 `normalize_model_context` 的输出里删掉 `technical_characteristics_note` | ✅ 2 个用例报 `KeyError: 'technical_characteristics_note'`（说明 D 组口径只靠 `generate_application_info.py` 是接不上的）；补回后恢复 OK |

复现命令（M4/M5 依赖 Windows + Microsoft Word）：

```bash
python scripts/code_layout.py --docx "<代码docx>" --mode layout --expected-pages 40 --min-lines 60
python scripts/count_manual_words.py --docx "<操作手册docx>" --limit 9000
python -m unittest discover -s tests
```
