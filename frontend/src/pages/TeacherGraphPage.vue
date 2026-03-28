<template>
  <section class="graph-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Knowledge Graph</p>
        <h2>知识图谱管理</h2>
        <p class="page-copy">使用 Neo4j NVL 查看图谱，顶部工具栏负责搜索与布局，右侧面板负责节点和关系编辑。</p>
      </div>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <div class="toolbar">
      <button @click="startCreateNode">新增节点</button>
      <div class="toolbar-search">
        <input v-model="keyword" placeholder="搜索节点名或描述" @keydown.enter.prevent="searchGraph" />
        <button class="ghost" @click="searchGraph">搜索</button>
      </div>
      <span class="graph-meta">节点 {{ graph.nodes.length }} / 边 {{ graph.edges.length }}</span>
      <button class="ghost" @click="toggleFullscreen">全屏</button>
      <button class="ghost" @click="refreshGraph">刷新布局</button>
    </div>

    <div class="graph-layout">
      <section ref="graphViewport" class="graph-panel">
        <div v-if="isGraphLoading" class="graph-state">图谱加载中...</div>
        <div v-else-if="!graph.nodes.length" class="graph-state">当前没有可展示的知识图谱节点。</div>
        <div v-else-if="graphRenderError" class="graph-state graph-error">
          <div>
            <p>图谱组件加载失败</p>
            <small>{{ graphRenderError }}</small>
          </div>
        </div>
        <KnowledgeGraphCanvas
          v-if="graph.nodes.length > 0 && !isGraphLoading && !graphRenderError"
          ref="graphCanvas"
          :nodes="graph.nodes"
          :edges="graph.edges"
          :selected-node-id="selectedNodeId"
          :selected-edge-id="selectedEdgeId"
          @select-node="handleSelectNode"
          @select-edge="handleSelectEdge"
          @clear-selection="clearSelection"
        />
      </section>

      <aside class="detail-panel">
        <div class="panel-card">
          <div class="panel-head">
            <h3>详细信息</h3>
            <span v-if="selectedNode">节点</span>
            <span v-else-if="selectedEdge">关系</span>
            <span v-else>未选择</span>
          </div>

          <div v-if="selectedNode" class="detail-body">
            <label>
              节点名
              <input v-model="nodeForm.name" placeholder="节点名" />
            </label>
            <label>
              描述
              <textarea v-model="nodeForm.desc" rows="5" placeholder="节点描述"></textarea>
            </label>
            <label>
              类型
              <input v-model="nodeForm.node_type" placeholder="节点类型（可选）" />
            </label>
            <div class="detail-actions">
              <button @click="submitNode">保存节点</button>
              <button class="danger" @click="deleteNode">删除</button>
            </div>
          </div>

          <div v-else-if="selectedEdge" class="detail-body">
            <label>
              起点
              <select v-model="edgeForm.source">
                <option value="">选择起点节点</option>
                <option v-for="node in graph.nodes" :key="`src-${node.id}`" :value="node.name">{{ node.name }}</option>
              </select>
            </label>
            <label>
              关系名
              <input v-model="edgeForm.relation" placeholder="如 DEPENDS_ON" />
            </label>
            <label>
              终点
              <select v-model="edgeForm.target">
                <option value="">选择终点节点</option>
                <option v-for="node in graph.nodes" :key="`tgt-${node.id}`" :value="node.name">{{ node.name }}</option>
              </select>
            </label>
            <div class="detail-actions">
              <button @click="submitEdge">保存关系</button>
              <button class="danger" @click="deleteEdge">删除</button>
            </div>
          </div>

          <div v-else class="empty-detail">
            <p>点击左侧图谱中的节点或关系，就能在这里查看详细信息并继续编辑。</p>
          </div>
        </div>

        <div class="panel-card">
          <div class="panel-head">
            <h3>快捷新增关系</h3>
            <button class="ghost small" @click="startCreateEdge">清空</button>
          </div>
          <div class="detail-body">
            <label>
              起点
              <select v-model="edgeForm.source">
                <option value="">选择起点节点</option>
                <option v-for="node in graph.nodes" :key="`create-src-${node.id}`" :value="node.name">{{ node.name }}</option>
              </select>
            </label>
            <label>
              关系名
              <input v-model="edgeForm.relation" placeholder="如 DEPENDS_ON" />
            </label>
            <label>
              终点
              <select v-model="edgeForm.target">
                <option value="">选择终点节点</option>
                <option v-for="node in graph.nodes" :key="`create-tgt-${node.id}`" :value="node.name">{{ node.name }}</option>
              </select>
            </label>
            <div class="detail-actions">
              <button @click="submitEdge">{{ selectedEdge ? "另存为新关系" : "创建关系" }}</button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onErrorCaptured, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import {
  createTeacherEdgeApi,
  createTeacherNodeApi,
  deleteTeacherEdgeApi,
  deleteTeacherNodeApi,
  getTeacherGraphApi,
  updateTeacherEdgeApi,
  updateTeacherNodeApi,
} from "../api/teacher";
import KnowledgeGraphCanvas from "../components/KnowledgeGraphCanvas.vue";

