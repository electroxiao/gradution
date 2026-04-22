import http, { API_BASE_URL } from "./http";
import { getAccessToken } from "../utils/authStorage";

export const listTeacherAssignmentsApi = () => http.get("/api/teacher/assignments");
export const createTeacherAssignmentApi = (payload) => http.post("/api/teacher/assignments", payload);
export const getTeacherAssignmentApi = (assignmentId) => http.get(`/api/teacher/assignments/${assignmentId}`);
export const getTeacherAssignmentProgressApi = (assignmentId) =>
  http.get(`/api/teacher/assignments/${assignmentId}/progress`);
export const getTeacherAssignmentSubmissionApi = (assignmentId, submissionId) =>
  http.get(`/api/teacher/assignments/${assignmentId}/submissions/${submissionId}`);
export const reviewTeacherAssignmentSubmissionApi = (assignmentId, submissionId, payload) =>
  http.post(`/api/teacher/assignments/${assignmentId}/submissions/${submissionId}/review`, payload);
export const updateTeacherAssignmentApi = (assignmentId, payload) =>
  http.patch(`/api/teacher/assignments/${assignmentId}`, payload);
export const updateTeacherAssignmentQuestionsApi = (assignmentId, payload) =>
  http.put(`/api/teacher/assignments/${assignmentId}/questions`, payload);
export const generateAssignmentQuestionApi = (payload) =>
  http.post("/api/teacher/assignments/generate-question", payload);
export const generateAssignmentTestCasesApi = (payload) =>
  http.post("/api/teacher/assignments/generate-testcases", payload);
export const generateAssignmentFocusApi = (payload) =>
  http.post("/api/teacher/assignments/generate-focus", payload);

export const listStudentAssignmentsApi = () => http.get("/api/assignments");
export const getStudentAssignmentApi = (assignmentId) => http.get(`/api/assignments/${assignmentId}`);
export const listStudentAssignmentSubmissionsApi = (assignmentId) =>
  http.get(`/api/assignments/${assignmentId}/submissions`);
export const submitAssignmentQuestionApi = (assignmentId, questionId, payload) =>
  http.post(`/api/assignments/${assignmentId}/questions/${questionId}/submit`, payload);
export const askAssignmentAiHelpApi = (assignmentId, questionId, payload) =>
  http.post(`/api/assignments/${assignmentId}/questions/${questionId}/ai-help`, payload);

export async function streamAssignmentAiHelpApi(assignmentId, questionId, payload, handlers = {}) {
  const token = getAccessToken();
  const response = await fetch(
    `${API_BASE_URL}/api/assignments/${assignmentId}/questions/${questionId}/ai-help/stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    },
  );

  if (!response.ok || !response.body) {
    let detail = "AI 流式请求失败";
    try {
      const data = await response.json();
      detail = data?.detail || detail;
    } catch {
      // ignore parse failure
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    while (buffer.includes("\n\n")) {
      const boundary = buffer.indexOf("\n\n");
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const parsed = parseSseEvent(rawEvent);
      if (!parsed) continue;

      if (parsed.event === "metadata") handlers.onMetadata?.(parsed.data);
      if (parsed.event === "answer_delta") handlers.onAnswerDelta?.(parsed.data);
      if (parsed.event === "answer_done") handlers.onAnswerDone?.(parsed.data);
      if (parsed.event === "error") handlers.onError?.(parsed.data);
    }
  }
}

function parseSseEvent(rawEvent) {
  const lines = rawEvent.split("\n");
  let event = "message";
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!dataLines.length) return null;
  return {
    event,
    data: JSON.parse(dataLines.join("\n")),
  };
}
