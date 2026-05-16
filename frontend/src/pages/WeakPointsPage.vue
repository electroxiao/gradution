<template>
  <section class="app-page weak-page">
    <PageHeader title="我的薄弱点" />

    <section v-if="isInitialLoading" class="summary-row">
      <article v-for="index in 3" :key="`weak-summary-skeleton-${index}`" class="skeleton-card"></article>
    </section>

    <section v-else class="summary-row">
      <article class="summary-card">
        <span class="summary-icon blue"><TriangleAlert :size="22" aria-hidden="true" /></span>
        <span>当前待掌握</span>
        <strong>{{ weakPoints.length }} <small>个</small></strong>
      </article>
      <article class="summary-card">
        <span class="summary-icon cyan"><History :size="22" aria-hidden="true" /></span>
        <span>历史薄弱点</span>
        <strong>{{ historyWeakPoints.length }} <small>个</small></strong>
      </article>
      <article class="summary-card">
        <span class="summary-icon green"><MessageCircleQuestion :size="22" aria-hidden="true" /></span>
        <span>最近咨询</span>
        <strong>{{ recentConsultations.length }} <small>次</small></strong>
      </article>
    </section>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <div :class="['weak-workbench', { 'training-open': isTrainingLayoutOpen }]">
      <aside class="panel weak-list-panel">
        <header class="weak-list-header">
          <div>
            <h2>待掌握薄弱点</h2>
            <p>{{ filteredWeakPoints.length }} / {{ weakPoints.length }} 个知识点</p>
          </div>
        </header>

        <div :class="['weak-search-control', { expanded: isWeakSearchOpen }]">
          <button type="button" class="weak-search-icon" aria-label="搜索薄弱点" @click="openWeakSearch">
            <Search :size="18" aria-hidden="true" />
          </button>
          <input
            ref="weakSearchInput"
            v-model="weakSearchQuery"
            type="search"
            placeholder="搜索薄弱点"
            aria-label="搜索薄弱点"
            :tabindex="isWeakSearchOpen ? 0 : -1"
            @keydown.esc="closeWeakSearch"
          />
          <button type="button" class="weak-search-clear" aria-label="收起搜索" @click="closeWeakSearch">
            <X :size="16" aria-hidden="true" />
          </button>
        </div>
        <div :class="['weak-search-slot', { expanded: isWeakSearchOpen }]" aria-hidden="true"></div>

        <div v-if="isInitialLoading" class="weak-list-loading">
          <div v-for="index in 5" :key="`weak-list-skeleton-${index}`" class="skeleton-row"></div>
        </div>

        <div v-else-if="filteredWeakPoints.length" class="weak-list">
          <button
            v-for="item in filteredWeakPoints"
            :key="item.id"
            type="button"
            :class="['weak-list-item', { active: item.id === currentWeakPointId }]"
            @click="selectWeakPoint(item)"
          >
            <span class="weak-list-name">{{ item.node_name }}</span>
            <span class="weak-list-meta">最近出现 {{ formatDate(item.last_seen_at) }}</span>
            <span class="weak-list-meta muted">首次记录 {{ formatDate(item.first_seen_at) }}</span>
          </button>
        </div>

        <div v-else class="side-empty">
          <h3>暂无匹配薄弱点</h3>
          <p>{{ weakPoints.length ? "换个关键词试试。" : "完成作业或训练后，这里会出现待掌握知识点。" }}</p>
        </div>
      </aside>

      <section class="graph-section">
        <div class="graph-container">
          <div class="graph-header">
            <h2>知识点掌握情况图谱</h2>
            <div class="legend">
              <span class="legend-item"><span class="legend-dot weak"></span> 薄弱</span>
              <span class="legend-item"><span class="legend-dot recommended"></span> 推荐学习</span>
              <span class="legend-item"><span class="legend-dot mastered"></span> 已掌握</span>
            </div>
          </div>
          <div v-if="isInitialLoading || isGraphLoading" class="skeleton-graph" aria-label="薄弱点图谱加载中"></div>
          <div v-else-if="!graphNodes.length" class="graph-state">当前没有可展示的薄弱点图谱，请先完成作业或训练来记录待掌握知识点。</div>
          <KnowledgeGraphCanvas
            v-else
            ref="graphCanvas"
            :nodes="graphNodes"
            :edges="graphEdges"
            :selected-node-id="selectedNodeId"
            @select-node="handleNodeSelect"
            @clear-selection="selectedNodeId = ''"
          />
        </div>
      </section>

      <div :class="['weak-side-panel-shell', { wide: isSidePanelWide }, sidePanelMotionClass]">
        <Transition name="weak-side-panel" mode="out-in">
          <aside v-if="showQuizPanel" key="quiz-panel" class="panel quiz-panel">
            <header class="quiz-header">
              <h3>薄弱点训练</h3>
              <button class="close-btn" aria-label="关闭训练面板" @click="closeQuizPanel">
                <X :size="18" aria-hidden="true" />
              </button>
            </header>

            <div class="quiz-body">
              <div v-if="quizStep === 'intro'" class="quiz-intro">
                <div class="intro-icon">
                  <span class="icon-circle"><TriangleAlert :size="24" aria-hidden="true" /></span>
                </div>
                <p class="intro-text">
                  是否针对 <strong>【{{ quizNodeName }}】</strong>开始训练？
                </p>
                <div class="intro-actions">
                  <button class="secondary-btn" @click="closeQuizPanel">稍后再说</button>
                  <button class="primary-btn" @click="startQuiz" :disabled="isGenerating">
                    {{ isGenerating ? '准备中...' : '开始训练' }}
                  </button>
                </div>
              </div>

              <div v-else-if="quizStep === 'quiz'" class="quiz-content">
                <div class="quiz-meta">
                  <span class="quiz-badge">题目</span>
                  <span class="quiz-node">{{ quizNodeName }}</span>
                </div>
                <div class="quiz-question">
                  <MarkdownContent :content="quizQuestion" />
                  <span v-if="isGenerating" class="streaming-indicator">正在生成...</span>
                </div>
                <div class="quiz-answer">
                  <textarea
                    v-model="userAnswer"
                    rows="4"
                    placeholder="请输入你的答案..."
                    :disabled="isSubmitting"
                  />
                </div>
                <div class="quiz-actions">
                  <button class="secondary-btn" @click="closeQuizPanel">放弃</button>
                  <button
                    class="primary-btn"
                    @click="submitAnswer"
                    :disabled="isSubmitting || isGenerating || !userAnswer.trim()"
                  >
                    {{ isSubmitting ? '判题中...' : '提交答案' }}
                  </button>
                </div>
              </div>

              <div v-else-if="quizStep === 'result'" class="quiz-result">
                <div v-if="isSubmitting" class="result-icon">
                  <LoaderCircle :size="28" aria-hidden="true" />
                </div>
                <div v-else class="result-icon" :class="isCorrect ? 'correct' : 'incorrect'">
                  <CircleCheck v-if="isCorrect" :size="28" aria-hidden="true" />
                  <CircleX v-else :size="28" aria-hidden="true" />
                </div>
                <h4 class="result-title">{{ isSubmitting ? '判断中...' : (isCorrect ? '回答正确！' : '回答不完全正确') }}</h4>
                <div class="result-feedback">
                  <MarkdownContent :content="feedbackContent" />
                  <span v-if="isSubmitting" class="streaming-indicator">正在生成反馈...</span>
                </div>
                <div v-if="!isSubmitting" class="result-actions">
                  <button class="secondary-btn" @click="resetQuiz">再来一题</button>
                  <button class="primary-btn" @click="handleComplete">
                    {{ isCorrect ? '完成' : '我知道了' }}
                  </button>
                </div>
              </div>
            </div>
          </aside>

          <aside v-else-if="currentWeakPointId" key="recommendation-panel" class="panel recommendation-panel">
            <header class="recommendation-header">
              <h3>{{ currentWeakPointName || "当前暂无薄弱点" }}</h3>
            </header>

            <template v-if="learningOrder.length">
              <p class="recommendation-summary">
                {{ recommendationSummary || "系统正在围绕当前薄弱点收敛推荐学习顺序。" }}
              </p>

              <p class="recommendation-tip">完成全部推荐结点的学习后，当前薄弱点会自动转为已掌握并进入历史记录。</p>

              <div class="recommendation-block">
                <span class="recommendation-label">推荐顺序</span>
                <ol class="learning-order">
                  <li v-for="item in learningOrder" :key="item">{{ item }}</li>
                </ol>
              </div>

              <div v-if="recommendedNodes.length" class="recommendation-block">
                <span class="recommendation-label">推荐理由</span>
                <ul class="recommendation-list">
                  <li v-for="item in recommendedNodes" :key="item.id">
                    <strong>{{ item.name }}</strong>
                    <p>{{ item.reason || "这是当前阶段最值得优先补齐的相关知识点。" }}</p>
                  </li>
                </ul>
              </div>
            </template>

            <div v-else class="side-empty">
              <h3>等待推荐</h3>
              <p>选择左侧薄弱点后，系统会展示推荐学习顺序和训练入口。</p>
            </div>
          </aside>

          <aside v-else key="empty-recommendation-panel" class="panel recommendation-panel">
            <div class="side-empty">
              <h3>选择薄弱点</h3>
              <p>从左侧列表选择一个知识点，查看图谱和推荐训练。</p>
            </div>
          </aside>
        </Transition>
      </div>
    </div>

    <section v-if="recentConsultations.length || historyWeakPoints.length" class="panel records-section">
      <div class="records-header">
        <div>
          <h2>学习记录</h2>
        </div>
        <div class="record-tabs" role="tablist" aria-label="学习记录类型">
          <button
            type="button"
            :class="{ active: activeRecordTab === 'consultations' }"
            role="tab"
            :aria-selected="activeRecordTab === 'consultations'"
            @click="activeRecordTab = 'consultations'"
          >
            最近咨询
          </button>
          <button
            type="button"
            :class="{ active: activeRecordTab === 'history' }"
            role="tab"
            :aria-selected="activeRecordTab === 'history'"
            @click="activeRecordTab = 'history'"
          >
            历史薄弱点
          </button>
        </div>
      </div>

      <div v-if="activeRecordTab === 'consultations'" class="record-list">
        <article v-for="item in recentConsultations" :key="item.id" class="history-card consultation-card">
          <div class="history-card-top">
            <span class="history-badge">咨询</span>
            <span class="history-time">{{ formatDate(item.created_at) }}</span>
          </div>
          <h3>{{ item.node_name }}</h3>
        </article>
        <div v-if="!recentConsultations.length" class="record-empty">暂无最近咨询记录。</div>
      </div>

      <div v-else class="record-list">
        <article v-for="item in historyWeakPoints" :key="`history-${item.id}`" class="history-card">
          <div class="history-card-top">
            <span class="history-badge">已掌握</span>
            <span class="history-time">最近更新 {{ formatDate(item.last_seen_at) }}</span>
          </div>
          <h3>{{ item.node_name }}</h3>
          <span class="weak-first-seen">首次记录 {{ formatDate(item.first_seen_at) }}</span>
        </article>
        <div v-if="!historyWeakPoints.length" class="record-empty">暂无历史薄弱点。</div>
      </div>
    </section>

    <section v-else-if="!isInitialLoading && !errorMessage && !graphNodes.length" class="panel empty-state">
      <div class="empty-orbit" />
      <h2>当前没有待补齐的薄弱点</h2>
      <p>聊天会记录最近咨询过的知识点；作业和训练结果会记录真正需要攻克的薄弱点。</p>
      <router-link class="empty-link" to="/chat">去聊天页继续提问</router-link>
    </section>
  </section>
