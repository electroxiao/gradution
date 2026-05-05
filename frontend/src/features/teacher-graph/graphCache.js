import { getTeacherGraphApi } from "../../api/teacher";

export const FULL_GRAPH_LIMIT = 2000;

const GRAPH_CACHE_TTL_MS = 5 * 60 * 1000;

let cachedFullGraph = null;
let cachedFullGraphAt = 0;
let fullGraphRequest = null;

export function getCachedFullGraph() {
  if (!cachedFullGraph) return null;
  return Date.now() - cachedFullGraphAt <= GRAPH_CACHE_TTL_MS ? cachedFullGraph : null;
}

export async function fetchFullGraph({ force = false } = {}) {
  if (!force) {
    const cachedGraph = getCachedFullGraph();
    if (cachedGraph) return cachedGraph;
  }
  if (!force && fullGraphRequest) return fullGraphRequest;

  fullGraphRequest = getTeacherGraphApi({ keyword: "", limit: FULL_GRAPH_LIMIT })
    .then(({ data }) => {
      cachedFullGraph = data;
      cachedFullGraphAt = Date.now();
      return data;
    })
    .finally(() => {
      fullGraphRequest = null;
    });

  return fullGraphRequest;
}

export function getStaleFullGraph() {
  return cachedFullGraph;
}
