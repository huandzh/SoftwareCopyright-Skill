# OfficeCLI DOCX 后端

## 固定版本与边界

- 已验证版本：`1.0.152`。
- 官方发布页：https://github.com/iOfficeAI/OfficeCLI/releases/tag/v1.0.152
- 本仓库不复制 OfficeCLI 源码或二进制；OfficeCLI 继续按其 Apache-2.0 许可证独立分发。
- OfficeCLI 必须全局安装，不下载到被分析项目、本 skill 或输出目录，也不使用项目内 `工具/` 文件夹保存二进制。
- Python 保留项目分析、业务草稿、代码选择、物理行折行、选材量估算和门禁逻辑；OfficeCLI 负责 DOCX 创建、编辑、校验和预览，最终分页由 Word 排版引擎自动完成。
- 运行时设置 `OFFICECLI_SKIP_UPDATE=1` 和 `OFFICECLI_NO_AUTO_RESIDENT=1`，避免版本漂移、后台文件锁和延迟落盘。

## 全局安装与检测

Windows PowerShell 使用官方安装命令：

```powershell
irm https://raw.githubusercontent.com/iOfficeAI/OfficeCLI/main/install.ps1 | iex
```

官方脚本默认安装到 `%LOCALAPPDATA%\OfficeCLI` 并写入用户 PATH。安装完成后，必须重启 Codex，让新进程读取更新后的 PATH；重启后运行 `officecli --version` 和环境检查，再继续工作流。不得要求用户设置 `OFFICECLI_PATH`，不得通过 `--officecli` 指定项目内或任意文件夹中的可执行文件。

运行时只从当前进程 PATH 查找全局 `officecli` / `officecli.exe`。如果 Windows 官方安装目录中已有二进制、但当前进程 PATH 尚未识别，环境检查必须报告“需要重启 Codex”并停止，不得把该文件当作项目便携版直接绕过重启。

版本缺失或不等于 `1.0.152`（当前固定验证版本）时，环境检查必须停止。只有用户明确接受兼容性风险后，正式生成才允许传入 `--allow-untested-officecli`。

`--allow-untested-officecli` 会长期保留，不是临时开关：固定验证版本只是本项目验证过的那一个，其他人完全可能在自己环境里使用更高或更低的版本。使用该参数时必须同时满足：

- 先记录 `environment` 门禁，把「使用的是未验证版本」写进确认说明；
- 生成报告与 `环境检查.json/md` 会如实记录实际版本号，便于回溯；
- 该版本仍必须通过 OpenXML 结构校验、主题字体校验和 Word 真实页数校验，任何一项不过都按失败处理，不能因为"版本未经验证"就放宽校验。

## 写入策略

- 每个 DOCX 先 `create --force --locale zh-CN`，再用一个原子 `batch --stop-on-error` 写入主要内容。
- A4、页边距、默认字体、黑色文字、页眉和页码全部写入文档，不依赖模板文件。
- 主要内容完成后读取 `/theme`，把 major/minor 的拉丁、东亚和复杂文字字体统一为 Times New Roman / SimSun，再通过 OfficeCLI `raw-set` 整体替换主题根节点；不使用 Python 直接改写 DOCX 压缩包。
- 页眉左侧为软件全称和版本号，右侧为 PAGE 字段。
- 操作手册先展开 OfficeCLI Markdown 子集，再统一设置中文正文格式；本地 Markdown 图片会通过 picture 元素嵌入。用户选择截图时，生成脚本读取 `截图/截图清单.json`，按清单顺序把可用图片依次替换到可见截图预留位置，再由 OfficeCLI 插入 Word；图片不足时保留未匹配提示，图片过多、缺失或格式不支持时写入生成报告。远程图片仍保留可见提示。
- 代码材料不使用 Word 自动行号。抽取脚本先按最多 90 显示列折行（全角字符按 2 列），正文使用 8pt 字号和 13pt 固定行距，并按每页 **56 个物理行**（该版式 A4 + 1.8cm 页边距的真实容量：26.1cm = 739.8pt ÷ 13pt = 56.9）对齐前后 N 页的选材量（默认 `N = 40`，可用 `--slice-pages 30` 切换）。★ 这个值不能取保守估计：切片按页边界切，估小了不会少页，但最后页会几乎空白（实测 2026-10-10 按 55 行/页选材，40 页文档的第 40 页只有 16 行，违反“程序每页不少于 50 行”）。抽取阶段默认移除全部注释（整行删除、行尾截掉、Python 文档字符串整段删除，普通字符串与 URL 保留），清单记录每个文件移除的注释数量。每个物理行写成一个固定行距段落，所有段落连续流入正文，不设置 `pageBreakBefore`；Word 根据页面可用高度自动换页，OfficeCLI 再读取真实页数。
- 正式生成只读取当前 `代码提取清单.json` 的 `outputs`，并按 `slice_pages` 推导代码 DOCX 文件名。重新抽取或生成时清理同一软件名下与当前模式冲突的旧代码草稿和旧代码 DOCX（含 30 页与 40 页两套），避免“前后 40 页”“前后 30 页”和“全部代码”同时残留。