</template>

<script setup>
import { CircleCheck, CircleX, History, LoaderCircle, MessageCircleQuestion, Search, TriangleAlert, X } from "lucide-vue-next";
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  getWeakPointsGraphApi,
  listWeakPointHistoryApi,
  listWeakPointsApi,
  markMasteredApi,
} from "../api/weakPoints";
import { listRecentConsultationsApi } from "../api/chat";
import PageHeader from "../components/PageHeader.vue";
import { streamGenerateQuizApi, streamSubmitAnswerApi } from "../api/quiz";
import KnowledgeGraphCanvas from "../components/KnowledgeGraphCanvas.vue";
import MarkdownContent from "../components/MarkdownContent.vue";
import { findGraphNodeById, markGraphNodeMastered } from "../features/weak-points/graphState";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const weakPoints = ref([]);
const historyWeakPoints = ref([]);
const recentConsultations = ref([]);
const weakSearchQuery = ref("");
const isWeakSearchOpen = ref(false);
const weakSearchInput = ref(null);
const activeRecordTab = ref("consultations");
const errorMessage = ref("");
const graphNodes = ref([]);
const graphEdges = ref([]);
const selectedNodeId = ref("");
const currentWeakPointId = ref(null);
const currentWeakPointName = ref("");
const isInitialLoading = ref(true);
const isGraphLoading = ref(false);
const graphCanvas = ref(null);
const recommendationSummary = ref("");
const learningOrder = ref([]);
const recommendedNodes = ref([]);
const graphCache = new Map();
const graphRequests = new Map();
let graphPrefetchTimer = null;
let graphCacheVersion = 0;
const GRAPH_PREFETCH_CONCURRENCY = 3;
const SIDE_PANEL_VISUAL_TRANSITION_MS = 180;

