from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any


def _post_openai_chat(base_url: str, api_key: str, model_name: str, messages: list[dict[str, str]], timeout: int = 60) -> str:
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint = f"{endpoint}/chat/completions"
    payload = json.dumps({"model": model_name, "messages": messages, "temperature": 0.2}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM调用失败：{exc}") from exc


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        raise ValueError("LLM返回内容中未找到JSON数组")
    data = json.loads(match.group(0))
    if not isinstance(data, list):
        raise ValueError("LLM返回内容不是题目数组")
    return data


def build_generation_prompt(params: dict[str, Any]) -> str:
    return f"""
请生成{params['count']}道模态逻辑推理题，并严格返回JSON数组。
每个对象字段为：title, premises, question_text, options, answer, question_type, explanation。
参数：
- 模态类型：{params['modal_type']}
- 逻辑系统：{params['logic_system']}
- 难度：{params['difficulty']}
- 模态嵌套深度：{params['modal_depth']}
- 题目格式：{params['question_type']}
premises和options必须是字符串数组；True/False题的answer只能是True或False；多选题answer只能是A/B/C/D。
""".strip()


def generate_questions(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Call a compatible LLM API; use demo drafts when no API key is provided."""
    if params.get("api_key") and params.get("base_url") and params.get("model_name"):
        content = _post_openai_chat(
            params["base_url"],
            params["api_key"],
            params["model_name"],
            [{"role": "user", "content": build_generation_prompt(params)}],
        )
        return _extract_json_array(content)

    drafts: list[dict[str, Any]] = []
    for index in range(1, int(params["count"]) + 1):
        is_tf = params["question_type"] == "true_false"
        drafts.append(
            {
                "title": f"{params['modal_type']}{params['logic_system']}演示题{index}",
                "premises": [f"在{params['logic_system']}系统中，若必然P成立，则P在可达世界中成立。"],
                "question_text": f"判断该{params['modal_type']}推理是否有效：若□P成立，是否可以推出P？",
                "options": [] if is_tf else ["A. 可以推出", "B. 不可以推出", "C. 条件不足", "D. 与系统无关"],
                "answer": "True" if is_tf else "A",
                "question_type": params["question_type"],
                "explanation": "演示模式生成：用于无API密钥时验证题目生成与确认流程。",
            }
        )
    return drafts


def render_prompt(template: str, question: dict[str, Any], examples: list[dict[str, Any]] | None = None) -> str:
    example_text = ""
    if examples:
        example_text = "\n".join(f"题目：{item['question_text']}\n答案：{item['answer']}" for item in examples)
    return template.replace("{question}", question["question_text"]).replace("{examples}", example_text)


def evaluate_question(prompt: str, question: dict[str, Any], model: dict[str, str]) -> tuple[str, str]:
    """Return raw output and parsed answer. Missing API key triggers deterministic demo mode."""
    if model.get("api_key") and model.get("base_url") and model.get("model_name"):
        raw = _post_openai_chat(
            model["base_url"],
            model["api_key"],
            model["model_name"],
            [{"role": "user", "content": prompt}],
        )
    else:
        raw = f"演示模式：根据题库标准答案判断，答案为 {question['answer']}。"

    candidates = re.findall(r"\b(True|False|A|B|C|D)\b", raw, flags=re.IGNORECASE)
    parsed = candidates[-1].upper() if candidates else ""
    if parsed in {"TRUE", "FALSE"}:
        parsed = parsed.title()
    return raw, parsed

