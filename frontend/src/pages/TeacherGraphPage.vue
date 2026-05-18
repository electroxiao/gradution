<template>
  <section v-if="!isInitialGraphLoading" class="graph-page content-ready">
    <PageHeader title="知识图谱管理" title-tag="h2" />

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <div class="toolbar">
      <div class="toolbar-search">
        <input
          v-model="keyword"
          class="toolbar-input"
          placeholder="搜索结点名或描述"
          @input="handleGraphKeywordInput"
          @focus="handleGraphKeywordInput"
          @keydown.enter.prevent="searchGraph()"
        />
        <div v-if="showGraphSuggestions && graphSuggestions.length" class="search-dropdown">
          <button
            v-for="node in graphSuggestions"
            :key="node.id"
            type="button"
            class="search-dropdown-item"
            @mousedown.prevent="selectGraphSuggestion(node)"
          >
            <strong>{{ node.name }}</strong>
            <small v-if="node.desc">{{ node.desc }}</small>
          </button>
        </div>
      </div>
      <Listbox v-model="selectedGraphChapter" as="div" class="animated-select toolbar-select" @update:model-value="searchGraph">
        <div class="animated-select-wrap">
          <ListboxButton class="animated-select-button">
            <span>{{ selectedGraphChapter || "全部章节" }}</span>
            <ChevronDown :size="16" aria-hidden="true" />
          </ListboxButton>
          <Transition name="select-pop">
            <ListboxOptions class="animated-select-options">
              <ListboxOption v-slot="{ active, selected }" as="template" value="">
                <li :class="['animated-select-option', { active, selected }]">全部章节</li>
              </ListboxOption>
              <ListboxOption v-for="chapter in graphChapterOptions" v-slot="{ active, selected }" :key="chapter" as="template" :value="chapter">
                <li :class="['animated-select-option', { active, selected }]">{{ chapter }}</li>
              </ListboxOption>
            </ListboxOptions>
          </Transition>
        </div>
      </Listbox>
      <span class="graph-meta">结点 {{ graph.nodes.length }} / 边 {{ graph.edges.length }}</span>
      <button class="ghost" @click="searchGraph">搜索</button>
      <button class="ghost" @click="toggleFullscreen">全屏</button>
      <button class="ghost" @click="refreshGraph">刷新布局</button>
    </div>

    <div class="graph-mode-layout">
      <section ref="graphViewport" class="graph-panel formal-panel">
        <div class="graph-panel-head">
          <div>
            <h3>知识图谱</h3>
          </div>
        </div>

        <div v-if="hasGraphLoaded && !isGraphLoading && !graph.nodes.length" class="graph-state">当前没有可展示的知识图谱结点。</div>

        <KnowledgeGraphCanvas
          v-if="graph.nodes.length && !isGraphLoading"
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

      <aside class="graph-side-panel">
        <div class="panel-card action-card">
          <div class="panel-head">
            <h3>基础操作</h3>
            <span>图谱</span>
          </div>
          <div class="action-bar">
            <button @click="startCreateNode">新增结点</button>
            <button @click="startCreateEdge">新增关系</button>
          </div>
          <div v-if="autoCreatedNodes.length" class="auto-created-panel">
            <div class="panel-head sub-head">
              <h4>刚自动创建</h4>
              <span>{{ autoCreatedNodes.length }} 个结点</span>
            </div>
            <div class="auto-created-list">
              <button
                v-for="node in autoCreatedNodes"
                :key="node.id"
                type="button"
                :class="['auto-created-chip', { active: selectedNodeId === node.id }]"
                @click="focusAutoCreatedNode(node.id)"
              >
                <strong>{{ node.name }}</strong>
                <small>{{ node.desc ? "已生成描述" : "描述待补充" }}</small>
              </button>
            </div>
          </div>
        </div>

        <div class="panel-card detail-card">
          <div class="panel-head">
            <h3>图谱编辑</h3>
            <span v-if="selectedNode">结点</span>
            <span v-else-if="selectedEdge">关系</span>
            <span v-else>未选择</span>
          </div>

          <div v-if="selectedNode" class="detail-body edit-detail-form node-edit-form">
            <label>
              结点名
              <input v-model="nodeForm.name" />
            </label>
            <label class="description-field">
              描述
              <textarea v-model="nodeForm.desc" rows="5" placeholder="结点描述"></textarea>
            </label>
            <label>
              章节标签
              <Listbox v-model="nodeForm.chapter" as="div" class="animated-select">
                <div class="animated-select-wrap">
                  <ListboxButton class="animated-select-button">
                    <span>{{ nodeForm.chapter || "未设置章节" }}</span>
                    <ChevronDown :size="16" aria-hidden="true" />
                  </ListboxButton>
                  <Transition name="select-pop">
                    <ListboxOptions class="animated-select-options">
                      <ListboxOption v-slot="{ active, selected }" as="template" value="">
                        <li :class="['animated-select-option', { active, selected }]">未设置章节</li>
                      </ListboxOption>
                      <ListboxOption v-for="chapter in graphChapterOptions" v-slot="{ active, selected }" :key="chapter" as="template" :value="chapter">
                        <li :class="['animated-select-option', { active, selected }]">{{ chapter }}</li>
                      </ListboxOption>
                    </ListboxOptions>
                  </Transition>
                </div>
              </Listbox>
            </label>
            <div class="detail-actions">
              <button class="primary" @click="submitNode">保存修改</button>
              <button class="danger" @click="openDeleteNodeConfirm">删除</button>
            </div>
          </div>

          <div v-else-if="selectedEdge" class="detail-body edit-detail-form edge-edit-form">
            <label>
              起点
              <div class="edge-search-box">
                <input
                  v-model="edgeForm.source"
                  placeholder="起点"
                  @input="handleEdgeFieldInput('source')"
                  @focus="handleEdgeFieldInput('source')"
                  @blur="deferHideEdgeNodeDropdown('source')"
                />
                <div v-if="showEdgeNodeDropdown.source && edgeNodeSuggestions.source.length" class="search-dropdown edge-dropdown">
                  <button
                    v-for="node in edgeNodeSuggestions.source"
                    :key="`edit-source-${node.id}`"
                    type="button"
                    class="search-dropdown-item"
                    @mousedown.prevent="applyEdgeNodeSuggestion('source', node)"
                  >
                    <strong>{{ node.name }}</strong>
                    <small v-if="node.desc">{{ node.desc }}</small>
                  </button>
                </div>
              </div>
            </label>
            <label>
              终点
              <div class="edge-search-box">
                <input
                  v-model="edgeForm.target"
                  placeholder="终点"
                  @input="handleEdgeFieldInput('target')"
                  @focus="handleEdgeFieldInput('target')"
                  @blur="deferHideEdgeNodeDropdown('target')"
                />
                <div v-if="showEdgeNodeDropdown.target && edgeNodeSuggestions.target.length" class="search-dropdown edge-dropdown">
                  <button
                    v-for="node in edgeNodeSuggestions.target"
                    :key="`edit-target-${node.id}`"
                    type="button"
                    class="search-dropdown-item"
                    @mousedown.prevent="applyEdgeNodeSuggestion('target', node)"
                  >
                    <strong>{{ node.name }}</strong>
                    <small v-if="node.desc">{{ node.desc }}</small>
                  </button>
                </div>
              </div>
            </label>
            <div class="edge-quick-actions">
              <button class="ghost" type="button" @click="swapEdgeDirection">交换起终点</button>
              <button v-if="selectedNode" class="ghost" type="button" @click="useSelectedNodeForEdge('source')">当前结点填入起点</button>
              <button v-if="selectedNode" class="ghost" type="button" @click="useSelectedNodeForEdge('target')">当前结点填入终点</button>
            </div>
            <div class="detail-actions">
              <button class="primary" @click="submitEdge">保存修改</button>
              <button class="danger" @click="openDeleteEdgeConfirm">删除</button>
            </div>
          </div>

          <div v-else class="empty-detail">
            <p>点击主画布中的结点或关系，在这里继续编辑。</p>
          </div>
        </div>
      </aside>
    </div>

    <div v-if="isCreatingNode" class="modal-overlay" @click.self="cancelCreateNode">
      <div class="modal-card">
        <h3>新增结点</h3>
        <p v-if="nodeDialogMessage" class="modal-feedback">{{ nodeDialogMessage }}</p>
        <div class="detail-body modal-form">
          <label>
            结点名
            <input v-model="nodeForm.name" placeholder="请输入唯一结点名" @keydown.enter.prevent="submitNode" />
          </label>
          <label>
            描述
            <textarea v-model="nodeForm.desc" rows="4" placeholder="结点描述" @keydown.ctrl.enter.prevent="submitNode"></textarea>
          </label>
          <div class="edge-quick-actions node-ai-action">
            <button class="primary" type="button" :disabled="isGeneratingNodeDesc" @click="generateNodeDescription">
              <Sparkles :size="16" :stroke-width="2" aria-hidden="true" />
              {{ isGeneratingNodeDesc ? "生成中..." : "AI 生成描述" }}
            </button>
          </div>
          <label>
            章节标签
            <Listbox v-model="nodeForm.chapter" as="div" class="animated-select select-up">
              <div class="animated-select-wrap">
                <ListboxButton class="animated-select-button">
                  <span>{{ nodeForm.chapter || "未设置章节" }}</span>
                  <ChevronDown :size="16" aria-hidden="true" />
                </ListboxButton>
                <Transition name="select-pop">
                  <ListboxOptions class="animated-select-options">
                    <ListboxOption v-slot="{ active, selected }" as="template" value="">
                      <li :class="['animated-select-option', { active, selected }]">未设置章节</li>
                    </ListboxOption>
                    <ListboxOption v-for="chapter in graphChapterOptions" v-slot="{ active, selected }" :key="chapter" as="template" :value="chapter">
                      <li :class="['animated-select-option', { active, selected }]">{{ chapter }}</li>
                    </ListboxOption>
                  </ListboxOptions>
                </Transition>
              </div>
            </Listbox>
          </label>
          <div class="detail-actions modal-actions">
            <button class="primary" @click="submitNode">确认创建</button>
            <button class="ghost modal-secondary" @click="cancelCreateNode">取消</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isCreatingEdge" class="modal-overlay" @click.self="cancelCreateEdge">
      <div class="modal-card">
        <h3>新增关系</h3>
        <p v-if="edgeDialogMessage" class="modal-feedback">{{ edgeDialogMessage }}</p>
        <div class="detail-body modal-form">
          <label>
            起点
            <div class="edge-search-box">
              <input
                v-model="edgeForm.source"
                placeholder="起点"
                @input="handleEdgeFieldInput('source')"
                @focus="handleEdgeFieldInput('source')"
                @blur="deferHideEdgeNodeDropdown('source')"
                @keydown.enter.prevent="submitEdge"
              />
              <div v-if="showEdgeNodeDropdown.source && edgeNodeSuggestions.source.length" class="search-dropdown edge-dropdown">
                <button
                  v-for="node in edgeNodeSuggestions.source"
                  :key="`create-source-${node.id}`"
                  type="button"
                  class="search-dropdown-item"
                  @mousedown.prevent="applyEdgeNodeSuggestion('source', node)"
                >
                  <strong>{{ node.name }}</strong>
                  <small v-if="node.desc">{{ node.desc }}</small>
                </button>
              </div>
            </div>
          </label>
          <label>
            终点
            <div class="edge-search-box">
              <input
                v-model="edgeForm.target"
                placeholder="终点"
                @input="handleEdgeFieldInput('target')"
                @focus="handleEdgeFieldInput('target')"
                @blur="deferHideEdgeNodeDropdown('target')"
                @keydown.enter.prevent="submitEdge"
              />
              <div v-if="showEdgeNodeDropdown.target && edgeNodeSuggestions.target.length" class="search-dropdown edge-dropdown">
                <button
                  v-for="node in edgeNodeSuggestions.target"
                  :key="`create-target-${node.id}`"
                  type="button"
                  class="search-dropdown-item"
                  @mousedown.prevent="applyEdgeNodeSuggestion('target', node)"
                >
                  <strong>{{ node.name }}</strong>
                  <small v-if="node.desc">{{ node.desc }}</small>
                </button>
              </div>
            </div>
          </label>
          <div class="edge-quick-actions modal-quick-actions">
            <button class="ghost modal-secondary" type="button" @click="swapEdgeDirection">交换起终点</button>
            <button v-if="selectedNode" class="ghost modal-secondary" type="button" @click="useSelectedNodeForEdge('source')">当前结点填入起点</button>
            <button v-if="selectedNode" class="ghost modal-secondary" type="button" @click="useSelectedNodeForEdge('target')">当前结点填入终点</button>
          </div>
          <div class="detail-actions modal-actions">
            <button class="primary" @click="submitEdge">确认创建</button>
            <button class="ghost modal-secondary" @click="cancelCreateEdge">取消</button>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="deleteConfirmTarget" class="dialog-backdrop" @click.self="closeDeleteConfirm">
        <div class="dialog-card">
          <h4>{{ deleteConfirmTarget.kind === "node" ? "删除结点" : "删除关系" }}</h4>
          <p>{{ deleteConfirmMessage }}</p>
          <div class="dialog-actions">
            <button type="button" class="ghost-btn" :disabled="isDeletingGraphItem" @click="closeDeleteConfirm">取消</button>
            <button type="button" class="danger-btn" :disabled="isDeletingGraphItem" @click="confirmDeleteGraphItem">
              {{ isDeletingGraphItem ? "删除中..." : "确认删除" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from "@headlessui/vue";
import { ChevronDown, Sparkles } from "lucide-vue-next";
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import {
  createTeacherEdgeApi,
  createTeacherNodeApi,
  deleteTeacherEdgeApi,
  deleteTeacherNodeApi,
  generateTeacherNodeDescriptionApi,
  getTeacherGraphApi,
  updateTeacherEdgeApi,
  updateTeacherNodeApi,
} from "../api/teacher";
import PageHeader from "../components/PageHeader.vue";
import KnowledgeGraphCanvas from "../components/KnowledgeGraphCanvas.vue";
import { FULL_GRAPH_LIMIT, fetchFullGraph, getCachedFullGraph, getStaleFullGraph } from "../features/teacher-graph/graphCache";
import { clearAuthSession } from "../utils/authStorage";

defineOptions({ name: "TeacherGraphPage" });

const router = useRouter();
const keyword = ref("");
const errorMessage = ref("");
const isGraphLoading = ref(true);
const isInitialGraphLoading = ref(true);
const hasGraphLoaded = ref(false);
const isGraphSuggesting = ref(false);
const fullGraph = ref({ nodes: [], edges: [] });
const graph = ref({ nodes: [], edges: [] });
const graphSuggestions = ref([]);
const showGraphSuggestions = ref(false);
const selectedGraphChapter = ref("");

const selectedNodeId = ref("");
const selectedEdgeId = ref("");

const graphViewport = ref(null);
const graphCanvas = ref(null);

const isCreatingNode = ref(false);
const isCreatingEdge = ref(false);
const isGeneratingNodeDesc = ref(false);
const nodeDialogMessage = ref("");
const edgeDialogMessage = ref("");
const autoCreatedNodeNames = ref([]);
const deleteConfirmTarget = ref(null);
const isDeletingGraphItem = ref(false);

const nodeForm = reactive({ name: "", desc: "", chapter: "" });
const edgeForm = reactive({ source: "", relation: "DEPENDS_ON", target: "" });
const edgeNodeSuggestions = reactive({ source: [], target: [] });
const showEdgeNodeDropdown = reactive({ source: false, target: false });

const selectedNode = computed(() => graph.value.nodes.find((node) => node.id === selectedNodeId.value) || null);
const selectedEdge = computed(() => graph.value.edges.find((edge) => edge.id === selectedEdgeId.value) || null);
const graphChapterOptions = computed(() => {
  const chapters = fullGraph.value.nodes.map((node) => node.chapter).filter(Boolean);
  return [...new Set(chapters)].sort((left, right) => left.localeCompare(right, "zh-Hans-CN"));
});
const autoCreatedNodes = computed(() =>
  autoCreatedNodeNames.value
    .map((name) => graph.value.nodes.find((node) => node.name === name))
    .filter(Boolean),
);
const deleteConfirmMessage = computed(() => {
  if (!deleteConfirmTarget.value) return "";
  if (deleteConfirmTarget.value.kind === "node") {
    return `确定删除结点「${deleteConfirmTarget.value.name}」吗？删除后相关关系也会被移除。`;
  }
  return "确定删除这条关系吗？删除后无法恢复。";
});
let graphSuggestTimer = null;
const edgeSearchTimers = { source: null, target: null };

onMounted(async () => {
  await loadGraph();
});

async function loadGraph() {
  const cachedGraph = getCachedFullGraph();
  if (cachedGraph) {
    fullGraph.value = cachedGraph;
    graph.value = cachedGraph;
    hasGraphLoaded.value = true;
    isGraphLoading.value = false;
    isInitialGraphLoading.value = false;
    return;
  }

  const staleGraph = getStaleFullGraph();
  if (staleGraph) {
    fullGraph.value = staleGraph;
    graph.value = staleGraph;
    hasGraphLoaded.value = true;
    isGraphLoading.value = false;
    isInitialGraphLoading.value = false;
    refreshFullGraphCacheInBackground();
    return;
  }

  isGraphLoading.value = true;
  try {
    const data = await fetchFullGraph({ force: false });
    fullGraph.value = data;
    graph.value = data;
  } catch (error) {
    handleApiError(error, "加载图谱失败。");
  } finally {
    hasGraphLoaded.value = true;
    isGraphLoading.value = false;
    isInitialGraphLoading.value = false;
  }
}

function refreshFullGraphCacheInBackground() {
  fetchFullGraph({ force: true })
    .then((data) => {
      if (keyword.value.trim() || selectedGraphChapter.value) return;
      fullGraph.value = data;
      graph.value = data;
    })
    .catch(() => {});
}

async function reloadGraphAfterMutation() {
  const query = keyword.value.trim();
  const chapter = selectedGraphChapter.value;
  const fullGraphRequest = fetchFullGraph({ force: true });
  const visibleGraphRequest =
    query || chapter ? getTeacherGraphApi({ keyword: query, chapter, limit: FULL_GRAPH_LIMIT }) : fullGraphRequest;

  const [fullGraphData, visibleGraphResponse] = await Promise.all([
    fullGraphRequest,
    visibleGraphRequest,
  ]);

  fullGraph.value = fullGraphData;
  graph.value = query || chapter ? visibleGraphResponse.data : fullGraphData;
}

async function refreshGraph(options = {}) {
  const { restartLayout = true, preserveSearch = false } = options;
  if (preserveSearch) {
    await reloadGraphAfterMutation();
  } else {
    await loadGraph();
  }
  await nextTick();
  if (restartLayout) {
    graphCanvas.value?.restartLayout?.();
  }
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

function handleSelectNode(nodeId) {
  selectedNodeId.value = nodeId;
  selectedEdgeId.value = "";
  const node = graph.value.nodes.find((item) => item.id === nodeId);
  if (!node) return;
  nodeForm.name = node.name;
  nodeForm.desc = node.desc || "";
  nodeForm.chapter = node.chapter || "";
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

function startCreateNode() {
  isCreatingNode.value = true;
  nodeForm.name = "";
  nodeForm.desc = "";
  nodeForm.chapter = "";
  nodeDialogMessage.value = "";
}

function cancelCreateNode() {
  isCreatingNode.value = false;
  nodeDialogMessage.value = "";
}

function startCreateEdge() {
  isCreatingEdge.value = true;
  edgeForm.source = selectedNode.value ? selectedNode.value.name : "";
  edgeForm.target = "";
  edgeForm.relation = "DEPENDS_ON";
  showEdgeNodeDropdown.source = false;
  showEdgeNodeDropdown.target = false;
  edgeDialogMessage.value = "";
}

function cancelCreateEdge() {
  isCreatingEdge.value = false;
  edgeDialogMessage.value = "";
}

async function submitNode() {
  if (!nodeForm.name.trim()) {
    if (isCreatingNode.value) {
      nodeDialogMessage.value = "结点名不能为空";
    } else {
      errorMessage.value = "结点名不能为空";
    }
    return;
  }
  const targetName = nodeForm.name.trim();
  try {
    nodeDialogMessage.value = "";
    if (isCreatingNode.value) {
      await createTeacherNodeApi({ ...nodeForm });
      isCreatingNode.value = false;
    } else if (selectedNode.value) {
      await updateTeacherNodeApi(selectedNode.value.name, { ...nodeForm });
    }
    await refreshGraph({ preserveSearch: true, restartLayout: false });
    const nextNode = graph.value.nodes.find((node) => node.name === targetName);
    if (nextNode) {
      handleSelectNode(nextNode.id);
      await nextTick();
      graphCanvas.value?.focusNodes?.([nextNode.id]);
    }
  } catch (error) {
    if (isCreatingNode.value) {
      nodeDialogMessage.value = error?.response?.data?.detail || "保存结点失败。";
    } else {
      handleApiError(error, "保存结点失败。");
    }
  }
}

async function submitEdge() {
  if (!edgeForm.source.trim() || !edgeForm.target.trim()) {
    if (isCreatingEdge.value) {
      edgeDialogMessage.value = "请填写起点和终点";
    } else {
      errorMessage.value = "请填写起点和终点";
    }
    return;
  }
  const sourceName = edgeForm.source.trim();
  const targetName = edgeForm.target.trim();
  try {
    edgeDialogMessage.value = "";
    let result = null;
    if (isCreatingEdge.value) {
      const response = await createTeacherEdgeApi({ ...edgeForm, relation: "DEPENDS_ON" });
      result = response?.data || null;
    } else if (selectedEdge.value) {
      await updateTeacherEdgeApi(selectedEdge.value.edge_key, { ...edgeForm, relation: "DEPENDS_ON" });
    }
    await refreshGraph({ preserveSearch: true, restartLayout: false });
    if (Array.isArray(result?.created_nodes) && result.created_nodes.length) {
      autoCreatedNodeNames.value = result.created_nodes.map((item) => item.name);
      const labels = result.created_nodes.map((item) =>
        item?.desc_generated ? `${item.name}（已生成描述）` : `${item.name}（描述待补充）`,
      );
      edgeDialogMessage.value = `已自动创建结点：${labels.join("、")}`;
      isCreatingEdge.value = false;
    } else if (isCreatingEdge.value) {
      autoCreatedNodeNames.value = [];
      isCreatingEdge.value = false;
    }
    const nextEdge = graph.value.edges.find(
      (edge) => edge.source_name === sourceName && edge.target_name === targetName && edge.relation === "DEPENDS_ON",
    );
    if (nextEdge) {
      handleSelectEdge(nextEdge.id);
      await nextTick();
      graphCanvas.value?.focusNodes?.([nextEdge.source, nextEdge.target]);
    }
    if (autoCreatedNodes.value.length) {
      await focusAutoCreatedNode(autoCreatedNodes.value[0].id);
    }
  } catch (error) {
    if (isCreatingEdge.value) {
      edgeDialogMessage.value = error?.response?.data?.detail || "保存关系失败。";
    } else {
      handleApiError(error, "保存关系失败。");
    }
  }
}

async function generateNodeDescription() {
  const name = nodeForm.name.trim();
  if (!name) {
    nodeDialogMessage.value = "请先填写结点名，再生成描述。";
    return;
  }
  isGeneratingNodeDesc.value = true;
  nodeDialogMessage.value = "";
  try {
    const { data } = await generateTeacherNodeDescriptionApi({ name });
    nodeForm.desc = String(data?.desc || "").trim();
  } catch (error) {
    nodeDialogMessage.value = error?.response?.data?.detail || "生成结点描述失败。";
  } finally {
    isGeneratingNodeDesc.value = false;
  }
}

function openDeleteNodeConfirm() {
  if (!selectedNode.value) return;
  deleteConfirmTarget.value = { kind: "node", name: selectedNode.value.name };
}

function openDeleteEdgeConfirm() {
  if (!selectedEdge.value) return;
  deleteConfirmTarget.value = { kind: "edge", edgeKey: selectedEdge.value.edge_key };
}

function closeDeleteConfirm() {
  if (isDeletingGraphItem.value) return;
  deleteConfirmTarget.value = null;
}

async function confirmDeleteGraphItem() {
  if (!deleteConfirmTarget.value) return;
  const target = deleteConfirmTarget.value;
  isDeletingGraphItem.value = true;
  try {
    if (target.kind === "node") {
      await deleteTeacherNodeApi(target.name);
    } else {
      await deleteTeacherEdgeApi(target.edgeKey);
    }
    deleteConfirmTarget.value = null;
    clearSelection();
    await refreshGraph({ preserveSearch: true, restartLayout: false });
  } catch (error) {
    handleApiError(error, target.kind === "node" ? "删除结点失败。" : "删除关系失败。");
  } finally {
    isDeletingGraphItem.value = false;
  }
}

async function searchGraph() {
  const query = keyword.value.trim();
  const chapter = selectedGraphChapter.value;
  if (!query && !chapter) {
    graph.value = fullGraph.value;
    clearSelection();
    showGraphSuggestions.value = false;
    return;
  }
  try {
    isGraphLoading.value = true;
    const { data } = await getTeacherGraphApi({ keyword: query, chapter, limit: FULL_GRAPH_LIMIT });
    graph.value = data;
    clearSelection();
    showGraphSuggestions.value = false;
    if (data.nodes.length) {
      await nextTick();
      graphCanvas.value?.focusNodes?.(data.nodes.map((node) => node.id));
    }
  } catch (error) {
    handleApiError(error, "搜索图谱失败。");
  } finally {
    hasGraphLoaded.value = true;
    isGraphLoading.value = false;
  }
}

function handleGraphKeywordInput() {
  if (graphSuggestTimer) clearTimeout(graphSuggestTimer);
  const query = keyword.value.trim();
  if (!query) {
    graphSuggestions.value = [];
    showGraphSuggestions.value = false;
    if (!selectedGraphChapter.value) {
      graph.value = fullGraph.value;
      clearSelection();
    } else {
      graphSuggestTimer = setTimeout(() => {
        searchGraph();
      }, 180);
    }
    return;
  }
  graphSuggestTimer = setTimeout(() => {
    fetchGraphSuggestions(query);
  }, 180);
}

async function fetchGraphSuggestions(query) {
  if (!query) return;
  isGraphSuggesting.value = true;
  try {
    const { data } = await getTeacherGraphApi({ keyword: query, chapter: selectedGraphChapter.value, limit: 50 });
    graphSuggestions.value = data.nodes || [];
    showGraphSuggestions.value = graphSuggestions.value.length > 0;
  } catch (error) {
    graphSuggestions.value = [];
    showGraphSuggestions.value = false;
  } finally {
    isGraphSuggesting.value = false;
  }
}

async function selectGraphSuggestion(node) {
  keyword.value = node.name;
  await searchGraph();
  const exactNode = graph.value.nodes.find((item) => item.name === node.name);
  if (exactNode) {
    handleSelectNode(exactNode.id);
    await nextTick();
    graphCanvas.value?.focusNodes?.([exactNode.id]);
  }
}

function handleEdgeFieldInput(field) {
  if (edgeSearchTimers[field]) clearTimeout(edgeSearchTimers[field]);
  const query = String(edgeForm[field] || "").trim();
  if (!query) {
    edgeNodeSuggestions[field] = [];
    showEdgeNodeDropdown[field] = false;
    return;
  }
  edgeSearchTimers[field] = setTimeout(() => {
    fetchEdgeNodeSuggestions(field, query);
  }, 180);
}

async function fetchEdgeNodeSuggestions(field, query) {
  try {
    const { data } = await getTeacherGraphApi({ keyword: query, limit: 20 });
    edgeNodeSuggestions[field] = data.nodes || [];
    showEdgeNodeDropdown[field] = edgeNodeSuggestions[field].length > 0;
  } catch (error) {
    edgeNodeSuggestions[field] = [];
    showEdgeNodeDropdown[field] = false;
  }
}

function applyEdgeNodeSuggestion(field, node) {
  edgeForm[field] = node.name;
  showEdgeNodeDropdown[field] = false;
}

function deferHideEdgeNodeDropdown(field) {
  setTimeout(() => {
    showEdgeNodeDropdown[field] = false;
  }, 120);
}

function swapEdgeDirection() {
  const source = edgeForm.source;
  edgeForm.source = edgeForm.target;
  edgeForm.target = source;
  showEdgeNodeDropdown.source = false;
  showEdgeNodeDropdown.target = false;
}

function useSelectedNodeForEdge(field) {
  if (!selectedNode.value) return;
  edgeForm[field] = selectedNode.value.name;
  showEdgeNodeDropdown[field] = false;
}

async function focusAutoCreatedNode(nodeId) {
  handleSelectNode(nodeId);
  selectedEdgeId.value = "";
  await nextTick();
  graphCanvas.value?.focusNodes?.([nodeId]);
}

function handleApiError(error, fallbackMessage) {
  const status = error?.response?.status;
  if (status === 401 || status === 403) {
    clearAuthSession();
    router.push("/login");
    return;
  }
  errorMessage.value = error?.response?.data?.detail || fallbackMessage;
}
</script>

<style scoped>
.graph-page {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 14px;
  height: calc(100vh - 38px);
  min-height: 0;
  overflow: hidden;
  font-size: var(--compact-body);
}

.toolbar {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) minmax(180px, 0.8fr) auto 86px 86px 86px;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--app-line);
  border-radius: 10px;
  background: #ffffff;
  box-shadow: var(--app-shadow);
}

.toolbar-search {
  position: relative;
  min-width: 0;
}

.toolbar .ghost {
  white-space: nowrap;
  min-height: 36px;
  width: 100%;
  padding: 0 14px;
}

.toolbar .ghost:first-of-type {
  background: var(--app-primary);
  color: #fff;
  box-shadow: 0 10px 24px rgba(47, 103, 246, 0.18);
}

.toolbar .ghost:first-of-type:hover:not(:disabled) {
  background: var(--app-primary-deep);
}

.toolbar .ghost:not(:first-of-type) {
  border: 1px solid var(--app-primary);
  background: #fff;
  color: var(--app-primary);
}

.toolbar .ghost:not(:first-of-type):hover:not(:disabled) {
  background: var(--app-primary-soft);
}

.toolbar-search {
  min-width: 260px;
}

.edge-search-box {
  position: relative;
}

.toolbar-input,
.detail-body input,
.detail-body textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--app-line);
  border-radius: 8px;
  background: #fff;
  font: inherit;
}