const showQuizPanel = ref(false);
const isTrainingLayoutOpen = ref(false);
const isSidePanelWide = ref(false);
const sidePanelMotionClass = ref("");
const quizNodeId = ref("");
const quizNodeName = ref("");
const quizStep = ref("intro");
const quizQuestion = ref("");
const userAnswer = ref("");
const feedbackContent = ref("");
const isCorrect = ref(false);
const isGenerating = ref(false);
const isSubmitting = ref(false);
let quizPanelCloseTimer = null;
let sidePanelMotionTimer = null;

const filteredWeakPoints = computed(() => {
  const keyword = weakSearchQuery.value.trim().toLowerCase();
  const items = keyword
    ? weakPoints.value.filter((item) => item.node_name?.toLowerCase().includes(keyword))
    : [...weakPoints.value];

  return items.sort((left, right) => compareDateDesc(left.last_seen_at, right.last_seen_at));
});

onMounted(async () => {
  try {
    const historyPromise = loadWeakPointHistory();
    const consultationPromise = loadRecentConsultations();
    await loadWeakPoints();
    const graphPromise = loadGraph();
    scheduleGraphPrefetch();
    await Promise.allSettled([historyPromise, graphPromise, consultationPromise]);
  } finally {
    isInitialLoading.value = false;
  }
});

