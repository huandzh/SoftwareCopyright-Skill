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
- **代码材料前 40 页 + 后 40 页**：官网表单文字写的是前后各 30 页，走中间代理时通常要多提供 20 页，所以默认前后各 40 页（共 80 页），申请表「页数」填 80。两个代码 Word 均由 Word 实测为 40 页。
- **代码材料移除全部注释**：抽取时按语言删除整行注释、截掉行尾注释，字符串与 URL 中的 `//`、`#` 保留。本例共移除整行注释 188 行、行尾注释 22 处，`代码提取清单.md/json` 中按文件记录。
- **主要功能双口径**：官网字段按 200 字以内生成（本例 107 字），同时保留 500~1300 字「软件的主要功能（详细版）」（本例 723 字），表单要求长文本时把「主要功能口径」改为长版。
- **技术特点只选标签**：本例为「网页应用、人工智能软件」，不写框架或技术栈描述。
- **操作手册按真实页面组织**：手册由业务理解里的 `manual_modules` 生成，包含相关文档、说明、功能特点、系统要求、逐模块操作、常见问题解答和术语表；未提供截图时保留可见的截图预留位置。

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
<python> scripts/generate_business_context.py --project 模拟项目 \
  --analysis 软件著作权申请资料/analysis/project.json \
  --software-name "StudioAgent AI视频制片平台软件" --out-dir 软件著作权申请资料/草稿
<python> scripts/generate_business_context.py --project 模拟项目 \
  --analysis 软件著作权申请资料/analysis/project.json \
  --software-name "StudioAgent AI视频制片平台软件" --out-dir 软件著作权申请资料/草稿 \
  --model-context 软件著作权申请资料/草稿/业务理解模型稿.json
<python> scripts/confirm_stage.py --workdir 软件著作权申请资料 --stage business --note "<用户确认内容>"

# 5. 代码文件选择与抽取（默认前后各 40 页、移除注释）
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

## 选材量的校准记录

代码 Word 的页数由 Word 自己排版决定，抽取阶段的「每页 55 行」只用于估算。本机实测 Word 每页可容纳约 56 行，因此：

- 前 40 页文档需要 2200 行（40 × 55），实测正好 40 页；
- 后 40 页文档由 39 个满页加最后一页组成，最后一页不足时 Word 会少排一页。第一次生成时尾页只有 13 行，实测 39 页；补足源码后尾页为 55 行，总计 2200 行，实测 40 页。

这份记录说明 `生成报告.md` 里「Word 自动分页为 40 页」是 Word 真实排版结果，不是脚本估算值。
