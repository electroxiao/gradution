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


# --- 2. 历史记录管理函数 ---
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


# --- 3. Session State 初始化 ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_history_from_file()

if "current_chat_id" not in st.session_state or st.session_state.current_chat_id not in st.session_state.all_chats:
    if st.session_state.all_chats:
        st.session_state.current_chat_id = list(st.session_state.all_chats.keys())[0]
    else:
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {
            "title": "新对话",
            "messages": [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.current_chat_id = new_id

current_chat = st.session_state.all_chats[st.session_state.current_chat_id]


# --- 辅助函数：绘制知识依赖图 ---
def draw_dependency_graph(facts):
    """
    解析后端返回的字符串列表，提取依赖关系并绘制 Graphviz 图，同时去重边。
    """
    if not facts:
        return None

    graph = graphviz.Digraph()
    graph.attr(rankdir='BT')
    graph.attr('node', shape='box', style='filled', fillcolor='#f0f2f6', color='#bdc3c7')

    added_edges = set()
    edge_count = 0

    for fact in facts:
        if "【完整溯源】" in fact:
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
                    edge_signature = (source, target)

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

    # === 新增功能：模式选择 ===
    st.info("💡 模式切换")
    role_selection = st.radio(
        "选择当前身份：",
        ("👨‍🎓 学生 (个别辅导)", "👩‍🏫 教师 (批量诊断)"),
        index=0,
        help="学生模式：苏格拉底式引导，不直接给代码。\n教师模式：输入批量错题，生成共性诊断报告。"
    )
    # 映射为后端可识别的字符串
    current_mode = "student" if "学生" in role_selection else "teacher"
    st.divider()

    if st.button("➕ 新建对话", use_container_width=True, type="secondary"):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {
            "title": "新对话", "messages": [], "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.current_chat_id = new_id
        save_history_to_file()
        st.rerun()

    st.divider()
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

    st.divider()
    with st.expander("🛠️ 系统后台状态"):
        st.success("图谱/模型已连接")
        # 显示当前模式状态
        st.caption(f"当前模式: {current_mode}")
        debug_container = st.container()

# --- 5. 主界面逻辑 ---
st.title(f"🎓 {current_chat['title']}")
# 动态更新副标题
if current_mode == "student":
    st.caption(f"当前模式：{role_selection} - 我会通过引导让你自己发现错误。")
else:
    st.caption(f"当前模式：{role_selection} - 请输入学生们的错题，我将为您生成诊断报告。")

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
                    st.markdown(f"- {f}")

if prompt := st.chat_input("请输入问题或粘贴代码..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    user_msg_obj = {
        "role": "user",
        "content": prompt,
        "keywords": [],
        "facts": []
    }
    current_chat["messages"].append(user_msg_obj)
    history_for_backend = current_chat["messages"][:-1]

    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        # Step 1: 意图识别
        with st.status("🧠 分析意图...", expanded=True) as status:
            keywords = backend.extract_keywords_with_llm(client, prompt, history=history_for_backend)
            current_chat["messages"][-1]["keywords"] = keywords
            save_history_to_file()
            status.update(label=f"✅ 关键词: {keywords}", state="complete", expanded=False)

        # Step 2: 图谱检索
        with st.status("🕸️ 检索图谱...", expanded=True) as status:
            facts = backend.query_graph_by_keywords(driver, keywords)
            current_chat["messages"][-1]["facts"] = facts
            save_history_to_file()

            if facts:
                graph_chart = draw_dependency_graph(facts)
                if graph_chart:
                    st.markdown("#### 🗺️ 知识依赖路径")
                    st.graphviz_chart(graph_chart)
                with st.expander("📄 查看详细文本信息"):
                    for f in facts:
                        st.markdown(f"- {f}")

            status.update(label=f"✅ 检索到 {len(facts)} 条知识", state="complete", expanded=False)

        # Step 3: 生成回复 (传入 mode 参数)
        stream_generator = backend.ask_deepseek_stream(
            client,
            prompt,
            facts,
            history=history_for_backend,
            mode=current_mode  # <--- 修改点：传入侧边栏选择的模式
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