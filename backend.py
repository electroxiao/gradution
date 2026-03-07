import json
import os
import re
from neo4j import GraphDatabase
from openai import OpenAI

# ================= 配置区域 =================
API_KEY = "sk-3e99ce7b256f45d89d006371fa15993e"
BASE_URL = "https://api.deepseek.com"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "12345678")
DB_NAME = "javagemini"


# ============================================

# --- 步骤 1: 意图识别 (通用) ---
def extract_keywords_with_llm(client, user_input, history=[]):
    print(f"\n🧠 [Step 1] 正在分析输入内容...")

    context_entities = []
    if history:
        for msg in history[-4:]:
            if "keywords" in msg and isinstance(msg["keywords"], list):
                context_entities.extend(msg["keywords"])

    context_str = f"{list(set(context_entities))}" if context_entities else "无"

    prompt = f"""
    你是一个Java知识实体提取专家。请从【用户输入】中提取核心的 Java 知识图谱实体 ID。

    【用户输入】
    "{user_input}"

    【任务要求】
    1. **批量处理**：如果输入包含多道错题或多个代码片段，请提取**所有**涉及的核心概念。
    2. **去噪**：忽略无关的描述性文字，只保留技术术语。
    3. **指代还原**：结合上下文 {context_str} 还原代词。
    4. **格式**：只返回 JSON 列表，如 ["ArrayList", "IndexOutOfBoundsException"]。
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content

        start = content.find('[')
        end = content.find(']') + 1
        if start != -1 and end != -1:
            keywords = json.loads(content[start:end])
        else:
            keywords = [user_input]

        print(f"   -> 识别关键词: {keywords}")
        return keywords
    except Exception as e:
        print(f"   -> 意图识别出错: {e}")
        return []


# --- 步骤 2: 递归查询完整依赖链 (通用) ---
def query_dependency_chain(driver, keyword):
    chains = []
    query = """
    MATCH path = (target:Knowledge)-[:DEPENDS_ON*]->(root)
    WHERE toLower(target.name) CONTAINS toLower($kw) 
    RETURN path, length(path) as len
    ORDER BY len DESC
    LIMIT 3
    """
    try:
        with driver.session(database=DB_NAME) as session:
            result = session.run(query, kw=keyword)
            for record in result:
                path = record["path"]
                nodes = path.nodes
                chain_names = [n["name"] for n in nodes]
                chain_str = " -> (依赖) -> ".join(chain_names)
                root_node = nodes[-1]
                root_desc = root_node.get("desc", "无描述")
                chains.append(f"【完整溯源】{chain_str} (底层概念: {root_desc})")
    except Exception as e:
        print(f"查询依赖链出错: {e}")
    return chains


# --- 步骤 2.5: 综合检索入口 (通用) ---
def query_graph_by_keywords(driver, keywords):
    print(f"\n🕸️ [Step 2] 正在检索图谱依赖链...")
    context_data = []

    for kw in keywords:
        # 1. 查定义
        base_query = """
        MATCH (n:Knowledge)
        WHERE toLower(n.name) CONTAINS toLower($kw)
        RETURN n.name, n.desc LIMIT 1
        """
        with driver.session(database=DB_NAME) as session:
            result = session.run(base_query, kw=kw)
            for record in result:
                context_data.append(f"【核心知识】{record['n.name']}: {record['n.desc']}")

        # 2. 查依赖链
        chains = query_dependency_chain(driver, kw)
        if chains:
            context_data.extend(chains)

    return list(set(context_data))


def _safe_json_extract(text, default):
    if not text:
        return default
    try:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return default


def _safe_json_object_extract(text, default):
    if not text:
        return default
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return default


def _token_overlap_score(question, text):
    q_tokens = set(re.findall(r"[A-Za-z_]{2,}", question.lower()))
    t_tokens = set(re.findall(r"[A-Za-z_]{2,}", text.lower()))
    if not q_tokens or not t_tokens:
        return 0.0
    return len(q_tokens & t_tokens) / len(q_tokens)


def _split_identifier(text):
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+|==|!=|<=|>=|[A-Za-z_]{2,}", text or "")
    return [part.lower() for part in parts if part]


def _normalize_keywords(question, keywords, limit=4):
    if not keywords:
        return []

    q_lower = question.lower()
    normalized = []
    seen = set()
    for raw in keywords:
        if not isinstance(raw, str):
            continue
        kw = raw.strip()
        if not kw:
            continue
        key = kw.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(kw)

    def keyword_rank(kw):
        kw_lower = kw.lower()
        phrase_hit = 1 if kw_lower in q_lower else 0
        token_overlap = _token_overlap_score(question, kw)
        generic_penalty = 0.15 if len(_split_identifier(kw)) == 1 and len(kw) <= 2 else 0.0
        return (phrase_hit, token_overlap - generic_penalty, -len(kw))

    normalized.sort(key=keyword_rank, reverse=True)
    kept = normalized[:limit]
    return kept


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _dedupe_dicts(rows, key_fields):
    uniq = {}
    for row in rows:
        key = tuple(row.get(field) for field in key_fields)
        uniq[key] = row
    return list(uniq.values())


def _seed_question_relevance(question, seed):
    q_lower = question.lower()
    name = seed.get("name", "")
    desc = seed.get("desc", "")
    keyword = seed.get("keyword", "")
    name_lower = name.lower()
    keyword_lower = keyword.lower()

    score = 0.0
    if name_lower and name_lower in q_lower:
        score += 1.0
    elif keyword_lower and keyword_lower in q_lower and keyword_lower == name_lower:
        score += 0.9
    elif keyword_lower and keyword_lower in name_lower:
        score += 0.35

    score += 0.5 * _token_overlap_score(question, f"{name} {desc}")

    if name_lower.startswith("assert") and not any(token in q_lower for token in ["assert", "junit", "单元测试", "测试用例"]):
        score -= 0.7
    if name_lower.endswith("reader") and not any(token in q_lower for token in ["reader", "stream", "io", "输入流", "字符流"]):
        score -= 0.5
    if name_lower.endswith("writer") and not any(token in q_lower for token in ["writer", "stream", "io", "输出流", "字符流"]):
        score -= 0.5
    if name_lower.endswith("builder") and not any(token in q_lower for token in ["builder", "append", "拼接", "可变字符串"]):
        score -= 0.45
    if name_lower.endswith("joiner") and not any(token in q_lower for token in ["joiner", "join", "分隔符", "拼接"]):
        score -= 0.45
    if name_lower.startswith("string") and "string" in q_lower:
        score += 0.2

    return max(score, 0.0)


def split_teacher_questions(user_input):
    pattern = r"(【第\s*\d+\s*题】.*?)(?=【第\s*\d+\s*题】|\Z)"
    matches = re.findall(pattern, user_input, flags=re.S)
    questions = []
    if matches:
        for block in matches:
            block = block.strip()
            id_match = re.search(r"【第\s*(\d+)\s*题】", block)
            question_id = f"Q{id_match.group(1)}" if id_match else f"Q{len(questions) + 1}"
            questions.append({"question_id": question_id, "raw_text": block})
    elif user_input.strip():
        questions.append({"question_id": "Q1", "raw_text": user_input.strip()})
    return questions


def _teacher_module_candidates(text):
    text_lower = text.lower()
    candidates = []
    if any(token in text_lower for token in ["string", "equals", "==", "integer", "new string"]):
        candidates.append("引用与对象比较")
    if any(token in text_lower for token in ["touppercase", "不可变", "immutable"]):
        candidates.append("String 与不可变性")
    if any(token in text_lower for token in ["extends", "animal", "dog", "classcast", "(string)", "向下转型", "多态"]):
        candidates.append("多态与类型转换")
    if any(token in text_lower for token in ["switch", "case", "for(", "for(int", "if (flag = true)", "flag = true", "print"]):
        candidates.append("控制流与语法细节")
    if any(token in text_lower for token in ["未初始化", "int i;", "system.out.println(i)"]):
        candidates.append("变量初始化与编译期规则")
    if any(token in text_lower for token in ["father", "son", " f.x", "字段", "field"]):
        candidates.append("字段隐藏与绑定规则")
    return candidates or ["基础语义理解"]


def _teacher_keyword_candidates(text):
    text_lower = text.lower()
    keywords = []
    candidate_map = [
        ("引用类型", ["string", "integer", "new string", "=="]),
        ("==运算符", ["=="]),
        ("equals()", ["equals"]),
        ("String不可变性", ["touppercase", "string s = \"hello\""]),
        ("多态", ["extends", "animal", "dog", "多态"]),
        ("向下转型", ["(string)", "向下转型"]),
        ("ClassCastException", ["classcast", "结果是？", "string s = (string) obj"]),
        ("局部变量初始化", ["未初始化", "int i;"]),
        ("switch穿透", ["switch", "case 0", "case 1"]),
        ("for循环", ["for(int", "hello"]),
        ("字段隐藏", ["father", "son", "f.x"]),
        ("赋值表达式", ["flag = true"]),
    ]
    for keyword, markers in candidate_map:
        if any(marker in text_lower for marker in markers):
            keywords.append(keyword)
    if not keywords:
        raw_tokens = re.findall(r"[A-Za-z_]{3,}|==", text)
        keywords.extend(raw_tokens[:3])
    return keywords[:3]


def _teacher_error_type(text):
    text_lower = text.lower()
    if "classcast" in text_lower:
        return "类型转换异常理解错误"
    if "编译错误" in text and "未初始化" in text:
        return "编译期规则误判"
    if "switch" in text_lower or "for(" in text_lower or "flag = true" in text_lower:
        return "控制流与语法误判"
    if "==" in text or "equals" in text_lower or "integer" in text_lower:
        return "引用与相等性误判"
    if "extends" in text_lower or "dog" in text_lower or "father" in text_lower:
        return "多态与绑定规则误判"
    return "基础语义误判"


def _fallback_teacher_question_profile(question):
    raw_text = question["raw_text"]
    modules = _teacher_module_candidates(raw_text)
    return {
        "question_id": question["question_id"],
        "raw_text": raw_text,
        "keywords": _teacher_keyword_candidates(raw_text),
        "error_type": _teacher_error_type(raw_text),
        "knowledge_module": modules[0],
    }


def analyze_teacher_batch(client, user_input):
    questions = split_teacher_questions(user_input)
    if not questions:
        return {"questions": [], "selected_modules": [], "selected_keywords": []}

    prompt_lines = []
    for q in questions:
        prompt_lines.append(f"{q['question_id']}: {q['raw_text']}")
    prompt = f"""