.toolbar-input:focus,
.detail-body input:focus,
.detail-body textarea:focus {
  border-color: #bfd0ea;
  box-shadow: none;
  outline: none;
}

.toolbar-input {
  min-width: 0;
}

.animated-select {
  width: 100%;
  min-width: 0;
}

.toolbar-select {
  min-width: 140px;
}

.animated-select-wrap {
  position: relative;
}

.animated-select-button {
  width: 100%;
  min-height: 37px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 12px;
  border: 1px solid var(--app-line);
  border-radius: 8px;
  background: #fff;
  color: #214666;
  font: inherit;
  text-align: left;
}

.animated-select-button:hover:not(:disabled),
.animated-select-button[aria-expanded="true"] {
  border-color: #bfd0ea;
  background: #fff;
}

.animated-select-button span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.animated-select-button svg {
  flex: 0 0 auto;
  color: #7890a7;
  transition: transform 140ms var(--motion-ease);
}

.animated-select-button[aria-expanded="true"] svg {
  transform: rotate(180deg);
}

.animated-select-options {
  position: absolute;
  z-index: 30;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 6px;
  list-style: none;
  border: 1px solid #dce8f5;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.12);
  transform-origin: top center;
}

.select-up .animated-select-options {
  top: auto;
  bottom: calc(100% + 6px);
  transform-origin: bottom center;
}

