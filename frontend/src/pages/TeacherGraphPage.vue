<template>
  <section class="graph-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Knowledge Graph</p>
        <h2>知识图谱管理</h2>
        <p class="page-copy">在正式图谱编辑和候选批次审核之间切换，用单主图工作台集中完成管理与审核。</p>
      </div>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <div class="toolbar">
      <div class="toolbar-search">
        <input
          v-model="keyword"
          class="toolbar-input"
          placeholder="搜索节点名或描述"
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
      <span class="graph-meta">节点 {{ graph.nodes.length }} / 边 {{ graph.edges.length }}</span>
      <button class="ghost" @click="searchGraph">搜索</button>
      <button class="ghost" @click="toggleFullscreen">全屏</button>
      <button class="ghost" @click="refreshGraph">刷新布局</button>
    </div>

    <div class="mode-switch">
      <button
        type="button"
        :class="['mode-tab', { active: activeMode === 'graph' }]"
        @click="switchMode('graph')"
      >
        正式图谱
      </button>
      <button
        type="button"
        :class="['mode-tab', { active: activeMode === 'review' }]"
        :disabled="!selectedBatchDetail"
        @click="switchMode('review')"
      >
        候选审核
      </button>
    </div>

    <div v-if="activeMode === 'graph'" class="graph-mode-layout">
      <section ref="graphViewport" class="graph-panel formal-panel">
        <div class="graph-panel-head">
          <div>
            <p class="graph-mode-label">Formal Graph</p>
            <h3>正式知识图谱</h3>
          </div>
          <span class="graph-mode-copy">编辑正式图谱中的节点与关系</span>
        </div>

        <div v-if="isGraphLoading" class="graph-state">图谱加载中...</div>
        <div v-else-if="!graph.nodes.length" class="graph-state">当前没有可展示的知识图谱节点。</div>

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
            <span>正式图谱</span>
          </div>
          <div class="action-bar">
            <button @click="startCreateNode">新增节点</button>
            <button @click="startCreateEdge">新增关系</button>
          </div>
          <div v-if="autoCreatedNodes.length" class="auto-created-panel">
            <div class="panel-head sub-head">
              <h4>刚自动创建</h4>
              <span>{{ autoCreatedNodes.length }} 个节点</span>
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
            <h3>正式图谱编辑</h3>
            <span v-if="selectedNode">节点</span>
            <span v-else-if="selectedEdge">关系</span>
            <span v-else>未选择</span>
          </div>

          <div v-if="selectedNode" class="detail-body">
            <label>
              节点名
              <input v-model="nodeForm.name" disabled />
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
              <button v-if="selectedNode" class="ghost" type="button" @click="useSelectedNodeForEdge('source')">当前节点填入起点</button>
              <button v-if="selectedNode" class="ghost" type="button" @click="useSelectedNodeForEdge('target')">当前节点填入终点</button>
            </div>
            <div class="detail-actions">
              <button @click="submitEdge">保存修改</button>
              <button class="danger" @click="deleteEdge">删除</button>
            </div>
          </div>

          <div v-else class="empty-detail">
            <p>点击主画布中的节点或关系，在这里继续编辑。</p>
          </div>
        </div>
      </aside>
    </div>

    <section v-else class="review-workbench">
      <div class="review-header-strip">
        <div class="panel-card review-strip-card">
          <div class="panel-head">
            <h3>候选批次</h3>
            <span>{{ pendingBatches.length }} 批次</span>
          </div>

          <div v-if="isPendingLoading" class="empty-detail compact">
            <p>候选批次加载中...</p>
          </div>
          <template v-else-if="pendingBatches.length">
            <div class="review-batch-list">
              <button
                v-for="batch in pendingBatches"
                :key="batch.id"
                type="button"
                :class="['batch-chip', { active: batch.id === selectedBatchId }]"
                @click="selectPendingBatch(batch.id)"
              >
                <strong>{{ batch.anchor_name }}</strong>
                <small>{{ batch.source_type }} · {{ batch.pending_node_count }} 个结点</small>
              </button>
            </div>
          </template>
          <div v-else class="empty-detail compact">
            <p>当前没有待教师确认的候选知识子图。</p>
          </div>
        </div>

        <div class="panel-card review-current-card">
          <div class="panel-head">
            <h3>当前批次</h3>
            <span>{{ selectedBatchDetail?.batch.source_type || "未选择" }}</span>
          </div>

          <div v-if="selectedBatchDetail" class="review-current-body">
            <div class="review-meta">
              <span>锚点：{{ selectedBatchDetail.batch.anchor_name }}</span>
              <span>锚点状态：{{ selectedBatchDetail.batch.anchor_status }}</span>
              <span>待审结点：{{ selectedNodeDrafts.length }}</span>
              <span>建议关系：{{ selectedEdgeDrafts.length }}</span>
              <span v-if="selectedBatchDetail.batch.source_weak_point">薄弱点：{{ selectedBatchDetail.batch.source_weak_point }}</span>
            </div>
            <p class="review-summary-text">
              {{ selectedBatchDetail.batch.question_excerpt || "该批次没有额外问题摘要。" }}
            </p>
          </div>

          <div v-else class="empty-detail compact">
            <p>请先选择一个候选批次开始审核。</p>
          </div>
        </div>
      </div>

      <div class="review-mode-layout">
        <section ref="graphViewport" class="graph-panel review-graph-panel">
          <div class="graph-panel-head">
            <div>
              <p class="graph-mode-label">Pending Review</p>
              <h3>{{ selectedBatchDetail?.batch.anchor_name || "候选批次审核" }}</h3>
            </div>
            <span class="graph-mode-copy">审核当前批次的候选结点、建议关系与锚点上下文</span>
          </div>

          <div v-if="isReviewLoading" class="graph-state">候选批次图加载中...</div>
          <div v-else-if="!reviewGraph.nodes.length" class="graph-state">当前批次没有可展示的候选结点。</div>

          <KnowledgeGraphCanvas
            v-if="reviewGraph.nodes.length && !isReviewLoading"
            ref="reviewCanvas"
            :nodes="reviewGraph.nodes"
            :edges="reviewGraph.edges"
            :selected-node-id="selectedReviewNodeId"
            :selected-edge-id="selectedReviewEdgeId"
            @select-node="handleSelectReviewNode"
            @select-edge="handleSelectReviewEdge"
            @clear-selection="clearReviewSelection"
          />
        </section>

        <aside class="review-side-panel">
          <div class="panel-card detail-card">
            <div class="panel-head">
              <h3>审核详情</h3>
              <span>{{ selectedReviewNode ? selectedReviewNode.name : selectedReviewEdge ? selectedReviewEdge.relation : "请选择图中元素" }}</span>
            </div>

            <div v-if="selectedReviewNode && editableReviewNode" class="detail-body">
              <label>
                节点名
                <input v-model="editableReviewNode.name" :disabled="isContextNode(selectedReviewNode)" />
              </label>
              <label>
                描述
                <textarea v-model="editableReviewNode.desc" rows="4" :disabled="isContextNode(selectedReviewNode)"></textarea>
              </label>
              <label>
                提议原因
                <textarea :value="selectedReviewNode.reason || '无'" rows="3" disabled />
              </label>
              <label v-if="!isContextNode(selectedReviewNode)" class="checkbox-row">
                <input v-model="editableReviewNode.keep" type="checkbox" />
                保留该待审结点
              </label>
            </div>

            <div v-else-if="selectedReviewEdge && editableReviewEdge" class="detail-body">
              <label>
                关系
                <input :value="reviewEdgeLabel(selectedReviewEdge)" disabled />
              </label>
              <label class="checkbox-row">
                <input v-model="editableReviewEdge.keep" type="checkbox" />
                保留该建议关系
              </label>
            </div>

            <div v-else class="empty-detail compact">
              <p>点击候选审核图中的节点或关系，在这里查看详情并决定是否保留。</p>
            </div>
          </div>

          <div class="panel-card approval-card">
            <div class="panel-head">
              <h3>勾选与审批</h3>
              <span>保留需要并入正式图谱的内容</span>
            </div>
            <div class="review-checklists">
              <div class="checklist-group">
                <div class="panel-head sub-head">
                  <h4>待审结点</h4>
                  <span>{{ selectedNodeDrafts.length }} 项</span>
                </div>
                <label
                  v-for="node in selectedNodeDrafts"
                  :key="node.id"
                  class="check-item"
                  @click="handleSelectReviewNode(node.id)"
                >
                  <input v-model="node.keep" type="checkbox" />
                  <span>{{ node.name }}</span>
                </label>
              </div>

              <div class="checklist-group">
                <div class="panel-head sub-head">
                  <h4>建议关系</h4>
                  <span>{{ selectedEdgeDrafts.length }} 项</span>
                </div>
                <label
                  v-for="edge in selectedEdgeDrafts"
                  :key="edge.id"
                  class="check-item"
                  @click="handleSelectReviewEdge(edge.id)"
                >
                  <input v-model="edge.keep" type="checkbox" />
                  <span>{{ reviewEdgeLabel(edge) }}</span>
                </label>
              </div>
            </div>

            <div class="approval-footer">
              <label class="detail-body reject-note">
                驳回备注
                <textarea v-model="batchRejectNote" rows="2" placeholder="可选，记录驳回原因"></textarea>
              </label>

              <div class="detail-actions">
                <button @click="approveSelectedBatch" :disabled="!selectedBatchDetail">通过所选内容并入图</button>
                <button class="danger" @click="rejectSelectedBatch" :disabled="!selectedBatchDetail">驳回整批</button>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </section>

    <div v-if="isCreatingNode" class="modal-overlay" @click.self="cancelCreateNode">
      <div class="modal-card">
        <h3>新增节点</h3>
        <p v-if="nodeDialogMessage" class="modal-feedback">{{ nodeDialogMessage }}</p>
        <div class="detail-body">
          <label>
            节点名
            <input v-model="nodeForm.name" placeholder="请输入唯一节点名" @keydown.enter.prevent="submitNode" />
          </label>
          <label>
            描述
            <textarea v-model="nodeForm.desc" rows="4" placeholder="节点描述" @keydown.ctrl.enter.prevent="submitNode"></textarea>
          </label>
          <div class="edge-quick-actions">
            <button class="ghost" type="button" :disabled="isGeneratingNodeDesc" @click="generateNodeDescription">
              {{ isGeneratingNodeDesc ? "生成中..." : "AI 生成描述" }}
            </button>
          </div>
          <div class="detail-actions">
            <button class="ghost" @click="cancelCreateNode">取消</button>
            <button @click="submitNode">确认创建</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isCreatingEdge" class="modal-overlay" @click.self="cancelCreateEdge">
      <div class="modal-card">
        <h3>新增关系</h3>
        <p v-if="edgeDialogMessage" class="modal-feedback">{{ edgeDialogMessage }}</p>
        <div class="detail-body">
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
          <div class="edge-quick-actions">
            <button class="ghost" type="button" @click="swapEdgeDirection">交换起终点</button>
            <button v-if="selectedNode" class="ghost" type="button" @click="useSelectedNodeForEdge('source')">当前节点填入起点</button>
            <button v-if="selectedNode" class="ghost" type="button" @click="useSelectedNodeForEdge('target')">当前节点填入终点</button>
          </div>
          <div class="detail-actions">
            <button class="ghost" @click="cancelCreateEdge">取消</button>
            <button @click="submitEdge">确认创建</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import {
  approvePendingTeacherBatchApi,
  createTeacherEdgeApi,
  createTeacherNodeApi,
  deleteTeacherEdgeApi,
  deleteTeacherNodeApi,
  generateTeacherNodeDescriptionApi,
  getPendingTeacherBatchDetailApi,
  getTeacherGraphApi,
  listPendingTeacherBatchesApi,
  rejectPendingTeacherBatchApi,
  updateTeacherEdgeApi,
  updateTeacherNodeApi,
} from "../api/teacher";
import KnowledgeGraphCanvas from "../components/KnowledgeGraphCanvas.vue";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const keyword = ref("");
const errorMessage = ref("");
const activeMode = ref("graph");
const isGraphLoading = ref(false);
const isGraphSuggesting = ref(false);
const isPendingLoading = ref(false);
const isReviewLoading = ref(false);
const fullGraph = ref({ nodes: [], edges: [] });
const graph = ref({ nodes: [], edges: [] });
const graphSuggestions = ref([]);
const showGraphSuggestions = ref(false);
const pendingBatches = ref([]);
const selectedBatchId = ref("");
const selectedBatchDetail = ref(null);
const batchRejectNote = ref("");

