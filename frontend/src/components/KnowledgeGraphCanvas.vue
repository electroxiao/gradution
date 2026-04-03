<template>
  <div ref="container" class="graph-canvas" @dragstart.prevent></div>
</template>

<script setup>
import { NVL } from "@neo4j-nvl/base";
import { PanInteraction, ZoomInteraction, DragNodeInteraction, ClickInteraction } from "@neo4j-nvl/interaction-handlers";
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
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
let panInteraction = null;
let zoomInteraction = null;
let dragInteraction = null;
let clickInteraction = null;

function getGraphPayload() {
  return toNvlGraph(
    { nodes: props.nodes, edges: props.edges },
    { selectedNodeId: props.selectedNodeId, selectedEdgeId: props.selectedEdgeId }
  );
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

function syncGraph() {
  if (!nvl) return;
  const payload = getGraphPayload();
  const incomingNodeIds = new Set(payload.nodes.map((node) => node.id));
  const incomingRelIds = new Set(payload.relationships.map((rel) => rel.id));

  const staleNodeIds = nvl.getNodes().map((n) => n.id).filter((id) => !incomingNodeIds.has(id));
  const staleRelIds = nvl.getRelationships().map((r) => r.id).filter((id) => !incomingRelIds.has(id));

  if (staleRelIds.length) nvl.removeRelationshipsWithIds(staleRelIds);
  if (staleNodeIds.length) nvl.removeNodesWithIds(staleNodeIds);

  nvl.addAndUpdateElementsInGraph(payload.nodes, payload.relationships);
}

function syncSelection() {
  if (!nvl) return;
  const payload = getGraphPayload();
  nvl.updateElementsInGraph(payload.nodes, payload.relationships);
}

function initializeGraph() {
  if (!container.value) return;

  const payload = getGraphPayload();
  
  nvl = new NVL(
    container.value,
    payload.nodes,
    payload.relationships,
    {
      disableTelemetry: true,
      disableWebWorkers: false,
      renderer: "canvas",
      layout: "d3Force",
      initialZoom: 0.9,
      layoutOptions: { nodeSpacing: 80 },
    }
  );

  zoomInteraction = new ZoomInteraction(nvl);
  panInteraction = new PanInteraction(nvl);
  dragInteraction = new DragNodeInteraction(nvl);
  
  clickInteraction = new ClickInteraction(nvl);
  clickInteraction.updateCallback('onNodeClick', (node) => {
    emit("select-node", node.id);
  });
  clickInteraction.updateCallback('onRelationshipClick', (rel) => {
    emit("select-edge", rel.id);
  });
  clickInteraction.updateCallback('onCanvasClick', () => {
    emit("clear-selection");
  });

  requestAnimationFrame(() => {
    if (props.selectedNodeId) {
      fitGraph([String(props.selectedNodeId)]);
    }
  });
}

function focusNodes(nodeIds = []) {
  fitGraph(nodeIds.map((id) => String(id)));
}

function restartLayout() {
  if (!nvl) return;
  if (props.selectedNodeId) {
    fitGraph([String(props.selectedNodeId)]);
    return;
  }
  nvl.resetZoom();
}

function destroyGraph() {
  if (nvl) {
    nvl.destroy();
    nvl = null;
  }
  panInteraction = null;
  zoomInteraction = null;
  dragInteraction = null;
  clickInteraction = null;
}

watch(() => [props.nodes, props.edges], () => { if (nvl) syncGraph(); }, { deep: true });
watch(() => [props.selectedNodeId, props.selectedEdgeId], () => { if (nvl) syncSelection(); });

onMounted(async () => {
  await nextTick();
  requestAnimationFrame(() => initializeGraph());
});

onBeforeUnmount(() => destroyGraph());

defineExpose({ fitGraph, focusNodes, restartLayout });
</script>

<style scoped>
.graph-canvas {
  width: 100%;
  height: 680px;
  min-height: 680px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  overflow: hidden;
  user-select: none;
  -webkit-user-drag: none;
  touch-action: none;
  overscroll-behavior: none;
}
</style>
