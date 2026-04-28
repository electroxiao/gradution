import http from "./http";

export const getTeacherGraphApi = (params = {}) => http.get("/api/teacher/graph", { params });
export const createTeacherNodeApi = (payload) => http.post("/api/teacher/graph/nodes", payload);
export const generateTeacherNodeDescriptionApi = (payload) =>
  http.post("/api/teacher/graph/nodes/generate-description", payload);
export const updateTeacherNodeApi = (nodeName, payload) =>
  http.patch(`/api/teacher/graph/nodes/${encodeURIComponent(nodeName)}`, payload);
export const batchUpdateTeacherNodeChapterApi = (payload) =>
  http.post("/api/teacher/graph/nodes/batch-chapter", payload);
export const deleteTeacherNodeApi = (nodeName) =>
  http.delete(`/api/teacher/graph/nodes/${encodeURIComponent(nodeName)}`);

export const createTeacherEdgeApi = (payload) => http.post("/api/teacher/graph/edges", payload);
export const updateTeacherEdgeApi = (edgeId, payload) =>
  http.patch(`/api/teacher/graph/edges/${encodeURIComponent(edgeId)}`, payload);
export const deleteTeacherEdgeApi = (edgeId) =>
  http.delete(`/api/teacher/graph/edges/${encodeURIComponent(edgeId)}`);
export const listPendingTeacherBatchesApi = () => http.get("/api/teacher/graph/pending-batches");
export const getPendingTeacherBatchDetailApi = (batchId) =>
  http.get(`/api/teacher/graph/pending-batches/${encodeURIComponent(batchId)}`);
export const approvePendingTeacherBatchApi = (batchId, payload) =>
  http.post(`/api/teacher/graph/pending-batches/${encodeURIComponent(batchId)}/approve`, payload);
export const rejectPendingTeacherBatchApi = (batchId, payload) =>
  http.post(`/api/teacher/graph/pending-batches/${encodeURIComponent(batchId)}/reject`, payload);

export const listTeacherKnowledgeNodesApi = (params = {}) => http.get("/api/teacher/knowledge-nodes", { params });
export const listTeacherStudentsApi = () => http.get("/api/teacher/students");
export const listTeacherStudentWeakPointsApi = (studentId) =>
  http.get(`/api/teacher/students/${studentId}/weak-points`);
export const listTeacherStudentMasteryApi = (studentId) =>
  http.get(`/api/teacher/students/${studentId}/mastery`);

export const getStudentPortraitApi = (studentId) =>
  http.get(`/api/teacher/students/${studentId}/portrait`);
export const getStudentPortraitSummaryApi = (studentId) =>
  http.get(`/api/teacher/students/${studentId}/portrait/summary`);

export const getTeacherDashboardApi = () => http.get("/api/teacher/dashboard/weak-points");
