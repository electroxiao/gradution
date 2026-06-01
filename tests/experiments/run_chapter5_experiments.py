from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.models.assignment import AssignmentTestCase
from backend.services import rag_engine
from backend.services.assignment_service import (
    _grade_submission,
    _resolve_ai_only_status,
    _run_ai_objective_review,
)
from backend.services.chat_service import get_openai_client
from backend.services.neo4j_service import get_neo4j_driver


DEFAULT_SAMPLES = ROOT / "tests" / "experiment_samples" / "chapter5_experiment_samples.json"
DEFAULT_OUT_DIR = ROOT / ".codex_tmp" / "chapter5_experiment_results"


def _node_relation(node_name: str, index: int):
    node = SimpleNamespace(id=index + 1, node_name=node_name)
    return SimpleNamespace(id=index + 1, sort_order=index, knowledge_node_id=index + 1, knowledge_node=node)


def _question_from_sample(sample: dict[str, Any]):
    return SimpleNamespace(
        id=sample["id"],
        title=sample["title"],
        prompt=sample["prompt"],
        question_type=sample["question_type"],
        options_json=[],
        answer_json=sample.get("answer"),
        explanation=sample.get("explanation", ""),
        grading_mode=sample.get("grading_mode", "ai_review"),
        enable_testcases=sample.get("enable_testcases", True),
        ai_review_level=sample.get("ai_review_level", "light"),
        ai_grading_rubric=sample.get("ai_grading_rubric", ""),
        ai_grading_focus_json=sample.get("ai_grading_focus_json", []),
        knowledge_nodes=[
            _node_relation(node_name, index)
            for index, node_name in enumerate(sample.get("expected_nodes", []))
        ],
        test_cases=[
            AssignmentTestCase(
                input_data=item["input_data"],
                expected_output=item["expected_output"],
                is_sample=bool(item.get("is_sample", True)),
                sort_order=int(item.get("sort_order", index)),
            )
            for index, item in enumerate(sample.get("test_cases", []))
        ],
    )


def _assignment():
    return SimpleNamespace(title="第五章自动判题实验")


def _is_wrong(status: str) -> bool:
    return status != "accepted"


