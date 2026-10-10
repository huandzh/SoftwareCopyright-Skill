# 生成 demo 说明

本目录是一份**按当前 skill 口径完整跑通**的演示产出，用来展示软著申请资料生成后的真实形态。

## 重要提醒

- 目录里的 `模拟项目/` 是**模拟示例源码**，为演示流程专门编写，不是任何真实上线项目，**不得作为软件著作权申请材料提交**。
- `软件著作权申请资料/` 下的草稿与正式资料都由这份模拟源码生成，同样只用于演示。
- 真实使用时，请把 skill 指向你自己的真实项目目录，代码材料必须来自真实源码。

## 目录结构

```text
生成demo/
├── README.md                       本说明
├── 模拟项目/                        模拟示例源码（前端 + 后端 + 需求文档）
└── 软件著作权申请资料/
    ├── 环境检查.md / 环境检查.json
    ├── 环境确认.json
    ├── 软件名称确认.json            软件全称/简称/版本号确认记录
    ├── 截图方式确认.json            本 demo 选择暂不截图
    ├── analysis/project.json        项目分析结果
    ├── 草稿/
    │   ├── 业务理解证据.md / .json
    │   ├── 业务理解模型稿.json      模型撰写的业务理解（含 manual_modules）
    │   ├── 业务理解.md / .json
    │   ├── 代码文件候选清单.md
    │   ├── 代码文件选择.json
    │   ├── 代码-前40页.md
    │   ├── 代码-后40页.md
    │   ├── 代码提取清单.md / .json
    │   ├── 申请表信息.md
    │   ├── 申请表字段答案.json
    │   ├── 申请表字段确认.json
    │   ├── 操作手册.md
    │   ├── 操作手册自检记录.md / .json
    │   └── 最终生成确认.json
    └── 正式资料/
        ├── 申请表信息.txt
        ├── StudioAgent AI视频制片平台软件-代码(前40页).docx
        ├── StudioAgent AI视频制片平台软件-代码(后40页).docx
        ├── StudioAgent AI视频制片平台软件_操作手册.docx
        └── 生成报告.md
```

## 这份 demo 体现了哪些口径

- **软件全称先确认**：`软件名称确认.json` 记录软件全称、简称和版本号，业务理解、申请表、Markdown 确认和正式生成四个环节都会校验一致性；软件名同时用于申请表、正式资料文件名、代码 Word 页眉和操作手册标题与页眉。
- **代码材料前 40 页 + 后 40 页**：官网表单文字写的是前后各 30 页，走中间代理时通常要多提供 20 页，所以默认前后各 40 页（共 80 页），申请表「页数」填 80。两份代码 Word 均由 Word 实测为 40 页，并且**每一页都是满页**（每页 56 行，含最后页）。
- **代码材料移除全部注释**：抽取时按语言删除整行注释、截掉行尾注释，并整段删除 Python 文档字符串（以及其它「整条语句就是一个字符串」的写法）；普通字符串与 URL 中的 `//`、`#` 保留。本例共移除整行注释 188 行、文档字符串/独立字符串语句 171 行、行尾注释 22 处，`代码提取清单.md/json` 中按文件记录；语法解析失败、需要人工复核的文件也会单独列出（本例 0 个）。
- **主要功能按官方模板注记生成**：官网字段要的是 500~1300 字（汉字字符加标点），所以「主要功能口径」默认就是长版、字段内容与「详细版」一致（本例 721 字）；只有表单只收短文本时才改成短版，脚本会按业务理解另写一段 ≤200 字短文本，而不是把长文本截断。
- **技术特点写成「标签；说明」**：本例为「网页应用、人工智能软件；以多智能体协作编排为核心……」，说明 78 字（≤100 字上限，官网注明所列标签不计入这 100 个字符），说明里不写框架或技术栈名称。
- **操作手册按真实页面组织且不超 1 万字**：手册由业务理解里的 `manual_modules` 生成，包含相关文档、说明、功能特点、系统要求、逐模块操作、常见问题解答和术语表；本例按 Word 口径实测 7837 字、9 页，并保留 10 个可见的截图预留位置（本 demo 选择暂不截图）。
- **两道 Word 侧门禁 + 工作目录锁**：正式生成前先抢 `草稿/.workdir.lock`（避免两个会话写同一份材料），生成后用 Word 逐页复核代码材料「每页 ≥50 行、末页也满」并用 Word 实测字数复核操作手册上限，结论直接写进 `生成报告.md`；取不到 Word 时报告会写明「当前环境无法复核」，不会静默通过。

## 复现步骤

