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
      <div class="toolbar-search">
        <input 
          v-model="keyword" 
          placeholder="搜索节点名或描述" 
          @input="handleSearchInput"
          @focus="handleSearchInput"
          @blur="hideSearchDropdown"
          @keydown.enter.prevent="searchGraph" 
        />
        <button class="ghost" @click="searchGraph">搜索</button>

        <ul v-if="showSearchResults" class="search-dropdown">
          <li v-for="res in searchResults" :key="res.id" @mousedown.prevent="selectSearchResult(res)">
            <strong>{{ res.name }}</strong>
            <span v-if="res.desc" class="desc-preview">{{ res.desc }}</span>
          </li>
        </ul>
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
        <div class="panel-card action-bar">
          <button @click="startCreateNode">➕ 新增节点</button>
          <button @click="startCreateEdge">➕ 新增关系</button>
        </div>

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
              <input v-model="nodeForm.name" placeholder="节点名" disabled title="节点名作为唯一标识不可修改" />
            </label>
            <label>
              描述
              <textarea v-model="nodeForm.desc" rows="5" placeholder="节点描述"></textarea>
            </label>
            <div class="detail-actions">
              <button @click="submitNode">保存修改</button>
              <button class="danger" @click="deleteNode">删除</button>
            </div>
          </div>

          <div v-else-if="selectedEdge" class="detail-body">
            <label>
              起点
              <input list="node-list" v-model="edgeForm.source" placeholder="搜索或选择起点" />
            </label>
            <label>
              终点
              <input list="node-list" v-model="edgeForm.target" placeholder="搜索或选择终点" />
            </label>
            <div class="detail-actions">
              <button @click="submitEdge">保存修改</button>
              <button class="danger" @click="deleteEdge">删除</button>
            </div>
          </div>

          <div v-else class="empty-detail">
            <p>点击左侧图谱中的节点或关系，就能在这里查看详细信息并继续编辑。</p>
          </div>
        </div>
      </aside>
    </div>

    <div v-if="isCreatingNode" class="modal-overlay" @click.self="cancelCreateNode">
      <div class="modal-card">
        <h3>新增节点</h3>
        <div class="detail-body">
          <label>
            节点名 <span class="required">*</span>
            <input v-model="nodeForm.name" placeholder="请输入唯一的节点名" />
          </label>
          <label>
            描述
            <textarea v-model="nodeForm.desc" rows="4" placeholder="节点描述"></textarea>
          </label>
          <div class="detail-actions modal-actions">
            <button class="ghost" @click="cancelCreateNode">取消</button>
            <button @click="submitNode">确认创建</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isCreatingEdge" class="modal-overlay" @click.self="cancelCreateEdge">
      <div class="modal-card">
        <h3>新增关系</h3>
        <div class="detail-body">
          <label>
            起点 <span class="required">*</span>
            <input list="node-list" v-model="edgeForm.source" placeholder="搜索或选择起点" />
          </label>
          <label>
            终点 <span class="required">*</span>
            <input list="node-list" v-model="edgeForm.target" placeholder="搜索或选择终点" />
          </label>
          <div class="detail-actions modal-actions">
            <button class="ghost" @click="cancelCreateEdge">取消</button>
            <button @click="submitEdge">确认创建</button>
          </div>
        </div>
      </div>
    </div>

    <datalist id="node-list">
      <option v-for="node in graph.nodes" :key="node.id" :value="node.name"></option>
    </datalist>

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

// 控制弹窗的显示状态
const isCreatingNode = ref(false);
const isCreatingEdge = ref(false);

// 搜索下拉相关状态
const showSearchResults = ref(false);
const searchResults = ref([]);

const graphViewport = ref(null);
const graphCanvas = ref(null);

const nodeForm = reactive({
  name: "",
  desc: "",
});

