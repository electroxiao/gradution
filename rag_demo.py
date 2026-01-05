from neo4j import GraphDatabase

# --- 1. 配置区域 ---
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "12345678")  # <--- 改密码
DB_NAME = "java"  # <--- 改成你的数据库名字


# --- 2. 模拟大模型 (先不真的调API，为了演示原理) ---
def mock_llm_chat(prompt):
    print("\n====== 正在发送给大模型 (模拟) ======")
    print(f"【发送的 Prompt 内容】:\n{prompt}")
    print("======================================")
    print("\n====== 大模型回复 (模拟) ======")
    # 这里假装是大模型生成的
    return "同学你好！根据你的描述，你可能遇到了‘死循环’的问题。这通常是因为..."


# --- 3. 核心功能：根据问题查图谱 ---
def search_knowledge_base(driver, keyword):
    # 这句 Cypher 的意思是：查找名字里包含关键词的节点，并找它相关的节点
    # (?i) 表示忽略大小写
    query = """
    MATCH (n:KnowledgePoint)-[r]->(m)
    WHERE n.name CONTAINS $keyword OR m.name CONTAINS $keyword
    RETURN n.name AS source, type(r) AS relation, m.name AS target
    """

    context_list = []
    with driver.session(database=DB_NAME) as session:
        result = session.run(query, keyword=keyword)
        for record in result:
            # 把查到的三元组拼成一句话，比如 "While循环 易导致 死循环"
            fact = f"{record['source']} --[{record['relation']}]--> {record['target']}"
            context_list.append(fact)

    return context_list


# --- 4. 主程序 ---
def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)

    # 假设这是用户输入的问题
    user_question = "我写的 While 循环好像出问题了，一直跑不停，怎么办？"
    print(f"User: {user_question}")

    # 第一步：提取关键词 (简单起见，我们手动指定，以后用 LLM 提取)
    keyword = "While"
    print(f"System: 提取关键词 -> '{keyword}'")

    # 第二步：去 Neo4j 查知识
    facts = search_knowledge_base(driver, keyword)

    if not facts:
        print("System: 知识库里没查到相关信息，将直接让大模型回答。")
        context_str = "无"
    else:
        print(f"System: 查到 {len(facts)} 条相关知识！")
        # 把列表变成一个字符串
        context_str = "\n".join(facts)

    # 第三步：组装 Prompt (这就是 RAG 的精髓！)
    prompt = f"""
    你是一个友善的 Python 助教。
    用户遇到了这个问题："{user_question}"

    为了帮助回答，我从知识库检索到了以下背景知识：
    ---
    {context_str}
    ---

    请结合上述背景知识，用通俗易懂的语言解答学生的疑惑。
    不要直接把三元组念出来，要融汇贯通。
    """

    # 第四步：调用大模型
    response = mock_llm_chat(prompt)
    print(response)

    driver.close()


if __name__ == "__main__":
    main()