const router = useRouter();
const keyword = ref("");
const errorMessage = ref("");
const graphRenderError = ref("");
const isGraphLoading = ref(false);
const fullGraph = ref({ nodes: [], edges: [] });
const graph = ref({ nodes: [], edges: [] });
const selectedNodeId = ref("");
const selectedEdgeId = ref("");
const graphViewport = ref(null);
const graphCanvas = ref(null);

const nodeForm = reactive({
  name: "",
  desc: "",
  node_type: "",
});

const edgeForm = reactive({
  source: "",
  relation: "",
  target: "",
});

const selectedNode = computed(() =>
  graph.value.nodes.find((node) => node.id === selectedNodeId.value) || null,
);
const selectedEdge = computed(() =>
  graph.value.edges.find((edge) => edge.id === selectedEdgeId.value) || null,
);

onMounted(async () => {
  await loadGraph();
});

onErrorCaptured((error) => {
  graphRenderError.value = error instanceof Error ? error.message : "图谱组件渲染失败。";
  return false;
});

async function loadGraph() {
  isGraphLoading.value = true;
  errorMessage.value = "";
  graphRenderError.value = "";
  try {
    const { data } = await getTeacherGraphApi({ keyword: "", limit: 1000 });
    fullGraph.value = data;
    applyGraphData(data);
  } catch (error) {
    handleApiError(error, "加载图谱失败。");
  } finally {
    isGraphLoading.value = false;
  }
}

async function refreshGraph() {
  await loadGraph();
  if (keyword.value.trim()) {
    await searchGraph({ useFreshBaseGraph: true });
    return;
  }
  await nextTick();
  graphCanvas.value?.restartLayout?.();
}

async function toggleFullscreen() {
  if (!graphViewport.value) return;
  if (document.fullscreenElement) {
    await document.exitFullscreen();
    return;
  }
  await graphViewport.value.requestFullscreen();
}

function clearSelection() {
  selectedNodeId.value = "";
  selectedEdgeId.value = "";
}

function startCreateNode() {
  clearSelection();
  nodeForm.name = "";
  nodeForm.desc = "";
  nodeForm.node_type = "";
}

function startCreateEdge() {
  selectedEdgeId.value = "";
  edgeForm.source = "";
  edgeForm.relation = "";
  edgeForm.target = "";
}

function handleSelectNode(nodeId) {
  selectedNodeId.value = nodeId;
  selectedEdgeId.value = "";
  const node = graph.value.nodes.find((item) => item.id === nodeId);
  if (!node) return;
  nodeForm.name = node.name;
  nodeForm.desc = node.desc || "";
  nodeForm.node_type = node.node_type || "";
}

function handleSelectEdge(edgeId) {
  selectedEdgeId.value = edgeId;
  selectedNodeId.value = "";
  const edge = graph.value.edges.find((item) => item.id === edgeId);
  if (!edge) return;
  edgeForm.source = edge.source_name || edge.source;
  edgeForm.relation = edge.relation;
  edgeForm.target = edge.target_name || edge.target;
}

async function submitNode() {
  try {
    if (selectedNode.value) {
      await updateTeacherNodeApi(selectedNode.value.name, { ...nodeForm });
    } else {
      await createTeacherNodeApi({ ...nodeForm });
    }
    await refreshGraph();
    startCreateNode();
  } catch (error) {
    handleApiError(error, "保存节点失败。");
  }
}

async function deleteNode() {
  if (!selectedNode.value) return;
  try {
    await deleteTeacherNodeApi(selectedNode.value.name);
    await refreshGraph();
    startCreateNode();
  } catch (error) {
    handleApiError(error, "删除节点失败。");
  }
}

async function submitEdge() {
  try {
    if (selectedEdge.value) {
      await updateTeacherEdgeApi(selectedEdge.value.edge_key, { ...edgeForm });
    } else {
      await createTeacherEdgeApi({ ...edgeForm });
    }
    await refreshGraph();
    startCreateEdge();
  } catch (error) {
    handleApiError(error, "保存关系失败。");
  }
}

async function deleteEdge() {
  if (!selectedEdge.value) return;
  try {
    await deleteTeacherEdgeApi(selectedEdge.value.edge_key);
    await refreshGraph();
    startCreateEdge();
  } catch (error) {
    handleApiError(error, "删除关系失败。");
  }
}

function handleApiError(error, fallbackMessage) {
  const status = error?.response?.status;
  if (status === 401 || status === 403) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_role");
    router.push("/login");
    return;
  }
  errorMessage.value = error?.response?.data?.detail || fallbackMessage;
}