onBeforeUnmount(() => {
  if (graphPrefetchTimer) {
    clearTimeout(graphPrefetchTimer);
  }
  clearQuizPanelCloseTimer();
  clearSidePanelMotionTimer();
});

async function loadWeakPoints(options = {}) {
  const preferredId = options.preferredId ?? currentWeakPointId.value;
  try {
    const { data } = await listWeakPointsApi();
    weakPoints.value = data;
    if (!weakPoints.value.length) {
      currentWeakPointId.value = null;
      currentWeakPointName.value = "";
      return;
    }
    const hasPreferred = weakPoints.value.some((item) => item.id === preferredId);
    const activeItem = hasPreferred
      ? weakPoints.value.find((item) => item.id === preferredId)
      : weakPoints.value[0];
    currentWeakPointId.value = activeItem?.id ?? null;
    currentWeakPointName.value = activeItem?.node_name ?? "";
  } catch (error) {
    handleApiError(error, "加载薄弱点失败。");
  }
}

async function loadWeakPointHistory() {
  try {
    const { data } = await listWeakPointHistoryApi();
    historyWeakPoints.value = data || [];
  } catch (error) {
    handleApiError(error, "加载历史薄弱点失败。");
  }
}

async function loadRecentConsultations() {
  try {
    const { data } = await listRecentConsultationsApi(12);
    recentConsultations.value = data || [];
  } catch (error) {
    handleApiError(error, "加载最近咨询记录失败。");
  }
}

async function loadGraph(nodeId = currentWeakPointId.value) {
  if (!nodeId) {
    graphNodes.value = [];
    graphEdges.value = [];
    learningOrder.value = [];
    recommendationSummary.value = "";
    recommendedNodes.value = [];
    selectedNodeId.value = "";
    return;
  }

  const cachedGraph = graphCache.get(nodeId);
  if (cachedGraph) {
    applyGraphData(cachedGraph);
    await restartGraphCanvas();
    return;
  }

  isGraphLoading.value = true;
  try {
    const data = await fetchGraphData(nodeId);
    applyGraphData(data);
    await restartGraphCanvas();
  } catch (error) {
    console.error("加载图谱失败:", error);
    handleApiError(error, "加载图谱失败。");
  } finally {
    isGraphLoading.value = false;
  }
}

async function fetchGraphData(nodeId) {
  if (graphCache.has(nodeId)) {
    return graphCache.get(nodeId);
  }
  if (graphRequests.has(nodeId)) {
    return graphRequests.get(nodeId);
  }

  const requestVersion = graphCacheVersion;
  const request = getWeakPointsGraphApi(nodeId)
    .then(({ data }) => {
      if (requestVersion === graphCacheVersion) {
        graphCache.set(nodeId, data);
      }
      return data;
    })
    .finally(() => {
      graphRequests.delete(nodeId);
    });
  graphRequests.set(nodeId, request);
  return request;
}

function applyGraphData(data = {}) {
  graphNodes.value = data.nodes || [];
  graphEdges.value = data.edges || [];
  learningOrder.value = data.learning_order || [];
  recommendationSummary.value = data.summary || "";
  recommendedNodes.value = data.recommended_nodes || [];
  currentWeakPointName.value = data.target?.name || currentWeakPointName.value;
  selectedNodeId.value = data.target?.id || "";
}

async function restartGraphCanvas() {
  await nextTick();
  if (graphCanvas.value && graphNodes.value.length) {
    graphCanvas.value.restartLayout?.();
  }
}

function scheduleGraphPrefetch() {
  if (graphPrefetchTimer) {
    clearTimeout(graphPrefetchTimer);
  }

  graphPrefetchTimer = setTimeout(async () => {
    const prefetchItems = weakPoints.value.filter(
      (item) => item?.id && item.id !== currentWeakPointId.value && !graphCache.has(item.id)
    );

    for (let index = 0; index < prefetchItems.length; index += GRAPH_PREFETCH_CONCURRENCY) {
      const batch = prefetchItems.slice(index, index + GRAPH_PREFETCH_CONCURRENCY);
      await Promise.allSettled(
        batch.map((item) =>
          fetchGraphData(item.id).catch((error) => {
            console.debug("预加载薄弱点图谱失败:", error);
            throw error;
          })
        )
      );
    }
  }, 250);
}

function clearGraphCache() {
  graphCacheVersion += 1;
  graphCache.clear();
  graphRequests.clear();
}

async function selectWeakPoint(item) {
  if (!item || item.id === currentWeakPointId.value) return;
  currentWeakPointId.value = item.id;
  currentWeakPointName.value = item.node_name;
  selectedNodeId.value = "";
  closeQuizPanel();
  await loadGraph(item.id);
}

function handleNodeSelect(nodeId) {
  selectedNodeId.value = nodeId;
  const node = findGraphNodeById(graphNodes.value, nodeId);
  if (!node || !["recommended", "mastered"].includes(node.status)) return;
  clearQuizPanelCloseTimer();
  startSidePanelMotion("motion-opening");
  quizNodeId.value = nodeId;
  quizNodeName.value = node.name || nodeId;
  isTrainingLayoutOpen.value = true;
  isSidePanelWide.value = true;
  showQuizPanel.value = true;
  quizStep.value = "intro";
  quizQuestion.value = "";
  userAnswer.value = "";
  feedbackContent.value = "";
}