.animated-select-option {
  padding: 9px 10px;
  border-radius: 7px;
  color: #214666;
  cursor: pointer;
  line-height: 1.25;
}

.animated-select-option.active {
  background: var(--app-primary-soft);
  color: var(--app-primary-deep);
}

.animated-select-option.selected {
  background: var(--app-primary);
  color: #ffffff;
}

.select-pop-enter-active,
.select-pop-leave-active {
  transition:
    opacity 140ms var(--motion-ease),
    transform 140ms var(--motion-ease);
}

.select-pop-enter-from,
.select-pop-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}

.select-pop-enter-to,
.select-pop-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.graph-meta {
  color: var(--app-text-muted);
  font-size: 13px;
  white-space: nowrap;
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 8;
  display: grid;
  gap: 6px;
  max-height: 320px;
  padding: 8px;
  overflow-y: auto;
  border: 1px solid #dce8f5;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.12);
}

.edge-dropdown {
  z-index: 12;
}

.search-dropdown-item {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  text-align: left;
  color: #214666;
  background: #fff;
  border: 1px solid #d8e7f6;
}

.search-dropdown-item small {
  overflow: hidden;
  color: #73869a;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-dropdown-item:hover {
  color: #fff;
  background: #1e63a7;
}

.search-dropdown-item:hover small {
  color: rgba(255, 255, 255, 0.78);
}

