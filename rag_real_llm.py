from neo4j import GraphDatabase
from openai import OpenAI
import os

# ================= 配置区域 =================
API_KEY = "sk-3e99ce7b256f45d89d006371fa15993e"  # <---【确认这里填了你的Key】
BASE_URL = "https://api.deepseek.com"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "12345678")  # <---【确认这里填了你的密码】
DB_NAME = "java"  # <---【确认这里是 java】


# ============================================

def search_knowledge_base(driver, keyword):
    print(f"\n🔍 系统正在图谱中检索关键词: [{keyword}] ...")
    query = """
    MATCH (n:KnowledgePoint)-[r]->(m)
    WHERE n.name CONTAINS $keyword OR m.name CONTAINS $keyword
    RETURN n.name AS source, type(r) AS relation, m.name AS target
    LIMIT 5
    """
    knowledge_list = []
    try:
        with driver.session(database=DB_NAME) as session:
            result = session.run(query, keyword=keyword)
            for record in result:
                fact = f"{record['source']} --[{record['relation']}]--> {record['target']}"
                knowledge_list.append(fact)
    except Exception as e:
        print(f"❌ 数据库查询出错: {e}")
    return knowledge_list


# --- 修改点 1: 改为流式生成器 ---
def ask_deepseek_stream(client, user_question, context_knowledge):
    print("\n🤖 系统正在思考 (请求 DeepSeek API)...")

    if not context_knowledge:
        knowledge_text = "数据库中未找到相关具体技术细节，请凭借通用知识回答。"
    else:
        knowledge_text = "\n".join(context_knowledge)

    system_prompt = f"""
    你是一个专业的 Python 编程辅导助教。
    请根据以下【参考知识库】来回答学生的问题。

    【参考知识库】
    ---------------------
    {knowledge_text}
    ---------------------

    要求：引用知识库内容，语气友善，逻辑清晰。
    """

    try:
        # 【关键修改】：stream=True
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question},
            ],
            stream=True,  # <--- 开启流式输出
            temperature=0.7
        )

        # 【关键修改】：使用 yield 逐步返回字符
        for chunk in response:
            # 并不是所有 chunk 都有 content，有时候是结束标志，所以要判断
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        yield f"❌ 调用大模型出错: {e}"


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    user_question = "我的循环好像停不下来了，一直跑，这是怎么回事？"
    print(f"🙋‍♂️ 学生提问: {user_question}")

    keyword = "While"
    facts = search_knowledge_base(driver, keyword)

    if facts:
        print(f"✅ 检索成功! 找到了 {len(facts)} 条相关知识。")
        for f in facts:
            print(f"   - {f}")

    print("\n" + "=" * 30)
    print("🎓 AI 助教的回答:")
    print("=" * 30)

    # --- 修改点 2: 接收流式数据并打印 ---
    # 创建一个空字符串用来存完整的回答（如果你后面要存数据库的话会用到）
    full_answer = ""

    # 这里的 chunk 就是大模型每次吐出来的几个字
    for chunk in ask_deepseek_stream(client, user_question, facts):
        print(chunk, end="", flush=True)  # end="" 防止换行，flush=True 强制立即刷新缓冲区
        full_answer += chunk  # 拼接到完整答案里

    print("\n" + "=" * 30)  # 打完字后换行

    driver.close()


if __name__ == "__main__":
    main()