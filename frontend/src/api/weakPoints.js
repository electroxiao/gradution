import http from "./http";

export const listWeakPointsApi = () => http.get("/api/weak-points");
export const markMasteredApi = (nodeId) => http.post(`/api/weak-points/${nodeId}/mastered`);
export const getWeakPointsGraphApi = () => http.get("/api/weak-points/graph");
