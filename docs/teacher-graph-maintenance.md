# Teacher Graph Maintenance Guide

本文件记录当前教师图谱维护流程。

## 数据边界

- Neo4j 是知识图谱的来源，用于学生聊天 RAG 检索、聊天提问知识点记录、弱点推荐、图谱展示、作业题目知识点绑定和训练节点上下文。
- MySQL 中的 `knowledge_nodes` 只镜像知识点的引用信息，例如题目绑定和章节筛选需要的 `id`、`node_name`、`chapter`。
- 教师端图谱页面直接编辑 Neo4j 节点和关系，并在需要时同步 MySQL 引用表。
- ChatPage 默认在回答前调用聊天 RAG：后端从当前问题中抽取图谱实体关键词，查询 Neo4j 子图并选择重点路径，前端展示相关节点、已选路径和检索过程。
- ChatPage 在聊天回答完成后仍会异步抽取本轮涉及的正式知识点，写入提问记录用于学生回看和教师热点统计。
- 聊天提问记录只是弱学习足迹，不会写入 `user_weak_points`，也不会改变 `user_knowledge_states`。

## 关键代码

- `backend/services/teacher_service.py`
  - `get_graph()` 读取 Neo4j 图谱。
  - `create_graph_node_with_db_sync()` / `update_graph_node()` / `create_graph_edge_with_db_sync()` 维护图谱并同步引用表。
  - `list_knowledge_node_refs()` 为作业绑定等页面提供知识点搜索。
- `backend/api/routes/teacher.py`
  - 暴露 `/api/teacher/graph`、节点、关系、章节批量更新和知识点引用接口。
- `frontend/src/pages/TeacherGraphPage.vue`
  - 教师图谱搜索、章节过滤、节点编辑、关系编辑和 AI 生成节点描述。
- `backend/services/rag_engine.py`
  - 学生聊天 RAG 的关键词抽取、Neo4j 子图召回、路径选择和图谱增强回答。
- `frontend/src/pages/ChatPage.vue`
  - 学生聊天图谱检索开关、`graph_trace` 接收、相关节点和检索过程展示。

## 维护规则

- 聊天 RAG 和聊天提问记录都只使用 Neo4j 图谱已有知识点；如果图谱缺知识点，由教师在 TeacherGraphPage 直接新增或编辑。
- 聊天 RAG 的 `facts`、`reasoning_trace`、`retrieval_trace` 随助手消息保存到 `chat_messages`，不等同于 `chat_knowledge_events`。
- 作业错题薄弱点更新只依赖题目绑定的知识点：提交状态不是 `accepted` 时，把该题绑定的所有知识点标记为未掌握。
- 修改图谱接口时，同时检查后端 schema、`frontend/src/api/teacher.js` 和 `TeacherGraphPage.vue`。

## 验证建议

```powershell
python -m compileall backend
npm --prefix frontend run build
```