function closeQuizPanel() {
  clearQuizPanelCloseTimer();
  startSidePanelMotion("motion-closing");
  isSidePanelWide.value = false;
  showQuizPanel.value = false;
  isTrainingLayoutOpen.value = false;
  quizPanelCloseTimer = setTimeout(() => {
    resetQuizPanelState();
    quizPanelCloseTimer = null;
  }, SIDE_PANEL_VISUAL_TRANSITION_MS);
}

function clearQuizPanelCloseTimer() {
  if (!quizPanelCloseTimer) return;
  clearTimeout(quizPanelCloseTimer);
  quizPanelCloseTimer = null;
}

function startSidePanelMotion(className) {
  clearSidePanelMotionTimer();
  sidePanelMotionClass.value = className;
  sidePanelMotionTimer = setTimeout(() => {
    sidePanelMotionClass.value = "";
    sidePanelMotionTimer = null;
  }, SIDE_PANEL_VISUAL_TRANSITION_MS);
}

function clearSidePanelMotionTimer() {
  if (!sidePanelMotionTimer) return;
  clearTimeout(sidePanelMotionTimer);
  sidePanelMotionTimer = null;
}

function resetQuizPanelState() {
  quizNodeId.value = "";
  quizNodeName.value = "";
  quizStep.value = "intro";
  quizQuestion.value = "";
  userAnswer.value = "";
  feedbackContent.value = "";
}

async function startQuiz() {
  isGenerating.value = true;
  quizQuestion.value = "";
  quizStep.value = "quiz";

  try {
    await streamGenerateQuizApi(quizNodeId.value, (chunk) => {
      quizQuestion.value += chunk;
    });
  } catch (error) {
    console.error("生成题目失败:", error);
    quizQuestion.value = "生成题目失败，请稍后重试。";
  } finally {
    isGenerating.value = false;
  }
}

async function submitAnswer() {
  if (!userAnswer.value.trim() || isGenerating.value) return;

  isSubmitting.value = true;
  feedbackContent.value = "";
  quizStep.value = "result";

  try {
    await streamSubmitAnswerApi(
      quizNodeId.value,
      quizQuestion.value,
      userAnswer.value,
      {
        onFeedbackDelta: (content) => {
          feedbackContent.value += content;
        },
        onResult: (data) => {
          isCorrect.value = data.is_correct;
          if (data.mastered) {
            handleMastered(quizNodeId.value);
          }
        },
        onDone: () => {
          isSubmitting.value = false;
        },
      }
    );
  } catch (error) {
    console.error("提交答案失败:", error);
    feedbackContent.value = "判题过程出错，请稍后重试。";
    isCorrect.value = false;
  } finally {
    isSubmitting.value = false;
  }
}

function resetQuiz() {
  quizStep.value = "intro";
  quizQuestion.value = "";
  userAnswer.value = "";
  feedbackContent.value = "";
  isCorrect.value = false;
}

async function handleMastered(nodeId) {
  markGraphNodeMastered(graphNodes.value, nodeId);
  const recommended = recommendedNodes.value.find((item) => String(item.id) === String(nodeId));
  if (recommended) {
    recommended.status = "mastered";
  }
  if (recommended && shouldAutoArchiveCurrentWeakPoint()) {
    await completeCurrentWeakPoint();
  }
}

async function handleComplete() {
  if (isCorrect.value) {
    await handleMastered(quizNodeId.value);
  }
  closeQuizPanel();
}

function formatDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  });
}

async function openWeakSearch() {
  isWeakSearchOpen.value = true;
  await nextTick();
  weakSearchInput.value?.focus();
}

function closeWeakSearch() {
  weakSearchQuery.value = "";
  isWeakSearchOpen.value = false;
}

function compareDateDesc(leftValue, rightValue) {
  const leftTime = new Date(leftValue || 0).getTime() || 0;
  const rightTime = new Date(rightValue || 0).getTime() || 0;
  return rightTime - leftTime;
}

function shouldAutoArchiveCurrentWeakPoint() {
  if (!currentWeakPointId.value || !recommendedNodes.value.length) return false;
  return recommendedNodes.value.every((item) => item.status === "mastered");
}

async function completeCurrentWeakPoint() {
  if (!currentWeakPointId.value) return;
  await markMasteredApi(currentWeakPointId.value);
  clearGraphCache();
  await Promise.all([
    loadWeakPoints({ preferredId: null }),
    loadWeakPointHistory(),
  ]);
  await loadGraph();
  scheduleGraphPrefetch();
  closeQuizPanel();
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
.weak-page {
  gap: 14px;
  font-size: var(--compact-body);
}

.empty-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--compact-control-height);
  padding: 0 12px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-md);
  background: #fff;
  color: #31445f;
  text-decoration: none;
  cursor: pointer;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card,
