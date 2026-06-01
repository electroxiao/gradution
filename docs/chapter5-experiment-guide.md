# 第五章实验复现说明

本文档记录第五章实验样本生成、实验运行和结果查看流程，便于后续重新运行实验或调整样本。实验脚本均在项目根目录下执行。

## 1. 实验内容

第五章当前包含两组实验：

1. 自动判题准确性实验
   - 填空题：基础答案样本 + 语义/格式边界样本。
   - 编程题：基础正确/错误代码样本 + AI 复核增强样本。
   - 统计准确率、精确率、召回率和 F1。

2. 图谱增强答疑检索实验
   - 使用 Java 学习问题和人工标注知识点。
   - 调用大模型抽取关键词，再查询 Neo4j 知识图谱。
   - 统计问题级命中率和知识点覆盖率。

## 2. 相关文件

| 文件 | 作用 |
|---|---|
| `tests/experiment_samples/build_chapter5_samples.py` | 生成第五章实验样本 JSON |
| `tests/experiment_samples/chapter5_experiment_samples.json` | 实验样本文件 |
| `tests/experiments/run_chapter5_experiments.py` | 实验运行脚本 |
| `.codex_tmp/chapter5_experiment_results/chapter5_experiment_result.json` | 完整实验结果 |
| `.codex_tmp/chapter5_experiment_results/chapter5_experiment_tables.md` | 可直接复制到论文的结果表 |

## 3. 运行前准备

运行实验前，需要保证项目依赖的服务已经启动：

1. MySQL 已启动。
2. Neo4j 已启动，并且已有知识图谱数据。
3. 后端 `.env` 中的大模型配置可用。
4. Docker Desktop 已启动，编程题判题依赖 Java Docker 沙箱。

建议先确认 Docker 可用：

```powershell
docker info
docker run --rm eclipse-temurin:17-jdk java -version
```

如果只运行图谱增强实验，不需要 Docker；如果只运行自动判题中的编程题，则必须保证 Docker 可用。

## 4. 生成实验样本

每次修改样本脚本后，先重新生成样本 JSON：

```powershell
python tests\experiment_samples\build_chapter5_samples.py
```

生成成功后会写入：

```text
tests/experiment_samples/chapter5_experiment_samples.json
```

当前样本规模如下：

| 实验类型 | 题目数 | 提交/问题数 | 说明 |
|---|---:|---:|---|
| 填空题判题 | 20 | 52 | 含基础样本和边界答案样本 |
| 编程题判题 | 25 | 35 | 含基础编程题和 15 条 AI 复核增强样本 |
| 图谱增强检索 | 25 | 25 | 每题人工标注 1-2 个核心知识点 |

## 5. 运行自动判题实验

推荐使用并发参数运行：

```powershell
python tests\experiments\run_chapter5_experiments.py --mode grading --fill-workers 10 --programming-workers 3
```

参数说明：

| 参数 | 含义 |
|---|---|
| `--mode grading` | 只运行自动判题实验 |
| `--fill-workers 10` | 填空题并发数为 10 |
| `--programming-workers 3` | 编程题并发数为 3 |

编程题会调用 Docker 沙箱，若出现 Docker pipe permission 相关错误，通常是因为脚本运行环境无法访问 Docker Desktop。此时应确认 Docker Desktop 已启动，并在有权限的终端中重新执行命令。

## 6. 运行图谱增强答疑检索实验

推荐使用较低并发，避免大模型接口请求过快：

```powershell
python tests\experiments\run_chapter5_experiments.py --mode rag --rag-workers 2
```

参数说明：

| 参数 | 含义 |
|---|---|
| `--mode rag` | 只运行图谱增强答疑检索实验 |
| `--rag-workers 2` | RAG 问题并发数为 2 |

图谱增强实验会调用大模型服务和 Neo4j。若出现 `Connection error`，优先检查网络、大模型 API 配置和 Neo4j 连接配置。

## 7. 一次性运行全部实验

如需一次性运行自动判题和图谱增强检索，可以执行：

```powershell
python tests\experiments\run_chapter5_experiments.py --mode all --fill-workers 10 --programming-workers 3 --rag-workers 2
```

由于该命令同时调用 Docker、大模型和 Neo4j，耗时会更长，也更容易受到外部服务状态影响。实际写论文时，可以分别运行 `grading` 和 `rag`，便于定位问题。

## 8. 查看实验结果

实验完成后，查看 Markdown 结果表：

