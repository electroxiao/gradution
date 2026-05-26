# 教师端学生画像页设计

## 背景

当前教师端已有 `/teacher/students` 页面，页面标题为“学生薄弱点”，主要承载学生列表、薄弱知识点和最近提问知识点汇总。随着教师需要在同一入口查看单个学生的薄弱点、作业完成情况和提问历史，该页面的职责需要从单一薄弱点列表扩展为“学生画像”工作台。

本设计保留现有教师端导航和学生筛选基础结构，将侧边栏入口从“学生薄弱点”调整为“学生画像”。路由可先沿用 `/teacher/students`，避免一次性引入额外页面层级。

## 目标

- 教师可以从一个学生入口查看该生的薄弱点、作业情况和提问情况。
- 教师可以通过“提问过的知识点”定位到相关聊天记录。
- 学生画像页展示作业情况到列表级深度，包括完成状态、通过情况和最后提交时间。
- 作业详情、提交代码和 AI 评审仍由现有作业进度页承担，学生画像页只负责定位和跳转。
- 页面结构为后续继续接入训练记录、趋势图和更细粒度学习分析留出空间。

## 非目标

- 不在学生画像页内复刻完整作业批改弹窗。
- 不允许教师以学生身份发送聊天消息或修改学生聊天会话。
- 不在本次设计中变更学生端聊天交互。
- 不将聊天知识点抽取逻辑改为同步阻塞流程。
- 不改变作业沙箱执行、安全限制或判题逻辑。

## 信息架构

教师侧边栏保留四个一级入口：

- 数据看板
- 知识图谱
- 学生画像
- 作业管理

学生画像页采用“左侧学生列表 + 右侧画像工作台”的结构：

- 左侧学生列表：姓名搜索、班级筛选、排序、分页、学生行摘要。
- 右侧顶部摘要：学生姓名、班级、薄弱点数、未完成作业数、最近提问次数。
- 右侧主体 Tab：薄弱点、作业情况、提问情况。

默认选中第一个筛选命中的学生。切换学生时，右侧摘要和当前 Tab 数据同步刷新。

## 页面布局

### 左侧学生列表

左侧继续使用当前学生列表模式：

- 搜索框：按学生姓名过滤。
- 班级筛选：按 `class_name` 过滤。
- 排序：
  - 按薄弱点数
  - 按未完成作业数
  - 按姓名
- 学生行展示：
  - 学生姓名
  - 班级
  - 薄弱点数量
  - 可选的未完成作业数量提示

### 学生摘要区

右侧顶部展示当前学生的紧凑摘要：

- 学生姓名和班级。
- 当前薄弱点数。
- 未完成作业数。
- 最近提问知识点数或最近提问次数。

摘要区只展示概览，不承载复杂操作。

### 薄弱点 Tab

薄弱点 Tab 展示该学生当前未掌握或待巩固的知识点：

- 知识点名称。
- 状态。
- 首次出现时间。
- 最近出现时间。

可保留当前“薄弱知识点”列表的视觉和数据来源。后续可扩展为按章节、来源或状态筛选，但不作为本次设计的必要项。

### 作业情况 Tab

作业情况 Tab 采用列表级深度：

- 作业标题。
- 发布或截止时间。
- 完成状态：
  - 未提交
  - 部分提交
  - 已提交
  - 已完成
- 题目通过概览，例如 `2/3 题通过`。
- 最后提交时间。
- 操作入口：
  - 查看作业进度
  - 可定位到现有教师作业进度页

学生画像页不直接展示提交代码、测试用例详情或 AI 评审全文。需要深钻时跳转到现有作业进度页，并可带上学生标识作为查询参数，例如 `/teacher/assignments/:assignmentId/progress?studentId=:studentId`，用于打开后自动定位该学生行。

### 提问情况 Tab

提问情况 Tab 分为两层：

第一层是知识点汇总：

- 知识点名称。
- 提问次数。
- 最近提问时间。

点击某个知识点后，展示第二层“相关提问时间线”：

- 每条时间线记录对应一次包含该知识点的问答轮次。
- 展示会话标题、提问时间、学生问题摘要和 AI 回答摘要。
- 点击记录后展开完整的学生问题和 AI 回答。

同一个知识点可能出现在多个会话和多个时间点，所以不直接跳进单个会话，而是先展示该知识点的相关问答时间线。这样更符合教师排查学习困难的路径。

## 数据流

### 现有可复用数据

当前教师端已经有以下能力可复用：

- `GET /api/teacher/students`：学生列表，包含薄弱点数和未完成作业次数。
- `GET /api/teacher/students/{student_id}/weak-points`：单个学生薄弱点。
- `GET /api/teacher/students/{student_id}/consultations`：单个学生提问知识点汇总。

