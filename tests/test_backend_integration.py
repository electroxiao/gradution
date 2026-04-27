import httpx
import pytest

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