const edgeForm = reactive({
  source: "",
  relation: "DEPENDS_ON", // 🚀 优化 3：默认为 DEPENDS_ON 且不暴露给用户修改
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
    // 修复了隐藏的 bug，将 limit 统一改为 2000
    const { data } = await getTeacherGraphApi({ keyword: "", limit: 2000 });
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
  isCreatingNode.value = true;
  nodeForm.name = "";
  nodeForm.desc = "";
}

function cancelCreateNode() {
  isCreatingNode.value = false;
  if (selectedNodeId.value) handleSelectNode(selectedNodeId.value);
}

function startCreateEdge() {
  isCreatingEdge.value = true;
  edgeForm.source = selectedNode.value ? selectedNode.value.name : "";
  edgeForm.relation = "DEPENDS_ON"; // 永远固定为 DEPENDS_ON
  edgeForm.target = "";
}

function cancelCreateEdge() {
  isCreatingEdge.value = false;
  if (selectedEdgeId.value) handleSelectEdge(selectedEdgeId.value);
}

function handleSelectNode(nodeId) {
  selectedNodeId.value = nodeId;
  selectedEdgeId.value = "";
  const node = graph.value.nodes.find((item) => item.id === nodeId);
  if (!node) return;
  nodeForm.name = node.name;
  nodeForm.desc = node.desc || "";
}

function handleSelectEdge(edgeId) {
  selectedEdgeId.value = edgeId;
  selectedNodeId.value = "";
  const edge = graph.value.edges.find((item) => item.id === edgeId);
  if (!edge) return;
  edgeForm.source = edge.source_name || edge.source;
  edgeForm.relation = edge.relation || "DEPENDS_ON";
  edgeForm.target = edge.target_name || edge.target;
}

async function submitNode() {
  if (!nodeForm.name.trim()) {
    errorMessage.value = "节点名不能为空";
    return;
  }
  try {
    if (isCreatingNode.value) {
      await createTeacherNodeApi({ ...nodeForm });
      isCreatingNode.value = false;
    } else if (selectedNode.value) {
      await updateTeacherNodeApi(selectedNode.value.name, { ...nodeForm });
    }
    await refreshGraph();
    errorMessage.value = "";
  } catch (error) {
    handleApiError(error, "保存节点失败。");
  }
}

async function submitEdge() {
  if (!edgeForm.source || !edgeForm.target) {
    errorMessage.value = "请填写起点和终点信息";
    return;
  }
  // 提交前再次确认关系名称
  edgeForm.relation = "DEPENDS_ON";
  
  try {
    if (isCreatingEdge.value) {
      await createTeacherEdgeApi({ ...edgeForm });
      isCreatingEdge.value = false;
    } else if (selectedEdge.value) {
      await updateTeacherEdgeApi(selectedEdge.value.edge_key, { ...edgeForm });
    }
    await refreshGraph();
    errorMessage.value = "";
  } catch (error) {
    handleApiError(error, "保存关系失败。");
  }
}

function asyncDeleteAction(actionFn) {
    return async () => {
        try {
            await actionFn();
            await refreshGraph();
            clearSelection();
        } catch (error) {
            handleApiError(error, "删除失败。");
        }
    }
}

async function deleteNode() {
  if (!selectedNode.value) return;
  if(!confirm(`确定要删除节点 "${selectedNode.value.name}" 吗？这可能也会删除关联的边。`)) return;
  await asyncDeleteAction(() => deleteTeacherNodeApi(selectedNode.value.name))();
}

async function deleteEdge() {
  if (!selectedEdge.value) return;
  if(!confirm("确定要删除这条关系吗？")) return;
  await asyncDeleteAction(() => deleteTeacherEdgeApi(selectedEdge.value.edge_key))();
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

// 🚀 搜索与下拉框逻辑
function handleSearchInput() {
  const query = keyword.value.trim();
  if (!query) {
    showSearchResults.value = false;
    searchResults.value = [];
    return;
  }
  searchResults.value = findLocalMatches(query);
  showSearchResults.value = searchResults.value.length > 0;
}

function hideSearchDropdown() {
  // 延迟关闭，以确保点击事件能触发
  setTimeout(() => { showSearchResults.value = false; }, 150);
}

async function selectSearchResult(node) {
  keyword.value = node.name; // 将输入框内容替换为选中的节点名
  showSearchResults.value = false;
  handleSelectNode(node.id);
  await focusNodeIds([node.id]);
}

async function focusNodeIds(nodeIds) {
  await nextTick();
  graphCanvas.value?.focusNodes?.(nodeIds);
}

async function searchGraph(options = {}) {
  showSearchResults.value = false;
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

  if (!options.useFreshBaseGraph) isGraphLoading.value = true;

  try {
    const { data } = await getTeacherGraphApi({ keyword: query, limit: 2000 });
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
    if (!options.useFreshBaseGraph) isGraphLoading.value = false;
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

/* 🚀 搜索框布局调整 */
.toolbar-search {
  display: flex;
  flex: 1;
  min-width: 260px;
  gap: 10px;
  position: relative; /* 为绝对定位的下拉框做基准 */
}

/* 🚀 新增下拉菜单样式 */
.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 80px; /* 避开右侧的搜索按钮 */
  margin-top: 8px;
  background: #ffffff;
  border: 1px solid #e2ebf4;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(15, 40, 64, 0.15);
  list-style: none;
  padding: 8px 0;
  max-height: 280px;
  overflow-y: auto;
  z-index: 1000;
}

.search-dropdown li {
  padding: 10px 16px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-bottom: 1px solid #f0f5fa;
}

.search-dropdown li:last-child {
  border-bottom: none;
}

.search-dropdown li:hover {
  background: #f8fbff;
}

.search-dropdown li strong {
  color: #10283d;
  font-size: 14px;
}

.desc-preview {
  color: #6f8297;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
.detail-actions button,
.action-bar button {
  font: inherit;
}

.toolbar input,
.detail-body input,
.detail-body textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #d8e2ee;
  border-radius: 14px;
  background: #fff;
}

.toolbar button,
.detail-actions button,
.action-bar button {
  border: none;
  border-radius: 14px;
  padding: 12px 16px;
  background: #10283d;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toolbar button:hover,
.detail-actions button:hover,
.action-bar button:hover {
  background: #1c3d5a;
}

.toolbar .ghost,
.detail-actions .ghost,
.panel-head .ghost {
  background: #edf4ff;
  color: #2d5278;
}

.toolbar .ghost:hover,
.detail-actions .ghost:hover {
  background: #d8e6fa;
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

.action-bar {
  display: flex;
  gap: 12px;
  padding: 14px;
  background: #fff;
  border: 1px solid #e2ebf4;
}
.action-bar button {
  flex: 1;
  background: #2563eb;
  font-weight: 500;
}
.action-bar button:hover {
  background: #1d4ed8;
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
  gap: 14px;
}

.detail-body label {
  display: grid;
  gap: 8px;
  color: #526b84;
  font-size: 13px;
  font-weight: 500;
}

.required {
  color: #e11d48;
}

.detail-body textarea {
  resize: vertical;
}

.detail-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.detail-actions .danger {
  background: #f97316;
}

.detail-actions .danger:hover {
  background: #ea580c;
}

.empty-detail {
  color: #6f8297;
  line-height: 1.7;
  font-size: 14px;
  text-align: center;
  padding: 20px 0;
}

.feedback.error {
  padding: 18px;
  border-radius: 18px;
  background: #fff8f8;
  color: #b42318;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

.modal-card {
  width: 100%;
  max-width: 420px;
  background: #ffffff;
  padding: 28px;
  border-radius: 24px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.12);
  transform: translateY(-5vh);
}

.modal-card h3 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: #0f2840;
}

.modal-actions {
  justify-content: flex-end;
  margin-top: 12px;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@media (max-width: 1120px) {
  .graph-layout {
    grid-template-columns: 1fr;
  }
}
</style>