function applyGraphData(data) {
  graph.value = data;
  if (selectedNodeId.value && !data.nodes.some((node) => node.id === selectedNodeId.value)) {
    selectedNodeId.value = "";
  }
  if (selectedEdgeId.value && !data.edges.some((edge) => edge.id === selectedEdgeId.value)) {
    selectedEdgeId.value = "";
  }
}

function findLocalMatches(query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return [];
  return fullGraph.value.nodes.filter((node) => {
    const name = String(node.name || "").toLowerCase();
    const desc = String(node.desc || "").toLowerCase();
    return name.includes(normalized) || desc.includes(normalized);
  });
}

async function focusNodeIds(nodeIds) {
  await nextTick();
  graphCanvas.value?.focusNodes?.(nodeIds);
}

async function searchGraph(options = {}) {
  const query = keyword.value.trim();
  errorMessage.value = "";
  graphRenderError.value = "";
  if (!query) {
    applyGraphData(fullGraph.value);
    clearSelection();
    await focusNodeIds(graph.value.nodes.map((node) => node.id));
    return;
  }

  const localMatches = findLocalMatches(query);
  if (localMatches.length) {
    applyGraphData(fullGraph.value);
    handleSelectNode(localMatches[0].id);
    await focusNodeIds(localMatches.map((node) => node.id));
    return;
  }

  if (!options.useFreshBaseGraph) {
    isGraphLoading.value = true;
  }

  try {
    const { data } = await getTeacherGraphApi({ keyword: query, limit: 1000 });
    applyGraphData(data);
    if (data.nodes.length) {
      handleSelectNode(data.nodes[0].id);
      await focusNodeIds(data.nodes.map((node) => node.id));
    } else {
      clearSelection();
    }
  } catch (error) {
    handleApiError(error, "搜索图谱失败。");
  } finally {
    if (!options.useFreshBaseGraph) {
      isGraphLoading.value = false;
    }
  }
}
</script>

<style scoped>
.graph-page {
  display: grid;
  gap: 20px;
}

.page-header h2 {
  margin: 8px 0 10px;
  font-size: 34px;
  color: #0f2840;
}

.eyebrow {
  margin: 0;
  color: #5b86b3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.page-copy {
  margin: 0;
  color: #6f8297;
  max-width: 760px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px;
  border: 1px solid #e2ebf4;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

.toolbar-search {
  display: flex;
  flex: 1;
  min-width: 260px;
  gap: 10px;
}

.graph-meta {
  color: #6f8297;
  font-size: 13px;
  white-space: nowrap;
}

.toolbar button,
.toolbar input,
.detail-body input,
.detail-body textarea,
.detail-body select,
.detail-actions button {
  font: inherit;
}

.toolbar input,
.detail-body input,
.detail-body textarea,
.detail-body select {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #d8e2ee;
  border-radius: 14px;
  background: #fff;
}

.toolbar button,
.detail-actions button {
  border: none;
  border-radius: 14px;
  padding: 12px 16px;
  background: #10283d;
  color: #fff;
  cursor: pointer;
}

.toolbar .ghost,
.detail-actions .ghost,
.panel-head .ghost {
  background: #edf4ff;
  color: #2d5278;
}

.toolbar .ghost.small {
  padding: 10px 12px;
}

.graph-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
}

.graph-panel,
.detail-panel {
  border: 1px solid #e2ebf4;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
}

.graph-panel {
  position: relative;
  min-height: 680px;
  padding: 10px;
}

.graph-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #6f8297;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.88);
  border-radius: 26px;
  z-index: 2;
}

.graph-error p {
  margin: 0 0 8px;
  font-weight: 700;
  color: #8b1e1e;
}

.graph-error small {
  color: #7c8a99;
}

.detail-panel {
  display: grid;
  gap: 14px;
  align-self: start;
  padding: 16px;
}

.panel-card {
  padding: 18px;
  border-radius: 22px;
  background: #f8fbff;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-head h3 {
  margin: 0;
  color: #10283d;
}

.panel-head span {
  color: #7890a7;
  font-size: 13px;
}

.detail-body {
  display: grid;
  gap: 12px;
}

.detail-body label {
  display: grid;
  gap: 8px;
  color: #526b84;
  font-size: 13px;
}

.detail-body textarea {
  resize: vertical;
}

.detail-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-actions .danger {
  background: #f97316;
}

.empty-detail {
  color: #6f8297;
  line-height: 1.7;
}

.feedback.error {
  padding: 18px;
  border-radius: 18px;
  background: #fff8f8;
  color: #b42318;
}

@media (max-width: 1120px) {
  .graph-layout {
    grid-template-columns: 1fr;
  }
}
</style>