.edge-quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.edge-quick-actions .ghost {
  padding: 8px 12px;
  border-radius: 8px;
}

button {
  border: none;
  border-radius: 8px;
  padding: 9px 13px;
  background: #10283d;
  color: #fff;
  cursor: pointer;
  font: inherit;
}

button:hover {
  background: #1c3d5a;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.ghost {
  background: #edf4ff;
  color: #2d5278;
}

.ghost:hover:not(:disabled) {
  background: #d8e6fa;
}

.graph-mode-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 340px);
  gap: 14px;
  align-items: stretch;
  min-height: 0;
  overflow: hidden;
}

.graph-panel {
  border: 1px solid #e2ebf4;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
  position: relative;
  padding: 2px 0 0;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 10px;
  min-height: 0;
  overflow: hidden;
}

.formal-panel :deep(.graph-canvas) {
  height: 100%;
  min-height: 0;
}

.graph-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-left: 10px;
}

.graph-panel-head h3 {
  margin: 4px 0 0;
  color: #10283d;
  font-size: var(--compact-section-title);
}

.graph-state {
  position: absolute;
  inset: 54px 0 0;
  display: grid;
  place-items: center;
  color: #6f8297;
  font-size: var(--compact-body);
  background: #ffffff;
  border-radius: 10px;
  z-index: 2;
}

