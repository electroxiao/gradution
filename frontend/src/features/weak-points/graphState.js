const NODE_STATUS_COLOR_MAP = {
  weak: "#ef4444",
  mastered: "#22c55e",
  learning: "#f59e0b",
  unknown: "#94a3b8",
};

export function findGraphNodeById(nodes, nodeId) {
  return nodes.find((node) => String(node.id) === String(nodeId));
}

export function applyGraphNodeStatus(nodes, nodeId, status) {
  const node = findGraphNodeById(nodes, nodeId);
  if (!node) return null;

  node.status = status;
  node.color = NODE_STATUS_COLOR_MAP[status] || NODE_STATUS_COLOR_MAP.unknown;
  return node;
}

export function markGraphNodeMastered(nodes, nodeId) {
  return applyGraphNodeStatus(nodes, nodeId, "mastered");
}