const selectedNodeId = ref("");
const selectedEdgeId = ref("");
const selectedReviewNodeId = ref("");
const selectedReviewEdgeId = ref("");

const graphViewport = ref(null);
const graphCanvas = ref(null);
const reviewCanvas = ref(null);

const isCreatingNode = ref(false);
const isCreatingEdge = ref(false);
const isGeneratingNodeDesc = ref(false);
const nodeDialogMessage = ref("");
const edgeDialogMessage = ref("");
const autoCreatedNodeNames = ref([]);

const nodeForm = reactive({ name: "", desc: "" });
const edgeForm = reactive({ source: "", relation: "DEPENDS_ON", target: "" });
const reviewNodeDrafts = reactive({});
const reviewEdgeDrafts = reactive({});
const edgeNodeSuggestions = reactive({ source: [], target: [] });
const showEdgeNodeDropdown = reactive({ source: false, target: false });

const selectedNode = computed(() => graph.value.nodes.find((node) => node.id === selectedNodeId.value) || null);
const selectedEdge = computed(() => graph.value.edges.find((edge) => edge.id === selectedEdgeId.value) || null);
const autoCreatedNodes = computed(() =>
  autoCreatedNodeNames.value
    .map((name) => graph.value.nodes.find((node) => node.name === name))
    .filter(Boolean),
);
// The review canvas reuses the shared graph component, so pending-batch detail
// is normalized into the same node/edge shape as the formal graph here.
const reviewGraph = computed(() => ({
  nodes: (selectedBatchDetail.value?.nodes || []).map((node) => ({
    id: node.id,
    name: node.name,
    label: node.name,
    desc: node.desc || "",
    status: node.status,
  })),
  edges: (selectedBatchDetail.value?.edges || []).map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    relation: edge.relation,
  })),
}));
const selectedReviewNode = computed(() =>
  (selectedBatchDetail.value?.nodes || []).find((node) => node.id === selectedReviewNodeId.value) || null,
);
const selectedReviewEdge = computed(() =>
  (selectedBatchDetail.value?.edges || []).find((edge) => edge.id === selectedReviewEdgeId.value) || null,
);
const selectedNodeDrafts = computed(() =>
  (selectedBatchDetail.value?.nodes || [])
    .filter((node) => !isContextNode(node))
    .map((node) => reviewNodeDrafts[node.id])
    .filter(Boolean),
);
const selectedEdgeDrafts = computed(() =>
  (selectedBatchDetail.value?.edges || []).map((edge) => reviewEdgeDrafts[edge.id]).filter(Boolean),
);
const editableReviewNode = computed(() => (selectedReviewNode.value ? reviewNodeDrafts[selectedReviewNode.value.id] : null));
const editableReviewEdge = computed(() => (selectedReviewEdge.value ? reviewEdgeDrafts[selectedReviewEdge.value.id] : null));
const isActiveGraphLoading = computed(() => activeMode.value === "graph" ? isGraphLoading.value : isReviewLoading.value);
let graphSuggestTimer = null;
const edgeSearchTimers = { source: null, target: null };

