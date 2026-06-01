import json

from backend.core.config import settings
from backend.services.rag_utils import (
    _append_trace,
    _dedupe_dicts,
    _extract_selected_path_fact,
    _format_path_text,
    _log_timing,
    _normalize_keywords,
    _now,
    _safe_float,
    _safe_json_extract,
    _seed_question_relevance,
    _token_overlap_score,
    build_knowledge_text,
)

DB_NAME = settings.neo4j_db_name


def extract_keywords_with_llm(client, user_input, history=None, trace=None):
    fn_started_at = _now()
    print("\n[Step 1] 正在分析输入内容...")
    history = history or []

    context_entities = []
    for message in history[-4:]:
        keywords = message.get("keywords")
        if isinstance(keywords, list):
            context_entities.extend(keywords)

    context_str = f"{list(set(context_entities))}" if context_entities else "无"
    prompt = f"""
请从【用户输入】中提取核心的 Java 知识图谱实体 ID。

【用户输入】
"{user_input}"

【任务要求】
1. 如果输入包含多道错题或多个代码片段，请提取所有涉及的核心概念。
2. 忽略无关的描述性文字，只保留技术术语。
3. 结合上下文 {context_str} 还原代词。
4. 只返回 JSON 列表，如 ["ArrayList", "IndexOutOfBoundsException"]。
"""

    try:
        api_started_at = _now()
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        _log_timing("extract_keywords_with_llm.api", api_started_at, f"input_len={len(user_input)}")
        content = response.choices[0].message.content or "[]"
        keywords = _safe_json_extract(content, [user_input])
        if not isinstance(keywords, list):
            keywords = [user_input]

        normalized = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
        print(f"   -> 识别关键词: {normalized}")
        _append_trace(
            trace,
            "reasoning",
            "关键词提取",
            f"从输入中提取出 {len(normalized)} 个候选概念",
            details=normalized[:8],
            stage="keyword_extraction",
        )
        _log_timing("extract_keywords_with_llm.total", fn_started_at, f"keywords={len(normalized)}")
        return normalized
    except Exception as error:
        print(f"   -> 意图识别出错: {error}")
        _append_trace(
            trace,
            "reasoning",
            "关键词提取失败",
            "关键词提取阶段出错，已回退为空列表",
            details=[str(error)],
            stage="keyword_extraction",
        )
        _log_timing("extract_keywords_with_llm.total", fn_started_at, "failed")
        return []


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
            for record in session.run(query, kw=keyword):
                path = record["path"]
                nodes = [node["name"] for node in path.nodes]
                root_node = path.nodes[-1]
                chains.append(
                    {
                        "type": "dependency_chain",
                        "target": keyword,
                        "nodes": nodes,
                        "root_desc": root_node.get("desc", "无描述"),
                        "path_text": " -> (依赖) -> ".join(nodes),
                    }
                )
    except Exception as error:
        print(f"查询依赖链出错: {error}")
    _log_timing("_query_dependency_chain_evidence", fn_started_at, f"keyword={keyword} chains={len(chains)}")
    return chains