你是 Java 教学诊断分析器。请逐题识别错因，输出 JSON 对象。

输入题目:
{chr(10).join(prompt_lines)}

输出格式:
{{
  "questions": [
    {{
      "question_id": "Q1",
      "keywords": ["概念1", "概念2", "概念3"],
      "error_type": "一句话错误类型",
      "knowledge_module": "知识模块名称"
    }}
  ]
}}

要求:
1. 每题 keywords 最多 3 个，优先根因概念，不要返回无关 API 类名。
2. knowledge_module 必须是教学模块，如“引用与对象比较”“多态与类型转换”“控制流与语法细节”。
3. 不要返回 assertEquals、StringReader、StringBuilder 这类表面相似但不关键的类名，除非题面明确讨论它们。
4. 只返回 JSON。
"""

    question_profiles = []
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        payload = _safe_json_object_extract(response.choices[0].message.content, {})
        payload_questions = payload.get("questions", []) if isinstance(payload, dict) else []
        by_id = {item["question_id"]: item for item in payload_questions if isinstance(item, dict) and item.get("question_id")}
        for question in questions:
            item = by_id.get(question["question_id"])
            if not item:
                question_profiles.append(_fallback_teacher_question_profile(question))
                continue
            keywords = _normalize_keywords(question["raw_text"], item.get("keywords", []), limit=3)
            if not keywords:
                keywords = _teacher_keyword_candidates(question["raw_text"])
            question_profiles.append({
                "question_id": question["question_id"],
                "raw_text": question["raw_text"],
                "keywords": keywords[:3],
                "error_type": item.get("error_type") or _teacher_error_type(question["raw_text"]),
                "knowledge_module": item.get("knowledge_module") or _teacher_module_candidates(question["raw_text"])[0],
            })
    except Exception:
        question_profiles = [_fallback_teacher_question_profile(question) for question in questions]

    module_map = {}
    concept_counts = {}
    for item in question_profiles:
        module_name = item["knowledge_module"]
        entry = module_map.setdefault(module_name, {
            "module": module_name,
            "question_ids": [],
            "error_types": [],
            "core_concepts": [],
        })
        entry["question_ids"].append(item["question_id"])
        entry["error_types"].append(item["error_type"])
        for keyword in item["keywords"]:
            concept_key = (module_name, keyword)
            concept_counts[concept_key] = concept_counts.get(concept_key, 0) + 1

    for module_name, entry in module_map.items():
        concepts = [
            {"keyword": keyword, "count": count}
            for (module, keyword), count in concept_counts.items()
            if module == module_name
        ]
        concepts.sort(key=lambda item: (item["count"], len(item["keyword"])), reverse=True)
        entry["core_concepts"] = [item["keyword"] for item in concepts[:2]]
        entry["error_types"] = list(dict.fromkeys(entry["error_types"]))[:3]
        entry["question_ids"] = sorted(entry["question_ids"], key=lambda x: int(re.sub(r"\D", "", x) or "0"))

    modules = list(module_map.values())
    modules.sort(key=lambda item: (len(item["question_ids"]), len(item["core_concepts"])), reverse=True)
    selected_modules = modules[:3]
    selected_keywords = []
    for module in selected_modules:
        selected_keywords.extend(module["core_concepts"][:2])

    return {
        "questions": question_profiles,
        "selected_modules": selected_modules,
        "selected_keywords": list(dict.fromkeys(selected_keywords)),
    }


def format_fact_for_display(fact):
    if isinstance(fact, str):
        return fact
    if not isinstance(fact, dict):
        return str(fact)

    fact_type = fact.get("type")
    if fact_type == "seed":
        return (
            f"【种子实体】{fact.get('seed')} (match={fact.get('match_type', 'unknown')}, "
            f"score={fact.get('score', 0):.2f}): {fact.get('desc', '无描述')}"
        )
    if fact_type == "path":
        return (
            f"【ToG路径 hop={fact.get('hop', '?')}】{fact.get('path_text', '')} "
            f"(score={fact.get('score', 0):.2f}, relation={fact.get('relation_score', 0):.2f}, "
            f"entity={fact.get('entity_score', 0):.2f})"
        )
    if fact_type == "dependency_chain":
        chain_text = " -> (依赖) -> ".join(fact.get("nodes", []))
        return f"【完整溯源】{chain_text} (底层概念: {fact.get('root_desc', '无描述')})"
    if fact_type == "summary":
        return f"【检索总结】{fact.get('text', '')}"
    if fact_type == "question_summary":
        return (
            f"【题目画像】{fact.get('question_id')} | 模块={fact.get('knowledge_module')} | "
            f"错误={fact.get('error_type')} | 概念={', '.join(fact.get('keywords', []))}"
        )
    if fact_type == "module_summary":
        return (
            f"【知识模块】{fact.get('module')} | 题号={', '.join(fact.get('question_ids', []))} | "
            f"核心概念={', '.join(fact.get('core_concepts', []))} | 高频错误={', '.join(fact.get('error_types', []))}"
        )
    if fact_type == "diagnostic":
        return f"【检索诊断】{fact.get('text', '')}"
    return json.dumps(fact, ensure_ascii=False)


def build_knowledge_text(context_knowledge):
    if not context_knowledge:
        return "（未检索到特定图谱路径）"
    preferred = []
    supplemental = []
    for item in context_knowledge:
        if isinstance(item, dict) and item.get("type") in {"module_summary", "path", "dependency_chain", "diagnostic", "summary"}:
            preferred.append(item)
        elif isinstance(item, dict) and item.get("type") == "question_summary":
            supplemental.append(item)
        else:
            preferred.append(item)
    ordered = preferred + supplemental
    return "\n".join(format_fact_for_display(item) for item in ordered)


def _format_path_text(path_rows):
    if not path_rows:
        return ""
    parts = [path_rows[0]["source"]]
    for row in path_rows:
        parts.append(f"-> ({row['relation']},{row['direction']}) -> {row['target']}")
    return " ".join(parts)


def _query_dependency_chain_evidence(driver, keyword):
    chains = []
    query = """
    MATCH path = (target:Knowledge)-[:DEPENDS_ON*]->(root)
    WHERE toLower(target.name) CONTAINS toLower($kw)
    RETURN path, length(path) as len
    ORDER BY len DESC
    LIMIT 3
    """
    try:
        with driver.session(database=DB_NAME) as session:
            result = session.run(query, kw=keyword)
            for record in result:
                path = record["path"]
                nodes = [node["name"] for node in path.nodes]
                root_node = path.nodes[-1]
                chains.append({
                    "type": "dependency_chain",
                    "target": keyword,
                    "nodes": nodes,
                    "root_desc": root_node.get("desc", "无描述"),
                    "path_text": " -> (依赖) -> ".join(nodes),
                })
    except Exception as e:
        print(f"查询依赖链出错: {e}")
    return chains


def _query_seed_nodes(driver, question, keywords, limit_per_kw=3, max_total=4, retrieval_mode="student"):
    seeds = []
    query = """
    MATCH (n:Knowledge)
    WITH n,
         CASE
             WHEN toLower(n.name) = toLower($kw) THEN 4
             WHEN toLower(n.name) CONTAINS toLower($kw) THEN 3
             WHEN toLower(coalesce(n.desc, "")) CONTAINS toLower($kw) THEN 2
             ELSE 0
         END AS match_score
    WHERE match_score > 0
    RETURN n.name AS name,
           coalesce(n.desc, "无描述") AS `desc`,
           match_score
    ORDER BY match_score DESC, n.name ASC
    LIMIT $lim
    """
    with driver.session(database=DB_NAME) as session:
        for kw in keywords:
            for record in session.run(query, kw=kw, lim=limit_per_kw):
                match_score = float(record["match_score"])
                if match_score >= 4:
                    match_type = "exact_name"
                elif match_score >= 3:
                    match_type = "name_contains"
                elif match_score >= 2:
                    match_type = "desc_match"
                else:
                    match_type = "weak_match"
                seeds.append({
                    "name": record["name"],
                    "desc": record["desc"],
                    "keyword": kw,
                    "match_score": match_score / 4.0,
                    "match_type": match_type,
                })
    seeds = _dedupe_dicts(seeds, ("name",))
    for seed in seeds:
        seed["question_relevance"] = _seed_question_relevance(question, seed)
        if retrieval_mode == "teacher":
            name_lower = seed["name"].lower()
            if any(name_lower.endswith(suffix) for suffix in ["reader", "writer", "builder", "joiner"]) or name_lower.startswith("assert"):
                seed["question_relevance"] *= 0.55
            if re.search(r"[A-Za-z]+\(", seed["name"]) or "(" in seed["name"]:
                seed["question_relevance"] += 0.1
        seed["final_seed_score"] = 0.55 * seed["match_score"] + 0.45 * min(seed["question_relevance"], 1.0)

    seeds.sort(key=lambda item: (item["final_seed_score"], item["question_relevance"], item["match_score"]), reverse=True)
    if not seeds:
        return []

    best_score = seeds[0]["final_seed_score"]
    filtered = [seed for seed in seeds if seed["final_seed_score"] >= max(0.35, best_score - 0.18)]
    return filtered[:max_total]


def _query_candidate_relations(driver, entity_name, limit=12):
    query = """
    MATCH (src:Knowledge {name: $name})-[r]-(nbr:Knowledge)
    RETURN src.name AS source,
           type(r) AS relation,
           CASE WHEN startNode(r) = src THEN "out" ELSE "in" END AS direction,
           count(nbr) AS neighbor_count,
           collect(nbr.name)[0..3] AS sample_targets
    ORDER BY neighbor_count DESC, relation ASC
    LIMIT $lim
    """
    rows = []
    with driver.session(database=DB_NAME) as session:
        for rec in session.run(query, name=entity_name, lim=limit):
            rows.append({
                "source": rec["source"],
                "relation": rec["relation"],
                "direction": rec["direction"],
                "neighbor_count": rec["neighbor_count"],
                "sample_targets": rec["sample_targets"] or [],
            })
    return rows


def relation_prune(client, question, current_entity, candidate_relations, top_k=3):
    if not candidate_relations:
        return []

    brief = []
    for i, relation in enumerate(candidate_relations):
        samples = ", ".join(relation.get("sample_targets", [])[:3]) or "无样例"
        brief.append(
            f"{i}. {relation['relation']} ({relation['direction']}, neighbors={relation['neighbor_count']}) "
            f"samples=[{samples}]"
        )

    prompt = f"""