.graph-side-panel {
  display: grid;
  gap: 10px;
  grid-template-rows: auto minmax(440px, 1fr);
  min-height: 0;
  overflow: hidden;
}

.panel-card {
  min-height: 0;
  padding: 12px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #ebf1f7;
  display: grid;
  gap: 10px;
  overflow: hidden;
}

.detail-card {
  grid-template-rows: auto 1fr;
}

.action-card {
  align-content: start;
}

.action-bar {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.action-bar button {
  background: #2563eb;
}

.auto-created-panel {
  display: grid;
  gap: 10px;
  padding-top: 6px;
  border-top: 1px solid var(--app-line);
}

.auto-created-list {
  display: grid;
  gap: 8px;
}

.auto-created-chip {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  text-align: left;
  color: #214666;
  background: #fff;
  border: 1px solid #d8e7f6;
}

.auto-created-chip small {
  color: #708294;
}

.auto-created-chip.active,
.auto-created-chip:hover {
  background: #1e63a7;
  color: #fff;
}

.auto-created-chip.active small,
.auto-created-chip:hover small {
  color: rgba(255, 255, 255, 0.8);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-head h3,
.panel-head h4 {
  margin: 0;
  color: #10283d;
}

.panel-head span {
  color: #7890a7;
  font-size: 13px;
}

.detail-body {
  display: grid;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.edit-detail-form {
  height: 100%;
  overflow: hidden;
  padding-bottom: 0;
}

.node-edit-form {
  grid-template-rows: auto minmax(0, 1fr) auto auto;
}

.edge-edit-form {
  grid-template-rows: auto auto auto minmax(0, 1fr);
}

.detail-body label {
  display: grid;
  gap: 6px;
  color: #526b84;
  font-size: 13px;
  font-weight: 400;
}

.description-field {
  min-height: 0;
  grid-template-rows: auto minmax(0, 1fr);
}

.detail-body textarea {
  resize: none;
}

.description-field textarea {
  height: 100%;
  min-height: 120px;
}

.detail-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-self: end;
}

.edit-detail-form .detail-actions {
  justify-content: space-between;
}

.detail-actions button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  min-height: 34px;
  padding: 0 13px;
  line-height: 1;
}

.primary {
  background: var(--app-primary);
  color: #fff;
  box-shadow: 0 10px 24px rgba(47, 103, 246, 0.18);
}

.detail-actions .primary {
  box-shadow: none;
}

.primary:hover:not(:disabled) {
  background: var(--app-primary-deep);
}

.danger {
  background: #ef4444;
}

.danger:hover:not(:disabled) {
  background: #dc2626;
}

.sub-head {
  margin-bottom: 8px;
}

.empty-detail {
  display: grid;
  min-height: 100%;
  place-items: center;
  color: #6f8297;
  line-height: 1.7;
  font-size: var(--compact-body);
  text-align: center;
  padding: 20px;
}

.empty-detail.compact {
  padding: 8px 0;
}

.feedback.error {
  padding: 12px;
  border-radius: 8px;
  background: #fff8f8;
  color: #b42318;
}

.modal-feedback {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #eef6ff;
  color: #1f4f7b;
  line-height: 1.6;
  font-size: 13px;
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
}

.modal-card {
  width: 100%;
  max-width: 420px;
  background: #ffffff;
  padding: 18px;
  border-radius: 10px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.12);
}

