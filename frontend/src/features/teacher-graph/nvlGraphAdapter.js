const TYPE_COLOR_MAP = {
  syntax: "#6aa9ff",
  collection: "#49a57d",
  exception: "#f29a4a",
  oop: "#7c74f5",
  io: "#3ba7b8",
  thread: "#d56ca4",
};

const STATUS_COLOR_MAP = {
  weak: "#ef4444",
  mastered: "#22c55e",
  learning: "#f59e0b",
};

function createNodeHtml(label, isSelected) {
  if (typeof document === "undefined") {
    return undefined;
  }

  const element = document.createElement("div");
  element.textContent = label;
  element.style.pointerEvents = "none";
  element.style.userSelect = "none";
  element.style.whiteSpace = "nowrap";
  element.style.display = "inline-block";
  element.style.fontSize = isSelected ? "14px" : "12px";
  element.style.fontWeight = isSelected ? "700" : "600";
  element.style.lineHeight = "1.2";
  element.style.color = "#10283d";
  element.style.textAlign = "center";
  element.style.textShadow = "0 1px 2px rgba(255, 255, 255, 0.9)";
  element.style.transform = "translate(-50%, 16px)";

  return element;
}

function normalizeType(rawType) {
  return String(rawType || "").trim().toLowerCase();
}

function resolveNodeColor(nodeType, isSelected, status) {
  if (isSelected) {
    return "#2b76f0";
  }

  if (status && STATUS_COLOR_MAP[status]) {
    return STATUS_COLOR_MAP[status];
  }

  if (nodeType && nodeType.startsWith("#")) {
    return nodeType;
  }

  const normalized = normalizeType(nodeType);
  if (!normalized) {
    return "#d8e7ff";
  }

  if (TYPE_COLOR_MAP[normalized]) {
    return TYPE_COLOR_MAP[normalized];
  }
  if (normalized.includes("collection")) {
    return TYPE_COLOR_MAP.collection;
  }
  if (normalized.includes("exception")) {
    return TYPE_COLOR_MAP.exception;
  }
  if (normalized.includes("thread")) {
    return TYPE_COLOR_MAP.thread;
  }
  if (normalized.includes("syntax")) {
    return TYPE_COLOR_MAP.syntax;
  }
  if (normalized.includes("oop")) {
    return TYPE_COLOR_MAP.oop;
  }
  if (normalized.includes("io")) {
    return TYPE_COLOR_MAP.io;
  }

  return "#d8e7ff";
}

export function toNvlNodes(nodes, selectedNodeId = "") {
  return nodes.map((node) => {
    const isSelected = String(node.id) === String(selectedNodeId);
    const label = node.label || node.name || String(node.id);

    return {
      id: String(node.id),
      size: isSelected ? 45 : 28,
      color: resolveNodeColor(node.color || node.node_type, isSelected, node.status),
      selected: isSelected,
      html: createNodeHtml(label, isSelected),
    };
  });
}

export function toNvlRelationships(edges, selectedEdgeId = "") {
  return edges.map((edge) => {
    const isSelected = String(edge.id) === String(selectedEdgeId);

    return {
      id: String(edge.id),
      from: String(edge.source),
      to: String(edge.target),
      type: "",
      selected: isSelected,
      color: isSelected ? "#2b76f0" : "#8eabc8",
      width: isSelected ? 3 : 2,
    };
  });
}

export function toNvlGraph(graph, selection = {}) {
  return {
    nodes: toNvlNodes(graph.nodes || [], selection.selectedNodeId || ""),
    relationships: toNvlRelationships(graph.edges || [], selection.selectedEdgeId || ""),
  };
}
