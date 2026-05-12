from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from typing import Any, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .auth import create_token, get_current_user, hash_password, require_admin, verify_password
from .database import fetch_all, fetch_one, get_connection, init_db
from .llm import evaluate_question, generate_questions, render_prompt


app = FastAPI(title="面向大语言模型的模态逻辑推理数据集构建与评测系统", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


QuestionType = Literal["true_false", "multiple_choice"]
Difficulty = Literal["single_step", "multi_step", "nested"]
Source = Literal["llm_generated", "manual", "imported"]
ReviewStatus = Literal["draft", "confirmed"]
StrategyType = Literal["zero_shot", "cot", "few_shot"]


class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    email: str
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


class QuestionBase(BaseModel):
    title: str
    premises: list[str] = Field(default_factory=list)
    question_text: str
    options: list[str] = Field(default_factory=list)
    answer: str
    question_type: QuestionType
    modal_type: str
    logic_system: str
    modal_depth: int = Field(ge=1, le=3)
    difficulty: Difficulty
    explanation: str | None = None


class QuestionCreate(QuestionBase):
    source: Source = "manual"
    review_status: ReviewStatus = "draft"


class QuestionGenerateIn(BaseModel):
    modal_type: str
    logic_system: str
    difficulty: Difficulty
    modal_depth: int = Field(ge=1, le=3)
    question_type: QuestionType
    count: int = Field(ge=1, le=50)
    base_url: str | None = None
    api_key: str | None = None
    model_name: str | None = None


class ImportIn(BaseModel):
    format: Literal["json", "csv"]
    content: str


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None


class DatasetQuestionIn(BaseModel):
    question_id: int


class PromptTemplateIn(BaseModel):
    name: str
    strategy_type: StrategyType
    template_content: str


class EvalModelIn(BaseModel):
    model_name: str
    base_url: str = ""
    api_key: str = ""


class EvalStrategyIn(BaseModel):
    strategy_type: StrategyType
    prompt_template_id: int | None = None


class EvalTaskCreate(BaseModel):
    dataset_id: int
    task_name: str
    models: list[EvalModelIn]
    strategies: list[EvalStrategyIn]


def parse_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def row_to_question(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["premises"] = parse_json(item.get("premises"), [])
    item["options"] = parse_json(item.get("options"), [])
    return item


def visible_owner_clause(user: dict, alias: str = "") -> tuple[str, tuple[object, ...]]:
    prefix = f"{alias}." if alias else ""
    if user["role"] == "admin":
        return "1 = 1", ()
    return f"{prefix}user_id = ?", (user["id"],)


def ensure_owned_dataset(dataset_id: int, user: dict) -> dict:
    dataset = fetch_one("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
    if dataset is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    if user["role"] != "admin" and dataset["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="无权访问该数据集")
    return dict(dataset)


def ensure_owned_question(question_id: int, user: dict) -> dict:
    question = fetch_one("SELECT * FROM questions WHERE id = ?", (question_id,))
    if question is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    if user["role"] != "admin" and question["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="无权访问该题目")
    return row_to_question(question)


def insert_question(conn, user_id: int, payload: dict[str, Any], source: Source, status: ReviewStatus = "draft") -> int:
    conn.execute(
        """
        INSERT INTO questions (
          user_id, title, premises, question_text, options, answer, question_type,
          modal_type, logic_system, modal_depth, difficulty, source, explanation, review_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            payload["title"],
            json.dumps(payload.get("premises", []), ensure_ascii=False),
            payload["question_text"],
            json.dumps(payload.get("options", []), ensure_ascii=False),
            payload["answer"],
            payload["question_type"],
            payload["modal_type"],
            payload["logic_system"],
            payload["modal_depth"],
            payload["difficulty"],
            source,
            payload.get("explanation"),
            status,
        ),
    )
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


@app.on_event("startup")
def startup() -> None:
    init_db()
    admin = fetch_one("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    if admin is None:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, 'admin')",
                ("admin", hash_password("admin123"), "admin@example.com"),
            )
            conn.commit()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register")
def register(payload: RegisterIn) -> dict[str, Any]:
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, 'user')",
                (payload.username, hash_password(payload.password), payload.email),
            )
            conn.commit()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="用户名或邮箱已存在") from exc
    user = fetch_one("SELECT id, username, email, role, created_at FROM users WHERE username = ?", (payload.username,))
    return {"user": dict(user), "token": create_token(user["id"], user["role"])}


@app.post("/api/auth/login")
def login(payload: LoginIn) -> dict[str, Any]:
    user = fetch_one("SELECT * FROM users WHERE username = ?", (payload.username,))
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    public_user = {key: user[key] for key in ("id", "username", "email", "role", "created_at")}
    return {"user": public_user, "token": create_token(user["id"], user["role"])}


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return user


@app.post("/api/auth/logout")
def logout() -> dict[str, str]:
    return {"message": "已退出登录"}


@app.post("/api/auth/change-password")
def change_password(payload: PasswordChangeIn, user: dict = Depends(get_current_user)) -> dict[str, str]:
    stored = fetch_one("SELECT password_hash FROM users WHERE id = ?", (user["id"],))
    if stored is None or not verify_password(payload.old_password, stored["password_hash"]):
        raise HTTPException(status_code=400, detail="原密码错误")
    with get_connection() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(payload.new_password), user["id"]))
        conn.commit()
    return {"message": "密码已修改"}


@app.get("/api/questions")
def list_questions(
    modal_type: str | None = None,
    logic_system: str | None = None,
    difficulty: str | None = None,
    question_type: str | None = None,
    review_status: str | None = None,
    source: str | None = None,
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    clause, params = visible_owner_clause(user)
    filters = [clause]
    values = list(params)
    for field, value in {
        "modal_type": modal_type,
        "logic_system": logic_system,
        "difficulty": difficulty,
        "question_type": question_type,
        "review_status": review_status,
        "source": source,
    }.items():
        if value:
            filters.append(f"{field} = ?")
            values.append(value)
    rows = fetch_all(f"SELECT * FROM questions WHERE {' AND '.join(filters)} ORDER BY updated_at DESC, id DESC", values)
    return [row_to_question(row) for row in rows]


@app.post("/api/questions")
def create_question(payload: QuestionCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    data = payload.model_dump()
    with get_connection() as conn:
        question_id = insert_question(conn, user["id"], data, data["source"], data["review_status"])
        conn.commit()
    return ensure_owned_question(question_id, user)


@app.post("/api/questions/generate")
def generate_question_drafts(payload: QuestionGenerateIn, user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    params = payload.model_dump()
    try:
        drafts = generate_questions(params)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    created: list[dict[str, Any]] = []
    with get_connection() as conn:
        for draft in drafts:
            data = {
                **draft,
                "modal_type": payload.modal_type,
                "logic_system": payload.logic_system,
                "modal_depth": payload.modal_depth,
                "difficulty": payload.difficulty,
                "question_type": payload.question_type,
            }
            question_id = insert_question(conn, user["id"], data, "llm_generated", "draft")
            created.append(question_id)
        conn.commit()
    return [ensure_owned_question(question_id, user) for question_id in created]


@app.post("/api/questions/import")
def import_questions(payload: ImportIn, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if payload.format == "json":
        try:
            records = json.loads(payload.content)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"JSON格式错误：{exc}") from exc
    else:
        reader = csv.DictReader(io.StringIO(payload.content))
        records = list(reader)

    if not isinstance(records, list):
        raise HTTPException(status_code=400, detail="导入内容必须是题目数组")
    errors: list[str] = []
    created_ids: list[int] = []
    required = {"title", "question_text", "answer", "question_type", "modal_type", "logic_system", "modal_depth", "difficulty"}
    with get_connection() as conn:
        for index, record in enumerate(records, start=1):
            missing = required - set(record.keys())
            if missing:
                errors.append(f"第{index}行缺少字段：{', '.join(sorted(missing))}")
                continue
            try:
                record["modal_depth"] = int(record["modal_depth"])
                if isinstance(record.get("premises"), str):
                    record["premises"] = parse_json(record["premises"], [record["premises"]] if record["premises"] else [])
                if isinstance(record.get("options"), str):
                    record["options"] = parse_json(record["options"], [item.strip() for item in record["options"].split("|") if item.strip()])
                question_id = insert_question(conn, user["id"], record, "imported", "draft")
                created_ids.append(question_id)
            except Exception as exc:
                errors.append(f"第{index}行导入失败：{exc}")
        conn.commit()
    return {"created": len(created_ids), "ids": created_ids, "errors": errors}


@app.get("/api/questions/{question_id}")
def get_question(question_id: int, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return ensure_owned_question(question_id, user)


@app.put("/api/questions/{question_id}")
def update_question(question_id: int, payload: QuestionCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    ensure_owned_question(question_id, user)
    data = payload.model_dump()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE questions SET
              title = ?, premises = ?, question_text = ?, options = ?, answer = ?, question_type = ?,
              modal_type = ?, logic_system = ?, modal_depth = ?, difficulty = ?, source = ?,
              explanation = ?, review_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                data["title"],
                json.dumps(data["premises"], ensure_ascii=False),
                data["question_text"],
                json.dumps(data["options"], ensure_ascii=False),
                data["answer"],
                data["question_type"],
                data["modal_type"],
                data["logic_system"],
                data["modal_depth"],
                data["difficulty"],
                data["source"],
                data["explanation"],
                data["review_status"],
                question_id,
            ),
        )
        conn.commit()
    return ensure_owned_question(question_id, user)


@app.post("/api/questions/{question_id}/confirm")
def confirm_question(question_id: int, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    ensure_owned_question(question_id, user)
    with get_connection() as conn:
        conn.execute("UPDATE questions SET review_status = 'confirmed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (question_id,))
        conn.commit()
    return ensure_owned_question(question_id, user)


@app.delete("/api/questions/{question_id}")
def delete_question(question_id: int, user: dict = Depends(get_current_user)) -> dict[str, str]:
    ensure_owned_question(question_id, user)
    with get_connection() as conn:
        conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        conn.commit()
    return {"message": "题目已删除"}


@app.get("/api/datasets")
def list_datasets(user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    clause, params = visible_owner_clause(user)
    rows = fetch_all(
        f"""
        SELECT d.*, COUNT(dq.id) AS question_count
        FROM datasets d
        LEFT JOIN dataset_questions dq ON dq.dataset_id = d.id
        WHERE {clause.replace('user_id', 'd.user_id')}
        GROUP BY d.id
        ORDER BY d.updated_at DESC, d.id DESC
        """,
        params,
    )
    return [dict(row) for row in rows]


@app.post("/api/datasets")
def create_dataset(payload: DatasetCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO datasets (user_id, name, description) VALUES (?, ?, ?)",
            (user["id"], payload.name, payload.description),
        )
        dataset_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    return get_dataset(dataset_id, user)


def dataset_stats(questions: list[dict[str, Any]]) -> dict[str, Any]:
    stats: dict[str, dict[str, int]] = {
        "modal_type": defaultdict(int),
        "logic_system": defaultdict(int),
        "difficulty": defaultdict(int),
        "question_type": defaultdict(int),
    }
    for question in questions:
        for key in stats:
            stats[key][question[key]] += 1
    return {"total": len(questions), **{key: dict(value) for key, value in stats.items()}}


@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: int, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    dataset = ensure_owned_dataset(dataset_id, user)
    rows = fetch_all(
        """
        SELECT q.* FROM dataset_questions dq
        JOIN questions q ON q.id = dq.question_id
        WHERE dq.dataset_id = ?
        ORDER BY dq.sort_order ASC, dq.id ASC
        """,
        (dataset_id,),
    )
    questions = [row_to_question(row) for row in rows]
    return {**dataset, "questions": questions, "stats": dataset_stats(questions)}


@app.post("/api/datasets/{dataset_id}/questions")
def add_dataset_question(dataset_id: int, payload: DatasetQuestionIn, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    ensure_owned_dataset(dataset_id, user)
    question = ensure_owned_question(payload.question_id, user)
    if question["review_status"] != "confirmed":
        raise HTTPException(status_code=400, detail="只能加入已确认题目")
    with get_connection() as conn:
        next_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM dataset_questions WHERE dataset_id = ?", (dataset_id,)).fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO dataset_questions (dataset_id, question_id, sort_order) VALUES (?, ?, ?)",
            (dataset_id, payload.question_id, next_order),
        )
        conn.execute("UPDATE datasets SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (dataset_id,))
        conn.commit()
    return get_dataset(dataset_id, user)


@app.delete("/api/datasets/{dataset_id}/questions/{question_id}")
def remove_dataset_question(dataset_id: int, question_id: int, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    ensure_owned_dataset(dataset_id, user)
    with get_connection() as conn:
        conn.execute("DELETE FROM dataset_questions WHERE dataset_id = ? AND question_id = ?", (dataset_id, question_id))
        conn.execute("UPDATE datasets SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (dataset_id,))
        conn.commit()
    return get_dataset(dataset_id, user)


@app.get("/api/datasets/{dataset_id}/export")
def export_dataset(dataset_id: int, user: dict = Depends(get_current_user)) -> JSONResponse:
    dataset = get_dataset(dataset_id, user)
    headers = {"Content-Disposition": f"attachment; filename=dataset-{dataset_id}.json"}
    return JSONResponse(dataset, headers=headers)


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, user: dict = Depends(get_current_user)) -> dict[str, str]:
    ensure_owned_dataset(dataset_id, user)
    with get_connection() as conn:
        conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
        conn.commit()
    return {"message": "数据集已删除"}


@app.get("/api/prompt-templates")
def list_prompt_templates(user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    rows = fetch_all(
        "SELECT * FROM prompt_templates WHERE user_id IS NULL OR user_id = ? ORDER BY user_id ASC, id ASC",
        (user["id"],),
    )
    return [dict(row) for row in rows]


@app.post("/api/prompt-templates")
def create_prompt_template(payload: PromptTemplateIn, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO prompt_templates (user_id, name, strategy_type, template_content) VALUES (?, ?, ?, ?)",
            (user["id"], payload.name, payload.strategy_type, payload.template_content),
        )
        template_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    return dict(fetch_one("SELECT * FROM prompt_templates WHERE id = ?", (template_id,)))


@app.put("/api/prompt-templates/{template_id}")
def update_prompt_template(template_id: int, payload: PromptTemplateIn, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    row = fetch_one("SELECT * FROM prompt_templates WHERE id = ?", (template_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    if row["user_id"] is None:
        raise HTTPException(status_code=400, detail="默认模板不可直接修改，请新建自定义模板")
    if user["role"] != "admin" and row["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="无权修改该模板")
    with get_connection() as conn:
        conn.execute(
            "UPDATE prompt_templates SET name = ?, strategy_type = ?, template_content = ? WHERE id = ?",
            (payload.name, payload.strategy_type, payload.template_content, template_id),
        )
        conn.commit()
    return dict(fetch_one("SELECT * FROM prompt_templates WHERE id = ?", (template_id,)))


@app.delete("/api/prompt-templates/{template_id}")
def delete_prompt_template(template_id: int, user: dict = Depends(get_current_user)) -> dict[str, str]:
    row = fetch_one("SELECT * FROM prompt_templates WHERE id = ?", (template_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    if row["user_id"] is None:
        raise HTTPException(status_code=400, detail="默认模板不可删除")
    if user["role"] != "admin" and row["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="无权删除该模板")
    with get_connection() as conn:
        conn.execute("DELETE FROM prompt_templates WHERE id = ?", (template_id,))
        conn.commit()
    return {"message": "模板已删除"}


def get_eval_questions(dataset_id: int) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT q.* FROM dataset_questions dq
        JOIN questions q ON q.id = dq.question_id
        WHERE dq.dataset_id = ?
        ORDER BY dq.sort_order ASC, dq.id ASC
        """,
        (dataset_id,),
    )
    return [row_to_question(row) for row in rows]


def recompute_reports(eval_task_id: int) -> None:
    predictions = [dict(row) for row in fetch_all("SELECT p.*, q.modal_type, q.logic_system, q.difficulty, q.question_type FROM eval_predictions p JOIN questions q ON q.id = p.question_id WHERE p.eval_task_id = ?", (eval_task_id,))]
    groups: list[tuple[str, str, str | None, str | None, list[dict[str, Any]]]] = [
        ("overall", "总体", None, None, predictions),
    ]
    for key in ["modal_type", "logic_system", "difficulty", "question_type"]:
        for name in sorted({item[key] for item in predictions}):
            groups.append((key, name, None, None, [item for item in predictions if item[key] == name]))
    for model_name in sorted({item["model_name"] for item in predictions}):
        groups.append(("model", model_name, model_name, None, [item for item in predictions if item["model_name"] == model_name]))
    for strategy in sorted({item["strategy_type"] for item in predictions}):
        groups.append(("strategy", strategy, None, strategy, [item for item in predictions if item["strategy_type"] == strategy]))

    with get_connection() as conn:
        conn.execute("DELETE FROM eval_reports WHERE eval_task_id = ?", (eval_task_id,))
        for group_type, group_name, model_name, strategy_type, items in groups:
            total = len(items)
            correct = sum(1 for item in items if item["is_correct"])
            accuracy = round(correct / total, 4) if total else 0
            conn.execute(
                """
                INSERT INTO eval_reports (eval_task_id, model_name, strategy_type, group_type, group_name, total, correct, accuracy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (eval_task_id, model_name, strategy_type, group_type, group_name, total, correct, accuracy),
            )
        conn.commit()


def run_eval_task(eval_task_id: int, dataset_id: int, models: list[dict[str, str]], strategies: list[dict[str, Any]]) -> None:
    try:
        questions = get_eval_questions(dataset_id)
        with get_connection() as conn:
            conn.execute("UPDATE eval_tasks SET status = 'running', total_questions = ?, finished_questions = 0 WHERE id = ?", (len(questions) * len(models) * len(strategies), eval_task_id))
            conn.commit()

        for model in models:
            for strategy in strategies:
                template = fetch_one("SELECT * FROM prompt_templates WHERE id = ?", (strategy.get("prompt_template_id") or {"zero_shot": 1, "cot": 2, "few_shot": 3}[strategy["strategy_type"]],))
                template_content = template["template_content"] if template else "{question}"
                for question in questions:
                    current = fetch_one("SELECT status FROM eval_tasks WHERE id = ?", (eval_task_id,))
                    if current and current["status"] == "cancelled":
                        return
                    examples = []
                    if strategy["strategy_type"] == "few_shot":
                        example_rows = fetch_all(
                            """
                            SELECT * FROM questions
                            WHERE review_status = 'confirmed' AND id != ? AND modal_type = ? AND question_type = ?
                            ORDER BY RANDOM() LIMIT 3
                            """,
                            (question["id"], question["modal_type"], question["question_type"]),
                        )
                        examples = [row_to_question(row) for row in example_rows]
                    prompt_text = render_prompt(template_content, question, examples)
                    try:
                        raw_output, parsed_answer = evaluate_question(prompt_text, question, model)
                        is_correct = int(parsed_answer == question["answer"])
                        status = "success"
                        error_message = None
                    except Exception as exc:
                        raw_output = ""
                        parsed_answer = ""
                        is_correct = 0
                        status = "failed"
                        error_message = str(exc)
                    with get_connection() as conn:
                        conn.execute(
                            """
                            INSERT INTO eval_predictions (
                              eval_task_id, question_id, model_name, strategy_type, prompt_text, raw_output,
                              parsed_answer, gold_answer, is_correct, status, error_message
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                eval_task_id,
                                question["id"],
                                model["model_name"],
                                strategy["strategy_type"],
                                prompt_text,
                                raw_output,
                                parsed_answer,
                                question["answer"],
                                is_correct,
                                status,
                                error_message,
                            ),
                        )
                        conn.execute("UPDATE eval_tasks SET finished_questions = finished_questions + 1 WHERE id = ?", (eval_task_id,))
                        conn.commit()
        recompute_reports(eval_task_id)
        with get_connection() as conn:
            conn.execute("UPDATE eval_tasks SET status = 'completed', finished_at = CURRENT_TIMESTAMP WHERE id = ? AND status != 'cancelled'", (eval_task_id,))
            conn.commit()
    except Exception:
        with get_connection() as conn:
            conn.execute("UPDATE eval_tasks SET status = 'failed', finished_at = CURRENT_TIMESTAMP WHERE id = ?", (eval_task_id,))
            conn.commit()


@app.get("/api/eval-tasks")
def list_eval_tasks(user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    clause, params = visible_owner_clause(user)
    rows = fetch_all(f"SELECT * FROM eval_tasks WHERE {clause} ORDER BY created_at DESC, id DESC", params)
    return [dict(row) for row in rows]


@app.post("/api/eval-tasks")
def create_eval_task(payload: EvalTaskCreate, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    ensure_owned_dataset(payload.dataset_id, user)
    if not payload.models or not payload.strategies:
        raise HTTPException(status_code=400, detail="至少配置一个模型和一个提示策略")
    questions = get_eval_questions(payload.dataset_id)
    if not questions:
        raise HTTPException(status_code=400, detail="数据集没有题目，无法评测")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO eval_tasks (user_id, dataset_id, task_name, total_questions) VALUES (?, ?, ?, ?)",
            (user["id"], payload.dataset_id, payload.task_name, len(questions) * len(payload.models) * len(payload.strategies)),
        )
        task_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        for model in payload.models:
            conn.execute(
                "INSERT INTO eval_task_models (eval_task_id, model_name, base_url) VALUES (?, ?, ?)",
                (task_id, model.model_name, model.base_url),
            )
        for strategy in payload.strategies:
            conn.execute(
                "INSERT INTO eval_task_strategies (eval_task_id, strategy_type, prompt_template_id) VALUES (?, ?, ?)",
                (task_id, strategy.strategy_type, strategy.prompt_template_id),
            )
        conn.commit()

    background_tasks.add_task(
        run_eval_task,
        task_id,
        payload.dataset_id,
        [model.model_dump() for model in payload.models],
        [strategy.model_dump() for strategy in payload.strategies],
    )
    return get_eval_task(task_id, user)


@app.get("/api/eval-tasks/{task_id}")
def get_eval_task(task_id: int, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    task = fetch_one("SELECT * FROM eval_tasks WHERE id = ?", (task_id,))
    if task is None:
        raise HTTPException(status_code=404, detail="评测任务不存在")
    if user["role"] != "admin" and task["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="无权访问该评测任务")
    models = [dict(row) for row in fetch_all("SELECT id, model_name, base_url FROM eval_task_models WHERE eval_task_id = ?", (task_id,))]
    strategies = [dict(row) for row in fetch_all("SELECT * FROM eval_task_strategies WHERE eval_task_id = ?", (task_id,))]
    predictions = [dict(row) for row in fetch_all("SELECT * FROM eval_predictions WHERE eval_task_id = ? ORDER BY id ASC", (task_id,))]
    reports = [dict(row) for row in fetch_all("SELECT * FROM eval_reports WHERE eval_task_id = ? ORDER BY group_type ASC, id ASC", (task_id,))]
    return {**dict(task), "models": models, "strategies": strategies, "predictions": predictions, "reports": reports}


@app.post("/api/eval-tasks/{task_id}/cancel")
def cancel_eval_task(task_id: int, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    get_eval_task(task_id, user)
    with get_connection() as conn:
        conn.execute("UPDATE eval_tasks SET status = 'cancelled', finished_at = CURRENT_TIMESTAMP WHERE id = ? AND status IN ('pending', 'running')", (task_id,))
        conn.commit()
    return get_eval_task(task_id, user)


@app.get("/api/eval-tasks/{task_id}/export")
def export_eval_report(task_id: int, format: Literal["json", "csv"] = "json", user: dict = Depends(get_current_user)):
    task = get_eval_task(task_id, user)
    if format == "json":
        return JSONResponse(task, headers={"Content-Disposition": f"attachment; filename=eval-task-{task_id}.json"})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "question_id", "model_name", "strategy_type", "parsed_answer", "gold_answer", "is_correct", "status", "error_message"])
    writer.writeheader()
    for row in task["predictions"]:
        writer.writerow({field: row.get(field) for field in writer.fieldnames})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=eval-task-{task_id}.csv"},
    )


@app.get("/api/admin/users")
def admin_users(_: dict = Depends(require_admin)) -> list[dict[str, Any]]:
    rows = fetch_all("SELECT id, username, email, role, created_at FROM users ORDER BY id ASC")
    return [dict(row) for row in rows]


@app.get("/api/admin/overview")
def admin_overview(_: dict = Depends(require_admin)) -> dict[str, Any]:
    return {
        "users": fetch_one("SELECT COUNT(*) AS count FROM users")["count"],
        "questions": fetch_one("SELECT COUNT(*) AS count FROM questions")["count"],
        "datasets": fetch_one("SELECT COUNT(*) AS count FROM datasets")["count"],
        "eval_tasks": fetch_one("SELECT COUNT(*) AS count FROM eval_tasks")["count"],
    }


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: dict = Depends(require_admin)) -> dict[str, str]:
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="不能删除当前管理员账号")
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    return {"message": "用户已删除"}


@app.exception_handler(HTTPException)
def http_exception_handler(_, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
