# API接口概览

统一前缀：`/api`

## 用户与权限

- `POST /auth/register`：注册普通用户。
- `POST /auth/login`：登录并返回令牌。
- `GET /auth/me`：获取当前用户。
- `POST /auth/change-password`：修改密码。
- `GET /admin/users`：管理员查看用户列表。
- `GET /admin/overview`：管理员查看系统概览。

## 题目

- `GET /questions`：题目列表，支持模态类型、逻辑系统、难度、格式、状态、来源筛选。
- `POST /questions`：手动创建题目。
- `POST /questions/generate`：调用LLM或演示模式生成草稿题目。
- `POST /questions/import`：导入CSV或JSON题目。
- `PUT /questions/{id}`：更新题目。
- `POST /questions/{id}/confirm`：确认题目。
- `DELETE /questions/{id}`：删除题目。

## 数据集

- `GET /datasets`：数据集列表。
- `POST /datasets`：创建数据集。
- `GET /datasets/{id}`：数据集详情和统计。
- `POST /datasets/{id}/questions`：加入已确认题目。
- `DELETE /datasets/{id}/questions/{question_id}`：移除题目。
- `GET /datasets/{id}/export`：导出标准JSON。

## 模板与评测

- `GET /prompt-templates`：模板列表。
- `POST /prompt-templates`：创建模板。
- `PUT /prompt-templates/{id}`：修改自定义模板。
- `DELETE /prompt-templates/{id}`：删除自定义模板。
- `GET /eval-tasks`：历史评测任务。
- `POST /eval-tasks`：创建并启动评测任务。
- `GET /eval-tasks/{id}`：评测详情、预测明细和报告。
- `POST /eval-tasks/{id}/cancel`：取消任务。
- `GET /eval-tasks/{id}/export?format=json|csv`：导出报告。
