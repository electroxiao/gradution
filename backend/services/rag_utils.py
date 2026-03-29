import json
import re
import time

def _now():
    return time.perf_counter()

def _log_timing(label, started_at, extra=""):
    elapsed = _now() - started_at
    suffix = f" | {extra}" if extra else ""
    print(f"[rag_timing] {label}: {elapsed:.2f}s{suffix}")
    return elapsed

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

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
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
    return normalized[:limit]

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
        return f"【种子实体】{fact.get('seed')} (match={fact.get('match_type', 'unknown')}, score={fact.get('score', 0):.2f}): {fact.get('desc', '无描述')}"
    if fact_type == "path":
        return f"【ToG路径 hop={fact.get('hop', '?')}】{fact.get('path_text', '')} (score={fact.get('score', 0):.2f}, relation={fact.get('relation_score', 0):.2f}, entity={fact.get('entity_score', 0):.2f})"
    if fact_type == "selected_path":
        return f"【已选路径 hop={fact.get('hop', '?')}】{fact.get('path_text', '')} (score={fact.get('score', 0):.2f}, reason={fact.get('reason', '未提供')})"
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