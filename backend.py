import json
import os
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


# --- 步骤 3: 核心生成 (支持消融测试) ---
def ask_deepseek_stream(client, user_input, context_knowledge, history=[], mode="student", enable_graph=True):
    """
    enable_graph: True (RAG模式) / False (纯LLM模式，用于消融实验)
    """
    print(f"\n💬 [Step 3] AI 正在思考 (模式: {mode}, 图谱: {enable_graph}) ...")

    # === 分支 A: 启用图谱 (Ours: Graph-Augmented) ===
    if enable_graph:
        knowledge_text = "\n".join(context_knowledge) if context_knowledge else "（未检索到特定图谱路径）"

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
            你的任务是分析这些错误背后的**共性**，并利用知识图谱生成一份**全覆盖的教学诊断报告**。
    
            【相关知识点的依赖链】
            {knowledge_text}
    
            === 分析任务 ===
            1. **聚类统计**：输入中包含了哪些类型的错误？（按出现频率排序）。
            2. **多维溯源 (关键)**：
               - 不要强行将所有错误归结为一个原因。如果错误跨度大（如“内存”和“语法”），请找出 **Top 1-3 个主要根因**。
               - 利用【图谱依赖链】，寻找每一类错误的**底层前置概念**。
               - *格式要求*：必须引用图谱中的路径，如 `[错误点] -> 依赖 -> [根节点]`。
            3. **教学建议**：
               - 针对识别出的每一个主要根因，分别给出教学策略。
               - 确保没有遗漏“错误分布”中的高频错误项。
    
            === 报告格式 ===
            ### 📊 错误类型分布 (Top 5)
            | 错误归类 | 频次 | 涉及题目 |
            | :--- | :--- | :--- |
            | ... | ... | ... |
    
            ### 🧬 核心根因分析 (Root Cause Analysis)
            通过图谱分析，本次错题主要暴露出 **[数量]** 个维度的知识盲区：
    
            #### 根因 1：[根节点名称] (关联 [X]% 的错误)
            - **图谱路径证据**：[具体错误] -> (依赖) -> [中间节点] -> (依赖) -> [根节点]
            - **分析**：学生混淆了......
    
            #### 根因 2：[根节点名称] (关联 [Y]% 的错误)
            - **图谱路径证据**：......
            - **分析**：......
    
            ### 💡 针对性教学建议
            1. **针对 [根因1]**：建议讲解......
            2. **针对 [根因2]**：建议练习......
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
    
            ### 💡 针对性教学建议
            1. **针对 [根因1]**：建议讲解......
            2. **针对 [根因2]**：建议练习......
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
            temperature=0.4
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"❌ 出错: {e}"