onMounted(async () => {
  await Promise.all([loadGraph(), loadPendingBatches()]);
});

async function loadGraph() {
  isGraphLoading.value = true;
  try {
    const { data } = await getTeacherGraphApi({ keyword: "", limit: 2000 });
    fullGraph.value = data;
    graph.value = data;
  } catch (error) {
    handleApiError(error, "加载图谱失败。");
  } finally {
    isGraphLoading.value = false;
  }
}

async function loadPendingBatches() {
  isPendingLoading.value = true;
  try {
    const { data } = await listPendingTeacherBatchesApi();
    pendingBatches.value = data || [];
    if (selectedBatchId.value && !pendingBatches.value.some((item) => item.id === selectedBatchId.value)) {
      selectedBatchId.value = "";
      selectedBatchDetail.value = null;
      clearReviewSelection();
      if (activeMode.value === "review") {
        activeMode.value = "graph";
      }
    }
    if (!selectedBatchId.value && pendingBatches.value.length) {
      await selectPendingBatch(pendingBatches.value[0].id, { switchModeToReview: false });
    }
  } catch (error) {
    handleApiError(error, "加载候选批次失败。");
  } finally {
    isPendingLoading.value = false;
  }
}

async function selectPendingBatch(batchId, options = {}) {
  const { switchModeToReview = true } = options;
  selectedBatchId.value = batchId;
  clearReviewSelection();
  batchRejectNote.value = "";
  isReviewLoading.value = true;
  try {
    const { data } = await getPendingTeacherBatchDetailApi(batchId);
    selectedBatchDetail.value = data;
    hydrateReviewDrafts(data);
    const firstPendingNode = data.nodes.find((node) => !isContextNode(node));
    if (firstPendingNode) {
      selectedReviewNodeId.value = firstPendingNode.id;
    }
    if (switchModeToReview) {
      activeMode.value = "review";
      await nextTick();
      reviewCanvas.value?.restartLayout?.();
    }
  } catch (error) {
    handleApiError(error, "加载候选批次详情失败。");
  } finally {
    isReviewLoading.value = false;
  }
}