.modal-card h3 {
  margin: 0 0 20px;
  color: #0f2840;
}

.modal-form {
  overflow: visible;
}

.node-ai-action {
  display: grid;
}

.node-ai-action button {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.node-ai-action svg {
  flex: 0 0 auto;
  color: #ffffff;
  stroke: currentColor;
}

.modal-actions {
  justify-content: space-between;
}

.modal-secondary,
.modal-quick-actions .modal-secondary {
  border: 1px solid var(--app-primary);
  background: #ffffff;
  color: var(--app-primary);
}

.modal-secondary:hover:not(:disabled),
.modal-quick-actions .modal-secondary:hover:not(:disabled) {
  background: var(--app-primary-soft);
  color: var(--app-primary-deep);
}

.modal-quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.modal-quick-actions button {
  flex: 1 1 auto;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  background: rgba(9, 19, 33, 0.46);
}

.dialog-card {
  width: min(92vw, 380px);
  padding: 18px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 28px 70px rgba(15, 23, 42, 0.28);
}

.dialog-card h4 {
  margin: 0 0 10px;
  color: var(--app-text);
}

.dialog-card p {
  margin: 0 0 16px;
  color: var(--app-text-muted);
  line-height: 1.45;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.ghost-btn,
.danger-btn {
  min-height: 34px;
  padding: 0 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.ghost-btn {
  background: #f4f7fb;
  color: #475569;
}

.danger-btn {
  background: #ef4444;
  color: #fff;
}

.danger-btn:hover:not(:disabled) {
  background: #dc2626;
}

.danger-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .graph-page {
    height: auto;
    min-height: calc(100vh - 38px);
    overflow: visible;
  }

  .toolbar {
    grid-template-columns: 1fr 1fr;
  }

  .toolbar-search {
    min-width: 0;
  }

  .graph-meta {
    justify-self: start;
  }

  .graph-mode-layout {
    grid-template-columns: 1fr;
    overflow: visible;
  }

  .formal-panel {
    min-height: 560px;
  }

  .formal-panel :deep(.graph-canvas) {
    min-height: 480px;
  }

  .graph-side-panel {
    min-height: auto;
    overflow: visible;
    grid-template-rows: auto auto;
  }
}

@media (max-width: 720px) {
  .graph-panel-head {
    flex-direction: column;
  }

  .action-bar {
    grid-template-columns: 1fr;
  }

}
</style>
