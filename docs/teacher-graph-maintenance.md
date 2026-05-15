# Teacher Graph Maintenance Guide

本文件记录当前教师图谱维护流程。系统已移除 pending 候选批次审核链路，聊天、弱点推荐和作业 AI 诊断都不会再写入候选审核队列。

## 数据边界

- Neo4j 是正式知识图谱的来源，用于聊天检索、弱点推荐和图谱展示。
- MySQL 中的 `knowledge_nodes` 只镜像正式知识点的引用信息，例如题目绑定和章节筛选需要的 `id`、`node_name`、`chapter`。
- 教师端图谱页面直接编辑 Neo4j 正式节点和关系，并在需要时同步 MySQL 引用表。
- ChatPage 不再在回答前检索 Neo4j 图谱；聊天回答完成后会异步抽取本轮涉及的正式知识点，写入咨询记录用于学生回看和教师热点统计。
- 聊天咨询记录只是弱学习足迹，不会写入 `user_weak_points`，也不会改变 `user_knowledge_states`。

## 关键代码

- `backend/services/teacher_service.py`
  - `get_graph()` 读取 Neo4j 正式图谱。
  - `create_graph_node_with_db_sync()` / `update_graph_node()` / `create_graph_edge_with_db_sync()` 维护正式图谱并同步引用表。
  - `list_knowledge_node_refs()` 为作业绑定等页面提供正式知识点搜索。
- `backend/api/routes/teacher.py`
  - 暴露 `/api/teacher/graph`、节点、关系、章节批量更新和知识点引用接口。
- `frontend/src/pages/TeacherGraphPage.vue`
  - 教师正式图谱搜索、章节过滤、节点编辑、关系编辑和 AI 生成节点描述。

## 维护规则

- 不要恢复 pending batch、legacy pending proposal、`pending:` 或 `pending-batch-node:` 这类伪节点入口。
- 聊天咨询记录和弱点推荐只能消费正式图谱；如果图谱缺知识点，由教师在 TeacherGraphPage 直接新增或编辑。
- 作业错题薄弱点更新只依赖题目绑定的正式知识点：提交状态不是 `accepted` 时，把该题绑定的所有知识点标记为未掌握。
- 修改图谱接口时，同时检查后端 schema、`frontend/src/api/teacher.js` 和 `TeacherGraphPage.vue`。

## 验证建议

```powershell
python -m compileall backend
npm --prefix frontend run build
```
