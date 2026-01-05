from neo4j import GraphDatabase

# 1. 连接配置
# bolt是Neo4j专用的通讯协议，localhost:7687是默认地址
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "12345678")  # <--- 请在这里修改你的密码！


def test_connection():
    # 2. 建立连接驱动
    driver = GraphDatabase.driver(URI, auth=AUTH)

    try:
        # 验证一下连上了没
        driver.verify_connectivity()
        print("✅ 恭喜！Python 成功连接到了 Neo4j 数据库！")

        # 3. 执行一个查询
        # 这句 Cypher 的意思是：查找所有有名字的节点，把名字打印出来
        query = "MATCH (n) WHERE n.name IS NOT NULL RETURN n.name AS name, labels(n) AS label"

        # 使用 verify_connectivity 后，我们可以直接开一个会话跑查询
        with driver.session(database="java") as session:
            result = session.run(query)

            print("\n--- 数据库里的数据 ---")
            for record in result:
                # record["name"] 对应上面 query 里的 n.name
                print(f"[{record['label'][0]}] : {record['name']}")

    except Exception as e:
        print(f"❌ 连接失败，报错信息如下：\n{e}")
        print("👉 请检查：1. 密码对不对？ 2. Neo4j Desktop 里的绿灯亮着吗？")

    finally:
        # 4. 记得关门
        driver.close()


if __name__ == "__main__":
    test_connection()