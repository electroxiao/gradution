import http from "./http";

export const listSessionsApi = () => http.get("/api/chat/sessions");
export const createSessionApi = (payload) => http.post("/api/chat/sessions", payload);
export const listMessagesApi = (sessionId) => http.get(`/api/chat/sessions/${sessionId}/messages`);
export const sendMessageApi = (sessionId, payload) =>
  http.post(`/api/chat/sessions/${sessionId}/messages`, payload);
