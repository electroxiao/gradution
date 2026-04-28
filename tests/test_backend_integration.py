import httpx
import pytest

from backend.core.security import get_password_hash
from backend.db.session import SessionLocal
from backend.models.user import User
from tests.conftest import assert_status, auth_headers, unique_name


pytestmark = pytest.mark.integration


def test_health_check(client: httpx.Client) -> None:
    response = client.get("/api/health")
    assert_status(response, 200)
    assert response.json() == {"status": "ok"}


def test_authentication_flow(
    client: httpx.Client,
    teacher_token: str,
    test_student: dict,
) -> None:
    teacher_response = client.get("/api/auth/me", headers=auth_headers(teacher_token))
    assert_status(teacher_response, 200)
    assert teacher_response.json()["role"] == "teacher"

    student_login = client.post(
        "/api/auth/login",
        json={"username": test_student["username"], "password": test_student["password"]},
    )
    assert_status(student_login, 200)
    assert student_login.json()["user"]["role"] == "student"

    student_response = client.get(
        "/api/auth/me",
        headers=auth_headers(test_student["token"]),
    )
    assert_status(student_response, 200)
    assert student_response.json()["username"] == test_student["username"]


def test_permissions(client: httpx.Client, test_student: dict) -> None:
    protected_response = client.get("/api/auth/me")
    assert_status(protected_response, {401, 403})

    teacher_only_response = client.get(
        "/api/teacher/students",
        headers=auth_headers(test_student["token"]),
    )
    assert_status(teacher_only_response, 403)


def test_teacher_read_endpoints(
    client: httpx.Client,
    teacher_token: str,
    neo4j_available: None,
) -> None:
    headers = auth_headers(teacher_token)

    students_response = client.get("/api/teacher/students", headers=headers)
    assert_status(students_response, 200)
    assert isinstance(students_response.json(), list)

    graph_response = client.get("/api/teacher/graph", params={"limit": 10}, headers=headers)
    assert_status(graph_response, 200)
    assert isinstance(graph_response.json(), (dict, list))


def test_assignment_submission_integration_flow(
    client: httpx.Client,
    auto_test_prefix: str,
    teacher_token: str,
    test_student: dict,
) -> None:
    teacher_headers = auth_headers(teacher_token)
    student_headers = auth_headers(test_student["token"])
    assignment_title = unique_name(auto_test_prefix, "assignment")

    create_response = client.post(
        "/api/teacher/assignments",
        headers=teacher_headers,
        json={
            "title": assignment_title,
            "description": "Created by backend integration tests.",
            "status": "published",
            "student_ids": [test_student["id"]],
            "questions": [
                {
                    "title": "Echo input",
                    "prompt": "Read one line from standard input and print the same line.",
                    "starter_code": "",
                    "language": "java",
                    "enable_testcases": True,
                    "ai_review_level": "light",
                    "sort_order": 0,
                    "test_cases": [
                        {
                            "input_data": "hello\n",
                            "expected_output": "hello",
                            "is_sample": True,
                            "sort_order": 0,
                        },
                        {
                            "input_data": "AUTO_TEST\n",
                            "expected_output": "AUTO_TEST",
                            "is_sample": False,
                            "sort_order": 1,
                        },
                    ],
                }
            ],
        },
    )
    assert_status(create_response, 200)
    assignment = create_response.json()
    assignment_id = assignment["id"]
    question_id = assignment["questions"][0]["id"]
    assert assignment["title"] == assignment_title
    assert assignment["assigned_students"][0]["id"] == test_student["id"]

    detail_response = client.get(
        f"/api/teacher/assignments/{assignment_id}",
        headers=teacher_headers,
    )
    assert_status(detail_response, 200)
    assert detail_response.json()["questions"][0]["id"] == question_id

    progress_response = client.get(
        f"/api/teacher/assignments/{assignment_id}/progress",
        headers=teacher_headers,
    )
    assert_status(progress_response, 200)
    progress = progress_response.json()
    assert any(student["id"] == test_student["id"] for student in progress["students"])
    assert any(question["id"] == question_id for question in progress["questions"])

    student_assignments_response = client.get("/api/assignments", headers=student_headers)
    assert_status(student_assignments_response, 200)
    assert any(item["id"] == assignment_id for item in student_assignments_response.json())

    student_detail_response = client.get(
        f"/api/assignments/{assignment_id}",
        headers=student_headers,
    )
    assert_status(student_detail_response, 200)
    assert student_detail_response.json()["questions"][0]["id"] == question_id

    submit_response = client.post(
        f"/api/assignments/{assignment_id}/questions/{question_id}/submit",
        headers=student_headers,
        json={
            "code": (
                "import java.io.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) throws Exception {\n"
                "    BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n"
                "    String line = br.readLine();\n"
                "    System.out.println(line == null ? \"\" : line);\n"
                "  }\n"
                "}\n"
            )
        },
    )
    assert_status(submit_response, 200)
    submit_data = submit_response.json()
    assert "submission" in submit_data
    assert "results" in submit_data
    assert submit_data["status"] in {"accepted", "needs_manual_review"}
    assert submit_data["submission"]["assignment_id"] == assignment_id
    assert submit_data["submission"]["question_id"] == question_id
    assert isinstance(submit_data["results"], list)
    assert submit_data["results"], submit_data

    submissions_response = client.get(
        f"/api/assignments/{assignment_id}/submissions",
        headers=student_headers,
    )
    assert_status(submissions_response, 200)
    assert any(
        item["id"] == submit_data["submission"]["id"]
        for item in submissions_response.json()
    )