def _metrics(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    tp = fp = fn = tn = 0
    for row in rows:
        expected_wrong = _is_wrong(row["expected_status"])
        actual_wrong = _is_wrong(row["actual_status"])
        if expected_wrong and actual_wrong:
            tp += 1
        elif not expected_wrong and actual_wrong:
            fp += 1
        elif expected_wrong and not actual_wrong:
            fn += 1
        else:
            tn += 1
    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "total": total,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _grade_fill_blank_task(task: dict[str, Any]) -> dict[str, Any]:
    assignment = _assignment()
    question_sample = task["question_sample"]
    submission = task["submission"]
    question = _question_from_sample(question_sample)
    review = _run_ai_objective_review(assignment, question, submission["answer"])
    actual_status = _resolve_ai_only_status(question, review)
    return {
        "sample_id": submission["id"],
        "question_id": question_sample["id"],
        "question_type": "fill_blank",
        "expected_status": submission["expected_status"],
        "actual_status": actual_status,
        "label": submission["label"],
        "summary": review.get("summary", ""),
        "decision_source": "ai_objective_review",
    }


def _grade_programming_task(task: dict[str, Any]) -> dict[str, Any]:
    assignment = _assignment()
    question_sample = task["question_sample"]
    submission = task["submission"]
    question = _question_from_sample(question_sample)
    actual_status, results, review, source = _grade_submission(assignment, question, submission["code"])
    return {
        "sample_id": submission["id"],
        "question_id": question_sample["id"],
        "question_type": "programming",
        "expected_status": submission["expected_status"],
        "actual_status": actual_status,
        "label": submission["label"],
        "summary": review.get("summary", "") if isinstance(review, dict) else "",
        "results": results,
        "decision_source": source,
    }


def _run_tasks_concurrently(tasks: list[dict[str, Any]], worker_count: int, fn, label: str) -> list[dict[str, Any]]:
    if not tasks:
        return []
    rows: list[dict[str, Any]] = []
    worker_count = max(1, min(worker_count, len(tasks)))
    print(f"[chapter5] {label}: {len(tasks)} samples, workers={worker_count}")
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_id = {executor.submit(fn, task): task["submission"]["id"] for task in tasks}
        for index, future in enumerate(as_completed(future_to_id), start=1):
            sample_id = future_to_id[future]
            row = future.result()
            rows.append(row)
            status = row.get("actual_status")
            if status is None and "question_hit" in row:
                status = "hit" if row["question_hit"] else "miss"
            print(f"[chapter5] {label}: {index}/{len(tasks)} done ({sample_id} -> {status})")
    return sorted(rows, key=lambda item: item["sample_id"])


def run_grading(samples: dict[str, Any], *, fill_workers: int = 8, programming_workers: int = 3) -> dict[str, Any]:
    fill_tasks = [
        {"question_sample": question_sample, "submission": submission}
        for question_sample in samples["grading"]["fill_blank"]
        for submission in question_sample["submissions"]
    ]
    programming_tasks = [
        {"question_sample": question_sample, "submission": submission}
        for question_sample in samples["grading"]["programming"]
        for submission in question_sample["submissions"]
    ]
    rows = []
    rows.extend(_run_tasks_concurrently(fill_tasks, fill_workers, _grade_fill_blank_task, "fill_blank"))
    rows.extend(_run_tasks_concurrently(programming_tasks, programming_workers, _grade_programming_task, "programming"))

    by_type = {}
    for question_type in ["fill_blank", "programming"]:
        by_type[question_type] = _metrics([row for row in rows if row["question_type"] == question_type])
    return {"rows": rows, "metrics": {"overall": _metrics(rows), **by_type}}


def _fact_names(value: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"keyword", "name", "node_name", "seed", "source", "target"} and isinstance(item, str):
                names.add(item.strip())
            elif isinstance(item, (dict, list)):
                names.update(_fact_names(item))
    elif isinstance(value, list):
        for item in value:
            names.update(_fact_names(item))
    return {name for name in names if name}


def _run_rag_task(task: dict[str, Any]) -> dict[str, Any]:
    sample = task["sample"]
    client = get_openai_client()
    driver = get_neo4j_driver()
    reasoning_trace: list = []
    retrieval_trace: list = []
    keywords = rag_engine.extract_keywords_with_llm(client, sample["question"], history=[], trace=reasoning_trace)
    facts = rag_engine.query_graph_with_reasoning(
        driver,
        client,
        sample["question"],
        keywords=keywords,
        max_depth=2,
        width=3,
        reasoning_trace=reasoning_trace,
        retrieval_trace=retrieval_trace,
    )
    actual_names = _fact_names(facts)
    expected_names = set(sample["expected_nodes"])
    matched = sorted(expected_names & actual_names)
    return {
        "sample_id": sample["id"],
        "question": sample["question"],
        "expected_nodes": sample["expected_nodes"],
        "keywords": keywords,
        "matched_nodes": matched,
        "actual_nodes": sorted(actual_names),
        "question_hit": bool(matched),
        "facts_count": len(facts),
    }


def run_rag(samples: dict[str, Any], *, rag_workers: int = 4) -> dict[str, Any]:
    tasks = [{"sample": sample, "submission": {"id": sample["id"]}} for sample in samples["rag_retrieval"]]
    rows = _run_tasks_concurrently(tasks, rag_workers, _run_rag_task, "rag")
    total_expected = 0
    total_matched = 0
    question_hits = 0
    for row in rows:
        expected_names = set(row["expected_nodes"])
        matched = row["matched_nodes"]
        total_expected += len(expected_names)
        total_matched += len(matched)
        if matched:
            question_hits += 1
    total_questions = len(samples["rag_retrieval"])
    return {
        "rows": rows,
        "metrics": {
            "total_questions": total_questions,
            "question_hit_rate": round(question_hits / total_questions, 4) if total_questions else 0.0,
            "knowledge_coverage": round(total_matched / total_expected, 4) if total_expected else 0.0,
            "matched_expected_nodes": total_matched,
            "total_expected_nodes": total_expected,
        },
    }


def _percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def write_markdown(result: dict[str, Any], path: Path) -> None:
    lines = ["# 第五章实验结果", ""]
    if "grading" in result:
        lines.extend(["## 自动判题准确性实验", ""])
        lines.append("| 范围 | 样本数 | TP | FP | FN | TN | 准确率 | 精确率 | 召回率 | F1 |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for key, label in [("fill_blank", "填空题"), ("programming", "编程题"), ("overall", "总体")]:
            item = result["grading"]["metrics"][key]
            lines.append(
                f"| {label} | {item['total']} | {item['tp']} | {item['fp']} | {item['fn']} | {item['tn']} | "
                f"{_percent(item['accuracy'])} | {_percent(item['precision'])} | {_percent(item['recall'])} | {_percent(item['f1'])} |"
            )
        lines.append("")
    if "rag" in result:
        lines.extend(["## 图谱增强答疑检索命中实验", ""])
        item = result["rag"]["metrics"]
        lines.append("| 问题数 | 问题级命中率 | 知识点覆盖率 | 命中知识点数 | 人工标注知识点数 |")
        lines.append("|---:|---:|---:|---:|---:|")
        lines.append(
            f"| {item['total_questions']} | {_percent(item['question_hit_rate'])} | {_percent(item['knowledge_coverage'])} | "
            f"{item['matched_expected_nodes']} | {item['total_expected_nodes']} |"
        )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Chapter 5 experiment samples against backend services.")
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--mode", choices=["grading", "rag", "all"], default="all")
    parser.add_argument("--fill-workers", type=int, default=10, help="Concurrent workers for fill-blank grading samples.")
    parser.add_argument("--programming-workers", type=int, default=3, help="Concurrent workers for programming grading samples.")
    parser.add_argument("--rag-workers", type=int, default=4, help="Concurrent workers for RAG retrieval samples.")
    args = parser.parse_args()

    samples = json.loads(args.samples.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "chapter5_experiment_result.json"
    if args.mode != "all" and json_path.exists():
        result = json.loads(json_path.read_text(encoding="utf-8"))
        result["sample_file"] = str(args.samples)
    else:
        result: dict[str, Any] = {"sample_file": str(args.samples)}
    if args.mode in {"grading", "all"}:
        result["grading"] = run_grading(
            samples,
            fill_workers=args.fill_workers,
            programming_workers=args.programming_workers,
        )
    if args.mode in {"rag", "all"}:
        result["rag"] = run_rag(samples, rag_workers=args.rag_workers)

    md_path = args.out_dir / "chapter5_experiment_tables.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(result, md_path)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
