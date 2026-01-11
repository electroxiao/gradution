import streamlit as st
from neo4j import GraphDatabase
from openai import OpenAI
import backend  # <--- 导入你刚才整理好的 backend.py

# --- 页面配置 ---
st.set_page_config(page_title="Java 智能编程导师", page_icon="🎓", layout="wide")


# --- 初始化 (利用 Streamlit 的缓存机制，避免每次刷新都重连数据库) ---
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

# --- 初始化聊天记录 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 侧边栏：系统状态与调试信息 ---
with st.sidebar:
    st.title("🎛️ 系统控制台")
    st.success("✅ 知识图谱已连接")
    st.success("✅ DeepSeek大模型已连接")

    st.divider()
    st.markdown("### 🧠 思维链可视")
    debug_container = st.container()  # 占位符，用于显示最新的思考过程

# --- 主界面：标题 ---
st.title("🎓 基于知识图谱的 Java 自适应辅导系统")
st.caption("我是你的 AI 导师。我不会直接给你答案，但我会引导你学会它。")

# --- 1. 展示历史聊天记录 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 2. 处理用户输入 ---
if prompt := st.chat_input("请输入你的 Java 问题或粘贴代码..."):
    # 显示用户输入
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # --- AI 处理流程 ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # === Step 1: 意图识别 ===
        with st.status("🧠 正在分析你的意图...", expanded=True) as status:
            keywords = backend.extract_keywords_with_llm(client, prompt)
            st.write(f"**提取关键词**: `{keywords}`")
            status.update(label="✅ 意图识别完成", state="complete", expanded=False)

            # 更新侧边栏
            with debug_container:
                st.info(f"**最新意图**: {keywords}")

        # === Step 2: 图谱检索 ===
        with st.status("🕸️ 正在检索知识图谱...", expanded=True) as status:
            facts = backend.query_graph_by_keywords(driver, keywords)
            if facts:
                st.write(f"**检索到 {len(facts)} 条知识**")
                # 用折叠框展示具体的三元组，避免刷屏
                with st.expander("查看图谱详情"):
                    for f in facts:
                        st.markdown(f"- {f}")
            else:
                st.warning("未检索到直接关联知识，将启用通用教学模式。")
            status.update(label="✅ 图谱检索完成", state="complete", expanded=False)

        # === Step 3: 引导式生成 (流式输出) ===
        st.markdown("### 🎓 导师建议")
        # 创建一个流式输出的容器
        stream_generator = backend.ask_deepseek_stream(client, prompt, facts)
        response = st.write_stream(stream_generator)

        # 记录 AI 的回复到历史
        st.session_state.messages.append({"role": "assistant", "content": response})