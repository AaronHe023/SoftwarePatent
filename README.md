# 面向大语言模型的模态逻辑推理数据集构建与评测系统 V1.0

本项目用于软件著作权申请演示，基于需求文档实现一个中文界面的模态逻辑题库、数据集构建与大语言模型评测系统。

## 技术栈

- 前端：Vue 3 + Vite
- 后端：Python + FastAPI
- 数据库：SQLite
- LLM调用：兼容 OpenAI Chat Completions 格式，可配置 `base_url`、`api_key`、`model_name`

## 目录结构

```text
backend/          FastAPI后端服务
database/         SQLite初始化脚本和运行时数据库
frontend/         Vue 3前端工作台
docs/             软著申请辅助说明
RequirementDoc.docx
```

## 后端启动

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后访问：

- 健康检查：http://127.0.0.1:8000/api/health
- API文档：http://127.0.0.1:8000/docs

首次启动会自动创建默认管理员：

- 用户名：`admin`
- 密码：`admin123`

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

默认前端地址：http://127.0.0.1:5173

如果后端不是 `http://127.0.0.1:8000`，可通过环境变量配置：

```powershell
$env:VITE_API_BASE="http://127.0.0.1:8000/api"
npm run dev
```

## 功能覆盖

- 用户注册、登录、退出、修改密码、管理员后台
- 题目生成、手动录入、CSV/JSON导入、筛选、确认、增删改查
- 数据集创建、确认题目加入、统计概览、JSON导出
- Prompt模板管理，内置 Zero-shot、CoT、Few-shot 模板
- 多模型、多策略批量评测，进度查看，中途取消
- 总体准确率、分类准确率、模型/策略对比、单题输出明细
- 评测报告 JSON/CSV 导出

## 演示模式

题目生成和评测均支持无 API Key 的演示模式：

- 生成题目时不填写 `api_key/base_url/model_name`，系统会生成示例草稿题。
- 发起评测时不填写 `api_key/base_url`，系统会用题库标准答案生成演示输出。

这便于软著申请截图和本地流程演示；真实评测时填写兼容 OpenAI API 的模型配置即可。