```bash
# 1. 环境检查与确认
<python> scripts/check_environment.py --out-dir 软件著作权申请资料
<python> scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage environment --note "<用户确认内容>"

# 2. 定位并分析项目
<python> scripts/analyze_project.py --project 模拟项目 --out 软件著作权申请资料/analysis/project.json

# 3. 软件全称与版本号（最高优先级门禁）
<python> scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage software-name \
  --software-name "StudioAgent AI视频制片平台软件" --version "V0.1.0" --short-name "StudioAgent" --note "<用户确认内容>"

# 4. 业务理解（证据 + 模型稿）
#    模型稿里 technical_characteristics 写官网标签数组，technical_characteristics_note 写 ≤100 字
#    技术特点说明（不写框架/技术栈名称）；脚本会拼成「标签；说明」放进申请表字段。
<python> scripts/generate_business_context.py --project 模拟项目 \
  --analysis 软件著作权申请资料/analysis/project.json \
  --software-name "StudioAgent AI视频制片平台软件" --out-dir 软件著作权申请资料/草稿
<python> scripts/generate_business_context.py --project 模拟项目 \
  --analysis 软件著作权申请资料/analysis/project.json \
  --software-name "StudioAgent AI视频制片平台软件" --out-dir 软件著作权申请资料/草稿 \
  --model-context 软件著作权申请资料/草稿/业务理解模型稿.json
<python> scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage business --note "<用户确认内容>"

# 5. 代码文件选择与抽取（默认前后各 40 页、移除注释）
#    注意：propose_code_selection.py 会重写 代码文件选择.json（selected 一律为 false），
#    所以重跑后要由模型按业务重新填 selected/model_reason，再记录 code-selection 门禁。
<python> scripts/propose_code_selection.py --project 模拟项目 --out-dir 软件著作权申请资料/草稿
<python> scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage code-selection --note "<用户确认内容>"
<python> scripts/extract_code_material.py --project 模拟项目 \
  --analysis 软件著作权申请资料/analysis/project.json \
  --selection 软件著作权申请资料/草稿/代码文件选择.json \
  --software-name "StudioAgent AI视频制片平台软件" --version "V0.1.0" \
  --out-dir 软件著作权申请资料/草稿

# 6. 申请表信息与操作手册
<python> scripts/generate_application_info.py --analysis 软件著作权申请资料/analysis/project.json \
  --code-manifest 软件著作权申请资料/草稿/代码提取清单.json \
  --business-context 软件著作权申请资料/草稿/业务理解.json \
  --answers 软件著作权申请资料/草稿/申请表字段答案.json \
  --software-name "StudioAgent AI视频制片平台软件" --version "V0.1.0" \
  --out-dir 软件著作权申请资料/草稿
<python> scripts/generate_manual_draft.py --analysis 软件著作权申请资料/analysis/project.json \
  --business-context 软件著作权申请资料/草稿/业务理解.json \
  --software-name "StudioAgent AI视频制片平台软件" --version "V0.1.0" \
  --out-dir 软件著作权申请资料/草稿
<python> scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage screenshot-method --method skip --note "暂不截图"
<python> scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage application-fields --note "<用户确认内容>"
<python> scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage markdown --note "<用户确认内容>"

# 7. 正式生成（本 demo 使用固定验证版本 OfficeCLI 1.0.152，无需额外参数；
#    如果你本机是其他版本，请先记录 environment 门禁并加上 --allow-untested-officecli）
<python> scripts/build_docx_from_md.py --workdir 软件著作权申请资料 \
  --software-name "StudioAgent AI视频制片平台软件" --version "V0.1.0" \
  --skip-preview
```

## 选材量与分页的校准记录

代码 Word 的页数由 Word 自己排版决定，抽取阶段的行数只用来决定选多少素材：

- 该版式（A4 + 1.8cm 页边距、8pt 字号、13pt 固定行距）的真实容量是**每页 56 个物理行**：可用高度 29.7 − 1.8×2 = 26.1cm = 739.8pt，739.8 ÷ 13 ≈ 56.9。
- 前后各 40 页各需要 40 × 56 = **2240 行**；本 demo 两份材料实测都是 40 页、每页 56 行（含最后页），Word 段落数 2240。
- 这里踩过一个坑：早期按「每页 55 行」估算时总页数照样是 40 页（页数校验看不出来），但切片是按页边界切的，估小了**最后一页只剩 16 行**，违反「程序每页不少于 50 行」。现在选材按 56 行对齐、切片改按物理行切，生成期再用 Word 逐页复核每页行数，填不满的页直接判定生成失败。
