# 改进说明文档

**软件名称**：面向大语言模型的模态逻辑推理数据集构建与评测系统 V1.0
**改进版本目录**：`Claude-made/`
**原始版本目录**：`backend/` / `frontend/`

本文档逐条说明在原始版本基础上实施的全部功能改进，包括改进描述、涉及文件及与原版的对比差异，供软件著作权申请备查。

---

## 后端改进

### 1. 题目列表分页（Pagination for Question List）

**涉及文件**：`Claude-made/backend/app/main.py`

**改进描述**：
原版 `GET /api/questions` 将当前用户的所有题目一次性返回为 JSON 数组，当题目数量增多时响应体积增大，对前端渲染和网络传输均不友好。

改进版新增 `page`（默认 1）和 `page_size`（默认 20，最大 500）查询参数，响应结构由数组改为包含分页元信息的对象：

```json
{
  "items": [...],
  "total": 142,
  "page": 2,
  "page_size": 20,
  "total_pages": 8
}
```

同时新增 `_build_question_filters()` 辅助函数，将过滤条件构建逻辑提取为可复用模块，供列表、导出、统计三个接口共享，消除代码重复。

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 响应格式 | `[{...}, {...}]` 数组 | `{ items, total, page, page_size, total_pages }` |
| 分页支持 | 无 | 有（`page` / `page_size` 参数） |
| 过滤逻辑 | 内联在函数体 | 提取为 `_build_question_filters()` 复用 |

---

### 2. 题目批量导出（Bulk Export for Questions）

**涉及文件**：`Claude-made/backend/app/main.py`

**改进描述**：
新增 `GET /api/questions/export` 接口，支持将当前用户题目按筛选条件导出为 **JSON** 或 **CSV** 格式文件。

- 支持与题目列表相同的全部过滤参数（`modal_type`、`difficulty`、`logic_system`、`review_status`、`q`）
- `format=json` 返回格式化 JSON 文件；`format=csv` 返回带 BOM 的 UTF-8 CSV 文件
- 响应头设置 `Content-Disposition: attachment` 触发浏览器下载
- 复用 `_build_question_filters()` 保持过滤逻辑一致

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 题目导出 | 无 | 支持 JSON / CSV 格式导出 |
| 过滤联动 | N/A | 导出遵循当前筛选条件 |

---

### 3. 题目统计接口（Question Statistics Endpoint）

**涉及文件**：`Claude-made/backend/app/main.py`

**改进描述**：
新增 `GET /api/questions/stats` 接口，通过 SQL `GROUP BY` 一次性返回当前用户题目的多维度分类统计：

```json
{
  "total": 142,
  "by_modal_type": { "认知模态": 38, "道义模态": 35, ... },
  "by_difficulty": { "easy": 51, "medium": 48, "hard": 43 },
  "by_logic_system": { "K": 30, "T": 28, "S4": 42, "S5": 42 },
  "by_review_status": { "draft": 89, "confirmed": 53 }
}
```

前端 Hub 首页统计卡片和图表均调用此接口，无需加载全量题目即可展示分布信息。

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 题目统计 | 无专用接口 | `GET /api/questions/stats` |
| 实现方式 | 前端遍历全量数组 | 后端 GROUP BY SQL，高效 |

---

### 4. 批量确认题目（Batch Confirm Questions）

**涉及文件**：`Claude-made/backend/app/main.py`

**改进描述**：
新增 `POST /api/questions/batch-confirm` 接口，接收题目 ID 数组，将其中属于当前用户且处于草稿状态的题目批量改为"已确认"状态：

```json
// 请求体
{ "question_ids": [1, 5, 7, 12] }

// 响应体
{ "confirmed": 3, "ids": [1, 5, 7], "skipped": [12] }
```

- 逐条执行所有权校验，非本用户题目记入 `skipped` 而非抛错
- 原有单条确认接口 `PUT /api/questions/{id}` 保持不变

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 批量确认 | 无 | `POST /api/questions/batch-confirm` |
| 安全校验 | N/A | 逐条验证所有权，不可越权 |

---

### 5. 管理员活动日志（Admin Activity Log）

**涉及文件**：`Claude-made/backend/app/main.py`

**改进描述**：
新增 `GET /api/admin/activity-log` 接口（仅管理员可访问），无需新建数据库表，基于现有 `questions`、`datasets`、`eval_tasks` 三张表的 `created_at` 字段，在 Python 层合并为统一事件流：

