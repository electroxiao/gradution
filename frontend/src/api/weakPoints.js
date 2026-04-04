import http from "./http";

export const listWeakPointsApi = () => http.get("/api/weak-points");
export const listWeakPointHistoryApi = () => http.get("/api/weak-points/history");
export const markMasteredApi = (nodeId) => http.post(`/api/weak-points/${nodeId}/mastered`);
export const getWeakPointsGraphApi = (nodeId) =>
  http.get("/api/weak-points/graph", {
    params: nodeId ? { node_id: nodeId } : {},
  });
