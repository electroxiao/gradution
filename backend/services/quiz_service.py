import json
from neo4j import GraphDatabase
from openai import OpenAI

from backend.core.config import settings
from backend.services.knowledge_progress_service import mark_node_mastered

API_KEY = settings.llm_api_key
BASE_URL = settings.llm_base_url
MODEL_NAME = settings.llm_model_name
NEO4J_URI = settings.neo4j_uri
NEO4J_AUTH = settings.neo4j_auth
DB_NAME = settings.neo4j_db_name


def get_node_context_from_neo4j(node_id: str) -> dict:
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    context = {"name": node_id, "desc": "", "related_concepts": []}

    query = """
    MATCH (n {name: $node_id})
    OPTIONAL MATCH (n)-[r]-(m)
    RETURN n.name AS name, coalesce(n.desc, '') AS desc,
           collect(DISTINCT {name: m.name, relation: type(r)}) AS related
    """

    try:
        with driver.session(database=DB_NAME) as session:
            result = session.run(query, node_id=node_id)
            record = result.single()
            if record:
                context["name"] = record["name"] or node_id
                context["desc"] = record["desc"] or ""
                context["related_concepts"] = [
                    item for item in (record["related"] or [])
                    if item.get("name")
                ]
    finally:
        driver.close()

    return context


def generate_quiz_question(node_id: str) -> dict:
    context = get_node_context_from_neo4j(node_id)

    related_str = ""
    if context["related_concepts"]:
        related_str = "相关概念：" + "、".join(
            item["name"] for item in context["related_concepts"][:5]
        )

    prompt = f"""
你是一名 Java 编程教学专家。请根据以下知识点信息，生成一道选择题或简答题。

知识点：{context['name']}
描述：{context['desc'] or '无详细描述'}
{related_str}

请生成一道针对该知识点的练习题，要求：
1. 题目应该测试学生对核心概念的理解
2. 难度适中，适合初学者
3. 题目要有明确的正确答案

只返回 JSON 格式，格式如下：
{{"question": "题目内容", "hint": "可选的提示"}}
"""

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = response.choices[0].message.content

        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            quiz_data = json.loads(content[start:end])
            return {"question": quiz_data.get("question", ""), "hint": quiz_data.get("hint", "")}

        return {"question": content, "hint": ""}
    except Exception as e:
        print(f"生成题目失败: {e}")
        return {"question": f"请解释 {node_id} 的核心概念和用法。", "hint": ""}


def stream_generate_quiz_question(node_id: str):
    context = get_node_context_from_neo4j(node_id)

    related_str = ""
    if context["related_concepts"]:
        related_str = "相关概念：" + "、".join(
            item["name"] for item in context["related_concepts"][:5]
        )

    prompt = f"""
你是一名 Java 编程教学专家。请根据以下知识点信息，生成一道选择题或简答题。

知识点：{context['name']}
描述：{context['desc'] or '无详细描述'}
{related_str}

请生成一道针对该知识点的练习题，要求：
1. 题目应该测试学生对核心概念的理解
2. 难度适中，适合初学者
3. 题目要有明确的正确答案

直接输出题目内容，不需要JSON格式。
"""

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            stream=True,
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        print(f"流式生成题目失败: {e}")
        yield f"请解释 {node_id} 的核心概念和用法。"


def submit_and_judge_answer(node_id: str, question: str, answer: str, db, user) -> dict:
    context = get_node_context_from_neo4j(node_id)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "mark_node_mastered",
                "description": "当用户回答正确时，调用此函数标记知识点已掌握",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "知识点节点ID",
                        }
                    },
                    "required": ["node_id"],
                },
            },
        }
    ]

    prompt = f"""
你是一名 Java 编程教学专家。请判断学生的回答是否正确。

知识点：{context['name']}
描述：{context['desc'] or '无详细描述'}

题目：{question}

学生回答：{answer}

请判断：
1. 学生回答是否正确（理解了核心概念）
2. 给出详细的反馈和解释

如果学生回答正确，请调用 mark_node_mastered 函数来标记该知识点已掌握。

返回 JSON 格式：
{{"is_correct": true/false, "feedback": "详细反馈", "mastered": true/false}}
"""

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice="auto",
            temperature=0.3,
        )

        message = response.choices[0].message
        mastered = False

        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "mark_node_mastered":
                    args = json.loads(tool_call.function.arguments)
                    if args.get("node_id"):
                        mark_node_mastered(db, user, args["node_id"])
                        db.commit()
                        mastered = True

        content = message.content or ""
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            result = json.loads(content[start:end])
            result["mastered"] = mastered or result.get("is_correct", False)
            return result

        is_correct = "正确" in content or "对" in content
        return {
            "is_correct": is_correct,
            "feedback": content,
            "mastered": is_correct,
        }
    except Exception as e:
        print(f"判题失败: {e}")
        return {
            "is_correct": False,
            "feedback": f"判题过程出错：{str(e)}",
            "mastered": False,
        }


def stream_judge_answer(node_id: str, question: str, answer: str, db, user):
    context = get_node_context_from_neo4j(node_id)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "mark_node_mastered",
                "description": "当用户回答正确时，调用此函数标记知识点已掌握",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "知识点节点ID",
                        }
                    },
                    "required": ["node_id"],
                },
            },
        }
    ]

    prompt = f"""
你是一名 Java 编程教学专家。请判断学生的回答是否正确，并给出详细的反馈。

知识点：{context['name']}
描述：{context['desc'] or '无详细描述'}

题目：{question}

学生回答：{answer}

请：
1. 首先明确判断学生回答是否正确（用"正确"或"错误"开头）
2. 然后给出详细的解释和反馈
3. 如果回答正确，解释为什么正确
4. 如果回答错误，指出错误之处并给出正确答案

直接输出反馈内容，不需要JSON格式。
"""

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    mastered = False
    is_correct = False

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice="auto",
            temperature=0.3,
            stream=True,
        )

        full_content = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content
                yield {"type": "feedback_delta", "content": content}

            if chunk.choices[0].delta.tool_calls:
                for tool_call in chunk.choices[0].delta.tool_calls:
                    if tool_call.function and tool_call.function.name == "mark_node_mastered":
                        mastered = True

        is_correct = "正确" in full_content and "错误" not in full_content[:10]

        if mastered or is_correct:
            mark_node_mastered(db, user, node_id)
            db.commit()

        yield {
            "type": "result",
            "is_correct": is_correct,
            "mastered": mastered or is_correct,
        }

    except Exception as e:
        print(f"流式判题失败: {e}")
        yield {"type": "feedback_delta", "content": f"判题过程出错：{str(e)}"}
        yield {"type": "result", "is_correct": False, "mastered": False}