```json
[
  { "type": "question", "username": "alice", "description": "创建了题目《在 K 系统中…》", "time": "2025-03-15T10:23:00" },
  { "type": "dataset", "username": "bob",   "description": "生成了数据集《认知模态测试集》", "time": "2025-03-15T09:51:00" }
]
```

- 支持 `limit` 参数（默认 20）
- 三类事件使用不同颜色点区分（前端实现）

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 活动日志 | 无 | `GET /api/admin/activity-log` |
| 新增表 | N/A | 不需要，复用现有表 |

---

### 6. 演示题库扩充（Demo Question Pool Expansion）

**涉及文件**：`Claude-made/backend/app/llm.py`

**改进描述**：
原版演示模式（无 LLM API Key 时的回退）仅包含 2–3 道固定题目，每次生成都返回相同内容，演示效果单调。

改进版将演示题库扩充至 **20 道**题目，覆盖全部 4 种模态类型（认知、道义、时态、真值）× 3 种难度（easy/medium/hard）× 2 种题型（判断题/单选题）的完整组合矩阵。`generate_questions()` 函数按请求的分类参数从题库中优先精确匹配，再按模态类型匹配，最终回退到全库随机抽取，确保每次演示结果具有多样性。

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 演示题数量 | 2–3 道 | 20 道 |
| 题型覆盖 | 部分类型 | 全部 4 类型 × 3 难度 × 2 题型 |
| 随机性 | 无（固定返回） | 有（按参数匹配后随机抽取） |

---

### 7. 答案解析增强（Enhanced Answer Parsing）

**涉及文件**：`Claude-made/backend/app/llm.py`

**改进描述**：
原版依赖简单的正则表达式从 LLM 输出中提取答案，对格式变体（大小写、中文词、括号形式）覆盖不足，解析失败时静默处理。

改进版新增独立的 `_parse_answer(raw, question_type)` 函数，按优先级依次尝试以下匹配策略：

1. 大小写不敏感 `true/false` 匹配
2. 中文词识别：`真/假/对/错/正确/错误`
3. 括号内字母提取：`(A)` / `（A）`（含全角括号）
4. 自然语言模式：`答案是 A`、`答案为 True`
5. 单字母/单词兜底

解析失败时返回 `(None, "无法从 LLM 输出中提取答案")` 元组，`error_message` 字段会向前端传递失败原因，便于调试。

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 解析策略 | 单一正则 | 5 级优先级匹配链 |
| 中文支持 | 无 | 真/假/对/错等中文词 |
| 括号形式 | 不支持 | `(A)` / `（A）` 全角半角 |
| 失败处理 | 静默（空字符串） | 返回错误原因到前端 |

---

## 前端改进

### 8. 题目列表分页控件（Pagination Controls）

**涉及文件**：`Claude-made/frontend/src/App.vue`、`Claude-made/frontend/src/styles.css`

**改进描述**：
在题目管理页底部新增分页导航控件，包含首页（«）、上页（‹）、当前页/总页数文字、下页（›）、末页（»）五个元素，以及"共 N 题"提示。

行为设计：
- 切换筛选条件时自动重置到第 1 页（`applyFilters()` 函数）
- 管理员使用 `page_size=500` 加载所有题目（保持管理员功能完整性）
- 普通用户使用 `page_size=20` 分页加载
- 兼容旧版数组格式响应（向下兼容）

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 分页 | 无 | 有（首/上/页码/下/末页控件） |
| 筛选联动 | N/A | 切换筛选自动回第 1 页 |

---

### 9. 报告页条形图（Bar Charts in Reports）

**涉及文件**：`Claude-made/frontend/src/App.vue`、`Claude-made/frontend/src/styles.css`

**改进描述**：
在评测报告页的分类准确率区块，为每个模态类型的题目准确率增加水平条形图可视化。使用纯 CSS 实现（CSS 自定义属性 `--bar-w` + `@keyframes growBar` 宽度增长动画），**无需引入 Chart.js 等外部依赖**。

- 条形宽度由内联 `style="--bar-w: XX%"` 驱动
- 加载时触发从 0 增长到目标宽度的动画（0.6s ease-out）
- 旁边显示百分比数字标签

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 准确率可视化 | 纯文字数字 | 水平条形图 + 动画 |
| 外部依赖 | 无 | 仍无（纯 CSS 实现） |

---

### 10. 批量操作（Bulk Actions）

**涉及文件**：`Claude-made/frontend/src/App.vue`、`Claude-made/frontend/src/styles.css`

**改进描述**：
题目表格每行左侧新增复选框，选中后页面底部浮现操作栏（使用 Vue `<transition>` + CSS `position: fixed` 实现）：

