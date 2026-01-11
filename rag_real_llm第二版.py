import json
from neo4j import GraphDatabase
from openai import OpenAI

# ================= 配置区域 =================
# 1. DeepSeek / OpenAI API 配置
API_KEY = "sk-3e99ce7b256f45d89d006371fa15993e"  # <---【请确认你的Key】
BASE_URL = "https://api.deepseek.com"

# 2. Neo4j 数据库配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "12345678")  # <---【请确认你的密码】
DB_NAME = "neo4j"  # <---【已修改】从 'java' 改为 'neo4j'


# ============================================

# --- 步骤 1: 意图识别 (让大模型把用户口语翻译成图谱里的 id) ---
def extract_keywords_with_llm(client, user_question):
    print(f"\n🧠 [Step 1] 正在分析用户意图: '{user_question}'")

    # 提示词微调：告诉 AI 我们的图谱里存的是标准术语（如 "main方法"）
    prompt = f"""
    请提取用户问题中的【Java编程实体关键词】。
    你的目标是匹配知识图谱中的节点 ID。

    例如：
    - 用户问“入口函数”，你应该提取 ["main方法"]
    - 用户问“怎么输出”，你应该提取 ["System.out.println"]
    - 用户问“整数类型”，你应该提取 ["int"]

    请直接返回 JSON 列表字符串，不要包含 Markdown 格式。

    用户问题：{user_question}
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content
        # 简单的清洗逻辑，提取 [] 之间的内容
        start = content.find('[')
        end = content.find(']') + 1
        if start != -1 and end != -1:
            keywords = json.loads(content[start:end])
        else:
            keywords = [user_question]  # 兜底

        print(f"   -> 识别关键词: {keywords}")
        return keywords
    except Exception as e:
        print(f"   -> 意图识别出错，使用原始输入: {e}")
        return [user_question]


# --- 步骤 2: 精准检索 (适配你的新数据结构) ---
def query_graph_by_keywords(driver, keywords):
    print(f"\n🕸️ [Step 2] 正在图谱中检索关联知识...")
    context_data = []

    with driver.session(database=DB_NAME) as session:
        for kw in keywords:
            # ====================================================
            # 核心 Cypher 查询 (已针对你的 JSON 结构修改)
            # 1. 匹配标签为 Concept 的节点
            # 2. 使用 id 属性进行模糊匹配 (CONTAINS)
            # 3. 同时查它的 desc，以及它连出去/连进来的关系
            # ====================================================
            query = """
            MATCH (n:Concept)
            WHERE toLower(n.id) CONTAINS toLower($kw)  // 忽略大小写匹配 id 属性

            // 查节点自身信息
            WITH n
            // 查这个节点指向了谁 (例如: Concept -> Error, Concept -> Chapter)
            OPTIONAL MATCH (n)-[r_out]->(target)

            // 查谁指向了这个节点 (例如: Chapter -> Concept, PreConcept -> Concept)
            OPTIONAL MATCH (source)-[r_in]->(n)

            RETURN 
                n.id AS entity_id,
                n.desc AS entity_desc,

                // 收集出边信息
                type(r_out) AS out_rel_type,
                target.id AS out_target_id,
                target.desc AS out_target_desc,
                labels(target) AS out_target_labels,

                // 收集入边信息
                type(r_in) AS in_rel_type,
                source.id AS source_id,
                labels(source) AS source_labels
            LIMIT 5
            """

            result = session.run(query, kw=kw)

            # 处理查询结果，拼接成一句话
            for record in result:
                # 1. 基础知识
                base_info = f"【知识点】{record['entity_id']}: {record['entity_desc']}"
                context_data.append(base_info)

                # 2. 关联信息 (如果存在)
                # 处理出边 (比如：main方法 --属于--> 第一章)
                if record['out_rel_type']:
                    # 也可以根据 labels 判断 target 是什么类型
                    target_type = "章节" if "Chapter" in record['out_target_labels'] else "概念"
                    if "Error" in record['out_target_labels']: target_type = "常见错误"

                    rel_info = f"   -> [关联] 它 {record['out_rel_type']} {target_type} '{record['out_target_id']}' ({record['out_target_desc']})"
                    context_data.append(rel_info)

                # 处理入边 (比如：前置知识 --依赖--> main方法)
                if record['in_rel_type']:
                    source_type = "章节" if "Chapter" in record['source_labels'] else "前置知识"
                    rel_info = f"   <- [背景] 由 {source_type} '{record['source_id']}' 通过关系 [{record['in_rel_type']}] 连接"
                    context_data.append(rel_info)

    # 去重 (因为查关系时可能会导致主节点重复)
    unique_context = list(set(context_data))

    if not unique_context:
        print("   -> ⚠️ 未检索到图谱数据")
    else:
        print(f"   -> ✅ 成功检索到 {len(unique_context)} 条知识，详情如下：")
        print("-" * 50)
        # 【修改点】：这里去掉了 [:3]，循环打印所有数据
        for i, item in enumerate(unique_context):
            print(f"   [{i + 1}] {item}")
        print("-" * 50)

    return unique_context


# --- 步骤 3: 最终生成 (流式输出) ---
def ask_deepseek_stream(client, user_question, context_knowledge):
    print("\n💬 [Step 3] AI 正在思考...")

    if not context_knowledge:
        knowledge_text = "数据库中未找到具体定义，请依据通用 Java 知识回答。"
    else:
        knowledge_text = "\n".join(context_knowledge)

    # Prompt 强调利用 id 和 desc
    system_prompt = f"""
    你是一个专业的 Java 编程辅导助教。
    请根据以下【图谱检索结果】回答学生问题。

    【图谱检索结果】
    ---------------------
    {knowledge_text}
    ---------------------

    要求：
    1. 准确引用图谱中的【知识点】名称(id)和描述(desc)。
    2. 如果有[关联]或[背景]信息，请利用它们来解释知识的前因后果。
    3. 给出简单的代码示例辅助说明。
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question},
            ],
            stream=True,
            temperature=0.7
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"❌ 出错: {e}"


# --- 主程序 (终极稳定版：使用 END 标记结束) ---
def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    print("\n" + "=" * 50)
    print("🤖 Java 编程智能助教已启动")
    print("👉 操作指南：")
    print("1. 粘贴任意多行代码或问题")
    print("2. 新起一行输入 'END' (不含引号) 并回车，即可发送")
    print("3. 输入 'exit' 退出程序")
    print("=" * 50)

    while True:
        print("\n🙋‍♂️ 请输入你的问题 (输入 END 结束):")
        lines = []

        while True:
            try:
                line = input()
            except EOFError:
                break

            # 核心逻辑：只有看到单独一行的 "END" 才结束
            if line.strip() == "END":
                break

            lines.append(line)

        # 拼接用户输入
        user_question = "\n".join(lines).strip()

        # 检查是否为空或退出
        if not user_question:
            continue
        if user_question.lower() in ["exit", "quit", "退出"]:
            print("👋 再见！")
            break

        # 1. 提取关键词
        keywords = extract_keywords_with_llm(client, user_question)

        # 2. 查图谱
        facts = query_graph_by_keywords(driver, keywords)

        # 3. 生成回答
        print("\n" + "=" * 30)
        print("🎓 AI 助教的回答:")
        print("=" * 30)

        for chunk in ask_deepseek_stream(client, user_question, facts):
            print(chunk, end="", flush=True)

        print("\n" + "=" * 30)

    driver.close()


if __name__ == "__main__":
    main()
