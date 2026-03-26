import http from "./http";

export const registerApi = (payload) => http.post("/api/auth/register", payload);
export const loginApi = (payload) => http.post("/api/auth/login", payload);
export const meApi = () => http.get("/api/auth/me");