- **批量确认**：调用后端新接口 `POST /api/questions/batch-confirm`
- **批量删除**：顺序调用现有单条 `DELETE /api/questions/{id}` 接口
- **全选/取消全选**：表头复选框切换当前页全选状态
- 操作栏显示已选数量；操作完成后自动清空选择并刷新列表
- 选中状态用 `Set<number>` 管理，响应性与性能均优于数组

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 批量操作 | 无 | 复选框 + 浮出操作栏 |
| 选中状态管理 | N/A | `Set<number>`（高效去重） |
| 操作栏动画 | N/A | `bulkSlideUp` 入场动画 |

---

### 11. 题目预览弹窗（Question Preview Modal）

**涉及文件**：`Claude-made/frontend/src/App.vue`、`Claude-made/frontend/src/styles.css`

**改进描述**：
点击题目标题（`q-title-link` 样式）弹出全屏 Modal，格式化展示题目完整内容：

- 前提列表（每条独立行）
- 题目正文
- 选项列表（单选题）
- 答案徽章（`answer-badge` 样式，青色渐变药丸）
- 解释文本
- 元信息：模态类型、逻辑系统、难度、状态

弹窗底部提供"关闭"和"前往编辑"按钮；使用 Vue 3 `<Teleport to="body">` 确保遮罩层正确渲染在文档最顶层，避免 `z-index` 层叠问题。

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 题目预览 | 无（需展开行内详情） | 弹窗（完整格式化展示） |
| 遮罩渲染 | N/A | `<Teleport to="body">` |
| 答案展示 | 纯文字 | 青色渐变徽章 |

---

### 12. 一键复制题目（Duplicate Question）

**涉及文件**：`Claude-made/frontend/src/App.vue`

**改进描述**：
题目操作区新增"复制"按钮，调用现有 `POST /api/questions` 接口，自动将标题加上"（副本）"后缀，其余字段（前提、题干、选项、答案等）原样复制，新题目以草稿状态创建。

复制成功后：
1. 刷新题目列表
2. 将 `newItemId` 设为新题目 ID
3. 新题目行触发 `row-highlight` CSS 动画（2.2 秒青色背景渐出）

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 复制题目 | 无 | 一键复制（自动加"（副本）"） |
| 新条目高亮 | 无 | `highlightNew` 2.2s 动画 |

---

### 13. 键盘快捷键（Keyboard Shortcuts）

**涉及文件**：`Claude-made/frontend/src/App.vue`

**改进描述**：
通过全局 `keydown` 事件监听实现两个快捷键：

- **`Escape`**：关闭题目预览弹窗（`closePreview()`）
- **`Ctrl + Enter`**：提交当前激活页面的表单（生成题目 / 手动录入 / 评测配置均适用）

监听器在 `onMounted` 时注册，在 `onUnmounted` 时移除，无内存泄漏风险。

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 键盘快捷键 | 无 | Esc（关弹窗）/ Ctrl+Enter（提交） |
| 内存安全 | N/A | `onUnmounted` 移除监听器 |

---

### 14. Hub 首页增强（Enhanced Hub Dashboard）

**涉及文件**：`Claude-made/frontend/src/App.vue`、`Claude-made/frontend/src/styles.css`

**改进描述**：
Hub 首页统计卡片的题目分布展示从静态数字改为动态数据驱动：

**普通用户**：
- 调用 `GET /api/questions/stats` 接口，将难度分布（easy/medium/hard）以带颜色标记的数据行展示
- 统计卡片数字（总题数、已确认、草稿）均来自统计接口，无需遍历题目数组

**管理员**：
- 额外显示"最近活动"时间线（3 条），来自 `GET /api/admin/activity-log` 接口
- 三种事件类型（question/dataset/eval_task）用不同颜色的圆点（`activity-dot`）区分
- 时间显示为本地化时间格式

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 题目分布 | 静态或缺失 | 动态（来自统计接口） |
| 活动日志 | 无 | 管理员可见时间线 |

---

### 15. 题目导出按钮（Export Buttons in UI）

**涉及文件**：`Claude-made/frontend/src/App.vue`、`Claude-made/frontend/src/api.js`

**改进描述**：
题目管理页标题栏新增"导出 JSON"和"导出 CSV"两个按钮，调用 `exportQuestions(filters, format)` 函数，将当前筛选条件传递给后端导出接口，触发文件下载。`api.js` 中的 `download()` 工具函数通过创建临时 `<a>` 元素实现浏览器侧文件保存。