function hydrateReviewDrafts(detail) {
  // Drafts intentionally decouple teacher edits and keep-flags from the raw API
  // payload, which makes partial approval and UI rollbacks much easier to reason about.
  Object.keys(reviewNodeDrafts).forEach((key) => delete reviewNodeDrafts[key]);
  Object.keys(reviewEdgeDrafts).forEach((key) => delete reviewEdgeDrafts[key]);

  (detail.nodes || []).forEach((node) => {
    reviewNodeDrafts[node.id] = {
      id: node.id,
      name: node.name,
      desc: node.desc || "",
      node_type: "",
      keep: node.is_selected_default && !isContextNode(node),
      status: node.status,
      reason: node.reason || "",
    };
  });
  (detail.edges || []).forEach((edge) => {
    reviewEdgeDrafts[edge.id] = {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      relation: edge.relation,
      keep: !!edge.is_selected_default,
    };
  });
}

function switchMode(mode) {
  if (mode === "review" && !selectedBatchDetail.value) return;
  activeMode.value = mode;
  nextTick(() => {
    // Each mode has a different visual layout, so the canvas gets a fresh
    // layout pass after switching to avoid stale viewport sizing.
    if (mode === "graph") {
      graphCanvas.value?.restartLayout?.();
    } else {
      reviewCanvas.value?.restartLayout?.();
    }
  });
}

