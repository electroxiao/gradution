<template>
  <div ref="container" class="graph-canvas"></div>
</template>

<script setup>
import { NVL } from "@neo4j-nvl/base";
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { buildTeacherGraphLayout } from "../features/teacher-graph/graphLayout";
import { toNvlGraph } from "../features/teacher-graph/nvlGraphAdapter";

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  selectedNodeId: { type: String, default: "" },
  selectedEdgeId: { type: String, default: "" },
});

const emit = defineEmits(["select-node", "select-edge", "clear-selection"]);

const container = ref(null);
let nvl = null;
let resizeObserver = null;
let clickHandler = null;

function getViewportSize() {
  const rect = container.value?.getBoundingClientRect();
  return {
    width: rect?.width || 1120,
    height: rect?.height || 680,
  };
}

function getGraphPayload() {
  return toNvlGraph(
    {
      nodes: props.nodes,
      edges: props.edges,
    },
    {
      selectedNodeId: props.selectedNodeId,
      selectedEdgeId: props.selectedEdgeId,
    },
  );
}

function bindCanvasEvents() {
  if (!container.value || !nvl) return;

  clickHandler = (event) => {
    const hits = nvl.getHits(event);
    const hitNode = hits?.nvlTargets?.nodes?.[0];
    const hitRelationship = hits?.nvlTargets?.relationships?.[0];

    if (hitNode?.data?.id) {
      emit("select-node", hitNode.data.id);
      return;
    }
    if (hitRelationship?.data?.id) {
      emit("select-edge", hitRelationship.data.id);
      return;
    }
    emit("clear-selection");
  };

  container.value.addEventListener("click", clickHandler);
}

function unbindCanvasEvents() {
  if (container.value && clickHandler) {
    container.value.removeEventListener("click", clickHandler);
  }
  clickHandler = null;
}

function fitGraph(nodeIds = []) {
  if (!nvl) return;
  const ids = nodeIds.length ? nodeIds : props.nodes.map((node) => String(node.id));
  if (!ids.length) {
    nvl.resetZoom();
    return;
  }
  nvl.fit(ids);
}

function applyLayout(nodeIdsToFit = []) {
  if (!nvl) return;
  const positions = buildTeacherGraphLayout(props.nodes, props.edges, getViewportSize());
  nvl.setNodePositions(positions, false);
  requestAnimationFrame(() => {
    fitGraph(nodeIdsToFit);
  });
}

function syncGraph() {
  if (!nvl) return;

  const payload = getGraphPayload();
  const incomingNodeIds = new Set(payload.nodes.map((node) => node.id));
  const incomingRelationshipIds = new Set(payload.relationships.map((relationship) => relationship.id));

  const staleNodeIds = nvl
    .getNodes()
    .map((node) => node.id)
    .filter((id) => !incomingNodeIds.has(id));
  const staleRelationshipIds = nvl
    .getRelationships()
    .map((relationship) => relationship.id)
    .filter((id) => !incomingRelationshipIds.has(id));

  if (staleRelationshipIds.length) {
    nvl.removeRelationshipsWithIds(staleRelationshipIds);
  }
  if (staleNodeIds.length) {
    nvl.removeNodesWithIds(staleNodeIds);
  }

  nvl.addAndUpdateElementsInGraph(payload.nodes, payload.relationships);
  applyLayout(props.selectedNodeId ? [String(props.selectedNodeId)] : []);
}

function syncSelection() {
  if (!nvl) return;

  const payload = getGraphPayload();
  nvl.updateElementsInGraph(payload.nodes, payload.relationships);

  if (props.selectedNodeId) {
    requestAnimationFrame(() => {
      fitGraph([String(props.selectedNodeId)]);
    });
  }
}

function initializeGraph() {
  if (!container.value) return;

  destroyGraph();

  const payload = getGraphPayload();
  nvl = new NVL(
    container.value,
    payload.nodes,
    payload.relationships,
    {
      disableTelemetry: true,
      disableWebWorkers: true,
      renderer: "canvas",
      layout: "free",
      initialZoom: 0.9,
    },
    {
      onLayoutDone: () => {
        fitGraph(props.selectedNodeId ? [String(props.selectedNodeId)] : []);
      },
    },
  );

  nvl.setRenderer("canvas");
  nvl.setLayout("free");
  applyLayout(props.selectedNodeId ? [String(props.selectedNodeId)] : []);
  bindCanvasEvents();

  resizeObserver = new ResizeObserver(() => {
    applyLayout(props.selectedNodeId ? [String(props.selectedNodeId)] : []);
  });
  resizeObserver.observe(container.value);
}

function focusNodes(nodeIds = []) {
  fitGraph(nodeIds.map((id) => String(id)));
}

function restartLayout() {
  applyLayout(props.selectedNodeId ? [String(props.selectedNodeId)] : []);
}

function destroyGraph() {
  unbindCanvasEvents();
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  if (nvl) {
    nvl.destroy();
    nvl = null;
  }
}

watch(
  () => [props.nodes, props.edges],
  () => {
    if (!nvl) return;
    syncGraph();
  },
  { deep: true },
);

watch(
  () => [props.selectedNodeId, props.selectedEdgeId],
  () => {
    if (!nvl) return;
    syncSelection();
  },
);

onMounted(async () => {
  await nextTick();
  requestAnimationFrame(() => {
    initializeGraph();
  });
});

onBeforeUnmount(() => {
  destroyGraph();
});

defineExpose({
  fitGraph,
  focusNodes,
  restartLayout,
});
</script>

<style scoped>
.graph-canvas {
  width: 100%;
  height: 680px;
  min-height: 680px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  overflow: hidden;
}
</style>