```powershell
Get-Content .codex_tmp\chapter5_experiment_results\chapter5_experiment_tables.md
```

当前一次实验结果如下：

### 自动判题准确性实验

| 范围 | 样本数 | TP | FP | FN | TN | 准确率 | 精确率 | 召回率 | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 填空题 | 52 | 25 | 0 | 0 | 27 | 100.00% | 100.00% | 100.00% | 100.00% |
| 编程题 | 35 | 24 | 0 | 1 | 10 | 97.14% | 100.00% | 96.00% | 97.96% |
| 总体 | 87 | 49 | 0 | 1 | 37 | 98.85% | 100.00% | 98.00% | 98.99% |

### 图谱增强答疑检索实验

| 问题数 | 问题级命中率 | 知识点覆盖率 | 命中知识点数 | 人工标注知识点数 |
|---:|---:|---:|---:|---:|
| 25 | 92.00% | 83.78% | 31 | 37 |

## 9. 指标含义

自动判题实验中，将“错误提交被系统识别为未通过”视为正类。

| 指标 | 含义 |
|---|---|
| TP | 错误提交被正确识别为错误 |
| FP | 正确提交被误判为错误 |
| FN | 错误提交被误判为正确 |
| TN | 正确提交被正确识别为正确 |

计算公式如下：

```text
Accuracy = (TP + TN) / (TP + FP + FN + TN)
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 * Precision * Recall / (Precision + Recall)
```

图谱增强答疑检索实验中：

```text
QuestionHitRate = 至少命中一个标注知识点的问题数 / 问题总数
Coverage = 命中的人工标注知识点数 / 人工标注知识点总数
```

## 10. 样本设计说明

当前实验集加入了真实边界样本和 AI 复核增强样本。其目的不是人为修改结果，而是分别检验客观题语义判分能力，以及编程题在测试用例通过后继续进行代码语义复核的能力。

填空题边界样本主要包括：

- `equals()` 与 `equals` 这类格式差异。
- `keySet()` 与 `keySet` 这类方法名写法差异。
- `start()` 与 `start` 这类带括号答案。
- “参数列表”等语义等价答案。
- “返回值和参数列表”等部分错误答案。

编程题 AI 复核增强样本主要包括：

- 面向测试用例硬编码输入和输出。
- 只处理固定输入规模，不满足题干要求的通用输入。
- 通过测试输出，但违反题目指定算法要求。
- 当前测试用例通过，但遗漏题干明确要求的边界条件。
- 使用外部命令或危险 API 完成计算。
- 输出结果正确，但实现方式不符合教学目标。

这类样本的共同特点是：代码能够通过当前测试用例，但存在隐藏问题。系统在测试用例通过后继续调用大模型进行复核，如果大模型发现硬编码、投机实现、安全风险或题意违背，则仍可将提交判定为不通过。

## 11. 误判分析方法

如需查看具体误判样本，可以执行：

```powershell
@'
import json
from pathlib import Path

r = json.loads(Path(".codex_tmp/chapter5_experiment_results/chapter5_experiment_result.json").read_text(encoding="utf-8"))
for row in r["grading"]["rows"]:
    expected_wrong = row["expected_status"] != "accepted"
    actual_wrong = row["actual_status"] != "accepted"
    if expected_wrong != actual_wrong:
        print(row["sample_id"], row["question_type"], "expected=", row["expected_status"], "actual=", row["actual_status"])
        print(row.get("summary", ""))
        print()
'@ | python -
```

当前实验中，自动判题共有 1 个 FN，来自编程题 AI 复核增强样本。该样本为“统计元音字母（忽略大小写）”，错误代码只统计小写元音，但当前测试用例均为小写输入，因此测试用例通过；大模型复核也未发现其未处理大写输入。与此同时，15 条 AI 复核增强样本中有 14 条被正确拒绝，说明系统能够在测试用例通过后继续发现多数隐藏问题。

## 12. 推荐论文表述

论文中建议将该实验描述为“小规模实验样本集上的功能有效性验证”，不要表述为大规模泛化性能评估。

可以采用如下表述：

```text
实验样本由基础题目样本、填空题边界样本和编程题 AI 复核增强样本组成。编程题增强样本用于模拟“测试用例输出正确但代码存在硬编码样例、固定输入规模、违反指定算法或危险 API 使用”等情况。实验结果表明，系统不仅能够完成基于测试用例的输出比对，还能在测试通过后通过大模型复核识别多数隐藏问题，从而弥补单纯输入输出测试的不足。
```
