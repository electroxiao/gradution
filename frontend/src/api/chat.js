import http from "./http";
import { getAccessToken } from "../utils/authStorage";

export const listSessionsApi = () => http.get("/api/chat/sessions");
export const createSessionApi = (payload) => http.post("/api/chat/sessions", payload);
export const renameSessionApi = (sessionId, payload) => http.patch(`/api/chat/sessions/${sessionId}`, payload);
export const deleteSessionApi = (sessionId) => http.delete(`/api/chat/sessions/${sessionId}`);
export const listMessagesApi = (sessionId) => http.get(`/api/chat/sessions/${sessionId}/messages`);
export const sendMessageApi = (sessionId, payload) =>
  http.post(`/api/chat/sessions/${sessionId}/messages`, payload);

export async function streamMessageApi(sessionId, payload, handlers = {}) {
  const token = getAccessToken();
  const response = await fetch(`http://127.0.0.1:8000/api/chat/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    let detail = "流式请求失败";
    try {
      const data = await response.json();
      detail = data?.detail || detail;
    } catch {
      // ignore response parse failure
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
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    while (buffer.includes("\n\n")) {
      const boundary = buffer.indexOf("\n\n");
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const parsed = parseSseEvent(rawEvent);
      if (!parsed) continue;

      if (parsed.event === "user_message") {
        handlers.onUserMessage?.(parsed.data);
      } else if (parsed.event === "assistant_delta") {
        handlers.onAssistantDelta?.(parsed.data);
      } else if (parsed.event === "assistant_done") {
        handlers.onAssistantDone?.(parsed.data);
      } else if (parsed.event === "pending_notice") {
        handlers.onPendingNotice?.(parsed.data);
      } else if (parsed.event === "error") {
        handlers.onError?.(parsed.data);
      }
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