def _query_seed_nodes(driver, question, keywords, limit_per_kw=3, max_total=4):
    fn_started_at = _now()
    seeds = []
    query = """
    MATCH (n:Knowledge)
    WITH n,
         CASE
             WHEN toLower(n.name) = toLower($kw) THEN 1.0
             WHEN toLower(n.name) CONTAINS toLower($kw) THEN 0.75
             WHEN toLower(coalesce(n.desc, "")) CONTAINS toLower($kw) THEN 0.5
             ELSE 0.0
         END AS match_score
    WHERE match_score > 0
    RETURN n.name AS name, coalesce(n.desc, "无描述") AS `desc`, match_score
    ORDER BY match_score DESC, n.name ASC
    LIMIT $lim
    """
    with driver.session(database=DB_NAME) as session:
        for keyword in keywords:
            for record in session.run(query, kw=keyword, lim=limit_per_kw):
                match_score = float(record["match_score"])
                match_type = "exact_name" if match_score >= 1.0 else "name_contains" if match_score >= 0.75 else "desc_match"
                seeds.append(
                    {
                        "name": record["name"],
                        "desc": record["desc"],
                        "keyword": keyword,
                        "match_score": match_score,
                        "match_type": match_type,
                    }
                )
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
    WITH n, CASE
             WHEN any(kw IN $keywords WHERE toLower(n.name) = toLower(kw)) THEN 1.0
             WHEN any(kw IN $keywords WHERE toLower(n.name) CONTAINS toLower(kw)) THEN 0.75
             WHEN any(kw IN $keywords WHERE toLower(coalesce(n.desc, "")) CONTAINS toLower(kw)) THEN 0.5
             ELSE 0.0 END AS match_score
    WHERE match_score > 0
    RETURN n.name AS name, coalesce(n.desc, "无描述") AS desc, match_score
    ORDER BY match_score DESC, n.name ASC LIMIT $lim
    """
    neighbor_query = """
    UNWIND $seed_names AS seed_name
    MATCH (src:Knowledge {name: seed_name})-[r]-(nbr:Knowledge)
    RETURN src.name AS source, coalesce(src.desc, "无描述") AS source_desc, type(r) AS relation,
           CASE WHEN startNode(r) = src THEN "out" ELSE "in" END AS direction,
           nbr.name AS target, coalesce(nbr.desc, "无描述") AS target_desc LIMIT $lim
    """

    with driver.session(database=DB_NAME) as session:
        for record in session.run(keyword_query, keywords=keywords, lim=max(max_nodes * 2, 20)):
            name = record["name"]
            desc = record["desc"]
            score = 0.6 * float(record["match_score"]) + 0.4 * _token_overlap_score(question, f"{name} {desc}")
            if name not in nodes or score > nodes[name]["score"]:
                nodes[name] = {"name": name, "desc": desc, "score": score, "source": "keyword"}

        if seed_names:
            for record in session.run(neighbor_query, seed_names=seed_names, lim=max(max_nodes * 4, 40)):
                target = record["target"]
                target_desc = record["target_desc"]
                source = record["source"]
                score = 0.45 * _token_overlap_score(question, f"{target} {target_desc}") + 0.35 * nodes.get(source, {}).get("score", 0.0) + 0.20
                if target not in nodes or score > nodes[target]["score"]:
                    nodes[target] = {"name": target, "desc": target_desc, "score": score, "source": "neighbor"}

    result = sorted(nodes.values(), key=lambda item: item["score"], reverse=True)[:max_nodes]
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
    RETURN src.name AS source, coalesce(src.desc, "无描述") AS source_desc, type(r) AS relation,
           CASE WHEN startNode(r) = src THEN "out" ELSE "in" END AS direction,
           nbr.name AS target, coalesce(nbr.desc, "无描述") AS target_desc
    """
    rows = []
    with driver.session(database=DB_NAME) as session:
        for record in session.run(query, node_names=node_names):
            rows.append(
                {
                    "source": record["source"],
                    "source_desc": record["source_desc"],
                    "relation": record["relation"],
                    "direction": record["direction"],
                    "target": record["target"],
                    "target_desc": record["target_desc"],
                }
            )

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
            avg_score = sum(node_map.get(row["target"], {}).get("score", 0.0) for row in path_rows) / len(path_rows)
            candidates.append(
                {
                    "seed": seed_name,
                    "frontier_entity": target_name,
                    "frontier_desc": target_desc,
                    "path": [dict(row) for row in path_rows],
                    "path_text": _format_path_text(path_rows),
                    "score": avg_score,
                }
            )
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
        text = " ".join([path.get("seed", ""), path.get("frontier_entity", ""), path.get("frontier_desc", ""), path.get("path_text", "")])
        score = 0.65 * _token_overlap_score(question, text) + 0.35 * path.get("score", 0.0)
        scored.append({**path, "llm_score": score, "selection_reason": "根据问题与路径文本重叠度进行本地排序"})
    scored.sort(key=lambda item: item["llm_score"], reverse=True)
    return scored[:top_k]


def _select_paths_from_subgraph(client, question, candidate_paths, top_k=3):
    fn_started_at = _now()
    if not candidate_paths:
        return []
    if len(candidate_paths) <= top_k:
        result = [
            {**path, "llm_score": path.get("score", 0.0), "selection_reason": "候选路径数量较少，直接保留"}
            for path in candidate_paths
        ]
        _log_timing("_select_paths_from_subgraph.total", fn_started_at, f"paths={len(result)} mode=shortcut")
        return result

    brief = [
        f"{idx}. seed={path['seed']} | path={path['path_text']} | target_desc={path.get('frontier_desc', '无描述')}"
        for idx, path in enumerate(candidate_paths)
    ]
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
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        _log_timing("_select_paths_from_subgraph.api", api_started_at, f"candidates={len(candidate_paths)}")
        selected = _safe_json_extract(response.choices[0].message.content, [])
        picked = []
        for item in selected:
            idx = item.get("index")
            score = _safe_float(item.get("score", 0))
            if isinstance(idx, int) and 0 <= idx < len(candidate_paths):
                picked.append({**candidate_paths[idx], "llm_score": score, "selection_reason": item.get("reason", "")})
        if picked:
            picked.sort(key=lambda row: row["llm_score"], reverse=True)
            result = picked[:top_k]
            _log_timing("_select_paths_from_subgraph.total", fn_started_at, f"paths={len(result)} mode=llm")
            return result
    except Exception as error:
        print(f"子图路径选择出错，回退本地排序: {error}")

    result = _fallback_select_paths(question, candidate_paths, top_k)
    _log_timing("_select_paths_from_subgraph.total", fn_started_at, f"paths={len(result)} mode=fallback")
    return result