你是 ToG 风格图检索规划器。请从候选关系里挑出最值得扩展的关系。
问题: {question}
当前实体: {current_entity}
候选关系:
{chr(10).join(brief)}

只返回 JSON 数组，每项格式:
{{"index": 整数, "score": 0到1}}
按 score 从高到低排序，最多返回 {top_k} 项。
"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = resp.choices[0].message.content
        selected = _safe_json_extract(content, [])
        picked = []
        for item in selected:
            idx = item.get("index")
            score = _safe_float(item.get("score", 0))
            if isinstance(idx, int) and 0 <= idx < len(candidate_relations):
                row = dict(candidate_relations[idx])
                row["relation_score"] = score
                picked.append(row)
        if picked:
            picked.sort(key=lambda x: x["relation_score"], reverse=True)
            return picked[:top_k]
    except Exception:
        pass

    scored = []
    for relation in candidate_relations:
        raw = " ".join([
            current_entity,
            relation["relation"],
            relation["direction"],
            " ".join(relation.get("sample_targets", [])),
        ])
        score = 0.7 * _token_overlap_score(question, raw) + 0.3 * min(relation["neighbor_count"] / 5.0, 1.0)
        scored.append({**relation, "relation_score": score})
    scored.sort(key=lambda x: x["relation_score"], reverse=True)
    return scored[:top_k]


