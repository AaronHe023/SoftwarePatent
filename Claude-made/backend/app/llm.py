from __future__ import annotations

import json
import random
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


# 扩充后的演示题库：覆盖四种模态类型、三种难度、两种题型，共20道基础模板
_DEMO_POOL: list[dict[str, Any]] = [
    # 认知模态 - 单步推理 - True/False
    {
        "modal_type": "认知模态",
        "difficulty": "single_step",
        "question_type": "true_false",
        "title": "认知模态单步推理",
        "premises": ["在认知逻辑中，若主体A知道P，则P为真。"],
        "question_text": "若主体A知道"今天是星期一"，是否可以推出"今天确实是星期一"？",
        "options": [],
        "answer": "True",
        "explanation": "认知逻辑公理：K_a P → P（若A知道P，则P成立）。",
    },
    # 认知模态 - 多步推理 - True/False
    {
        "modal_type": "认知模态",
        "difficulty": "multi_step",
        "question_type": "true_false",
        "title": "认知模态多步传递推理",
        "premises": [
            "在S5系统中，若A知道P，则A知道A知道P。",
            "A知道"城市X的人口超过一百万"。",
        ],
        "question_text": "根据以上前提，能否推出A知道他自己知道"城市X的人口超过一百万"？",
        "options": [],
        "answer": "True",
        "explanation": "S5公理：K_a P → K_a K_a P，因此知识可正向迭代。",
    },
    # 认知模态 - 算子嵌套 - 多选
    {
        "modal_type": "认知模态",
        "difficulty": "nested",
        "question_type": "multiple_choice",
        "title": "认知模态嵌套算子推理",
        "premises": [
            "在S4系统中，若A知道P，则A知道A知道P（正内省公理）。",
            "A知道B知道"合同已签署"。",
        ],
        "question_text": "在S4系统下，以下哪项关于A的知识状态描述是正确的？",
        "options": [
            "A. A知道A知道B知道合同已签署",
            "B. A不知道B的知识状态",
            "C. B知道A知道合同已签署",
            "D. A的知识仅限于直接观察",
        ],
        "answer": "A",
        "explanation": "S4正内省：K_a φ → K_a K_a φ，因此A知道B知道P，可推出A知道A知道B知道P。",
    },
    # 道义模态 - 单步推理 - True/False
    {
        "modal_type": "道义模态",
        "difficulty": "single_step",
        "question_type": "true_false",
        "title": "道义模态单步推理",
        "premises": ["在标准义务逻辑中，若行为X是义务（O(X)），则X是被允许的（P(X)）。"],
        "question_text": "若"提交报告"是法律义务，则"提交报告"是被允许的行为，这一推断是否有效？",
        "options": [],
        "answer": "True",
        "explanation": "道义逻辑定理：O(P) → P(P)，义务蕴含允许。",
    },
    # 道义模态 - 多步推理 - 多选
    {
        "modal_type": "道义模态",
        "difficulty": "multi_step",
        "question_type": "multiple_choice",
        "title": "道义模态义务传递推理",
        "premises": [
            "若X是义务，则违反X是被禁止的。",
            "提交年度报告是义务。",
            "拒绝提交年度报告是违反提交义务的行为。",
        ],
        "question_text": "根据以上前提，下列哪项结论成立？",
        "options": [
            "A. 拒绝提交年度报告是被禁止的",
            "B. 提交报告是可选项",
            "C. 拒绝提交不产生任何义务后果",
            "D. 报告提交只适用于企业",
        ],
        "answer": "A",
        "explanation": "O(提交报告) → F(违反提交)，再由传递得 F(拒绝提交)。",
    },
    # 道义模态 - 算子嵌套 - True/False
    {
        "modal_type": "道义模态",
        "difficulty": "nested",
        "question_type": "true_false",
        "title": "道义嵌套：应当允许",
        "premises": ["若某行为X是义务，则X的允许性不依赖外部授权（道义完全性）。"],
        "question_text": "若"缴纳税款"是义务，则"允许缴纳税款"同时成立，该推断是否有效？",
        "options": [],
        "answer": "True",
        "explanation": "在标准道义系统中 O(X) → P(X) 恒成立，义务必然蕴含允许。",
    },
    # 时态模态 - 单步推理 - True/False
    {
        "modal_type": "时态模态",
        "difficulty": "single_step",
        "question_type": "true_false",
        "title": "时态模态单步推理",
        "premises": ["在线性时态逻辑中，□P 表示在所有未来时刻 P 均成立。"],
        "question_text": "若□P 成立，则在接下来每个时刻 P 都必须为真，该命题正确吗？",
        "options": [],
        "answer": "True",
        "explanation": "□P 的语义即为：对所有可达未来时刻，P 成立。",
    },
    # 时态模态 - 多步推理 - 多选
    {
        "modal_type": "时态模态",
        "difficulty": "multi_step",
        "question_type": "multiple_choice",
        "title": "时态模态 Until 算子推理",
        "premises": [
            "在 LTL 中，P U Q 表示 P 持续成立，直到 Q 成立为止（含 Q 成立时刻）。",
            "在某系统中，P U Q 已验证为真。",
        ],
        "question_text": "以下哪项关于 P U Q 的推断是正确的？",
        "options": [
            "A. 存在某时刻 Q 为真，且在此之前 P 持续为真",
            "B. P 和 Q 在所有时刻均为真",
            "C. Q 永远不会为真",
            "D. P 在 Q 成立后仍必须持续",
        ],
        "answer": "A",
        "explanation": "P U Q 的标准语义即"存在 i，Q 在 i 时刻为真，且对所有 j < i，P 为真"。",
    },
    # 时态模态 - 算子嵌套 - True/False
    {
        "modal_type": "时态模态",
        "difficulty": "nested",
        "question_type": "true_false",
        "title": "时态嵌套：G(F(P))",
        "premises": ["G(F(P)) 表示"P 总是最终会成立"，即在任何时刻后，P 都会在某个未来时刻出现。"],
        "question_text": "G(F(P)) 成立，能否推出 P 在无穷次数上为真？",
        "options": [],
        "answer": "True",
        "explanation": "G(F(P)) 等价于 P 无限次出现（在 ω 路径语义下），故 P 无穷多次为真。",
    },
    # 真值模态 - 单步推理 - True/False
    {
        "modal_type": "真值模态",
        "difficulty": "single_step",
        "question_type": "true_false",
        "title": "真值模态 T 系统反射公理",
        "premises": ["在模态逻辑 T 系统中，反射公理为：□P → P。"],
        "question_text": "若在 T 系统中 □P 成立，能否推出 P 在当前世界成立？",
        "options": [],
        "answer": "True",
        "explanation": "T 系统公理：□P → P，即必然真蕴含实际真。",
    },
    # 真值模态 - 多步推理 - 多选
    {
        "modal_type": "真值模态",
        "difficulty": "multi_step",
        "question_type": "multiple_choice",
        "title": "真值模态 S5 等价世界推理",
        "premises": [
            "在 S5 系统中，可及关系是等价关系（自反、对称、传递）。",
            "□P 在当前世界 w0 成立。",
        ],
        "question_text": "在 S5 系统下，以下哪项必然正确？",
        "options": [
            "A. 在所有与 w0 可及的世界中，P 均成立",
            "B. P 只在 w0 成立",
            "C. 存在某个可及世界中 P 不成立",
            "D. □P 仅在有限可及世界中成立",
        ],
        "answer": "A",
        "explanation": "□P 在 w0 成立意味着：对所有与 w0 可及的世界 w，P(w) 为真。",
    },
    # 真值模态 - 算子嵌套 - True/False
    {
        "modal_type": "真值模态",
        "difficulty": "nested",
        "question_type": "true_false",
        "title": "真值模态嵌套：□□P → □P",
        "premises": ["在 S4 系统中，传递公理为：□P → □□P。"],
        "question_text": "在 S4 系统中，若 □□P 成立，能否推出 □P 成立（即 □□P → □P）？",
        "options": [],
        "answer": "True",
        "explanation": "在 S4 中，由 □□P 和 T 公理（□P → P）可推得 □P；或直接由 S4 系统的可及性传递性得出。",
    },
    # 认知模态 - 单步推理 - 多选
    {
        "modal_type": "认知模态",
        "difficulty": "single_step",
        "question_type": "multiple_choice",
        "title": "认知模态：知识与信念的区别",
        "premises": [
            "在认知逻辑中，知道（K）和相信（B）的根本区别在于：K_a P 蕴含 P 为真，而 B_a P 不要求 P 为真。",
        ],
        "question_text": "以下哪项正确描述了认知算子 K 和信念算子 B 的核心区别？",
        "options": [
            "A. K_a P 蕴含 P 为真，B_a P 不蕴含 P 为真",
            "B. K_a P 和 B_a P 完全等价",
            "C. B_a P 比 K_a P 更强",
            "D. 两者均不要求命题为真",
        ],
        "answer": "A",
        "explanation": "知识的真值条件是其区别于信念的核心：K_a P → P，B_a P 不要求 P。",
    },
    # 道义模态 - 单步推理 - True/False（新增）
    {
        "modal_type": "道义模态",
        "difficulty": "single_step",
        "question_type": "true_false",
        "title": "道义模态：允许的否定",
        "premises": ["在标准道义逻辑中，P(X) 表示 X 是被允许的，F(X) = ¬P(X) 表示 X 被禁止。"],
        "question_text": "若 P(X)（X 被允许）为真，则 F(X)（X 被禁止）为真，该推断正确吗？",
        "options": [],
        "answer": "False",
        "explanation": "允许和禁止互为否定：P(X) 为真当且仅当 F(X) 为假，两者不能同时成立。",
    },
    # 时态模态 - 单步推理 - 多选（新增）
    {
        "modal_type": "时态模态",
        "difficulty": "single_step",
        "question_type": "multiple_choice",
        "title": "时态模态：◇P 的语义",
        "premises": ["在 LTL 中，◇P（F P）表示 P 将在某个未来时刻成立。"],
        "question_text": "◇P 成立，以下哪项描述最准确？",
        "options": [
            "A. P 在当前或某个未来时刻成立",
            "B. P 在所有时刻都成立",
            "C. P 已经在过去成立",
            "D. P 永远不会成立",
        ],
        "answer": "A",
        "explanation": "◇P 的标准语义：存在时刻 i ≥ 当前，P(i) 为真。",
    },
]


