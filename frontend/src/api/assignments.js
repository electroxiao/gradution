import http from "./http";

export const listTeacherAssignmentsApi = () => http.get("/api/teacher/assignments");
export const createTeacherAssignmentApi = (payload) => http.post("/api/teacher/assignments", payload);
export const getTeacherAssignmentApi = (assignmentId) => http.get(`/api/teacher/assignments/${assignmentId}`);
export const updateTeacherAssignmentApi = (assignmentId, payload) =>
  http.patch(`/api/teacher/assignments/${assignmentId}`, payload);
export const updateTeacherAssignmentQuestionsApi = (assignmentId, payload) =>
  http.put(`/api/teacher/assignments/${assignmentId}/questions`, payload);
export const generateAssignmentQuestionApi = (payload) =>
  http.post("/api/teacher/assignments/generate-question", payload);

export const listStudentAssignmentsApi = () => http.get("/api/assignments");
export const getStudentAssignmentApi = (assignmentId) => http.get(`/api/assignments/${assignmentId}`);
export const listStudentAssignmentSubmissionsApi = (assignmentId) =>
  http.get(`/api/assignments/${assignmentId}/submissions`);
export const submitAssignmentQuestionApi = (assignmentId, questionId, payload) =>
  http.post(`/api/assignments/${assignmentId}/questions/${questionId}/submit`, payload);
export const askAssignmentAiHelpApi = (assignmentId, questionId, payload) =>
  http.post(`/api/assignments/${assignmentId}/questions/${questionId}/ai-help`, payload);
