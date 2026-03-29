import json
import os
import re
import time
from neo4j import GraphDatabase
from openai import OpenAI
from backend.core.config import settings

API_KEY = settings.llm_api_key
BASE_URL = settings.llm_base_url
MODEL_NAME = settings.llm_model_name
NEO4J_URI = settings.neo4j_uri
NEO4J_AUTH = settings.neo4j_auth
DB_NAME = settings.neo4j_db_name


def _now():
    return time.perf_counter()


def _log_timing(label, started_at, extra=""):
    elapsed = _now() - started_at
    suffix = f" | {extra}" if extra else ""
    print(f"[rag_timing] {label}: {elapsed:.2f}s{suffix}")
    return elapsed

# --- 步骤 1: 意图识别 (通用) ---
def extract_keywords_with_llm(client, user_input, history=[], trace=None):
    fn_started_at = _now()
    print(f"\n[Step 1] 正在分析输入内容...")

    context_entities = []
    if history:
        for msg in history[-4:]:
            if "keywords" in msg and isinstance(msg["keywords"], list):
                context_entities.extend(msg["keywords"])

    context_str = f"{list(set(context_entities))}" if context_entities else "无"

    prompt = f"""
    请从【用户输入】中提取核心的 Java 知识图谱实体 ID。

    【用户输入】
    "{user_input}"

    【任务要求】
    1. **批量处理**：如果输入包含多道错题或多个代码片段，请提取**所有**涉及的核心概念。
    2. **去噪**：忽略无关的描述性文字，只保留技术术语。
    3. **指代还原**：结合上下文 {context_str} 还原代词。
    4. **格式**：只返回 JSON 列表，如 ["ArrayList", "IndexOutOfBoundsException"]。
    """

    try:
        api_started_at = _now()
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        _log_timing("extract_keywords_with_llm.api", api_started_at, f"input_len={len(user_input)}")
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
        _log_timing("extract_keywords_with_llm.total", fn_started_at, f"keywords={len(keywords)}")
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
        _log_timing("extract_keywords_with_llm.total", fn_started_at, "failed")
        return []


