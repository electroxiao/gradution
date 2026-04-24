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
    return {
        "case_index": 0,
        "is_sample": True,
        "status": status,
        "passed": False,
        "input": "",
        "expected_output": "",
        "actual_output": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "elapsed_ms": 0,
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