.panel {
  border: 1px solid var(--app-line);
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.summary-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  column-gap: 14px;
  row-gap: 6px;
  min-height: 98px;
  padding: 18px;
}

.summary-row > .skeleton-card {
  min-height: 98px;
}

.summary-card strong {
  display: block;
  grid-column: 2;
  color: var(--app-text);
  font-size: 25px;
  font-weight: 600;
  line-height: 1;
}

.summary-card small {
  color: var(--app-text);
  font-size: 14px;
  font-weight: 500;
}

.summary-card > span:not(.summary-icon) {
  grid-column: 2;
  color: #334155;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.2;
}

.summary-icon {
  grid-row: 1 / 3;
  width: 48px;
  height: 48px;
  display: inline-grid;
  place-items: center;
  border-radius: 12px;
  flex-shrink: 0;
}

.summary-icon.blue {
  background: #edf3ff;
  color: var(--app-primary);
}

.summary-icon.cyan {
  background: #e8fbfb;
  color: #0e9384;
}

.summary-icon.green {
  background: #eaf8ef;
  color: #229954;
}

.panel {
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.feedback {
  margin: 0;
  padding: 11px 13px;
}

.feedback.error {
  background: #fff5f5;
  color: #b42318;
  border: 1px solid #f0d3d3;
}

.weak-workbench {
  display: grid;
  grid-template-columns: minmax(220px, 0.7fr) minmax(420px, 1.8fr) minmax(280px, auto);
  gap: 14px;
  align-items: start;
}

.weak-workbench.training-open {
  grid-template-columns: minmax(220px, 0.62fr) minmax(340px, 1fr) minmax(380px, auto);
}

.weak-list-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 500px;
  min-width: 0;
  padding: 14px;
}

.weak-list-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding-right: 46px;
}

.weak-list-header > div {
  min-width: 0;
}

.weak-search-control {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 2;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 0;
  align-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid #dce6f2;
  border-radius: 10px;
  background: #ffffff;
  color: #61748a;
  box-shadow: none;
  overflow: hidden;
  transition:
    top 0.26s cubic-bezier(0.2, 0.8, 0.2, 1),
    right 0.26s cubic-bezier(0.2, 0.8, 0.2, 1),
    width 0.26s cubic-bezier(0.2, 0.8, 0.2, 1),
    border-color 0.18s ease,
    background 0.18s ease;
  will-change: top, right, width;
}

.weak-search-control.expanded {
  grid-template-columns: 34px minmax(0, 1fr) 28px;
  top: 66px;
  right: 14px;
  width: calc(100% - 28px);
  border-color: #c8d8ec;
}

.weak-search-slot {
  height: 0;
  margin-bottom: 0;
  transition:
    height 0.26s cubic-bezier(0.2, 0.8, 0.2, 1),
    margin-bottom 0.26s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.weak-search-slot.expanded {
  height: 34px;
  margin-bottom: 12px;
}

.weak-search-icon,
.weak-search-clear {
  display: inline-grid;
  place-items: center;
  width: 100%;
  height: 100%;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  transition: color 0.18s ease, opacity 0.18s ease, transform 0.18s ease;
}

.weak-search-control:hover {
  border-color: #b9cce4;
  background: #f6faff;
  color: #2f67f6;
}

.weak-search-icon:active,
.weak-search-clear:active {
  transform: scale(0.96);
}

.weak-search-control input {
  appearance: none;
  min-width: 0;
  width: 100%;
  height: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--app-text);
  opacity: 0;
  pointer-events: none;
  box-shadow: none;
  transition: opacity 0.16s ease 0.08s;
}

.weak-search-control.expanded input {
  opacity: 1;
  pointer-events: auto;
}

.weak-search-control input:focus {
  outline: none;
  box-shadow: none;
}

.weak-search-control .weak-search-clear {
  width: 28px;
  opacity: 0;
  pointer-events: none;
}

.weak-search-control.expanded .weak-search-clear {
  opacity: 1;
  pointer-events: auto;
}

.weak-list-header h2,
.records-header h2,
.graph-header h2,
.recommendation-header h3,
.quiz-header h3,
.empty-state h2 {
  margin: 0;
  color: var(--app-text);
  font-weight: 500;
}

.weak-list-header h2,
.records-header h2,
.graph-header h2,
.recommendation-header h3,
.empty-state h2 {
  font-size: var(--compact-section-title);
}

.weak-list-header p,
.records-header p {
  margin: 4px 0 0;
  color: var(--app-text-muted);
  line-height: 1.5;
}

.weak-list-loading,
.weak-list {
  min-height: 0;
}

.weak-list-loading {
  display: grid;
  flex: 1;
  gap: 8px;
  overflow: hidden;
}

.weak-list-loading .skeleton-row {
  min-height: 71px;
  border-radius: 12px;
}

.weak-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  padding-right: 2px;
  scrollbar-width: thin;
  scrollbar-color: #c7d7e8 transparent;
}