# --- 步骤 2: 递归查询完整依赖链 (通用) ---
def query_dependency_chain(driver, keyword):
    print("\n[Step 2] 递归查询依赖链...")
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
    if fact_type == "selected_path":
        return (
            f"【已选路径 hop={fact.get('hop', '?')}】{fact.get('path_text', '')} "
            f"(score={fact.get('score', 0):.2f}, reason={fact.get('reason', '未提供')})"
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


def _extract_selected_path_fact(context_knowledge):
    for fact in context_knowledge or []:
        if isinstance(fact, dict) and fact.get("type") == "selected_path":
            return fact
    return None


def _format_path_text(path_rows):
    if not path_rows:
        return ""
    parts = [path_rows[0]["source"]]
    for row in path_rows:
        parts.append(f"-> ({row['relation']},{row['direction']}) -> {row['target']}")
    return " ".join(parts)


def _query_dependency_chain_evidence(driver, keyword):
    fn_started_at = _now()
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
    _log_timing("_query_dependency_chain_evidence", fn_started_at, f"keyword={keyword} chains={len(chains)}")
    return chains

# 种子召回阶段：根据问题和关键词从图谱里找最值得扩展的初始节点。
def _query_seed_nodes(driver, question, keywords, limit_per_kw=3, max_total=4):
    fn_started_at = _now()
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
        _log_timing("_query_seed_nodes", fn_started_at, f"keywords={len(keywords)} seeds=0")
        return []

    best_score = seeds[0]["final_seed_score"]
    filtered = [seed for seed in seeds if seed["final_seed_score"] >= max(0.35, best_score - 0.18)]
    result = filtered[:max_total]
    _log_timing("_query_seed_nodes", fn_started_at, f"keywords={len(keywords)} seeds={len(result)}")
    return result


def _query_candidate_relations(driver, entity_name, limit=12):
    fn_started_at = _now()
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
    _log_timing("_query_candidate_relations", fn_started_at, f"entity={entity_name} rows={len(rows)}")
    return rows


def relation_prune(client, question, current_entity, candidate_relations, top_k=3):
    fn_started_at = _now()
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
你是图检索规划器。请从候选关系里挑出最值得扩展的关系。
问题: {question}
当前实体: {current_entity}
候选关系:
{chr(10).join(brief)}

只返回 JSON 数组，每项格式:
{{"index": 整数, "score": 0到1}}
按 score 从高到低排序，最多返回 {top_k} 项。
"""
    try:
        api_started_at = _now()
        resp = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        _log_timing("relation_prune.api", api_started_at, f"entity={current_entity} candidates={len(candidate_relations)}")
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
            result = picked[:top_k]
            _log_timing("relation_prune.total", fn_started_at, f"entity={current_entity} selected={len(result)} mode=llm")
            return result
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
    result = scored[:top_k]
    _log_timing("relation_prune.total", fn_started_at, f"entity={current_entity} selected={len(result)} mode=fallback")
    return result


def _query_neighbors_by_relation(driver, entity_name, relation, direction, limit=8):
    fn_started_at = _now()
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
    result = _dedupe_dicts(rows, ("source", "relation", "direction", "target"))
    _log_timing("_query_neighbors_by_relation", fn_started_at, f"entity={entity_name} relation={relation} rows={len(result)}")
    return result


def entity_score(client, question, current_entity, relation_row, entity_candidates, top_k=5):
    fn_started_at = _now()
    if not entity_candidates:
        return []

    brief = []
    for i, row in enumerate(entity_candidates):
        brief.append(
            f"{i}. {row['source']} -[{row['relation']},{row['direction']}]-> {row['target']} | {row['target_desc']}"
        )

    prompt = f"""
请评估哪些邻居实体最能帮助回答问题。
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
        api_started_at = _now()
        resp = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        _log_timing("entity_score.api", api_started_at, f"entity={current_entity} relation={relation_row['relation']} candidates={len(entity_candidates)}")
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
            result = picked[:top_k]
            _log_timing("entity_score.total", fn_started_at, f"entity={current_entity} relation={relation_row['relation']} selected={len(result)} mode=llm")
            return result
    except Exception:
        pass

    scored = []
    for row in entity_candidates:
        raw = f"{row['source']} {row['relation']} {row['target']} {row['target_desc']}"
        score = _token_overlap_score(question, raw)
        scored.append({**row, "entity_score": score})
    scored.sort(key=lambda x: x["entity_score"], reverse=True)
    result = scored[:top_k]
    _log_timing("entity_score.total", fn_started_at, f"entity={current_entity} relation={relation_row['relation']} selected={len(result)} mode=fallback")
    return result


def _query_subgraph_nodes(driver, question, keywords, seeds, max_nodes=18):
    fn_started_at = _now()
    nodes = {}
    seed_names = [seed["name"] for seed in seeds]

    for seed in seeds:
        nodes[seed["name"]] = {
            "name": seed["name"],
            "desc": seed["desc"],
            "score": max(seed.get("final_seed_score", seed.get("match_score", 0.0)), seed.get("match_score", 0.0)),
            "source": "seed",
        }

    keyword_query = """
    MATCH (n:Knowledge)
    WITH n,
         CASE
             WHEN any(kw IN $keywords WHERE toLower(n.name) = toLower(kw)) THEN 4
             WHEN any(kw IN $keywords WHERE toLower(n.name) CONTAINS toLower(kw)) THEN 3
             WHEN any(kw IN $keywords WHERE toLower(coalesce(n.desc, "")) CONTAINS toLower(kw)) THEN 2
             ELSE 0
         END AS match_score
    WHERE match_score > 0
    RETURN n.name AS name,
           coalesce(n.desc, "无描述") AS desc,
           match_score
    ORDER BY match_score DESC, n.name ASC
    LIMIT $lim
    """
    neighbor_query = """
    UNWIND $seed_names AS seed_name
    MATCH (src:Knowledge {name: seed_name})-[r]-(nbr:Knowledge)
    RETURN src.name AS source,
           coalesce(src.desc, "无描述") AS source_desc,
           type(r) AS relation,
           CASE WHEN startNode(r) = src THEN "out" ELSE "in" END AS direction,
           nbr.name AS target,
           coalesce(nbr.desc, "无描述") AS target_desc
    LIMIT $lim
    """

    with driver.session(database=DB_NAME) as session:
        for record in session.run(keyword_query, keywords=keywords, lim=max(max_nodes * 2, 20)):
            name = record["name"]
            desc = record["desc"]
            score = 0.6 * (float(record["match_score"]) / 4.0) + 0.4 * _token_overlap_score(question, f"{name} {desc}")
            if name not in nodes or score > nodes[name]["score"]:
                nodes[name] = {"name": name, "desc": desc, "score": score, "source": "keyword"}

        if seed_names:
            for record in session.run(neighbor_query, seed_names=seed_names, lim=max(max_nodes * 4, 40)):
                target = record["target"]
                target_desc = record["target_desc"]
                source = record["source"]
                score = (
                    0.45 * _token_overlap_score(question, f"{target} {target_desc}")
                    + 0.35 * nodes.get(source, {}).get("score", 0.0)
                    + 0.20
                )
                if target not in nodes or score > nodes[target]["score"]:
                    nodes[target] = {"name": target, "desc": target_desc, "score": score, "source": "neighbor"}

    sorted_nodes = sorted(nodes.values(), key=lambda item: item["score"], reverse=True)
    result = sorted_nodes[:max_nodes]
    _log_timing("_query_subgraph_nodes", fn_started_at, f"keywords={len(keywords)} seeds={len(seeds)} nodes={len(result)}")
    return result


def _query_edges_between_nodes(driver, node_names):
    fn_started_at = _now()
    if not node_names:
        return []

    query = """
    UNWIND $node_names AS node_name
    MATCH (src:Knowledge {name: node_name})-[r]-(nbr:Knowledge)
    WHERE nbr.name IN $node_names
    RETURN src.name AS source,
           coalesce(src.desc, "无描述") AS source_desc,
           type(r) AS relation,
           CASE WHEN startNode(r) = src THEN "out" ELSE "in" END AS direction,
           nbr.name AS target,
           coalesce(nbr.desc, "无描述") AS target_desc
    """
    rows = []
    with driver.session(database=DB_NAME) as session:
        for rec in session.run(query, node_names=node_names):
            rows.append({
                "source": rec["source"],
                "source_desc": rec["source_desc"],
                "relation": rec["relation"],
                "direction": rec["direction"],
                "target": rec["target"],
                "target_desc": rec["target_desc"],
            })

    result = _dedupe_dicts(rows, ("source", "relation", "direction", "target"))
    _log_timing("_query_edges_between_nodes", fn_started_at, f"nodes={len(node_names)} edges={len(result)}")
    return result


def _enumerate_subgraph_paths(seed_names, edges, node_map, max_depth=2, max_paths=24):
    fn_started_at = _now()
    adjacency = {}
    for edge in edges:
        adjacency.setdefault(edge["source"], []).append(edge)

    candidates = []

    def dfs(seed_name, current_name, visited, path_rows):
        if len(candidates) >= max_paths:
            return
        if path_rows:
            target_name = path_rows[-1]["target"]
            target_desc = node_map.get(target_name, {}).get("desc", path_rows[-1].get("target_desc", "无描述"))
            avg_score = 0.0
            if path_rows:
                avg_score = sum(
                    node_map.get(row["target"], {}).get("score", 0.0)
                    for row in path_rows
                ) / len(path_rows)
            candidates.append({
                "seed": seed_name,
                "frontier_entity": target_name,
                "frontier_desc": target_desc,
                "path": [dict(row) for row in path_rows],
                "path_text": _format_path_text(path_rows),
                "score": avg_score,
            })
        if len(path_rows) >= max_depth:
            return

        for edge in adjacency.get(current_name, []):
            next_name = edge["target"]
            if next_name in visited:
                continue
            dfs(seed_name, next_name, visited | {next_name}, path_rows + [edge])

    for seed_name in seed_names:
        dfs(seed_name, seed_name, {seed_name}, [])

    uniq = _dedupe_dicts(candidates, ("seed", "path_text", "frontier_entity"))
    _log_timing("_enumerate_subgraph_paths", fn_started_at, f"seeds={len(seed_names)} paths={len(uniq)}")
    return uniq[:max_paths]


def _fallback_select_paths(question, candidate_paths, top_k):
    scored = []
    for path in candidate_paths:
        text = " ".join(
            [
                path.get("seed", ""),
                path.get("frontier_entity", ""),
                path.get("frontier_desc", ""),
                path.get("path_text", ""),
            ]
        )
        score = 0.65 * _token_overlap_score(question, text) + 0.35 * path.get("score", 0.0)
        scored.append({**path, "llm_score": score, "selection_reason": "根据问题与路径文本重叠度进行本地排序"})
    scored.sort(key=lambda item: item["llm_score"], reverse=True)
    return scored[:top_k]


def _select_paths_from_subgraph(client, question, candidate_paths, top_k=3):
    fn_started_at = _now()
    if not candidate_paths:
        return []
    if len(candidate_paths) <= top_k:
        result = [{**path, "llm_score": path.get("score", 0.0), "selection_reason": "候选路径数量较少，直接保留"} for path in candidate_paths]
        _log_timing("_select_paths_from_subgraph.total", fn_started_at, f"paths={len(result)} mode=shortcut")
        return result

    brief = []
    for idx, path in enumerate(candidate_paths):
        brief.append(
            f"{idx}. seed={path['seed']} | path={path['path_text']} | "
            f"target_desc={path.get('frontier_desc', '无描述')}"
        )

    prompt = f"""
你是 Java 教学知识图谱上的路径推理器。
请根据问题，从候选路径中选出最能解释问题根因、最适合用于教学辅导的路径。

问题:
{question}

候选路径:
{chr(10).join(brief)}

只返回 JSON 数组，每项格式如下：
{{"index": 整数, "score": 0到1, "reason": "简短原因"}}

要求：
1. 优先选择能直接解释异常、概念误区、底层依赖关系的路径。
2. 最多返回 {top_k} 条路径。
3. 按 score 从高到低排序。
"""
    try:
        api_started_at = _now()
        resp = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        _log_timing("_select_paths_from_subgraph.api", api_started_at, f"candidates={len(candidate_paths)}")
        content = resp.choices[0].message.content
        selected = _safe_json_extract(content, [])
        picked = []
        for item in selected:
            idx = item.get("index")
            score = _safe_float(item.get("score", 0))
            if isinstance(idx, int) and 0 <= idx < len(candidate_paths):
                picked.append({
                    **candidate_paths[idx],
                    "llm_score": score,
                    "selection_reason": item.get("reason", ""),
                })
        if picked:
            picked.sort(key=lambda row: row["llm_score"], reverse=True)
            result = picked[:top_k]
            _log_timing("_select_paths_from_subgraph.total", fn_started_at, f"paths={len(result)} mode=llm")
            return result
    except Exception as e:
        print(f"子图路径选择出错，回退本地排序: {e}")

    result = _fallback_select_paths(question, candidate_paths, top_k)
    _log_timing("_select_paths_from_subgraph.total", fn_started_at, f"paths={len(result)} mode=fallback")
    return result


def _fallback_select_weak_points(selected_path_fact, dependency_chains, max_points=2):
    picked = []
    seen = set()

    target = selected_path_fact.get("target")
    if target:
        picked.append({
            "node_name": target,
            "reason": "这是一条已选路径的终点，也是当前问题最直接暴露出的知识薄弱点。",
        })
        seen.add(target)

    for chain in dependency_chains:
        for node_name in reversed(chain.get("nodes", [])):
            if not node_name or node_name in seen or node_name == selected_path_fact.get("seed"):
                continue
            picked.append({
                "node_name": node_name,
                "reason": "这是支撑当前路径的底层依赖概念，优先补齐会更有帮助。",
            })
            seen.add(node_name)
            if len(picked) >= max_points:
                return picked[:max_points]

    return picked[:max_points]


def _select_weak_points_from_path(client, question, selected_path_fact, dependency_chains, max_points=2):
    fn_started_at = _now()
    if not selected_path_fact:
        return []

    candidate_nodes = []
    seen = set()

    for node_name in [selected_path_fact.get("seed"), selected_path_fact.get("source"), selected_path_fact.get("target")]:
        if node_name and node_name not in seen:
            candidate_nodes.append(node_name)
            seen.add(node_name)

    for chain in dependency_chains:
        for node_name in chain.get("nodes", []):
            if node_name and node_name not in seen:
                candidate_nodes.append(node_name)
                seen.add(node_name)

    if not candidate_nodes:
        return []

    prompt = f"""
你是一名 Java 学习诊断助手。请根据问题和已选路径，从候选知识节点中挑出 1 到 2 个最主要的薄弱点。

问题:
{question}

已选路径:
{selected_path_fact.get("path_text", "")}

路径选择原因:
{selected_path_fact.get("reason", "未提供")}

候选节点:
{json.dumps(candidate_nodes, ensure_ascii=False)}

只返回 JSON 数组，每项格式如下：
{{"node_name": "节点名", "reason": "为什么这是主要薄弱点"}}

要求：
1. 最多返回 {max_points} 个。
2. 优先返回真正需要补的核心概念，不要返回太多相近节点。
3. node_name 必须来自候选节点列表。
"""
    try:
        api_started_at = _now()
        resp = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        _log_timing("_select_weak_points_from_path.api", api_started_at, f"candidates={len(candidate_nodes)}")
        content = resp.choices[0].message.content
        selected = _safe_json_extract(content, [])
        picked = []
        used = set()
        for item in selected:
            node_name = item.get("node_name")
            if node_name in candidate_nodes and node_name not in used:
                picked.append({
                    "node_name": node_name,
                    "reason": item.get("reason", ""),
                })
                used.add(node_name)
            if len(picked) >= max_points:
                break
        if picked:
            _log_timing("_select_weak_points_from_path.total", fn_started_at, f"points={len(picked)} mode=llm")
            return picked
    except Exception as e:
        print(f"薄弱点选择出错，回退规则选择: {e}")

    result = _fallback_select_weak_points(selected_path_fact, dependency_chains, max_points=max_points)
    _log_timing("_select_weak_points_from_path.total", fn_started_at, f"points={len(result)} mode=fallback")
    return result


# student 模式的核心检索入口：关键词提取 -> 子图召回 -> 一次性路径选择。
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
    fn_started_at = _now()
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
        _log_timing("query_graph_with_reasoning.total", fn_started_at, "no_seeds")
        _append_trace(
            retrieval_trace,
            "retrieval",
            "种子召回",
            "未召回到可用种子节点",
            stage="seed_recall",
            mode="student",
        )
        return []

    for seed in seeds[:width]:
        evidence.append({
            "type": "seed",
            "seed": seed["name"],
            "keyword": seed["keyword"],
            "desc": seed["desc"],
            "score": seed["match_score"],
            "match_type": seed["match_type"],
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

    subgraph_nodes = _query_subgraph_nodes(
        driver,
        question,
        keywords,
        seeds,
        max_nodes=max(width * max_depth * 3, 12),
    )
    node_map = {node["name"]: node for node in subgraph_nodes}
    _append_trace(
        retrieval_trace,
        "retrieval",
        "子图召回",
        f"召回 {len(subgraph_nodes)} 个相关节点",
        details=[f"{node['name']} score={node['score']:.2f}" for node in subgraph_nodes[:12]],
        stage="subgraph_recall",
        mode="student",
    )

    subgraph_edges = _query_edges_between_nodes(driver, list(node_map.keys()))
    _append_trace(
        retrieval_trace,
        "retrieval",
        "子图边召回",
        f"召回 {len(subgraph_edges)} 条相关边",
        details=[
            f"{edge['source']} -[{edge['relation']},{edge['direction']}]-> {edge['target']}"
            for edge in subgraph_edges[:12]
        ],
        stage="subgraph_edges",
        mode="student",
    )

    candidate_paths = _enumerate_subgraph_paths(
        [seed["name"] for seed in seeds[:width]],
        subgraph_edges,
        node_map,
        max_depth=max_depth,
        max_paths=max(width * 8, 16),
    )
    max_candidate_hops = max((len(path.get("path", [])) for path in candidate_paths), default=0)
    print(
        "[rag_timing] subgraph_summary: "
        f"nodes={len(subgraph_nodes)} "
        f"edges={len(subgraph_edges)} "
        f"candidate_paths={len(candidate_paths)} "
        f"max_candidate_hops={max_candidate_hops}"
    )
    _append_trace(
        retrieval_trace,
        "retrieval",
        "候选路径生成",
        f"从子图中生成 {len(candidate_paths)} 条候选路径",
        details=[path["path_text"] for path in candidate_paths[:12]],
        stage="path_generation",
        mode="student",
    )

    selected_paths = _select_paths_from_subgraph(
        client,
        question,
        candidate_paths,
        top_k=1,
    )
    _append_trace(
        retrieval_trace,
        "retrieval",
        "路径选择",
        f"大模型最终保留 {len(selected_paths)} 条路径",
        details=[
            f"{path['path_text']} | score={path.get('llm_score', path.get('score', 0.0)):.2f} | reason={path.get('selection_reason', '未提供')}"
            for path in selected_paths
        ],
        stage="path_selection",
        mode="student",
    )

    selected_path_fact = None
    selected_path_dependency_chains = []

    for path in selected_paths:
        last_row = path["path"][-1] if path["path"] else None
        if not last_row:
            continue
        selected_path_fact = {
            "type": "selected_path",
            "seed": path["seed"],
            "hop": len(path["path"]),
            "source": last_row["source"],
            "relation": last_row["relation"],
            "direction": last_row["direction"],
            "target": last_row["target"],
            "target_desc": last_row["target_desc"],
            "score": path.get("llm_score", path.get("score", 0.0)),
            "path_text": path["path_text"],
            "reason": path.get("selection_reason", ""),
        }
        evidence.append(selected_path_fact)
        evidence.append({
            "type": "path",
            "seed": path["seed"],
            "hop": len(path["path"]),
            "source": last_row["source"],
            "relation": last_row["relation"],
            "direction": last_row["direction"],
            "target": last_row["target"],
            "target_desc": last_row["target_desc"],
            "relation_score": 0.0,
            "entity_score": path.get("llm_score", path.get("score", 0.0)),
            "score": path.get("llm_score", path.get("score", 0.0)),
            "path_text": path["path_text"],
        })
        for chain in _query_dependency_chain_evidence(driver, last_row["target"]):
            selected_path_dependency_chains.append(chain)
            evidence.append(chain)

    weak_points = _select_weak_points_from_path(
        client,
        question,
        selected_path_fact,
        selected_path_dependency_chains,
        max_points=2,
    )
    if weak_points:
        evidence.extend(
            {
                "type": "weak_point",
                "node_name": item["node_name"],
                "reason": item.get("reason", ""),
            }
            for item in weak_points
        )
        _append_trace(
            reasoning_trace,
            "reasoning",
            "主要薄弱点判定",
            f"根据已选路径收敛出 {len(weak_points)} 个主要薄弱点",
            details=[f"{item['node_name']} | {item.get('reason', '')}" for item in weak_points],
            stage="weak_point_selection",
            mode="student",
        )

    evidence.append({
        "type": "summary",
        "text": (
            f"subgraph_nodes={len(subgraph_nodes)}, "
            f"subgraph_edges={len(subgraph_edges)}, "
            f"candidate_paths={len(candidate_paths)}, "
            f"selected_paths={len(selected_paths)}"
        ),
    })
    _append_trace(
        reasoning_trace,
        "reasoning",
        "子图路径推理",
        "先召回相关子图，再由大模型一次性选择最优路径",
        details=[
            f"nodes={len(subgraph_nodes)}",
            f"edges={len(subgraph_edges)}",
            f"candidate_paths={len(candidate_paths)}",
            f"selected_paths={len(selected_paths)}",
        ],
        stage="subgraph_reasoning",
        mode="student",
    )

    result = _dedupe_dicts(evidence, ("type", "path_text", "seed", "target", "text"))
    _log_timing("query_graph_with_reasoning.total", fn_started_at, f"facts={len(result)}")
    return result

def ask_deepseek_stream(client, user_input, context_knowledge, history=[]):
    """
    固定使用图谱证据生成学生辅导回答。
    """
    print("\n💬 [Step 3] AI 正在思考 (模式: student, 图谱: True) ...")

    selected_path_fact = _extract_selected_path_fact(context_knowledge)
    if selected_path_fact:
        focused_knowledge = [selected_path_fact]
        focused_knowledge.extend(
            fact
            for fact in context_knowledge
            if isinstance(fact, dict)
            and fact.get("type") == "dependency_chain"
            and fact.get("target") == selected_path_fact.get("target")
        )
        knowledge_text = build_knowledge_text(focused_knowledge)
        path_instruction = (
            f"你必须优先围绕这条已选路径来解释问题：{selected_path_fact.get('path_text', '')}。"
            f" 这条路径被选中的原因是：{selected_path_fact.get('reason', '未提供')}。"
        )
    else:
        knowledge_text = build_knowledge_text(context_knowledge)
        path_instruction = "如果存在多条证据，请优先围绕最能解释根因的那条路径组织回答。"
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
4. **围绕已选路径回答**：{path_instruction}
"""

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        messages.extend(history[-6:])

    messages.append({"role": "user", "content": user_input})

    try:
        api_started_at = _now()
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=messages,
            stream=True,
            temperature=0.1
        )
        _log_timing("ask_deepseek_stream.api_create", api_started_at, f"history={len(history)} facts={len(context_knowledge)}")
        stream_started_at = _now()
        first_chunk_logged = False
        for chunk in response:
            if chunk.choices[0].delta.content:
                if not first_chunk_logged:
                    _log_timing("ask_deepseek_stream.first_chunk", stream_started_at)
                    first_chunk_logged = True
                yield chunk.choices[0].delta.content
        _log_timing("ask_deepseek_stream.stream_total", stream_started_at)
    except Exception as e:
        yield f"❌ 出错: {e}"