**与原版对比**：
| 维度 | 原版 | 改进版 |
|------|------|--------|
| 题目导出 UI | 无 | "导出 JSON" / "导出 CSV" 按钮 |
| 筛选联动 | N/A | 导出遵循当前活跃筛选条件 |

---

## 新增 CSS 组件（styles.css）

**涉及文件**：`Claude-made/frontend/src/styles.css`

原版 CSS 已有完整的设计系统（深色/浅色主题、CSS 自定义属性、响应式布局）。改进版在不修改原有样式的基础上新增以下组件：

| 组件 | 类名 | 说明 |
|------|------|------|
| 分页控件 | `.pagination`、`.pagination button` | flex 行，带 hover/disabled 状态 |
| 批量操作浮出栏 | `.bulk-action-bar` | `position: fixed; bottom: 24px`，`bulkSlideUp` 入场动画 |
| 行复选框 | `.row-check`、`.check-cell` | `accent-color: var(--cyan)` |
| 新条目高亮 | `.row-highlight`、`@keyframes highlightNew` | 2.2s 青色背景渐出 |
| 题目预览弹窗 | `.question-modal-overlay`、`.question-modal` | 全屏遮罩 + 居中卡片，`overlayIn`/`modalIn` 动画 |
| 答案徽章 | `.answer-badge` | 青色渐变药丸形标签 |
| 报告条形图 | `.report-chart-section`、`.chart-bar-row`、`.chart-bar-track`、`.chart-bar-fill` | CSS `--bar-w` 变量驱动宽度，`growBar` 动画 |
| 活动日志时间线 | `.activity-log`、`.activity-item`、`.activity-dot.question/.dataset/.eval_task` | 彩色圆点时间线 |
| 可点击标题 | `.q-title-link` | hover 下划线，cursor pointer |
| Vue 过渡 | `.bulk-slide-enter-active`、`.bulk-slide-leave-active` | 批量操作栏进出场过渡 |

新增 `@keyframes`：`overlayIn`、`modalIn`、`bulkSlideUp`、`highlightNew`（原版已有 `growBar` 通过 CSS 变量复用）。

---

## 新增 API 封装（api.js）

**涉及文件**：`Claude-made/frontend/src/api.js`

在原版 `api.js`（封装了基础 `api()` / `download()` 函数）基础上，新增 5 个业务接口封装函数：

| 函数 | 对应接口 | 说明 |
|------|----------|------|
| `fetchQuestionsPage(filters, page, pageSize)` | `GET /questions` | 分页获取题目列表 |
| `exportQuestions(filters, format)` | `GET /questions/export` | 触发题目文件下载 |
| `fetchQuestionStats()` | `GET /questions/stats` | 获取题目分类统计 |
| `batchConfirmQuestions(ids)` | `POST /questions/batch-confirm` | 批量确认草稿题目 |
| `fetchActivityLog(limit)` | `GET /admin/activity-log` | 获取管理员活动日志 |

---

## 改进总览

| # | 改进项 | 类型 | 涉及文件 |
|---|--------|------|----------|
| 1 | 题目列表分页 | 后端 | `backend/app/main.py` |
| 2 | 题目批量导出接口 | 后端 | `backend/app/main.py` |
| 3 | 题目统计接口 | 后端 | `backend/app/main.py` |
| 4 | 批量确认题目接口 | 后端 | `backend/app/main.py` |
| 5 | 管理员活动日志接口 | 后端 | `backend/app/main.py` |
| 6 | 演示题库扩充（20 道） | 后端 | `backend/app/llm.py` |
| 7 | 答案解析增强（5 级策略） | 后端 | `backend/app/llm.py` |
| 8 | 前端分页控件 | 前端 | `frontend/src/App.vue`、`styles.css` |
| 9 | 报告页条形图（纯 CSS） | 前端 | `frontend/src/App.vue`、`styles.css` |
| 10 | 批量操作栏（批量确认/删除） | 前端 | `frontend/src/App.vue`、`styles.css` |
| 11 | 题目预览弹窗 | 前端 | `frontend/src/App.vue`、`styles.css` |
| 12 | 一键复制题目 | 前端 | `frontend/src/App.vue` |
| 13 | 键盘快捷键（Esc / Ctrl+Enter） | 前端 | `frontend/src/App.vue` |
| 14 | Hub 首页增强（统计图 + 活动日志） | 前端 | `frontend/src/App.vue`、`styles.css` |
| 15 | 题目导出按钮 | 前端 | `frontend/src/App.vue`、`api.js` |

**零新外部依赖**：所有前端改进均在现有 Vue 3 + Vite 技术栈内实现，未引入 Chart.js、D3 或其他第三方库。