def query_graph_with_reasoning(driver, client, question, keywords=None, max_depth=2, width=3, reasoning_trace=None, retrieval_trace=None):
    fn_started_at = _now()
    print("\n[Step 2] 正在检索图谱依赖链并分析子图...")

    if keywords is None:
        keywords = extract_keywords_with_llm(client, question, history=[], trace=reasoning_trace)
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
    )

    evidence = []
    seeds = _query_seed_nodes(driver, question, keywords, limit_per_kw=max(2, width), max_total=max(2, min(width, 3)))
    if not seeds:
        _log_timing("query_graph_with_reasoning.total", fn_started_at, "no_seeds")
        _append_trace(retrieval_trace, "retrieval", "种子召回", "未召回到可用种子节点", stage="seed_recall")
        return []

    for seed in seeds[:width]:
        evidence.append(
            {
                "type": "seed",
                "seed": seed["name"],
                "keyword": seed["keyword"],
                "desc": seed["desc"],
                "score": seed["match_score"],
                "match_type": seed["match_type"],
            }
        )

    subgraph_nodes = _query_subgraph_nodes(driver, question, keywords, seeds, max_nodes=max(width * max_depth * 3, 12))
    node_map = {node["name"]: node for node in subgraph_nodes}
    subgraph_edges = _query_edges_between_nodes(driver, list(node_map.keys()))
    candidate_paths = _enumerate_subgraph_paths(
        [seed["name"] for seed in seeds[:width]],
        subgraph_edges,
        node_map,
        max_depth=max_depth,
        max_paths=max(width * 8, 16),
    )
    selected_paths = _select_paths_from_subgraph(client, question, candidate_paths, top_k=1)

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
        evidence.append(
            {
                "type": "path",
                "seed": path["seed"],
                "hop": len(path["path"]),
                "source": last_row["source"],
                "relation": last_row["relation"],
                "direction": last_row["direction"],
                "target": last_row["target"],
                "target_desc": last_row["target_desc"],
                "score": path.get("llm_score", path.get("score", 0.0)),
                "path_text": path["path_text"],
            }
        )
        for chain in _query_dependency_chain_evidence(driver, last_row["target"]):
            selected_path_dependency_chains.append(chain)
            evidence.append(chain)

    if selected_path_fact:
        evidence.append(
            {
                "type": "weak_point",
                "node_name": selected_path_fact["target"],
                "reason": "该节点位于已选图谱路径末端，可作为本轮问题暴露出的重点概念。",
            }
        )

    evidence.append(
        {
            "type": "summary",
            "text": f"subgraph_nodes={len(subgraph_nodes)}, subgraph_edges={len(subgraph_edges)}, candidate_paths={len(candidate_paths)}, selected_paths={len(selected_paths)}",
        }
    )
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
    )

    result = _dedupe_dicts(evidence, ("type", "path_text", "seed", "target", "text", "node_name"))
    _log_timing("query_graph_with_reasoning.total", fn_started_at, f"facts={len(result)}")
    return result


def ask_deepseek_stream(client, user_input, context_knowledge, history=None):
    print("\n[Step 3] AI 正在思考 (模式: student, 图谱: True) ...")
    history = history or []

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
        path_instruction = f"你必须优先围绕这条已选路径来解释问题：{selected_path_fact.get('path_text', '')}。这条路径被选中的原因是：{selected_path_fact.get('reason', '未提供')}。"
    else:
        knowledge_text = build_knowledge_text(context_knowledge)
        path_instruction = "如果存在多条证据，请优先围绕最能解释根因的那条路径组织回答。"

    system_prompt = f"""
你是一名 Java 智能辅导员。你的目标是通过根因分析引导学生理解问题。

【知识图谱检索结果】
{knowledge_text}

【辅导策略】
1. 先回答学生当前问题，不绕弯子。
2. 结合知识图谱结果说明相关概念、依赖关系或前置知识。
3. 不要直接替学生完成整份作业，可以给短示例和检查步骤。
4. {path_instruction}
"""
    messages = [{"role": "system", "content": system_prompt}]
    for item in history[-6:]:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_input})

    api_started_at = _now()
    response = client.chat.completions.create(
        model=settings.llm_model_name,
        messages=messages,
        stream=True,
        temperature=0.1,
    )
    _log_timing("ask_deepseek_stream.api_create", api_started_at, f"history={len(history)} facts={len(context_knowledge)}")
    stream_started_at = _now()
    first_chunk_logged = False
    for chunk in response:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        content = getattr(delta, "content", None)
        if content:
            if not first_chunk_logged:
                _log_timing("ask_deepseek_stream.first_chunk", stream_started_at)
                first_chunk_logged = True
            yield content
    _log_timing("ask_deepseek_stream.stream_total", stream_started_at)