.weak-list-item {
  display: grid;
  gap: 5px;
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #e8eef6;
  border-radius: 12px;
  background: #ffffff;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.weak-list-item:hover {
  border-color: #ccdbef;
  background: #f8fbff;
}

.weak-list-item.active {
  border-color: #93b4e7;
  background: #edf5ff;
}

.weak-list-name {
  color: var(--app-text);
  font-size: 15px;
  line-height: 1.35;
}

.weak-list-meta {
  color: #708295;
  font-size: 12px;
  line-height: 1.35;
}

.weak-list-meta.muted {
  color: #9aa8b7;
}

.side-empty {
  display: grid;
  place-items: center;
  align-content: center;
  min-height: 180px;
  padding: 18px;
  color: var(--app-text-muted);
  text-align: center;
}

.side-empty h3 {
  margin: 0 0 8px;
  color: var(--app-text);
  font-size: 16px;
  font-weight: 500;
}

.side-empty p {
  margin: 0;
  line-height: 1.6;
}

.graph-section {
  min-width: 0;
}

.graph-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  flex-wrap: wrap;
  gap: 12px;
  background: #ffffff;
  backdrop-filter: blur(6px);
  border-radius: 12px 12px 0 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.quiz-header h3 {
  font-size: 16px;
}

.legend {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--app-text-muted);
  font-size: var(--compact-caption);
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-dot.weak {
  background: #ef4444;
}

.legend-dot.recommended {
  background: #2563eb;
}

.legend-dot.mastered {
  background: #22c55e;
}

.graph-container {
  position: relative;
  height: 500px;
  border: 1px solid var(--app-line);
  border-radius: 12px;
  background: #ffffff;
  box-shadow: var(--app-shadow);
  overflow: hidden;
}

.graph-container :deep(.graph-canvas) {
  height: 100%;
  min-height: 0;
}

.graph-container .skeleton-graph {
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 0;
  border-radius: 12px;
  box-shadow: none;
}

.graph-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #6f8297;
  font-size: 14px;
  background: #ffffff;
  border-radius: 12px;
  z-index: 2;
}

.quiz-panel,
.recommendation-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 500px;
  overflow-y: auto;
}

.weak-side-panel-shell {
  justify-self: end;
  width: 280px;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.weak-side-panel-shell.wide {
  width: 380px;
}

.weak-side-panel-shell > .panel {
  width: 100%;
  min-height: 0;
  overflow: hidden;
}

.weak-side-panel-shell.motion-opening > .panel {
  transform-origin: right center;
  animation: weak-panel-open 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.weak-side-panel-shell.motion-closing > .panel {
  transform-origin: right center;
  animation: weak-panel-close 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

@keyframes weak-panel-open {
  from {
    clip-path: inset(0 0 0 100px);
    transform: translateX(10px);
  }
  to {
    clip-path: inset(0 0 0 0);
    transform: translateX(0);
  }
}

@keyframes weak-panel-close {
  from {
    clip-path: inset(0 0 0 0);
    transform: translateX(0);
  }
  to {
    clip-path: inset(0 0 0 24px);
    transform: translateX(10px);
  }
}

.recommendation-panel {
  padding: 16px;
  gap: 12px;
  scrollbar-width: thin;
  scrollbar-color: #c7d7e8 transparent;
}

.recommendation-panel::-webkit-scrollbar {
  width: 10px;
}

.recommendation-panel::-webkit-scrollbar-track {
  background: transparent;
}

.recommendation-panel::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(147, 175, 204, 0.78), rgba(118, 147, 178, 0.9));
  border: 3px solid transparent;
  border-radius: 999px;
  background-clip: content-box;
}

.recommendation-panel::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, rgba(118, 147, 178, 0.95), rgba(92, 124, 156, 0.98));
  border: 3px solid transparent;
  background-clip: content-box;
}

.recommendation-header h3 {
  font-size: var(--compact-section-title);
}

.recommendation-summary {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
  line-height: 1.55;
}

.recommendation-tip {
  margin: -4px 0 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f3f8ff;
  color: #49657f;
  line-height: 1.45;
  font-size: 13px;
}

.recommendation-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recommendation-label {
  color: var(--app-text-muted);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.learning-order {
  margin: 0;
  padding-left: 18px;
  color: #10283d;
  display: grid;
  gap: 8px;
}

.learning-order li {
  line-height: 1.6;
}

.recommendation-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.recommendation-list li {
  padding: 10px;
  border: 1px solid #e8eef6;
  border-radius: var(--app-radius-lg);
  background: #ffffff;
}

.recommendation-list strong {
  display: block;
  color: var(--app-text);
  margin-bottom: 6px;
  font-weight: 500;
}

.recommendation-list p,
.recommendation-empty {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
  line-height: 1.5;
}

.quiz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--app-line);
}

.quiz-header h3 {
  font-size: var(--compact-section-title);
}

.close-btn {
  border: none;
  background: none;
  font-size: 22px;
  color: #94a3b8;
  cursor: pointer;
  line-height: 1;
}

