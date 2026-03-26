import json
import os
import re
from neo4j import GraphDatabase
from openai import OpenAI
from backend.core.config import settings

API_KEY = settings.llm_api_key
BASE_URL = settings.llm_base_url
NEO4J_URI = settings.neo4j_uri
NEO4J_AUTH = settings.neo4j_auth
DB_NAME = settings.neo4j_db_name

# --- 步骤 1: 意图识别 (通用) ---
def extract_keywords_with_llm(client, user_input, history=[], trace=None):
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
        _append_trace(
            trace,
            "reasoning",
            "关键词提取",
            f"从输入中提取出 {len(keywords)} 个候选概念",
            details=[str(keyword) for keyword in keywords[:8]],
            stage="keyword_extraction",
            mode="student",
        )
        return keywords
    except Exception as e:
        print(f"   -> 意图识别出错: {e}")
        _append_trace(
            trace,
            "reasoning",
            "关键词提取失败",
            "关键词提取阶段出错，已回退为空列表",
            details=[str(e)],
            stage="keyword_extraction",
            mode="student",
        )
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


def _append_trace(trace, trace_type, title, summary, details=None, stage="", mode="student"):
    if trace is None:
        return
    trace.append({
        "type": trace_type,
        "title": title,
        "summary": summary,
        "details": details or [],
        "stage": stage,
        "mode": mode,
    })


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
    return json.dumps(fact, ensure_ascii=False)


def build_knowledge_text(context_knowledge):
    if not context_knowledge:
        return "（未检索到特定图谱路径）"
    return "\n".join(format_fact_for_display(item) for item in context_knowledge)


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

# 种子召回阶段：根据问题和关键词从图谱里找最值得扩展的初始节点。
def _query_seed_nodes(driver, question, keywords, limit_per_kw=3, max_total=4):
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

# student 模式的核心检索入口：种子召回 -> 关系裁剪 -> 实体裁剪 -> beam 保留 -> 停止判定。
def query_graph_with_reasoning(
    driver,
    client,
    question,
    keywords=None,
    max_depth=2,
    width=3,
    relation_top_k=None,
    entity_top_k=5,
    reasoning_trace=None,
    retrieval_trace=None
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
        keywords = extract_keywords_with_llm(
            client,
            question,
            history=[],
            trace=reasoning_trace
        )
    if not keywords:
        keywords = [question]
    keywords = _normalize_keywords(question, keywords, limit=max(3, width))
    _append_trace(
        reasoning_trace,
        "reasoning",
        "关键词归一化",
        f"检索前保留 {len(keywords)} 个关键词",
        details=keywords,
        stage="keyword_normalization",
        mode="student",
    )

    if relation_top_k is None:
        relation_top_k = width

    evidence = []
    seeds = _query_seed_nodes(
        driver,
        question,
        keywords,
        limit_per_kw=max(2, width),
        max_total=max(2, min(width, 3))
    )
    if not seeds:
        _append_trace(
            retrieval_trace,
            "retrieval",
            "种子召回",
            "未召回到可用种子节点",
            stage="seed_recall",
            mode="student",
        )
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
    _append_trace(
        retrieval_trace,
        "retrieval",
        "种子召回",
        f"召回 {len(seeds[:width])} 个种子节点",
        details=[f"{seed['name']} | {seed['match_type']} | score={seed['match_score']:.2f}" for seed in seeds[:width]],
        stage="seed_recall",
        mode="student",
    )

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
            _append_trace(
                retrieval_trace,
                "retrieval",
                f"Hop {hop} 关系裁剪",
                f"实体 {state['frontier_entity']} 保留 {len(selected_relations)} 条关系",
                details=[
                    f"{row['relation']} ({row['direction']}) score={row.get('relation_score', 0):.2f}"
                    for row in selected_relations
                ],
                stage="relation_prune",
                mode="student",
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
                _append_trace(
                    retrieval_trace,
                    "retrieval",
                    f"Hop {hop} 实体裁剪",
                    f"{state['frontier_entity']} 经关系 {relation_row['relation']} 保留 {len(selected_entities)} 个邻居",
                    details=[
                        f"{row['target']} score={row.get('entity_score', 0):.2f}"
                        for row in selected_entities
                    ],
                    stage="entity_score",
                    mode="student",
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
            _append_trace(
                retrieval_trace,
                "retrieval",
                f"Hop {hop} 扩展结束",
                "没有产生新的候选路径，检索提前停止",
                stage="beam_truncate",
                mode="student",
            )
            break
        next_beam.sort(key=lambda item: item["score"], reverse=True)
        beam = next_beam[:width]
        _append_trace(
            retrieval_trace,
            "retrieval",
            f"Hop {hop} Beam 保留",
            f"当前保留 {len(beam)} 条候选路径",
            details=[f"{state['path_text']} | score={state['score']:.2f}" for state in beam],
            stage="beam_truncate",
            mode="student",
        )

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
            _append_trace(
                reasoning_trace,
                "reasoning",
                "停止判定",
                f"检索在 hop={hop} 时停止，原因是 {decision}",
                details=[f"beam_size={len(beam)}"],
                stage="stop_decision",
                mode="student",
            )
            break

    return _dedupe_dicts(evidence, ("type", "path_text", "seed", "target", "text"))

def ask_deepseek_stream(client, user_input, context_knowledge, history=[]):
    """
    固定使用图谱证据生成学生辅导回答。
    """
    print("\n💬 [Step 3] AI 正在思考 (模式: student, 图谱: True) ...")

    knowledge_text = build_knowledge_text(context_knowledge)
    system_prompt = f"""
你是一名 **Java 智能辅导员**。你的目标是通过**根因分析**引导学生自己发现错误。

【图谱依赖链】
{knowledge_text}

=== 辅导策略 ===
1. **错误定位**：识别用户代码中的逻辑错误或异常。
2. **溯源诊断**：根据图谱，找到导致该错误的**最底层前置概念**。
3. **苏格拉底提问**：
   - 不要直接给代码。
   - 指出错误现象。
   - 针对底层概念提一个简短问题，测试学生是否真正理解。
"""

    messages = [{"role": "system", "content": system_prompt}]

    if history:
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