### 建议新增接口

为避免前端遍历所有作业进度接口，建议新增学生维度的轻量聚合接口。

#### 学生作业情况

`GET /api/teacher/students/{student_id}/assignments`

返回该学生被布置过的作业列表，每条包含：

- `assignment_id`
- `title`
- `due_at`
- `status`
- `question_count`
- `submitted_question_count`
- `accepted_question_count`
- `latest_submitted_at`

状态由该学生在该作业下的题目提交情况聚合得到。具体提交详情仍通过现有作业进度和提交详情接口查看。

#### 知识点相关问答时间线

`GET /api/teacher/students/{student_id}/consultations/{knowledge_node_id}/turns`

返回该学生围绕某个知识点的相关问答轮次，每条包含：

- `event_id`
- `session_id`
- `session_title`
- `user_message_id`
- `assistant_message_id`
- `asked_at`
- `user_content`
- `assistant_content`

该接口基于 `chat_knowledge_events` 关联 `chat_messages` 和 `chat_sessions` 查询。教师只能读取学生历史，不能修改会话。

## 前端结构

建议在现有 `TeacherStudentsPage.vue` 基础上做有边界的拆分，避免页面继续膨胀：

- `TeacherStudentsPage.vue`：页面容器，负责学生筛选、选中学生、Tab 状态和数据编排。
- `StudentPortraitSummary.vue`：学生摘要区。
- `StudentWeakPointsPanel.vue`：薄弱点列表。
- `StudentAssignmentsPanel.vue`：作业情况列表。
- `StudentConsultationsPanel.vue`：提问知识点汇总和相关问答时间线。

API 封装继续放在 `frontend/src/api/teacher.js`：

- `listTeacherStudentAssignmentsApi(studentId)`
- `listTeacherStudentConsultationTurnsApi(studentId, knowledgeNodeId)`

如果初期希望控制改动范围，可以先不拆组件，只在 `TeacherStudentsPage.vue` 内完成结构调整；但新增接口封装仍应放在 `teacher.js`。

## 后端结构

后端沿用现有教师端分层：

- 路由：`backend/api/routes/teacher.py`
- Schema：`backend/schemas/teacher.py`
- 服务：`backend/services/teacher_service.py` 和 `backend/services/chat_knowledge_event_service.py`

建议新增：

- `TeacherStudentAssignmentResponse`
- `TeacherStudentConsultationTurnResponse`
- `list_student_assignments(db, student_id)`
- `list_student_consultation_turns(db, student_id, knowledge_node_id, limit)`

学生存在性检查保持在教师路由或服务层，要求 `role == "student"`。

## 权限与边界

- 所有新增教师接口必须依赖 `get_current_teacher`。
- 教师接口只读学生聊天历史，不复用学生端 `/api/chat` 的当前用户会话接口。
- 返回聊天内容时只返回与选中知识点关联的问答轮次，避免一次性暴露大量无关会话内容。
- 作业情况只读聚合状态，不修改提交、判题或 AI 评审结果。

## 错误与空状态

- 学生不存在：返回 404，前端提示“学生不存在或已被移除”。
- 学生无薄弱点：显示“暂无薄弱知识点”。
- 学生无作业：显示“暂无已布置作业”。
- 学生无提问知识点：显示“暂无提问记录”。
- 知识点无相关问答轮次：显示“暂无可展开的聊天记录”，但保留知识点汇总行。
- 接口失败：页面顶部保留当前 `feedback error` 形式提示，并允许切换学生后重新加载。

## 验证

实施完成后至少运行：

```powershell
python -m compileall backend
npm --prefix frontend run build
```

如果新增了服务层单元测试或集成测试，再运行：

```powershell
pytest
```

手工验证路径：

- 教师登录后进入“学生画像”。
- 选择不同学生，摘要、薄弱点、作业情况和提问情况同步刷新。
- 在作业情况中点击某个作业，可以跳转到教师作业进度页。
- 在提问情况中点击某个知识点，可以看到该知识点的相关问答时间线。
- 展开问答记录后，学生问题和 AI 回答内容正确对应。

## 实施顺序建议

1. 调整教师侧边栏文案和学生页标题为“学生画像”。
2. 重排 `TeacherStudentsPage.vue` 页面结构，形成摘要区和三个 Tab。
3. 新增学生作业情况接口并接入作业情况 Tab。
4. 新增知识点相关问答时间线接口并接入提问情况 Tab。
5. 为作业进度页增加可选 `studentId` 查询参数定位能力。
6. 执行后端语法检查和前端构建检查。
