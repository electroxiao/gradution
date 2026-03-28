<template>
  <div ref="container" class="graph-canvas" @dragstart.prevent></div>
</template>

<script setup>
import { NVL } from "@neo4j-nvl/base";
// 引入官方四大交互引擎
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

// 🚀 修复 2：必须将引擎声明为全局变量！
// 绝对不能让它们在函数执行完后被垃圾回收机制(GC)销毁！
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
  
  // ⛔️ 修复 3：删除了这里的 fitGraph()！
  // 之前你一缩放，Vue 的数据监听就触发这里强制把镜头拉回原点，导致了“无法缩放”的假象！
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
      renderer: "webgl",
      layout: "d3Force",
      initialZoom: 0.9,
      layoutOptions: { nodeSpacing: 80 }
    }
  );

  // 🚀 修复 4：把引擎实例存入全局变量，给它们“保活”
  zoomInteraction = new ZoomInteraction(nvl);
  panInteraction = new PanInteraction(nvl);
  dragInteraction = new DragNodeInteraction(nvl);
  
  // 🚀 修复 5：使用官方的点击引擎，完美解决拖拽和点击的冲突
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

  // 初次加载时居中一次即可
  requestAnimationFrame(() => {
    fitGraph(props.selectedNodeId ? [String(props.selectedNodeId)] : []);
  });
}

function focusNodes(nodeIds = []) {
  fitGraph(nodeIds.map((id) => String(id)));
}

function restartLayout() {
  if (!nvl) return;
  fitGraph(props.selectedNodeId ? [String(props.selectedNodeId)] : []);
}

function destroyGraph() {
  if (nvl) {
    nvl.destroy();
    nvl = null;
  }
  // 释放内存
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
  
  /* 🚀 修复 6：CSS 终极护盾，阻断所有系统级干扰 */
  user-select: none;           /* 禁止文本选中 */
  -webkit-user-drag: none;     /* 禁止触发原生拖拽（红色禁止图标的终极元凶） */
  touch-action: none;          /* 彻底将触控和滚轮交给底层的 Zoom 引擎处理 */
  overscroll-behavior: none;   /* 阻断浏览器回弹和页面上下乱滚 */
}
</style>