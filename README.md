# 基于大模型与知识图谱的自适应编程作业辅导系统

本项目是一个面向编程学习场景的自适应辅导系统，结合了：

- 大模型问答与讲解
- Neo4j 知识图谱检索与推荐
- 薄弱点识别与针对性训练
- 教师端知识图谱维护与候选知识子图审核

前端使用 Vue 3 + Vite，后端使用 FastAPI，数据层同时使用 MySQL 和 Neo4j。

## 主要功能

- 学生端聊天问答：基于图谱检索和大模型回答编程问题
- 薄弱点识别：根据对话与学习过程提取核心知识点，记录学生薄弱点
- 弱点推荐图谱：围绕薄弱点展示推荐学习结点与待审核候选结点
- 针对性训练：支持正式推荐结点与 pending 候选结点的做题练习
- 教师图谱管理：正式图谱编辑、候选批次审核、知识结点补充入图
- 作业管理：教师布置 Java 编程作业、选择学生发布、Docker 沙箱运行学生提交并提供 AI 辅导
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

- MySQL：用户、会话、薄弱点、pending 审核批次等结构化数据
- Neo4j：正式知识图谱

## 项目结构

```text
backend/   FastAPI 后端、数据库模型、服务层、路由
frontend/  Vue 前端页面、API 封装、图谱组件
docs/      维护文档
```

目前较重要的维护文档：

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
- `NEO4J_*`：正式知识图谱数据库连接
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

## 系统中的两类图谱数据

### 1. 正式图谱

- 存在 Neo4j
- 由教师端正式维护
- 会被聊天检索、弱点推荐、图谱展示等功能使用

### 2. 候选批次（pending batch）

- 存在 MySQL
- 来源于聊天或弱点推荐过程中，大模型提议出的候选知识子图
- 需要教师审核通过后，才会并入 Neo4j 正式图谱

## 关键页面

### 学生端

- Chat：编程问答与图谱辅助解释
- Weak Points：薄弱点、推荐学习路径、pending 候选学习点
- Assignments：查看作业、提交 Java 代码、查看测试结果、向作业助教提问

### 教师端

- TeacherGraphPage：正式图谱维护与候选批次审核
- TeacherDashboard / TeacherStudents：学生与班级概览
- TeacherAssignmentsPage：创建和维护编程作业、发布给指定学生

## 维护建议

- 不要把 pending 候选直接写进 Neo4j，必须走教师审核
- 登录态统一通过 `frontend/src/utils/authStorage.js` 访问，不要直接操作 `localStorage`
- 修改教师图谱审核逻辑前，先看：
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
- TeacherGraphPage 已经区分：
  - 正式图谱模式
  - 候选审核模式
- Chat 触发的 pending 候选会复用到弱点页与教师审核页

## License

当前仓库未单独声明许可证，如需开源或对外发布，建议补充 `LICENSE` 文件。
