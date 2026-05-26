# Chat RAG Flow

本文件记录学生端 ChatPage 当前的图谱增强回答流程，以及它和聊天提问知识点记录的边界。

## 业务目标

- 学生提问时默认启用知识图谱检索，回答可以结合 Neo4j 中的 Java 知识点、依赖关系和已选路径。
- 学生可以在输入框旁关闭“知识图谱检索”，此时聊天回退为普通大模型辅导回答。
- 图谱检索结果用于本轮回答和前端展示；回答完成后仍会异步抽取本轮涉及的正式知识点，写入提问记录。

## 后端流程

入口在 `backend/services/chat_service.py` 的 `stream_message()`：

1. 校验会话归属并保存用户 `ChatMessage`。
2. 构造最近对话历史。
3. 如果 `MessageCreateRequest.use_knowledge_graph` 为 `true`：
   - 调用 `rag_engine.extract_keywords_with_llm()` 从当前问题和上下文中提取 Java 图谱实体关键词。
   - 调用 `rag_engine.query_graph_with_reasoning()` 查询 Neo4j，召回种子节点、扩展子图、枚举路径并选择最优路径。
   - 通过 SSE 发送 `graph_trace`，包含 `facts`、`reasoning_trace`、`retrieval_trace`。
4. 如果 `facts` 非空，调用 `rag_engine.ask_deepseek_stream()` 生成图谱增强回答；否则调用普通导师回答流程。
5. 保存助手 `ChatMessage`，并把本轮 `facts_json`、`reasoning_trace_json`、`retrieval_trace_json` 持久化到 `chat_messages`。
6. 发送 `assistant_done`。
7. 启动后台知识点抽取任务，写入 `chat_knowledge_events`。

图谱检索失败时只记录日志，并回退为普通大模型回答，不阻断本轮聊天。

## RAG 检索细节

核心实现位于 `backend/services/rag_engine.py`：

- `extract_keywords_with_llm()`：要求大模型只返回 Java 知识图谱实体关键词。
- `_query_seed_nodes()`：按名称精确匹配、名称包含、描述匹配召回种子节点。
- `_query_subgraph_nodes()`：基于关键词和种子节点扩展相关子图。
- `_query_edges_between_nodes()`：查询子图节点之间的关系。
- `_enumerate_subgraph_paths()`：从种子节点枚举限定深度路径。
- `_select_paths_from_subgraph()`：优先用大模型选择最能解释问题的路径，失败时回退本地排序。
- `_query_dependency_chain_evidence()`：围绕已选路径目标补充 `DEPENDS_ON` 依赖链。

`facts` 目前可能包含：

- `seed`：召回种子节点。
- `selected_path`：最终用于回答的重点路径。
- `path`：路径证据。
- `dependency_chain`：围绕目标节点的依赖链。
- `weak_point`：本轮问题暴露出的关注概念提示。
- `summary`：子图规模和路径数量摘要。

这里的 `weak_point` 只是回答解释和前端展示中的关注概念，不写入 `user_weak_points`。

## 前端流程

相关文件：

- `frontend/src/api/chat.js`
- `frontend/src/pages/ChatPage.vue`
- `frontend/src/components/SelectedPathGraph.vue`

前端发送流式请求时会传入：

```json
{
  "content": "学生问题",
  "use_knowledge_graph": true
}
```

SSE 事件处理顺序：

1. `user_message`：替换临时用户消息。
2. `graph_trace`：更新临时助手消息的 `facts`、`reasoning_trace`、`retrieval_trace`，并标记 `graphTraceReady`。
3. `assistant_delta`：追加流式回答正文。
4. `assistant_done`：用后端持久化后的助手消息替换临时消息。

ChatPage 在助手正文上方展示：

- 图谱检索状态。
- `SelectedPathGraph` 已选路径图。
- 相关节点信息。
- 可展开的推理轨迹和检索轨迹。

## 数据边界

- `chat_messages.facts_json`、`reasoning_trace_json`、`retrieval_trace_json`：保存本轮回答使用的 RAG 证据和过程，供历史消息回显。
- `chat_knowledge_events`：保存后台抽取出的正式知识点事件，用于学生最近提问记录和教师热点统计。
- `user_weak_points` / `user_knowledge_states`：只由作业错题和针对性训练维护，不由聊天 RAG 或聊天提问记录直接写入。

## 验证建议

后端或 schema 改动后：

```powershell
python -m compileall backend
pytest tests/test_chat_knowledge_events.py
```

前端聊天页改动后：

```powershell
npm --prefix frontend run build
node frontend/src/pages/ChatPage.graphTraceLayout.test.mjs
```
