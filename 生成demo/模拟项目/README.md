# StudioAgent AI 视频制片平台（模拟示例项目）

> **模拟源码说明**：本目录下的源码是为了演示软著申请资料生成流程而编写的**模拟示例代码**，
> 不是任何真实上线项目的代码，**不得作为软件著作权申请材料提交**。
> 真实使用时，请把 skill 指向你自己的真实项目目录。

## 这是什么

一个用于演示的 AI 视频制片平台示例：创作者用一句创意描述创建项目，平台由多个智能体协作完成
剧本分析、分镜规划、视觉素材生成、视频合成、配音和音效设计，最后导出成片。

## 目录结构

```text
模拟项目/
├── frontend/            Next.js + React + TypeScript 前端
│   ├── app/             页面（项目列表、工作区、素材库、计费、登录）
│   ├── components/      对话面板、智能体状态、候选素材、资产面板等组件
│   ├── hooks/           数据请求与 SSE 对话流
│   ├── lib/             接口封装、类型定义与格式化工具
│   ├── store/           项目状态管理
│   └── styles/          全局样式
├── backend/             FastAPI + SQLAlchemy + Celery 后端
│   ├── app/api/         REST 接口（项目、对话、素材、计费、登录）
│   ├── app/models/      数据模型
│   ├── app/schemas/     请求与响应模型
│   ├── app/services/    智能体编排、视频合成、图片生成、语音与成本服务
│   └── app/workers/     异步生成与清理任务
└── docs/                产品需求与总体设计说明（供业务理解取证）
```

## 本地运行（示例命令，仅用于说明）

```bash
cd frontend && npm install && npm run dev
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
```

## 提醒

模拟源码仅用于演示资料生成效果；软著申请材料中的代码必须来自真实项目。
