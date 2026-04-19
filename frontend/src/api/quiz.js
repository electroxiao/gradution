import http, { API_BASE_URL } from "./http";
import { getAccessToken } from "../utils/authStorage";

export const generateQuizApi = (nodeId) =>
  http.post(`/api/quiz/generate`, { node_id: nodeId });

export const submitQuizAnswerApi = (nodeId, payload) =>
  http.post(`/api/quiz/submit`, {
    node_id: nodeId,
    answer: payload.answer,
    question: payload.question,
  });

export async function streamGenerateQuizApi(nodeId, onChunk) {
  const token = getAccessToken();
  const response = await fetch(`${API_BASE_URL}/api/quiz/generate/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ node_id: nodeId }),
  });

  if (!response.ok || !response.body) {
    throw new Error("生成题目失败");
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

      if (rawEvent.includes("[DONE]")) continue;

      const dataMatch = rawEvent.match(/data: (.+)/);
      if (dataMatch) {
        try {
          const data = JSON.parse(dataMatch[1]);
          if (data.content) {
            onChunk(data.content);
          }
        } catch {
          // ignore parse error
        }
      }
    }
  }
}

export async function streamSubmitAnswerApi(nodeId, question, answer, handlers = {}) {
  const token = getAccessToken();
  const response = await fetch(`${API_BASE_URL}/api/quiz/submit/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ node_id: nodeId, question, answer }),
  });

  if (!response.ok || !response.body) {
    throw new Error("提交答案失败");
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

      const eventMatch = rawEvent.match(/event: (\w+)/);
      const dataMatch = rawEvent.match(/data: (.+)/);

      if (!dataMatch) continue;

      const eventType = eventMatch ? eventMatch[1] : "message";

      try {
        const data = JSON.parse(dataMatch[1]);

        if (eventType === "feedback_delta") {
          handlers.onFeedbackDelta?.(data.content);
        } else if (eventType === "result") {
          handlers.onResult?.(data);
        } else if (eventType === "done") {
          handlers.onDone?.();
        }
      } catch {
        // ignore parse error
      }
    }
  }
}
