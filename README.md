# 基于大模型与知识图谱的智能助学系统

本项目是一个基于大模型与知识图谱的智能助学系统，结合了：

- 大模型问答与图谱增强讲解
- Neo4j 知识图谱维护、知识点记录与推荐
- 薄弱点识别与针对性训练
- 教师端知识图谱维护

前端使用 Vue 3 + Vite，后端使用 FastAPI，数据层同时使用 MySQL 和 Neo4j。

## 主要功能

- 学生端聊天问答：默认先检索 Neo4j 知识图谱并展示相关节点、已选路径和检索过程，再生成图谱增强回答；也支持关闭图谱检索回退为普通大模型辅导回答
- 薄弱点识别：根据作业错题绑定的知识点记录学生未掌握薄弱点
- 弱点推荐图谱：围绕薄弱点展示图谱中的推荐学习节点
- 针对性训练：支持推荐节点的做题练习，答对后可标记对应薄弱点为已掌握
- 教师图谱管理：图谱增删查改
- 作业管理：教师布置 Java 编程作业、绑定知识点、选择学生发布、Docker 沙箱运行学生提交并提供 AI 辅导
- 同浏览器多角色并存：前端登录态按标签页隔离，教师和学生可同时在线

## 技术栈

### 前端

- Vue 3
- Vue Router
- Pinia
- Axios
- `@neo4j-nvl/*` 图谱可视化组件

### 后端

- FastAPI
- SQLAlchemy
- PyMySQL
- Neo4j Python Driver
- OpenAI SDK

### 数据存储

- MySQL：用户、会话、薄弱点、作业与题目知识点绑定等结构化数据
- Neo4j：知识图谱

## 项目结构

```text
backend/   FastAPI 后端、数据库模型、服务层、路由
frontend/  Vue 前端页面、API 封装、图谱组件
docs/      维护文档
```

目前较重要的维护文档：

- [docs/chat-rag-flow.md](docs/chat-rag-flow.md)
- [docs/teacher-graph-maintenance.md](docs/teacher-graph-maintenance.md)

## 环境要求

- Python 3.10+
- Node.js 18+
- MySQL
- Neo4j
- Docker（用于运行学生提交的 Java 作业代码）

## 安装依赖

### 后端

```powershell
pip install -r requirements.txt
```

### 前端

```powershell
npm --prefix frontend install
```

## 环境变量

复制 `.env.example` 为 `.env`，再按本地环境修改：

```env
APP_ENV=development
SECRET_KEY=change-me
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/java_tutor?charset=utf8mb4
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678
NEO4J_DB_NAME=javagemini
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
CORS_ORIGINS=http://localhost:5173
TEACHER_SEED_USERNAME=teacher
TEACHER_SEED_PASSWORD=teacher123
SANDBOX_DOCKER_IMAGE=eclipse-temurin:17-jdk
SANDBOX_TIMEOUT_SECONDS=5
SANDBOX_MEMORY_LIMIT=256m
SANDBOX_CPU_LIMIT=1
```

说明：

- `DATABASE_URL`：MySQL 连接串
- `NEO4J_*`：知识图谱数据库连接
- `LLM_*`：大模型 API 配置
- `TEACHER_SEED_*`：系统初始化时自动创建的教师账号
- `SANDBOX_*`：学生编程作业 Docker 沙箱配置

## Docker 沙箱配置与启动

编程作业的代码运行依赖 Docker。后端不会自动启动 Docker Desktop，它只会在学生提交代码时调用系统里的 `docker run` 命令创建一次性 Java 容器。

Windows 本地开发时，启动顺序建议如下：

```text
1. 打开 Docker Desktop
2. 等待 Docker Desktop 显示 Running / Engine running
3. 启动 MySQL 和 Neo4j
4. 启动 FastAPI 后端
5. 启动 Vue 前端
```

确认 Docker 后台服务已经可用：

```powershell
docker info
```

首次使用编程作业前，拉取默认 Java 镜像：

```powershell
docker pull eclipse-temurin:17-jdk
```

也可以用下面命令确认镜像能正常运行：

```powershell
docker run --rm eclipse-temurin:17-jdk java -version
```

后端沙箱运行学生代码时会执行类似下面的容器策略：

