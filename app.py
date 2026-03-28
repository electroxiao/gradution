import json
import os
import uuid
import importlib.util
from pathlib import Path
from datetime import datetime

import graphviz
import streamlit as st
from neo4j import GraphDatabase
from openai import OpenAI


def load_legacy_backend():
    backend_path = Path(__file__).with_name("backend.py")
    spec = importlib.util.spec_from_file_location("legacy_backend", backend_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


backend = load_legacy_backend()


st.set_page_config(page_title="Java 智能编程导师", page_icon="🎓", layout="wide")
HISTORY_FILE = "chat_history.json"


@st.cache_resource
def init_connections():
    try:
        driver = GraphDatabase.driver(backend.NEO4J_URI, auth=backend.NEO4J_AUTH)
        client = OpenAI(api_key=backend.API_KEY, base_url=backend.BASE_URL)
        return driver, client
    except Exception as e:
        st.error(f"连接失败: {e}")
        return None, None


driver, client = init_connections()


def load_history_from_file():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_history_to_file():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.all_chats, f, ensure_ascii=False, indent=2)


if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_history_from_file()

if (
    "current_chat_id" not in st.session_state
    or st.session_state.current_chat_id not in st.session_state.all_chats
):
    if st.session_state.all_chats:
        st.session_state.current_chat_id = list(st.session_state.all_chats.keys())[0]
    else:
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {
            "title": "新对话",
            "messages": [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        st.session_state.current_chat_id = new_id

current_chat = st.session_state.all_chats[st.session_state.current_chat_id]


def render_trace_panel(title, trace_items):
    if not trace_items:
        return
    with st.expander(title):
        for item in trace_items:
            line = item.get("summary", "")
            if item.get("stage"):
                line = f"`{item['stage']}` {line}"
            st.markdown(f"**{item.get('title', '过程事件')}**")
            if line:
                st.markdown(line)
            details = item.get("details") or []
            for detail in details:
                st.markdown(f"- {detail}")


def draw_dependency_graph(facts):
    if not facts:
        return None

    graph = graphviz.Digraph()
    graph.attr(rankdir="BT")
    graph.attr("node", shape="box", style="filled", fillcolor="#f0f2f6", color="#bdc3c7")
    added_edges = set()
    edge_count = 0

    for fact in facts:
        if isinstance(fact, dict):
            if fact.get("type") == "dependency_chain":
                nodes = [n.strip() for n in fact.get("nodes", []) if n.strip()]
                if len(nodes) > 1:
                    for i in range(len(nodes) - 1):
                        source = nodes[i]
                        target = nodes[i + 1]
                        edge_signature = (source, target, "依赖")
                        if edge_signature not in added_edges:
                            graph.node(source, label=source)
                            graph.node(target, label=target, fillcolor="#d4e6f1")
                            graph.edge(source, target, label="依赖", color="#808080")
                            added_edges.add(edge_signature)
                            edge_count += 1
            elif fact.get("type") == "path":
                source = fact.get("source")
                target = fact.get("target")
                relation = fact.get("relation", "关联")
                if source and target:
                    edge_signature = (source, target, relation)
                    if edge_signature not in added_edges:
                        graph.node(source, label=source)
                        graph.node(target, label=target, fillcolor="#d4e6f1")
                        graph.edge(source, target, label=relation, color="#5d6d7e")
                        added_edges.add(edge_signature)
                        edge_count += 1
        elif isinstance(fact, str) and "【完整溯源】" in fact:
            clean_fact = fact.replace("【完整溯源】", "").strip()
            if " (底层概念" in clean_fact:
                clean_fact = clean_fact.split(" (底层概念")[0]
            elif "(底层概念" in clean_fact:
                clean_fact = clean_fact.split("(底层概念")[0]
            nodes = [n.strip() for n in clean_fact.split(" -> (依赖) -> ") if n.strip()]
            if len(nodes) > 1:
                for i in range(len(nodes) - 1):
                    source = nodes[i]
                    target = nodes[i + 1]
                    edge_signature = (source, target, "依赖")
                    if edge_signature not in added_edges:
                        graph.node(source, label=source)
                        graph.node(target, label=target, fillcolor="#d4e6f1")
                        graph.edge(source, target, label="依赖", color="#808080")
                        added_edges.add(edge_signature)
                        edge_count += 1

    return graph if edge_count > 0 else None


with st.sidebar:
    st.title("🗂️ 对话列表")
    st.divider()

    st.markdown("### 🕸️ 图检索配置")
    rag_depth = st.slider(
        "推理深度",
        min_value=1,
        max_value=4,
        value=2,
        step=1,
        help="每轮从当前实体继续扩展多少跳。",
    )
    rag_width = st.slider(
        "每跳保留候选数",
        min_value=1,
        max_value=8,
        value=3,
        step=1,
        help="每一跳由大模型筛选后保留的候选数量。",
    )
    st.caption("✅ 当前固定使用知识图谱辅导流程。")

    st.divider()

    if st.button("➕ 新建对话", use_container_width=True, type="secondary"):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {
            "title": "新对话",
            "messages": [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        st.session_state.current_chat_id = new_id
        save_history_to_file()
        st.rerun()

    st.markdown("---")
    sorted_chat_ids = sorted(
        st.session_state.all_chats.keys(),
        key=lambda k: st.session_state.all_chats[k].get("created_at", ""),
        reverse=True,
    )
    for chat_id in sorted_chat_ids:
        chat_data = st.session_state.all_chats[chat_id]
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            label = (
                f"🧵 {chat_data['title']}"
                if chat_id == st.session_state.current_chat_id
                else chat_data["title"]
            )
            if st.button(
                label,
                key=f"btn_{chat_id}",
                use_container_width=True,
                type="secondary" if chat_id != st.session_state.current_chat_id else "primary",
            ):
                st.session_state.current_chat_id = chat_id
                st.rerun()
        with col2:
            with st.popover("⋯", use_container_width=True):
                new_name = st.text_input("标题", value=chat_data["title"], key=f"input_{chat_id}")
                if st.button("💾", key=f"save_{chat_id}"):
                    st.session_state.all_chats[chat_id]["title"] = new_name
                    save_history_to_file()
                    st.rerun()
                if st.button("🗑️", key=f"del_{chat_id}", type="primary"):
                    del st.session_state.all_chats[chat_id]
                    save_history_to_file()
                    if chat_id == st.session_state.current_chat_id:
                        del st.session_state.current_chat_id
                    st.rerun()


st.title(f"🎓 {current_chat['title']}")
status_text = "🟢 知识图谱辅导"
st.caption(status_text)

for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_trace_panel("🧠 思维过程", message.get("reasoning_trace", []))
        render_trace_panel("🕸️ 检索过程", message.get("retrieval_trace", []))
        if "facts" in message and message["facts"]:
            facts = message["facts"]
            graph_chart = draw_dependency_graph(facts)
            if graph_chart:
                st.caption("📳 知识依赖路径分析")
                st.graphviz_chart(graph_chart)
            with st.expander("📚 溯源详情"):
                for fact in facts:
                    st.markdown(f"- {backend.format_fact_for_display(fact)}")


if prompt := st.chat_input("请输入内容..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    current_chat["messages"].append({"role": "user", "content": prompt})
    history_for_backend = current_chat["messages"][:-1]

    with st.chat_message("assistant"):
        keywords = []
        facts = []
        reasoning_trace = []
        retrieval_trace = []

        with st.status("🧠 分析意图...", expanded=True) as status:
            keywords = backend.extract_keywords_with_llm(
                client,
                prompt,
                history=history_for_backend,
                trace=reasoning_trace,
            )
            status.update(label=f"✅ 关键词: {keywords}", state="complete", expanded=False)

        with st.status("🕸️ 检索图谱...", expanded=True) as status:
            facts = backend.query_graph_with_reasoning(
                driver,
                client,
                prompt,
                keywords=keywords,
                max_depth=rag_depth,
                width=rag_width,
                reasoning_trace=reasoning_trace,
                retrieval_trace=retrieval_trace,
            )
            render_trace_panel("🧠 思维过程", reasoning_trace)
            render_trace_panel("🕸️ 检索过程", retrieval_trace)
            if facts:
                graph_chart = draw_dependency_graph(facts)
                if graph_chart:
                    st.markdown("#### 🗺️ 知识依赖路径")
                    st.graphviz_chart(graph_chart)
                with st.expander("📚 查看详细文本信息"):
                    for fact in facts:
                        st.markdown(f"- {backend.format_fact_for_display(fact)}")
            status.update(label=f"✅ 检索到 {len(facts)} 条知识", state="complete", expanded=False)

        response = st.write_stream(
            backend.ask_deepseek_stream(
                client,
                prompt,
                facts,
                history=history_for_backend,
            )
        )

        current_chat["messages"].append(
            {
                "role": "assistant",
                "content": response,
                "keywords": keywords,
                "facts": facts,
                "reasoning_trace": reasoning_trace,
                "retrieval_trace": retrieval_trace,
            }
        )
        save_history_to_file()

    if len(current_chat["messages"]) == 2:
        current_chat["title"] = prompt[:10] + "..." if len(prompt) > 10 else prompt
        st.session_state.all_chats[st.session_state.current_chat_id] = current_chat
        save_history_to_file()
        st.rerun()