def generate_questions(params: dict[str, Any]) -> list[dict[str, Any]]:
    """
    调用真实 LLM API 生成题目；若未提供 API 参数，则从扩充后的演示题库中
    按模态类型、难度和题型随机抽取，确保每次演示结果不完全相同。
    """
    if params.get("api_key") and params.get("base_url") and params.get("model_name"):
        content = _post_openai_chat(
            params["base_url"],
            params["api_key"],
            params["model_name"],
            [{"role": "user", "content": build_generation_prompt(params)}],
        )
        return _extract_json_array(content)

    count = int(params["count"])
    modal_type = params.get("modal_type", "")
    difficulty = params.get("difficulty", "")
    question_type = params.get("question_type", "")

    # 优先精确匹配三个维度
    candidates = [
        q for q in _DEMO_POOL
        if q["modal_type"] == modal_type
        and q["difficulty"] == difficulty
        and q["question_type"] == question_type
    ]
    # 若精确匹配不足，放宽到仅匹配模态类型
    if not candidates:
        candidates = [q for q in _DEMO_POOL if q["modal_type"] == modal_type]
    # 若仍不足，使用全库
    if not candidates:
        candidates = list(_DEMO_POOL)

    # 随机不重复抽取（超出时允许重复）
    if count <= len(candidates):
        selected = random.sample(candidates, count)
    else:
        selected = random.choices(candidates, k=count)

    drafts: list[dict[str, Any]] = []
    for item in selected:
        drafts.append({
            "title": item["title"],
            "premises": list(item["premises"]),
            "question_text": item["question_text"],
            "options": list(item["options"]),
            "answer": item["answer"],
            "question_type": item["question_type"],
            "explanation": item["explanation"],
        })
    return drafts