```text
docker run --rm --network none --memory 256m --cpus 1 ...
```

含义：

- `--rm`：代码运行结束后自动删除容器
- `--network none`：容器不能访问网络
- `--memory`：限制容器内存
- `--cpus`：限制容器 CPU
- `SANDBOX_TIMEOUT_SECONDS`：后端对子进程设置超时，避免死循环长期占用资源

如果学生提交代码时出现 Docker 相关沙箱错误，先在启动后端的同一个 PowerShell 里执行：

```powershell
docker info
docker run --rm eclipse-temurin:17-jdk java -version
```

如果这两个命令失败，通常是 Docker Desktop 没启动完成、Docker Engine 未运行，或当前终端找不到 `docker` 命令。重启 Docker Desktop 和 PowerShell 后再启动后端即可。

## 启动方式

### 启动后端

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 9000 --reload
```

默认地址：

- 后端 API：`http://127.0.0.1:9000`
- 健康检查：`GET /api/health`

### 启动前端

```powershell
npm --prefix frontend run dev
```

默认前端地址：

- `http://localhost:5173`

## 初始化说明

后端启动时会自动执行：

- `Base.metadata.create_all(bind=engine)`
- `ensure_schema_and_seed(engine)`

这意味着项目会在启动时自动检查数据库表结构，并初始化部分种子数据，例如教师账号。

## 系统图谱数据

- 以 Neo4j 为来源，由教师端维护。
- MySQL 中的知识点表只镜像题目绑定、章节筛选和提问记录所需的引用信息。
- 学生聊天默认开启知识图谱检索：后端先从当前问题中抽取图谱实体关键词，再在 Neo4j 中召回种子节点、扩展子图、选择重点路径，并将 `facts`、推理轨迹和检索轨迹随本轮助手消息保存。
- 如果关闭“知识图谱检索”或图谱检索失败，系统回退为普通大模型辅导回答。
- 回答完成后，系统仍会在后台从本轮问答中抽取已存在的图谱知识点，写入聊天提问记录。
- 聊天提问知识点用于学生回看最近关注内容、教师查看提问热点，以及辅助图谱相关展示；薄弱点和掌握状态由作业错题与训练结果维护。
- 知识图谱还用于弱点推荐图谱、图谱展示、作业题目知识点绑定和针对性训练节点上下文。

## 作业错题与薄弱点

- 教师创建作业题目时可以绑定知识点。
- 学生提交题目后，后端先保存提交记录，再根据提交状态更新薄弱点。
- 只要提交状态不是 `accepted`，系统就会把该题绑定的所有知识点标记为学生未掌握薄弱点。
- 通过提交保持现有薄弱点状态；针对性训练答对后可将对应薄弱点标记为已掌握。
- 作业 AI 评审中的 `diagnoses` 只作为解释信息展示，不参与系统薄弱点写入。
- 聊天中抽取到的提问知识点记录到提问历史；作业错题负责写入薄弱点。

## 关键页面

### 学生端

- Chat：编程问答与提问知识点记录
- Weak Points：薄弱点、推荐学习路径、针对性训练
- Assignments：查看作业、提交 Java 代码、查看测试结果、向作业助教提问

### 教师端

- TeacherGraphPage：图谱维护
- TeacherDashboard / TeacherStudents：学生与班级薄弱点概览
- TeacherAssignmentsPage：创建和维护编程作业、发布给指定学生

## 维护建议

- 登录态统一通过 `frontend/src/utils/authStorage.js` 访问，不要直接操作 `localStorage`
- 修改学生聊天 RAG、图谱检索展示或聊天提问记录前，先看：
  - [docs/chat-rag-flow.md](docs/chat-rag-flow.md)
- 修改教师图谱维护逻辑前，先看：
  - [docs/teacher-graph-maintenance.md](docs/teacher-graph-maintenance.md)

## 常用检查命令

### 后端语法检查

```powershell
python -m compileall backend
```

### 前端构建检查

```powershell
npm --prefix frontend run build
```

## 当前已知特点

- 前端图谱标签目前使用 NVL 的 `node.html` 方案显示文字

## License

当前仓库未单独声明许可证，如需开源或对外发布，建议补充 `LICENSE` 文件。