def test_mixed_assignment_class_publish_and_question_bank(
    client: httpx.Client,
    auto_test_prefix: str,
    teacher_token: str,
) -> None:
    teacher_headers = auth_headers(teacher_token)
    class_name = unique_name(auto_test_prefix, "class")
    usernames = [unique_name(auto_test_prefix, f"class_student_{index}") for index in range(2)]
    password = "AutoTest123"
    with SessionLocal() as db:
        for username in usernames:
            db.add(
                User(
                    username=username,
                    password_hash=get_password_hash(password),
                    role="student",
                    class_name=class_name,
                )
            )
        db.commit()

    assignment_title = unique_name(auto_test_prefix, "mixed_assignment")
    create_response = client.post(
        "/api/teacher/assignments",
        headers=teacher_headers,
        json={
            "title": assignment_title,
            "status": "published",
            "class_names": [class_name],
            "questions": [
                {
                    "title": f"{auto_test_prefix}选择题",
                    "prompt": "JDBC 中提交事务通常调用哪个方法？",
                    "question_type": "multiple_choice",
                    "options": [
                        {"key": "A", "text": "commit"},
                        {"key": "B", "text": "rollback"},
                    ],
                    "answer": "A",
                    "explanation": "commit 用于提交事务。",
                },
                {
                    "title": f"{auto_test_prefix}填空题",
                    "prompt": "释放 JDBC 连接通常应调用 ____ 方法。",
                    "question_type": "fill_blank",
                    "answer": ["close"],
                    "explanation": "close 用于释放连接资源。",
                },
            ],
        },
    )
    assert_status(create_response, 200)
    assignment = create_response.json()
    assert assignment["class_names"] == [class_name]
    assert len(assignment["assigned_students"]) == 2
    assert {question["question_type"] for question in assignment["questions"]} == {"multiple_choice", "fill_blank"}

    bank_response = client.get(
        "/api/teacher/assignments/question-bank",
        headers=teacher_headers,
        params={"keyword": auto_test_prefix},
    )
    assert_status(bank_response, 200)
    bank_items = bank_response.json()
    assert len(bank_items) >= 2
    assert {item["question_type"] for item in bank_items} >= {"multiple_choice", "fill_blank"}

    login_response = client.post("/api/auth/login", json={"username": usernames[0], "password": password})
    assert_status(login_response, 200)
    student_headers = auth_headers(login_response.json()["access_token"])
    question_id = assignment["questions"][0]["id"]
    submit_response = client.post(
        f"/api/assignments/{assignment['id']}/questions/{question_id}/submit",
        headers=student_headers,
        json={"answer": "A"},
    )
    assert_status(submit_response, 200)
    data = submit_response.json()
    assert data["status"] in {"accepted", "needs_manual_review"}
    assert data["decision_source"] == "ai_objective_review"
    assert data["submission"]["answer"] == "A"
