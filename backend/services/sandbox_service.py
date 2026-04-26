import subprocess
import tempfile
from pathlib import Path
from time import perf_counter

from backend.core.config import settings
from backend.models.assignment import AssignmentTestCase


def run_java_submission(
    code: str,
    test_cases: list[AssignmentTestCase],
    observe_only: bool = False,
) -> tuple[str, list[dict]]:
    with tempfile.TemporaryDirectory(prefix="java-assignment-") as temp_dir:
        workdir = Path(temp_dir)
        (workdir / "Main.java").write_text(code, encoding="utf-8")

        compile_result = _run_docker(["javac", "Main.java"], workdir)
        if compile_result["status"] != "ok":
            status = compile_result["status"]
            if status == "ok":
                status = "runtime_error"
            return status, [_compile_failure_result(compile_result)]
        if compile_result["returncode"] != 0:
            return "runtime_error", [_compile_failure_result(compile_result)]

        results = []
        overall_status = "accepted"
        run_cases = list(test_cases)
        if observe_only and not run_cases:
            run_cases = [None]

        for index, test_case in enumerate(run_cases, start=1):
            started_at = perf_counter()
            input_text = test_case.input_data if test_case is not None else ""
            run_result = _run_docker(["java", "Main"], workdir, input_text=input_text)
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            if observe_only:
                result = _observation_result(index, test_case, input_text, run_result, elapsed_ms)
            else:
                result = _case_result(index, test_case, run_result, elapsed_ms)
            results.append(result)
            if result["status"] != "accepted" and overall_status == "accepted":
                overall_status = result["status"]

        return overall_status, results


def _run_docker(args: list[str], workdir: Path, input_text: str | None = None) -> dict:
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--memory",
        settings.sandbox_memory_limit,
        "--cpus",
        settings.sandbox_cpu_limit,
        "-v",
        f"{workdir}:/workspace",
        "-w",
        "/workspace",
        settings.sandbox_docker_image,
        *args,
    ]
    if input_text is not None:
        command.insert(2, "-i")

    try:
        completed = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=settings.sandbox_timeout_seconds,
            check=False,
        )
        return {
            "status": "ok",
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "status": "timeout",
            "returncode": None,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "运行超时",
        }
    except FileNotFoundError:
        return {
            "status": "sandbox_error",
            "returncode": None,
            "stdout": "",
            "stderr": "Docker 未安装或不在 PATH 中。",
        }
    except Exception as error:
        return {
            "status": "sandbox_error",
            "returncode": None,
            "stdout": "",
            "stderr": str(error),
        }


def _compile_failure_result(result: dict) -> dict:
    status = "timeout" if result["status"] == "timeout" else "sandbox_error" if result["status"] == "sandbox_error" else "runtime_error"
    stderr = result.get("stderr", "")
    return {
        "case_index": 0,
        "is_sample": True,
        "status": status,
        "passed": False,
        "input": "",
        "expected_output": "",
        "actual_output": result.get("stdout", ""),
        "stderr": stderr,
        "elapsed_ms": 0,
        "error_signal": _classify_compile_error(stderr, status),
    }


def _classify_compile_error(stderr: str, status: str = "runtime_error") -> dict:
    if status == "timeout":
        return {
            "stage": "compile",
            "category": "compile_timeout",
            "candidate_concepts": ["编译流程", "代码结构"],
        }
    if status == "sandbox_error":
        return {
            "stage": "compile",
            "category": "sandbox_error",
            "candidate_concepts": ["运行环境"],
        }

    text = (stderr or "").lower()
    if "';' expected" in text or "illegal start of expression" in text or "reached end of file while parsing" in text:
        return {
            "stage": "compile",
            "category": "syntax_error",
            "candidate_concepts": ["Java基础语法", "语句结束符", "代码块结构"],
        }
    if "does not override or implement" in text:
        return {
            "stage": "compile",
            "category": "override_signature_error",
            "candidate_concepts": ["方法重写", "继承", "接口实现"],
        }
    if "cannot find symbol" in text:
        return {
            "stage": "compile",
            "category": "symbol_resolution",
            "candidate_concepts": ["变量作用域", "方法调用", "类与对象"],
        }
    if "incompatible types" in text:
        return {
            "stage": "compile",
            "category": "type_error",
            "candidate_concepts": ["数据类型", "类型转换", "泛型基础"],
        }
    if "non-static variable" in text and "static context" in text:
        return {
            "stage": "compile",
            "category": "static_instance_error",
            "candidate_concepts": ["静态成员", "实例成员", "main方法"],
        }
    if "constructor" in text and "cannot be applied" in text:
        return {
            "stage": "compile",
            "category": "constructor_argument_error",
            "candidate_concepts": ["构造方法", "方法参数", "对象创建"],
        }
    return {
        "stage": "compile",
        "category": "unknown_compile_error",
        "candidate_concepts": ["Java基础语法"],
    }


def _case_result(index: int, test_case: AssignmentTestCase, run_result: dict, elapsed_ms: int) -> dict:
    expected = (test_case.expected_output or "").rstrip()
    actual = (run_result.get("stdout") or "").rstrip()

    if run_result["status"] == "timeout":
        status = "timeout"
        passed = False
    elif run_result["status"] == "sandbox_error":
        status = "sandbox_error"
        passed = False
    elif run_result["returncode"] != 0:
        status = "runtime_error"
        passed = False
    elif actual == expected:
        status = "accepted"
        passed = True
    else:
        status = "wrong_answer"
        passed = False

    result = {
        "case_index": index,
        "is_sample": test_case.is_sample,
        "status": status,
        "passed": passed,
        "input": test_case.input_data if test_case.is_sample else "",
        "expected_output": test_case.expected_output if test_case.is_sample else "",
        "actual_output": actual if test_case.is_sample else "",
        "stderr": run_result.get("stderr", "") if test_case.is_sample or status != "accepted" else "",
        "elapsed_ms": elapsed_ms,
    }
    if not test_case.is_sample and status != "accepted":
        result["summary"] = "隐藏测试用例未通过"
    return result


def _observation_result(
    index: int,
    test_case: AssignmentTestCase | None,
    input_text: str,
    run_result: dict,
    elapsed_ms: int,
) -> dict:
    actual = (run_result.get("stdout") or "").rstrip()
    if run_result["status"] == "timeout":
        status = "timeout"
        passed = False
    elif run_result["status"] == "sandbox_error":
        status = "sandbox_error"
        passed = False
    elif run_result["returncode"] != 0:
        status = "runtime_error"
        passed = False
    else:
        status = "accepted"
        passed = True

    return {
        "case_index": index,
        "is_sample": True if test_case is None else test_case.is_sample,
        "status": status,
        "passed": passed,
        "input": input_text,
        "expected_output": "",
        "actual_output": actual,
        "stderr": run_result.get("stderr", ""),
        "elapsed_ms": elapsed_ms,
        "check_mode": "observe_only",
        "summary": "观察运行完成，输出将交由 AI 结合评分标准判断。",
    }