function isContextNode(node) {
  return node?.status === "context_existing" || node?.status === "anchor_existing";
}

function reviewEdgeLabel(edge) {
  const source = resolveReviewNodeName(edge.source);
  const target = resolveReviewNodeName(edge.target);
  return `${source} -> ${target} (${edge.relation})`;
}

function resolveReviewNodeName(nodeId) {
  const node = (selectedBatchDetail.value?.nodes || []).find((item) => item.id === nodeId);
  return node?.name || nodeId;
}

async function refreshGraph() {
  await Promise.all([loadGraph(), loadPendingBatches()]);
  await nextTick();
  if (activeMode.value === "graph") {
    graphCanvas.value?.restartLayout?.();
  } else {
    reviewCanvas.value?.restartLayout?.();
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

function clearReviewSelection() {
  selectedReviewNodeId.value = "";
  selectedReviewEdgeId.value = "";
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

function handleSelectReviewNode(nodeId) {
  selectedReviewNodeId.value = nodeId;
  selectedReviewEdgeId.value = "";
}

function handleSelectReviewEdge(edgeId) {
  selectedReviewEdgeId.value = edgeId;
  selectedReviewNodeId.value = "";
}

function startCreateNode() {
  isCreatingNode.value = true;
  nodeForm.name = "";
  nodeForm.desc = "";
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
      nodeDialogMessage.value = "节点名不能为空";
    } else {
      errorMessage.value = "节点名不能为空";
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
    await refreshGraph();
    const nextNode = graph.value.nodes.find((node) => node.name === targetName);
    if (nextNode) {
      handleSelectNode(nextNode.id);
      await nextTick();
      graphCanvas.value?.focusNodes?.([nextNode.id]);
    }
  } catch (error) {
    if (isCreatingNode.value) {
      nodeDialogMessage.value = error?.response?.data?.detail || "保存节点失败。";
    } else {
      handleApiError(error, "保存节点失败。");
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
    await refreshGraph();
    if (Array.isArray(result?.created_nodes) && result.created_nodes.length) {
      autoCreatedNodeNames.value = result.created_nodes.map((item) => item.name);
      const labels = result.created_nodes.map((item) =>
        item?.desc_generated ? `${item.name}（已生成描述）` : `${item.name}（描述待补充）`,
      );
      edgeDialogMessage.value = `已自动创建节点：${labels.join("、")}`;
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
    nodeDialogMessage.value = "请先填写节点名，再生成描述。";
    return;
  }
  isGeneratingNodeDesc.value = true;
  nodeDialogMessage.value = "";
  try {
    const { data } = await generateTeacherNodeDescriptionApi({ name });
    nodeForm.desc = String(data?.desc || "").trim();
  } catch (error) {
    nodeDialogMessage.value = error?.response?.data?.detail || "生成节点描述失败。";
  } finally {
    isGeneratingNodeDesc.value = false;
  }
}

async function deleteNode() {
  if (!selectedNode.value) return;
  if (!confirm(`确定删除节点 "${selectedNode.value.name}" 吗？`)) return;
  try {
    await deleteTeacherNodeApi(selectedNode.value.name);
    clearSelection();
    await refreshGraph();
  } catch (error) {
    handleApiError(error, "删除节点失败。");
  }
}

async function deleteEdge() {
  if (!selectedEdge.value) return;
  if (!confirm("确定删除这条关系吗？")) return;
  try {
    await deleteTeacherEdgeApi(selectedEdge.value.edge_key);
    clearSelection();
    await refreshGraph();
  } catch (error) {
    handleApiError(error, "删除关系失败。");
  }
}

async function searchGraph() {
  const query = keyword.value.trim();
  if (!query) {
    graph.value = fullGraph.value;
    clearSelection();
    showGraphSuggestions.value = false;
    return;
  }
  try {
    isGraphLoading.value = true;
    const { data } = await getTeacherGraphApi({ keyword: query, limit: 2000 });
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
    isGraphLoading.value = false;
  }
}

function handleGraphKeywordInput() {
  if (graphSuggestTimer) clearTimeout(graphSuggestTimer);
  const query = keyword.value.trim();
  if (!query) {
    graphSuggestions.value = [];
    showGraphSuggestions.value = false;
    graph.value = fullGraph.value;
    clearSelection();
    return;
  }
  graphSuggestTimer = setTimeout(() => {
    fetchGraphSuggestions(query);
  }, 180);
}

async function fetchGraphSuggestions(query) {
  if (!query || activeMode.value !== "graph") return;
  isGraphSuggesting.value = true;
  try {
    const { data } = await getTeacherGraphApi({ keyword: query, limit: 50 });
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

async function approveSelectedBatch() {
  if (!selectedBatchId.value || !selectedBatchDetail.value) return;
  // The approval payload only carries items still checked in the local drafts,
  // which is how the teacher can partially approve a candidate subgraph.
  const nodes = selectedNodeDrafts.value
    .filter((item) => item.keep)
    .map((item) => ({
      id: item.id,
      name: item.name,
      desc: item.desc,
      node_type: item.node_type || "",
    }));
  if (!nodes.length) {
    errorMessage.value = "至少保留一个待审结点。";
    return;
  }
  const edges = selectedEdgeDrafts.value
    .filter((item) => item.keep)
    .map((item) => ({
      id: item.id,
      source: resolveReviewNodeName(item.source),
      target: resolveReviewNodeName(item.target),
      relation: item.relation,
    }));
  try {
    await approvePendingTeacherBatchApi(selectedBatchId.value, { nodes, edges });
    await loadPendingBatches();
    await loadGraph();
    if (selectedBatchId.value && !pendingBatches.value.some((item) => item.id === selectedBatchId.value)) {
      if (pendingBatches.value.length) {
        await selectPendingBatch(pendingBatches.value[0].id, { switchModeToReview: true });
      } else {
        activeMode.value = "graph";
      }
    }
  } catch (error) {
    handleApiError(error, "通过候选批次失败。");
  }
}

async function rejectSelectedBatch() {
  if (!selectedBatchId.value) return;
  try {
    const rejectedBatchId = selectedBatchId.value;
    await rejectPendingTeacherBatchApi(rejectedBatchId, { note: batchRejectNote.value });
    await loadPendingBatches();
    if (!pendingBatches.value.length) {
      activeMode.value = "graph";
      return;
    }
    const nextBatch = pendingBatches.value.find((item) => item.id !== rejectedBatchId) || pendingBatches.value[0];
    await selectPendingBatch(nextBatch.id, { switchModeToReview: true });
  } catch (error) {
    handleApiError(error, "驳回候选批次失败。");
  }
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
  gap: 22px;
}

.page-header h2 {
  margin: 10px 0 8px;
  font-size: 32px;
  font-weight: 500;
  color: var(--app-text);
}

.eyebrow {
  margin: 0;
  color: #6e86a6;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.page-copy {
  margin: 0;
  color: var(--app-text-muted);
  max-width: 760px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px;
  border: 1px solid var(--app-line);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--app-shadow);
}

.toolbar-search {
  position: relative;
  flex: 1;
  min-width: 260px;
}

.edge-search-box {
  position: relative;
}

.toolbar-input,
.detail-body input,
.detail-body textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--app-line);
  border-radius: 14px;
  background: #fff;
  font: inherit;
}

.toolbar-input {
  min-width: 0;
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
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.98);
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
  border-radius: 12px;
}

button {
  border: none;
  border-radius: 14px;
  padding: 12px 16px;
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

.mode-switch {
  display: inline-flex;
  gap: 8px;
  padding: 6px;
  width: fit-content;
  border: 1px solid #e2ebf4;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.05);
}

.mode-tab {
  min-width: 116px;
  padding: 10px 16px;
  border-radius: 12px;
  background: transparent;
  color: #526b84;
}

.mode-tab.active {
  background: #10283d;
  color: #fff;
}

.graph-mode-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  align-items: start;
}

.review-workbench {
  display: grid;
  gap: 16px;
}

.review-header-strip {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(320px, 0.92fr);
  gap: 14px;
}

.review-mode-layout {
  display: grid;
  grid-template-columns: minmax(0, 0.94fr) minmax(380px, 0.86fr);
  gap: 18px;
  align-items: start;
}

.graph-panel {
  border: 1px solid #e2ebf4;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
  position: relative;
  padding: 16px;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 12px;
}

.formal-panel {
  min-height: 760px;
}

.formal-panel :deep(.graph-canvas) {
  height: 660px;
  min-height: 660px;
}

.review-graph-panel {
  min-height: 590px;
}

.review-graph-panel :deep(.graph-canvas) {
  height: 470px;
  min-height: 470px;
}

.graph-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.graph-panel-head h3 {
  margin: 4px 0 0;
  color: #10283d;
  font-size: 24px;
}

.graph-mode-label {
  margin: 0;
  color: #5b86b3;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.graph-mode-copy {
  max-width: 250px;
  color: #6f8297;
  font-size: 13px;
  line-height: 1.6;
  text-align: right;
}

.graph-state {
  position: absolute;
  inset: 16px;
  top: 88px;
  display: grid;
  place-items: center;
  color: #6f8297;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.88);
  border-radius: 20px;
  z-index: 2;
}

.graph-side-panel {
  display: grid;
  gap: 14px;
  grid-template-rows: auto minmax(440px, 1fr);
}

.review-side-panel {
  min-height: 590px;
  display: grid;
  grid-template-rows: minmax(250px, 0.9fr) minmax(320px, 1.1fr);
  gap: 14px;
}

.panel-card {
  min-height: 0;
  padding: 18px;
  border-radius: 22px;
  background: #f8fbff;
  border: 1px solid #ebf1f7;
  display: grid;
  gap: 12px;
  overflow: hidden;
}

.detail-card {
  grid-template-rows: auto 1fr;
}

.approval-card {
  grid-template-rows: auto 1fr auto;
}

.review-strip-card,
.review-current-card,
.action-card {
  align-content: start;
}

.action-bar {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.action-bar button {
  background: #2563eb;
}

.auto-created-panel {
  display: grid;
  gap: 10px;
  padding-top: 6px;
  border-top: 1px solid #e6edf5;
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

.review-batch-list {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(190px, 220px);
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.batch-chip {
  min-height: 88px;
  text-align: left;
  padding: 12px 14px;
  border: 1px solid #d9e6f3;
  border-radius: 16px;
  background: #ffffff;
  color: #10283d;
  display: grid;
  gap: 6px;
}

.batch-chip.active {
  border-color: #8b5cf6;
  background: #f6f1ff;
}

.batch-chip:hover:not(:disabled) {
  background: #f8fbff;
}

.batch-chip.active:hover:not(:disabled) {
  background: #f6f1ff;
}

.batch-chip small,
.review-meta span {
  color: #6f8297;
  font-size: 12px;
}

.review-current-body {
  display: grid;
  gap: 10px;
  align-content: start;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
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
  gap: 14px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.detail-body label {
  display: grid;
  gap: 8px;
  color: #526b84;
  font-size: 13px;
  font-weight: 500;
}

.detail-body textarea {
  resize: vertical;
}

.detail-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.danger {
  background: #f97316;
}

.danger:hover:not(:disabled) {
  background: #ea580c;
}

.review-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.review-summary-text {
  margin: 4px 0 0;
  color: #5f7287;
  line-height: 1.7;
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.review-checklists {
  display: grid;
  gap: 14px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.checklist-group {
  padding: 14px;
  border: 1px solid #e6edf5;
  border-radius: 16px;
  background: #fff;
  min-height: 0;
  display: grid;
  align-content: start;
  gap: 10px;
}

.sub-head {
  margin-bottom: 8px;
}

.check-item,
.checkbox-row {
  display: flex !important;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.check-item + .check-item {
  margin-top: 10px;
}

.check-item input,
.checkbox-row input {
  width: auto;
}

.reject-note {
  margin-top: 0;
}

.approval-footer {
  display: grid;
  gap: 14px;
  padding-top: 6px;
  border-top: 1px solid #e6edf5;
}

.approval-footer .detail-body {
  overflow: visible;
  padding-right: 0;
}

.empty-detail {
  color: #6f8297;
  line-height: 1.7;
  font-size: 14px;
  text-align: center;
  padding: 20px 0;
}

.empty-detail.compact {
  padding: 8px 0;
}

.feedback.error {
  padding: 18px;
  border-radius: 18px;
  background: #fff8f8;
  color: #b42318;
}

.modal-feedback {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-radius: 14px;
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
  padding: 28px;
  border-radius: 24px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.12);
}

.modal-card h3 {
  margin: 0 0 20px;
  color: #0f2840;
}

@media (max-width: 1200px) {
  .graph-mode-layout,
  .review-header-strip,
  .review-mode-layout {
    grid-template-columns: 1fr;
  }

  .formal-panel {
    min-height: 640px;
  }

  .formal-panel :deep(.graph-canvas) {
    height: 560px;
    min-height: 560px;
  }

  .review-graph-panel {
    min-height: 540px;
  }

  .review-graph-panel :deep(.graph-canvas) {
    height: 440px;
    min-height: 440px;
  }

  .graph-side-panel,
  .review-side-panel {
    min-height: auto;
    grid-template-rows: auto auto;
  }
}

@media (max-width: 720px) {
  .graph-panel-head {
    flex-direction: column;
  }

  .graph-mode-copy {
    max-width: none;
    text-align: left;
  }

  .action-bar {
    grid-template-columns: 1fr;
  }

  .review-batch-list {
    grid-auto-columns: minmax(180px, 78vw);
  }

  .mode-switch {
    width: 100%;
  }

  .mode-tab {
    flex: 1;
  }
}
</style>