## Word 占用与残留实例（★ 实测踩过）

OfficeCLI 取页数、Word COM 取每页行数都会拉起隐藏的 `WINWORD.exe`；它**可能残留**并占住交付文件，表现为下一次操作报「Word 无法保存此文件，因为它已在别处打开」。处置约定：

1. **一切复核都在副本上做**。`word_docx_probe.ps1`、`fill_application_form.ps1` 都先 `Copy-Item` 再 `Documents.Open`，交付文件本身不打开、不写入（Word 会顺带改字段缓存与时间戳，实测交付 docx 的字节数因此与报告记录不一致）。
2. **清理只清自己新建的实例**：记录调用前的 `WINWORD` pid 列表，结束时只 `Stop-Process` 「不在 baseline 且没有窗口标题」的那些。用户可见的 Word 一律不碰——它可能开着别的文档。
3. **交付文件被占用时不要硬写**：提示用户关闭，或另存为新文件名，并在报告里说明；不要为了写入而结束用户的 Word。
4. **`预览未生成` 不是结构失败**：无头浏览器（crashpad）偶发不可用，重试一次仍失败就记进生成报告即可，不要因此判定材料不合格。
5. **报告里的文件大小以最后一次 `stat` 为准**：生成流程结束后 OfficeCLI/Word 仍可能回写 docx，报告中的字节数只作参考。

## 两道 Word 侧复核

OfficeCLI 只回答「总页数」，回答不了「每页是不是都填满了」；中文「字数」也只有 Word 给得出。所以生成脚本额外调用两个探针（同一份 PowerShell 后端 `word_docx_probe.ps1`）：

| 脚本 | 作用 | 失败处理 |
| --- | --- | --- |
| `code_layout.py --docx <代码docx> --mode layout --expected-pages 40` | 逐页读物理行数，断言「总页数 == 文件名页数」且「每页 ≥50 行」 | 生成失败，要求重新校准选材量 |
| `count_manual_words.py --docx <操作手册docx>` | 读 Word 实测字数，上限 1 万字 | 生成失败（确有需要时加 `--allow-long-manual`） |

两个脚本在非 Windows / 没有 PowerShell / 没装 Word 时返回 `available: false` 与原因，由调用方写进生成报告，**不静默通过**。

## 工作目录锁

抽取与生成都会写 `草稿/.workdir.lock`（pid + 主机 + 开始时间 + 命令行）。发现锁的主人仍在运行时直接停止，避免两个会话互相覆盖材料（实测：另一个会话在同一 workdir 重跑构建，复核期间文件被重写、报告字节数与磁盘不一致）。查看与清理：

```bash
<PYTHON> "<SKILL_DIR>/scripts/workdir_lock.py" --workdir 软件著作权申请资料 --status
<PYTHON> "<SKILL_DIR>/scripts/workdir_lock.py" --workdir 软件著作权申请资料 --clear
```

## 校验策略

1. `officecli validate <file> --json`：OpenXML 结构错误必须为 0，否则生成失败。
2. 重新读取 `/theme`，确认六个主题字体槽均为 Times New Roman / SimSun，避免 WPS 因默认的 Calibri、Calibri Light、等线主题字体提示缺失字体。
3. `officecli view <file> issues --json`：内容/格式提示写入生成报告，不能把它误当成结构校验。
4. Windows 且安装 Microsoft Word 时，对代码材料执行 `view stats --page-count --json`，把自动分页后的真实页数写入报告。Markdown 页分组只代表选材估算；但代码文档的 Word 实际页数必须等于文件名中的页数（默认前 40 页/后 40 页，`--slice-pages 30` 时为 30 页），否则正式生成失败并要求重新校准选材量。
5. 生成全页联系表预览用于快速目检。OfficeCLI 的 HTML 渲染不能替代 Word/WPS 的最终分页复核。

用户确认会记录内容指纹。业务理解、代码选择、申请表或最终草稿被修改后，正式生成必须拒绝沿用旧确认，待用户重新核对并记录对应门禁。

## 常用命令

```bash
officecli --version
officecli validate output.docx --json
officecli view output.docx issues --json
officecli view output.docx stats --page-count --json
officecli view output.docx screenshot --grid auto --render auto -o preview.png
```