def _query_neighbors_by_relation(driver, entity_name, relation, direction, limit=8):
    query = """
    MATCH (src:Knowledge {name: $name})-[r]-(nbr:Knowledge)
    WHERE type(r) = $relation
      AND (
        ($direction = "out" AND startNode(r) = src) OR
        ($direction = "in" AND endNode(r) = src)
      )
    RETURN src.name AS source,
           type(r) AS relation,
           CASE WHEN startNode(r) = src THEN "out" ELSE "in" END AS direction,
           nbr.name AS target,
           coalesce(nbr.desc, "无描述") AS target_desc
    LIMIT $lim
    """
    rows = []
    with driver.session(database=DB_NAME) as session:
        for rec in session.run(
            query,
            name=entity_name,
            relation=relation,
            direction=direction,
            lim=limit
        ):
            rows.append({
                "source": rec["source"],
                "relation": rec["relation"],
                "direction": rec["direction"],
                "target": rec["target"],
                "target_desc": rec["target_desc"],
            })
    return _dedupe_dicts(rows, ("source", "relation", "direction", "target"))


def entity_score(client, question, current_entity, relation_row, entity_candidates, top_k=5):
    if not entity_candidates:
        return []

    brief = []
    for i, row in enumerate(entity_candidates):
        brief.append(
            f"{i}. {row['source']} -[{row['relation']},{row['direction']}]-> {row['target']} | {row['target_desc']}"
        )

    prompt = f"""
你是 ToG 风格图推理器。请评估哪些邻居实体最能帮助回答问题。
问题: {question}
当前实体: {current_entity}
已选关系: {relation_row['relation']} ({relation_row['direction']})
候选实体:
{chr(10).join(brief)}

只返回 JSON 数组，每项格式:
{{"index": 整数, "score": 0到1}}
按 score 从高到低排序，最多返回 {top_k} 项。
"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = resp.choices[0].message.content
        selected = _safe_json_extract(content, [])
        picked = []
        for item in selected:
            idx = item.get("index")
            score = _safe_float(item.get("score", 0))
            if isinstance(idx, int) and 0 <= idx < len(entity_candidates):
                row = dict(entity_candidates[idx])
                row["entity_score"] = score
                picked.append(row)
        if picked:
            picked.sort(key=lambda x: x["entity_score"], reverse=True)
            return picked[:top_k]
    except Exception:
        pass

    scored = []
    for row in entity_candidates:
        raw = f"{row['source']} {row['relation']} {row['target']} {row['target_desc']}"
        score = _token_overlap_score(question, raw)
        scored.append({**row, "entity_score": score})
    scored.sort(key=lambda x: x["entity_score"], reverse=True)
    return scored[:top_k]


def _stop_decision(question, beam, hop, max_depth):
    if beam:
        top_beam = beam[0]
        combined_text = " ".join(
            [top_beam.get("frontier_entity", ""), top_beam.get("frontier_desc", ""), top_beam.get("path_text", "")]
        )
        overlap = _token_overlap_score(question, combined_text)
        if hop >= 1 and (top_beam.get("score", 0) >= 0.85 or overlap >= 0.45):
            return "answerable"
    if hop >= max_depth:
        return "answerable" if beam else "dead_end"
    return "continue"


def query_graph_with_reasoning(
    driver,
    client,
    question,
    keywords=None,
    max_depth=2,
    width=3,
    relation_top_k=None,
    entity_top_k=5,
    retrieval_mode="student"
):
    """
    ToG 风格图检索:
    1) 种子召回
    2) 关系裁剪
    3) 实体扩展与打分
    4) beam 截断
    5) 证据充分性停止
    """
    if keywords is None:
        keywords = extract_keywords_with_llm(client, question, history=[])
    if not keywords:
        keywords = [question]
    keywords = _normalize_keywords(question, keywords, limit=max(3, width))

    if relation_top_k is None:
        relation_top_k = width

    evidence = []
    seeds = _query_seed_nodes(
        driver,
        question,
        keywords,
        limit_per_kw=max(2, width),
        max_total=max(2, min(width, 3)),
        retrieval_mode=retrieval_mode
    )
    if not seeds:
        return []

    beam = []
    for seed in seeds[:width]:
        evidence.append({
            "type": "seed",
            "seed": seed["name"],
            "keyword": seed["keyword"],
            "desc": seed["desc"],
            "score": seed["match_score"],
            "match_type": seed["match_type"],
        })
        beam.append({
            "seed": seed["name"],
            "frontier_entity": seed["name"],
            "frontier_desc": seed["desc"],
            "score": seed["match_score"],
            "path": [],
            "path_text": seed["name"],
            "visited": {seed["name"]},
            "relation_trace": [],
        })

    beam.sort(key=lambda item: item["score"], reverse=True)
    beam = beam[:width]

    for hop in range(1, max_depth + 1):
        next_beam = []
        for state in beam:
            relations = _query_candidate_relations(
                driver,
                state["frontier_entity"],
                limit=max(relation_top_k * 2, 6)
            )
            if not relations:
                continue

            selected_relations = relation_prune(
                client,
                question,
                state["frontier_entity"],
                relations,
                top_k=relation_top_k
            )
            for relation_row in selected_relations:
                neighbors = _query_neighbors_by_relation(
                    driver,
                    state["frontier_entity"],
                    relation_row["relation"],
                    relation_row["direction"],
                    limit=max(entity_top_k * 2, 6)
                )
                neighbors = [row for row in neighbors if row["target"] not in state["visited"]]
                if not neighbors:
                    continue

                selected_entities = entity_score(
                    client,
                    question,
                    state["frontier_entity"],
                    relation_row,
                    neighbors,
                    top_k=entity_top_k
                )
                for row in selected_entities:
                    relation_score = relation_row.get("relation_score", 0.0)
                    entity_score_value = row.get("entity_score", 0.0)
                    combined_score = (
                        0.5 * state["score"] +
                        0.2 * relation_score +
                        0.3 * entity_score_value
                    )
                    hop_row = {
                        "hop": hop,
                        "source": row["source"],
                        "relation": row["relation"],
                        "direction": row["direction"],
                        "target": row["target"],
                        "target_desc": row["target_desc"],
                        "relation_score": relation_score,
                        "entity_score": entity_score_value,
                        "score": combined_score,
                    }
                    path = state["path"] + [hop_row]
                    path_text = _format_path_text(path)
                    next_beam.append({
                        "seed": state["seed"],
                        "frontier_entity": row["target"],
                        "frontier_desc": row["target_desc"],
                        "score": combined_score,
                        "path": path,
                        "path_text": path_text,
                        "visited": set(state["visited"]) | {row["target"]},
                        "relation_trace": state["relation_trace"] + [relation_row["relation"]],
                    })

        if not next_beam:
            break
        next_beam.sort(key=lambda item: item["score"], reverse=True)
        beam = next_beam[:width]

        for state in beam:
            hop_row = state["path"][-1]
            evidence.append({
                "type": "path",
                "seed": state["seed"],
                "hop": hop_row["hop"],
                "source": hop_row["source"],
                "relation": hop_row["relation"],
                "direction": hop_row["direction"],
                "target": hop_row["target"],
                "target_desc": hop_row["target_desc"],
                "relation_score": hop_row["relation_score"],
                "entity_score": hop_row["entity_score"],
                "score": state["score"],
                "path_text": state["path_text"],
            })
            for chain in _query_dependency_chain_evidence(driver, hop_row["target"]):
                evidence.append(chain)

        decision = _stop_decision(question, beam, hop, max_depth)
        if decision != "continue":
            evidence.append({
                "type": "summary",
                "text": f"stop={decision}, hop={hop}, beam_size={len(beam)}",
            })
            break

    return _dedupe_dicts(evidence, ("type", "path_text", "seed", "target", "text"))


def query_teacher_graph_with_reasoning(driver, client, user_input, analysis=None, max_depth=2, width=3):
    if analysis is None:
        analysis = analyze_teacher_batch(client, user_input)

    facts = []
    for item in analysis.get("questions", []):
        facts.append({
            "type": "question_summary",
            "question_id": item["question_id"],
            "knowledge_module": item["knowledge_module"],
            "error_type": item["error_type"],
            "keywords": item["keywords"],
        })

    selected_modules = analysis.get("selected_modules", [])[:3]
    for module in selected_modules:
        facts.append({
            "type": "module_summary",
            "module": module["module"],
            "question_ids": module["question_ids"],
            "error_types": module["error_types"],
            "core_concepts": module["core_concepts"],
        })

    filtered_seed_count = 0
    used_keywords = []
    module_coverage_flags = []
    for module in selected_modules:
        module_keywords = list(dict.fromkeys(module["core_concepts"][:2] + [module["module"]]))
        used_keywords.extend(module_keywords)
        module_query = " ".join([module["module"]] + module["core_concepts"] + module["question_ids"])
        module_facts = query_graph_with_reasoning(
            driver,
            client,
            module_query,
            keywords=module_keywords,
            max_depth=max_depth,
            width=min(width, 2),
            relation_top_k=min(width, 2),
            entity_top_k=3,
            retrieval_mode="teacher"
        )
        seed_count = sum(1 for fact in module_facts if isinstance(fact, dict) and fact.get("type") == "seed")
        filtered_seed_count += seed_count
        path_count = sum(1 for fact in module_facts if isinstance(fact, dict) and fact.get("type") == "path")
        if path_count <= 1:
            module_coverage_flags.append(f"{module['module']}: 图谱证据较少")

        for fact in module_facts:
            if isinstance(fact, dict):
                annotated = dict(fact)
                annotated["module"] = module["module"]
                annotated["question_ids"] = module["question_ids"]
                facts.append(annotated)
            else:
                facts.append(fact)

    facts.append({
        "type": "diagnostic",
        "text": (
            f"teacher_questions={len(analysis.get('questions', []))}, "
            f"selected_modules={len(selected_modules)}, "
            f"selected_keywords={list(dict.fromkeys(used_keywords))[:6]}, "
            f"retained_seed_nodes={filtered_seed_count}"
        )
    })
    if module_coverage_flags:
        facts.append({
            "type": "diagnostic",
            "text": " ; ".join(module_coverage_flags)
        })

    return _dedupe_dicts(facts, ("type", "module", "path_text", "seed", "target", "text", "question_id"))


# --- 步骤 3: 核心生成 (支持消融测试) ---
def ask_deepseek_stream(client, user_input, context_knowledge, history=[], mode="student", enable_graph=True):
    """
    enable_graph: True (RAG模式) / False (纯LLM模式，用于消融实验)
    """
    print(f"\n💬 [Step 3] AI 正在思考 (模式: {mode}, 图谱: {enable_graph}) ...")

    # === 分支 A: 启用图谱 (Ours: Graph-Augmented) ===
    if enable_graph:
        knowledge_text = build_knowledge_text(context_knowledge)

        if mode == "student":
            system_prompt = f"""
            你是一名 **Java 智能辅导员**。你的目标是通过**根因分析**引导学生自己发现错误。

            【图谱依赖链】
            {knowledge_text}
    
            === 辅导策略 ===
            1. **错误定位**：识别用户代码中的逻辑错误或异常。
            2. **溯源诊断**：根据图谱，找到导致该错误的**最底层前置概念**（例如：报错是NPE，根因是“引用类型”）。
            3. **苏格拉底提问**：
               - 不要直接给代码！
               - 指出错误现象。
               - 针对底层概念提一个简单问题，测试学生是否理解。
            """
        else:  # teacher
            system_prompt = f"""
            你是一名 **Java 教学数据分析师**。
            用户会输入一系列学生的错题、报错信息或代码片段。
            你的任务是分析这些错误背后的**共性**，并利用知识图谱生成一份**模块化教学诊断报告**。
            找出学生们主要的知识薄弱点，并按知识模块分类。
    
            【模块化图谱证据】
            {knowledge_text}
    
            === 分析任务 ===
            1. **聚类统计**：先按知识模块归纳高频错误，再按模块内错误类型排序。
            2. **多维溯源 (关键)**：
               - 不要强行将所有错误归结为一个原因。请找出 **Top 3-5 个知识模块**。
               - 对每个模块，结合【题目画像】、【知识模块】和图谱路径，给出主要根因概念。
               - 如果某个模块的图谱证据较少，要明确写出“图谱证据有限”，不要编造路径。
            3. **教学建议**：
               - 针对每个知识模块分别给出教学策略。
               - 确保没有遗漏高频题号和高频错误项。
    
            === 报告格式 ===
            ### 📊 错误类型分布 (Top 5)
            | 错误归类 | 频次 | 涉及题目 |
            | :--- | :--- | :--- |
            | ... | ... | ... |
    
            ### 🧬 核心根因分析 (Root Cause Analysis)
            通过图谱分析，本次错题主要暴露出 **[数量]** 个维度的知识盲区：
    
            #### 模块 1：[知识模块名称]
            - **涉及题号**：Q1, Q2 ...
            - **核心概念**：[概念1]、[概念2]
            - **图谱路径证据**：[具体路径]；如果图谱不足，写“图谱证据有限”
            - **分析**：学生混淆了......
    
            #### 模块 2：[知识模块名称]
            - **涉及题号**：...
            - **核心概念**：...
            - **图谱路径证据**：......
            - **分析**：......
            
            ......
            
            #### 模块 n：[知识模块名称]
            - **涉及题号**：...
            - **核心概念**：...
            - **图谱路径证据**：......
            - **分析**：......
    
            ### 💡 针对性教学建议
            1. **针对 [模块1]**：建议讲解......
            2. **针对 [模块2]**：建议练习......
            ......
            n. **针对 [模块n]**：建议练习......
            """

    # === 分支 B: 禁用图谱 (Baseline: Pure LLM) ===
    else:
        knowledge_text = "N/A (消融测试模式)"

        if mode == "student":
            system_prompt = f"""
            你是一名 **Java 智能辅导员**。你的目标是通过**根因分析**引导学生自己发现错误。
    
            === 辅导策略 ===
            1. **错误定位**：识别用户代码中的逻辑错误或异常。
            2. **溯源诊断**：根据你的知识，找到导致该错误的**最底层前置概念**（例如：报错是NPE，根因是“引用类型”）。
            3. **苏格拉底提问**：
               - 不要直接给代码！
               - 指出错误现象。
               - 针对底层概念提一个简单问题，测试学生是否理解。
            """
        else:  # teacher
            system_prompt = f"""
            你是一名 **Java 教学数据分析师**。
            用户会输入一系列学生的错题、报错信息或代码片段。
            你的任务是分析这些错误背后的**共性**，并利用你的知识生成一份**全覆盖的教学诊断报告**。            
    
            === 分析任务 ===
            1. **聚类统计**：输入中包含了哪些类型的错误？（按出现频率排序）。
            2. **多维溯源 (关键)**：
               - 不要强行将所有错误归结为一个原因。如果错误跨度大（如“内存”和“语法”），请找出 **Top 1-3 个主要根因**。
            3. **教学建议**：
               - 针对识别出的每一个主要根因，分别给出教学策略。
               - 确保没有遗漏“错误分布”中的高频错误项。
    
            === 报告格式 ===
            ### 📊 错误类型分布 (Top 5)
            | 错误归类 | 频次 | 涉及题目 |
            | :--- | :--- | :--- |
            | ... | ... | ... |
    
            ### 🧬 核心根因分析 (Root Cause Analysis)
            本次错题主要暴露出 **[数量]** 个维度的知识盲区：
    
            #### 根因 1：
            - **分析**：学生混淆了......
    
            #### 根因 2：
            - **分析**：......
            
            ......
            
            #### 根因 n：
            - **分析**：......
    
            ### 💡 针对性教学建议
            1. **针对 [根因1]**：建议讲解......
            2. **针对 [根因2]**：建议练习......
            ......
            n. **针对 [根因n]**：建议练习......
            """

    # 构建消息
    messages = [{"role": "system", "content": system_prompt}]

    if mode == "student" and history:
        messages.extend(history[-6:])

    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True,
            temperature=0.1
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"❌ 出错: {e}"
