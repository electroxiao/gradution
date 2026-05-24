# AGENTS.md

本文件供 Codex、Claude Code 等编码代理在本仓库中工作时参考。请先阅读本文件，再按需阅读 `README.md`、`启动.txt` 和相关源码。

## 项目概览

这是一个“基于大模型与知识图谱的自适应编程作业辅导系统”。

- 前端：Vue 3 + Vite + Pinia + Vue Router + Axios + Neo4j NVL 图谱组件
- 后端：FastAPI + SQLAlchemy + PyMySQL + Neo4j Python Driver + OpenAI SDK
- 数据层：MySQL 存结构化业务数据，Neo4j 存知识图谱
- 沙箱：通过本机 Docker 运行学生提交的 Java 作业代码

主要业务模块：

- 学生端聊天问答、提问知识点记录、作业错题薄弱点识别、弱点推荐图谱、针对性训练
- 教师端图谱维护、学生与班级管理
- 编程作业发布、题目知识点绑定、学生代码提交、Docker 沙箱测试、AI 作业辅导
- 同一浏览器多角色并存，登录态按标签页隔离

## 目录结构

```text
backend/   FastAPI 后端、数据库模型、服务层、路由
frontend/  Vue 前端页面、API 封装、组件、状态管理
docs/      维护文档
tests/     后端集成测试
```

维护教师图谱相关逻辑前，先阅读：

- `docs/teacher-graph-maintenance.md`

## 环境要求

- Python 3.10+
- Node.js 18+
- MySQL
- Neo4j
- Docker Desktop 或可用的 Docker Engine

复制 `.env.example` 为 `.env`，并按本地环境修改 MySQL、Neo4j、LLM 和 Docker 沙箱配置。不要提交真实密钥或本地敏感配置。

## 安装依赖

后端：

```powershell
pip install -r requirements.txt
```

前端：

```powershell
npm --prefix frontend install
```

测试依赖：

```powershell
pip install -r requirements-test.txt
```

## 启动方式

后端：

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 9000 --reload
```

前端：

```powershell
npm --prefix frontend run dev
```

默认地址：

- 后端 API：`http://127.0.0.1:9000`
- 健康检查：`GET /api/health`
- 前端：`http://localhost:5173`

编程作业沙箱依赖 Docker。Windows 本地建议按此顺序启动：

1. 打开 Docker Desktop，并等待 Engine running。
2. 启动 MySQL 和 Neo4j。
3. 启动 FastAPI 后端。
4. 启动 Vue 前端。

如需验证 Docker：

```powershell
docker info
docker pull eclipse-temurin:17-jdk
docker run --rm eclipse-temurin:17-jdk java -version
```

## 常用检查命令

后端语法检查：

```powershell
python -m compileall backend
```

前端构建检查：

```powershell
npm --prefix frontend run build
```

测试：

```powershell
pytest
```

注意：`pytest.ini` 中的 `integration` 标记表示测试可能依赖运行中的后端和真实外部服务。运行失败时先确认 MySQL、Neo4j、Docker、后端服务和 `.env` 是否可用。

## 后端约定

- 后端入口是 `backend/main.py`。
- 路由、模型、schema、服务层分别放在 `backend/api/`、`backend/models/`、`backend/schemas/`、`backend/services/`。
- 启动时会执行数据库表结构检查和种子数据初始化，包括教师账号。
- MySQL 负责用户、会话、薄弱点、作业与题目知识点绑定等结构化数据。
- Neo4j 只保存知识图谱。
- 学生 Java 代码运行必须经过 Docker 沙箱，沙箱默认无网络并限制内存、CPU 和超时时间。

## 前端约定

- 前端入口在 `frontend/src/main.js`，全局样式在 `frontend/src/styles.css`。
- 页面主要位于 `frontend/src/pages/`，API 封装位于 `frontend/src/api/`。
- 登录态必须通过 `frontend/src/utils/authStorage.js` 访问，不要直接操作 `localStorage`。
- 图谱展示使用 `@neo4j-nvl/*`，当前图谱标签采用 NVL 的 `node.html` 方案显示文字。
- TeacherGraphPage 维护 Neo4j 图谱。

## 业务边界

- 系统图谱数据以 Neo4j 图谱为准，用于聊天提问知识点记录、弱点推荐、图谱展示、作业题目知识点绑定和训练节点上下文。
- 作业模块涉及教师布置 Java 编程作业、题目绑定知识点、学生提交代码、Docker 沙箱执行和 AI 辅导，不要把代码执行逻辑改成非隔离运行。
- 作业错题的薄弱点更新只依赖题目绑定知识点：提交状态不是 `accepted` 时，将该题绑定的所有知识点标记为未掌握薄弱点；AI 评审 `diagnoses` 只作为解释信息展示。

## 修改建议

- 优先沿用现有后端分层、前端页面/API 封装模式，不要为小改动引入新的框架或全局抽象。
- 改动共享接口时，同时检查后端 schema、前端 API 封装和相关页面调用。
- 涉及教师图谱维护数据流时，阅读 `docs/teacher-graph-maintenance.md` 后再改。
- 涉及登录态时，只改 `authStorage` 及其调用方，不要新增直接读写浏览器存储的路径。
- 涉及 Docker 沙箱时，保留无网络、资源限制和超时控制。
- 保持 `.env`、密钥、数据库密码、LLM API Key 不入库。

## 提交前检查

根据改动范围至少执行：

```powershell
python -m compileall backend
npm --prefix frontend run build
```

如果改动了后端业务流程或测试相关逻辑，再运行：

```powershell
pytest
```

如果改动了作业沙箱，请额外确认：

```powershell
docker info
docker run --rm eclipse-temurin:17-jdk java -version
```