.close-btn:hover {
  color: #64748b;
}

.quiz-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
}

.quiz-intro {
  text-align: center;
  padding: 20px 0;
}

.intro-icon {
  margin-bottom: 16px;
}

.icon-circle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #fef3c7;
  color: #f59e0b;
  font-size: 24px;
  font-weight: 500;
}

.intro-text {
  margin: 0 0 20px;
  color: #1e293b;
  font-size: 15px;
  line-height: 1.7;
}

.intro-text strong {
  color: #ef4444;
  font-weight: 500;
}

.intro-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.primary-btn,
.secondary-btn {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: var(--compact-body);
  cursor: pointer;
  transition: all 0.2s;
}

.primary-btn {
  border: none;
  background: #2563eb;
  color: #ffffff;
}

.primary-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn {
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #64748b;
}

.secondary-btn:hover {
  background: #f8fafc;
}

.quiz-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.quiz-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.quiz-badge {
  padding: 4px 10px;
  border-radius: 999px;
  background: #edf5ff;
  color: #34699a;
  font-size: 12px;
  font-weight: 500;
}

.quiz-node {
  color: #64748b;
  font-size: 13px;
}

.quiz-question {
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
  position: relative;
}

.streaming-indicator {
  display: inline-block;
  margin-left: 8px;
  color: #2563eb;
  font-size: 12px;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.quiz-answer textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  min-height: 80px;
}

.quiz-answer textarea:focus {
  outline: none;
  border-color: #2563eb;
}

.quiz-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.quiz-result {
  text-align: center;
}

.result-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  font-size: 28px;
  font-weight: 500;
  margin-bottom: 12px;
}

.result-icon.correct {
  background: #dcfce7;
  color: #22c55e;
}

.result-icon.incorrect {
  background: #fee2e2;
  color: #ef4444;
}

.result-title {
  margin: 0 0 16px;
  color: #10283d;
  font-size: 18px;
  font-weight: 500;
}

.result-feedback {
  padding: 16px;
  border-radius: 8px;
  background: #f8fafc;
  text-align: left;
  margin-bottom: 16px;
  min-height: 80px;
}

.result-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.records-section {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.records-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.record-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--app-line);
  border-radius: 12px;
  background: #f7f9fc;
}

.record-tabs button {
  min-height: 30px;
  padding: 0 12px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: var(--app-text-muted);
  cursor: pointer;
}

.record-tabs button.active {
  background: #ffffff;
  color: var(--app-text);
  box-shadow: var(--app-shadow);
}

.record-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  max-height: 250px;
  overflow-y: auto;
  padding-right: 2px;
}

.record-empty {
  grid-column: 1 / -1;
  padding: 18px;
  border: 1px dashed #dfe6ef;
  border-radius: 12px;
  color: var(--app-text-muted);
  text-align: center;
}

.consultation-card {
  border-color: #dbeafe;
}

.weak-first-seen {
  color: #8394a7;
  font-size: 12px;
}

.history-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 14px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: #ffffff;
  box-shadow: var(--app-shadow);
}

.history-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  background: #e8f8ee;
  color: #20854e;
  font-size: 12px;
  font-weight: 400;
}

.history-time {
  color: #8394a7;
  font-size: 12px;
}

.history-card h3 {
  margin: 12px 0 6px;
  color: var(--app-text);
  font-size: var(--compact-card-title);
  font-weight: 400;
}

.empty-state {
  position: relative;
  overflow: hidden;
  padding: 36px 18px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: #ffffff;
  text-align: center;
  box-shadow: var(--app-shadow);
}

.empty-orbit {
  position: absolute;
  top: -42px;
  left: 50%;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: rgba(181, 214, 255, 0.2);
  transform: translateX(-50%);
  filter: blur(16px);
}

.empty-state h2 {
  position: relative;
  margin: 0 0 12px;
  color: var(--app-text);
  font-weight: 500;
}

.empty-state p {
  position: relative;
  max-width: 560px;
  margin: 0 auto 22px;
  color: var(--app-text-muted);
  line-height: 1.7;
}

@media (max-width: 1180px) {
  .weak-workbench,
  .weak-workbench.training-open {
    grid-template-columns: minmax(220px, 0.8fr) minmax(0, 1.5fr);
  }

  .quiz-panel,
  .recommendation-panel {
    grid-column: 1 / -1;
    height: auto;
    max-height: 360px;
  }
}

@media (max-width: 860px) {
  .summary-row {
    grid-template-columns: repeat(2, minmax(150px, 1fr));
  }

  .weak-workbench,
  .weak-workbench.training-open {
    grid-template-columns: 1fr;
  }

  .weak-list-panel,
  .graph-container {
    height: 420px;
  }

  .graph-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 680px) {
  .summary-row {
    grid-template-columns: 1fr;
  }

  .weak-list-panel,
  .graph-container {
    height: 380px;
  }

  .records-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .record-tabs {
    width: 100%;
  }

  .record-tabs button {
    flex: 1;
  }

  .graph-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

</style>