def render_prompt(template: str, question: dict[str, Any], examples: list[dict[str, Any]] | None = None) -> str:
    example_text = ""
    if examples:
        example_text = "\n".join(f"题目：{item['question_text']}\n答案：{item['answer']}" for item in examples)
    return template.replace("{question}", question["question_text"]).replace("{examples}", example_text)


def _parse_answer(raw: str, question_type: str) -> tuple[str, str | None]:
    """
    从模型原始输出中提取标准答案字符串。

    改进点：
    1. 大小写不敏感匹配 True/False
    2. 识别中文"真/假/对/错"
    3. 支持括号形式 (A) 或（A）
    4. 解析失败时返回 (None, 错误原因) 而非静默失败

    返回 (parsed_answer, error_message)，成功时 error_message 为 None。
    """
    if question_type == "true_false":
        # 优先精确匹配（不区分大小写）
        match = re.search(r"\b(True|False)\b", raw, flags=re.IGNORECASE)
        if match:
            return match.group(1).capitalize(), None
        # 中文映射
        if re.search(r"[真对]", raw):
            return "True", None
        if re.search(r"[假错]", raw):
            return "False", None
        return "", "无法从输出中提取 True/False 答案"

    # multiple_choice
    # 优先匹配带括号形式（中英文括号）
    bracket_match = re.search(r"[(（]([A-Da-d])[)）]", raw)
    if bracket_match:
        return bracket_match.group(1).upper(), None
    # 匹配"答案是 A"或"答案为 B"模式
    ans_prefix = re.search(r"答案[是为：:]\s*([A-Da-d])", raw)
    if ans_prefix:
        return ans_prefix.group(1).upper(), None
    # 普通大写字母匹配
    candidates = re.findall(r"\b([A-Da-d])\b", raw)
    if candidates:
        return candidates[-1].upper(), None
    return "", "无法从输出中提取 A/B/C/D 答案"


def evaluate_question(prompt: str, question: dict[str, Any], model: dict[str, str]) -> tuple[str, str]:
    """
    发起评测并返回 (raw_output, parsed_answer)。
    缺少 API 参数时进入演示模式，直接返回标准答案。
    答案解析失败时记录在 parsed_answer 中为空字符串，由调用方决定如何处理。
    """
    if model.get("api_key") and model.get("base_url") and model.get("model_name"):
        raw = _post_openai_chat(
            model["base_url"],
            model["api_key"],
            model["model_name"],
            [{"role": "user", "content": prompt}],
        )
        parsed, parse_err = _parse_answer(raw, question.get("question_type", "true_false"))
        if parse_err:
            # 返回空 parsed_answer，让上层记录错误
            return raw, ""
        return raw, parsed

    # 演示模式：直接返回标准答案，模拟 100% 正确率
    demo_raw = f"演示模式：根据题库标准答案，本题答案为 {question['answer']}。"
    return demo_raw, question["answer"]
