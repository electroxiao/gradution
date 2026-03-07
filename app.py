import streamlit as st
from neo4j import GraphDatabase
from openai import OpenAI
import backend
import json
import os
import uuid
from datetime import datetime
import graphviz

# --- 1. 配置与初始化 ---
st.set_page_config(page_title="Java 智能编程导师", page_icon="🎓", layout="wide")
HISTORY_FILE = "chat_history.json"


@st.cache_resource
def init_connections():
    try:
        driver = GraphDatabase.driver(backend.NEO4J_URI, auth=backend.NEO4J_AUTH)
        client = OpenAI(api_key=backend.API_KEY, base_url=backend.BASE_URL)
        return driver, client
    except Exception as e:
        st.error(f"❌ 连接失败: {e}")
        return None, None


driver, client = init_connections()


# --- 2. 历史记录管理 ---
def load_history_from_file():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_history_to_file():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.all_chats, f, ensure_ascii=False, indent=2)


if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_history_from_file()

if "current_chat_id" not in st.session_state or st.session_state.current_chat_id not in st.session_state.all_chats:
    if st.session_state.all_chats:
        st.session_state.current_chat_id = list(st.session_state.all_chats.keys())[0]
    else:
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {
            "title": "新对话", "messages": [], "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.current_chat_id = new_id

current_chat = st.session_state.all_chats[st.session_state.current_chat_id]


# --- 辅助函数：绘制图谱 ---
def draw_dependency_graph(facts):
    if not facts:
        return None
    graph = graphviz.Digraph()
    graph.attr(rankdir='BT')
    graph.attr('node', shape='box', style='filled', fillcolor='#f0f2f6', color='#bdc3c7')
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
                            graph.node(target, label=target, fillcolor='#d4e6f1')
                            graph.edge(source, target, label="依赖", color='#808080')
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
                        graph.node(target, label=target, fillcolor='#d4e6f1')
                        graph.edge(source, target, label=relation, color='#5d6d7e')
                        added_edges.add(edge_signature)
                        edge_count += 1
        elif "【完整溯源】" in fact:
            clean_fact = fact.replace("【完整溯源】", "").strip()
            if " (底层概念" in clean_fact:
                clean_fact = clean_fact.split(" (底层概念")[0]
            elif "(底层概念" in clean_fact:
                clean_fact = clean_fact.split("(底层概念")[0]
            nodes = clean_fact.split(" -> (依赖) -> ")
            nodes = [n.strip() for n in nodes if n.strip()]
            if len(nodes) > 1:
                for i in range(len(nodes) - 1):
                    source = nodes[i]
                    target = nodes[i + 1]
                    edge_signature = (source, target, "依赖")
                    if edge_signature not in added_edges:
                        graph.node(source, label=source)
                        graph.node(target, label=target, fillcolor='#d4e6f1')
                        graph.edge(source, target, label="依赖", color='#808080')
                        added_edges.add(edge_signature)
                        edge_count += 1
    return graph if edge_count > 0 else None


# --- 4. 侧边栏布局 ---
with st.sidebar:
    st.title("🗂️ 对话列表")

    # === 功能区 1: 模式选择 ===
    st.info("💡 身份设定")
    role_selection = st.radio(
        "选择当前模式：",
        ("👨‍🎓 学生 (个别辅导)", "👩‍🏫 教师 (批量诊断)"),
        index=0
    )
    current_mode = "student" if "学生" in role_selection else "teacher"

    st.divider()

    # === 功能区 2: 消融测试开关 ===
    st.markdown("### 🧪 实验控制 (Ablation)")
    enable_kg = st.toggle("启用知识图谱 (RAG)", value=True, help="关闭此开关以进行消融测试（仅使用大模型，不查图谱）")
    rag_depth = st.slider("推理深度", min_value=1, max_value=4, value=2, step=1,
                          help="每轮从当前实体继续扩展多少跳")
    rag_width = st.slider("每跳保留候选数", min_value=1, max_value=8, value=3, step=1,
                          help="每一跳由大模型筛选保留的候选数量")

    if not enable_kg:
        st.warning("⚠️ 消融模式：图谱已禁用")
    else:
        st.caption("✅ 状态：图谱增强已激活")

    st.divider()

    # === 功能区 3: 对话管理 ===
    if st.button("➕ 新建对话", use_container_width=True, type="secondary"):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {
            "title": "新对话", "messages": [], "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.current_chat_id = new_id
        save_history_to_file()
        st.rerun()

    st.markdown("---")
    sorted_chat_ids = sorted(st.session_state.all_chats.keys(),
                             key=lambda k: st.session_state.all_chats[k].get("created_at", ""), reverse=True)
    for chat_id in sorted_chat_ids:
        chat_data = st.session_state.all_chats[chat_id]
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            label = f"📂 {chat_data['title']}" if chat_id == st.session_state.current_chat_id else chat_data["title"]
            if st.button(label, key=f"btn_{chat_id}", use_container_width=True,
                         type="secondary" if chat_id != st.session_state.current_chat_id else "primary"):
                st.session_state.current_chat_id = chat_id
                st.rerun()
        with col2:
            with st.popover("⋮", use_container_width=True):
                new_name = st.text_input("标题", value=chat_data["title"], key=f"input_{chat_id}")
                if st.button("💾", key=f"save_{chat_id}"):
                    st.session_state.all_chats[chat_id]["title"] = new_name
                    save_history_to_file()
                    st.rerun()
                if st.button("🗑️", key=f"del_{chat_id}", type="primary"):
                    del st.session_state.all_chats[chat_id]
                    save_history_to_file()
                    if chat_id == st.session_state.current_chat_id: del st.session_state.current_chat_id
                    st.rerun()

# --- 5. 主界面逻辑 ---
st.title(f"🎓 {current_chat['title']}")

# 动态状态栏
status_text = f"模式：{role_selection} | " + ("🟢 图谱增强 (Ours)" if enable_kg else "🔴 纯大模型 (Baseline)")
st.caption(status_text)

for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "facts" in message and message["facts"]:
            facts = message["facts"]
            graph_chart = draw_dependency_graph(facts)
            if graph_chart:
                st.caption("📊 知识依赖路径分析")
                st.graphviz_chart(graph_chart)
            with st.expander("📄 溯源详情"):
                for f in facts:
                    st.markdown(f"- {backend.format_fact_for_display(f)}")

# === 处理新输入 ===
if prompt := st.chat_input("请输入内容..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    # 初始化消息对象
    user_msg_obj = {"role": "user", "content": prompt, "keywords": [], "facts": []}
    current_chat["messages"].append(user_msg_obj)
    history_for_backend = current_chat["messages"][:-1]

    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        # 初始化变量，防止消融模式下报错
        keywords = []
        facts = []
        teacher_analysis = None

        # ==================== 分支 A: 启用图谱 (完整流程) ====================
        if enable_kg:
            if current_mode == "teacher":
                with st.status("🧠 逐题分析与聚类...", expanded=True) as status:
                    teacher_analysis = backend.analyze_teacher_batch(client, prompt)
                    keywords = teacher_analysis.get("selected_keywords", [])
                    current_chat["messages"][-1]["keywords"] = keywords
                    save_history_to_file()
                    status.update(
                        label=f"✅ 模块: {[item['module'] for item in teacher_analysis.get('selected_modules', [])]}",
                        state="complete",
                        expanded=False
                    )

                with st.status("🕸️ 聚焦检索知识模块...", expanded=True) as status:
                    facts = backend.query_teacher_graph_with_reasoning(
                        driver,
                        client,
                        prompt,
                        analysis=teacher_analysis,
                        max_depth=rag_depth,
                        width=rag_width
                    )
                    current_chat["messages"][-1]["facts"] = facts
                    save_history_to_file()

                    if facts:
                        graph_chart = draw_dependency_graph(facts)
                        if graph_chart:
                            st.markdown("#### 🗺️ 知识依赖路径")
                            st.graphviz_chart(graph_chart)
                        with st.expander("📄 查看详细文本信息"):
                            for f in facts:
                                st.markdown(f"- {backend.format_fact_for_display(f)}")
                    status.update(label=f"✅ 检索到 {len(facts)} 条模块化证据", state="complete", expanded=False)
            else:
                # Step 1: 意图识别
                with st.status("🧠 分析意图...", expanded=True) as status:
                    keywords = backend.extract_keywords_with_llm(client, prompt, history=history_for_backend)
                    current_chat["messages"][-1]["keywords"] = keywords
                    save_history_to_file()
                    status.update(label=f"✅ 关键词: {keywords}", state="complete", expanded=False)

                # Step 2: 图谱检索
                with st.status("🕸️ 检索图谱...", expanded=True) as status:
                    facts = backend.query_graph_with_reasoning(
                        driver,
                        client,
                        prompt,
                        keywords=keywords,
                        max_depth=rag_depth,
                        width=rag_width
                    )
                    current_chat["messages"][-1]["facts"] = facts
                    save_history_to_file()

                    if facts:
                        graph_chart = draw_dependency_graph(facts)
                        if graph_chart:
                            st.markdown("#### 🗺️ 知识依赖路径")
                            st.graphviz_chart(graph_chart)
                        with st.expander("📄 查看详细文本信息"):
                            for f in facts:
                                st.markdown(f"- {backend.format_fact_for_display(f)}")
                    status.update(label=f"✅ 检索到 {len(facts)} 条知识", state="complete", expanded=False)

        # ==================== 分支 B: 消融模式 (跳过前两步) ====================
        else:
            # 仅仅为了UI好看，显示一个已跳过的状态
            with st.status("🚀 纯大模型模式 (Ablation)", expanded=False) as status:
                st.write("已跳过意图识别 (Step 1)")
                st.write("已跳过图谱检索 (Step 2)")
                status.update(label="⏹️ 已跳过图谱处理，直接生成", state="complete")

        # Step 3: 生成回复 (无论是哪种模式，都调用这个，但 enable_graph 参数不同)
        # 注意：如果是消融模式，传入的 facts 是空的 []
        stream_generator = backend.ask_deepseek_stream(
            client,
            prompt,
            facts,  # 消融模式下这里是空列表
            history=history_for_backend,
            mode=current_mode,
            enable_graph=enable_kg
        )
        response = st.write_stream(stream_generator)

        current_chat["messages"].append({"role": "assistant", "content": response})
        save_history_to_file()

    if len(current_chat["messages"]) == 2:
        new_title = prompt[:10] + "..." if len(prompt) > 10 else prompt
        current_chat["title"] = new_title
        st.session_state.all_chats[st.session_state.current_chat_id] = current_chat
        save_history_to_file()
        st.rerun()
