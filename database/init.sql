CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  premises TEXT NOT NULL DEFAULT '[]',
  question_text TEXT NOT NULL,
  options TEXT NOT NULL DEFAULT '[]',
  answer TEXT NOT NULL,
  question_type TEXT NOT NULL CHECK (question_type IN ('true_false', 'multiple_choice')),
  modal_type TEXT NOT NULL,
  logic_system TEXT NOT NULL,
  modal_depth INTEGER NOT NULL,
  difficulty TEXT NOT NULL CHECK (difficulty IN ('single_step', 'multi_step', 'nested')),
  source TEXT NOT NULL CHECK (source IN ('llm_generated', 'manual', 'imported')),
  explanation TEXT,
  review_status TEXT NOT NULL DEFAULT 'draft' CHECK (review_status IN ('draft', 'confirmed')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS datasets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dataset_questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dataset_id INTEGER NOT NULL,
  question_id INTEGER NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  UNIQUE(dataset_id, question_id),
  FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
  FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prompt_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  name TEXT NOT NULL,
  strategy_type TEXT NOT NULL CHECK (strategy_type IN ('zero_shot', 'cot', 'few_shot')),
  template_content TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eval_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  dataset_id INTEGER NOT NULL,
  task_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'cancelled', 'failed')),
  total_questions INTEGER NOT NULL DEFAULT 0,
  finished_questions INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eval_task_models (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  eval_task_id INTEGER NOT NULL,
  model_name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  FOREIGN KEY (eval_task_id) REFERENCES eval_tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eval_task_strategies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  eval_task_id INTEGER NOT NULL,
  strategy_type TEXT NOT NULL,
  prompt_template_id INTEGER,
  FOREIGN KEY (eval_task_id) REFERENCES eval_tasks(id) ON DELETE CASCADE,
  FOREIGN KEY (prompt_template_id) REFERENCES prompt_templates(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS eval_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  eval_task_id INTEGER NOT NULL,
  question_id INTEGER NOT NULL,
  model_name TEXT NOT NULL,
  strategy_type TEXT NOT NULL,
  prompt_text TEXT NOT NULL,
  raw_output TEXT,
  parsed_answer TEXT,
  gold_answer TEXT NOT NULL,
  is_correct INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'skipped')),
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (eval_task_id) REFERENCES eval_tasks(id) ON DELETE CASCADE,
  FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eval_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  eval_task_id INTEGER NOT NULL,
  model_name TEXT,
  strategy_type TEXT,
  group_type TEXT NOT NULL CHECK (group_type IN ('overall', 'modal_type', 'logic_system', 'difficulty', 'question_type', 'model', 'strategy')),
  group_name TEXT NOT NULL,
  total INTEGER NOT NULL,
  correct INTEGER NOT NULL,
  accuracy REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (eval_task_id) REFERENCES eval_tasks(id) ON DELETE CASCADE
);

INSERT OR IGNORE INTO prompt_templates (id, user_id, name, strategy_type, template_content)
VALUES
  (1, NULL, 'Zero-shot默认模板', 'zero_shot', '请判断以下模态逻辑推理是否正确：{question}，直接回答True或False。'),
  (2, NULL, 'CoT默认模板', 'cot', '请判断以下模态逻辑推理是否正确：{question}，请一步步分析推理过程后给出答案。'),
  (3, NULL, 'Few-shot默认模板', 'few_shot', '以下是几个示例：{examples}，请判断：{question}');
