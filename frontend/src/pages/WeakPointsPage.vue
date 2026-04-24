<template>
  <section class="app-page weak-page">
    <header class="dashboard-hero">
      <div class="app-header-copy">
        <h1 class="app-title">我的薄弱点</h1>
        <p class="app-subtitle">系统会根据已选路径收敛出最值得优先补齐的 1 到 2 个核心节点，帮助你把复习重点压缩到真正关键的地方。</p>
      </div>
    </header>

    <section class="summary-row">
      <article class="summary-card">
        <span class="summary-dot blue" />
        <span>当前待掌握</span>
        <strong>{{ weakPoints.length }}</strong>
      </article>
      <article class="summary-card">
        <span class="summary-dot cyan" />
        <span>历史薄弱点</span>
        <strong>{{ historyWeakPoints.length }}</strong>
      </article>
    </section>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <div class="weak-grid-layout">
      <section class="graph-section">
        <div class="graph-header">
          <h2>知识点掌握情况图谱</h2>
          <div class="legend">
            <span class="legend-item"><span class="legend-dot weak"></span> 薄弱</span>
            <span class="legend-item"><span class="legend-dot recommended"></span> 推荐学习</span>
            <span class="legend-item"><span class="legend-dot pending"></span> 待审核</span>
            <span class="legend-item"><span class="legend-dot mastered"></span> 已掌握</span>
          </div>
        </div>
        <div class="graph-container">
          <div v-if="isGraphLoading" class="graph-state">图谱加载中...</div>
          <div v-else-if="!graphNodes.length" class="graph-state">当前没有可展示的知识图谱节点，请先在聊天页面提问以记录薄弱点。</div>
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

      <aside v-if="showQuizPanel" class="panel quiz-panel">
        <header class="quiz-header">
          <h3>薄弱点训练</h3>
          <button class="close-btn" @click="closeQuizPanel">&times;</button>
        </header>

        <div class="quiz-body">
          <div v-if="quizStep === 'intro'" class="quiz-intro">
            <div class="intro-icon">
              <span class="icon-circle">!</span>
            </div>
            <p class="intro-text">
              是否针对 <strong>【{{ quizNodeName }}】</strong>开始训练？
            </p>
            <p v-if="quizNodeStatus === 'pending'" class="quiz-pending-tip">
              这是待教师确认的候选知识点。本次训练只用于辅助学习，不会计入正式掌握状态。
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
              <span v-if="quizNodeStatus === 'pending'" class="quiz-pending-badge">候选知识点</span>
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
              ⏳
            </div>
            <div v-else class="result-icon" :class="isCorrect ? 'correct' : 'incorrect'">
              {{ isCorrect ? '✓' : '✗' }}
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

      <aside v-else-if="currentWeakPointId" class="panel recommendation-panel">
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

          <div v-if="pendingNodes.length" class="recommendation-block">
            <span class="recommendation-label">待教师确认的新结点</span>
            <ul class="recommendation-list pending-list">
              <li v-for="item in pendingNodes" :key="item.id">
                <strong>{{ item.name }}</strong>
                <p>{{ item.reason || "当前图谱里暂时没有更合适的已有结点，系统已提交教师审核。" }}</p>
              </li>
            </ul>
          </div>
        </template>

        <p v-else class="recommendation-empty">
          当前还没有足够的候选结点，先围绕这个薄弱点进行针对性训练也可以。
        </p>
      </aside>
    </div>

    <section v-if="weakPoints.length && !showQuizPanel" class="weak-grid">
      <article
        v-for="item in weakPoints"
        :key="item.id"
        :class="['weak-card', { active: item.id === currentWeakPointId }]"
        @click="selectWeakPoint(item)"
      >
        <div class="weak-card-top">
          <span class="weak-badge">核心薄弱点</span>
          <span class="weak-time">最近出现 {{ formatDate(item.last_seen_at) }}</span>
        </div>
        <h2>{{ item.node_name }}</h2>
        <p class="weak-caption">建议优先围绕这个知识点复盘概念定义、典型错误和与题目的关系。</p>
        <div class="weak-card-bottom">
          <span class="weak-first-seen">首次记录 {{ formatDate(item.first_seen_at) }}</span>
          <span class="weak-status-hint">完成推荐学习后自动归档</span>
        </div>
      </article>
    </section>

    <section v-if="historyWeakPoints.length && !showQuizPanel" class="panel history-section">
      <div class="history-header">
        <h2>历史薄弱点</h2>
        <p>这里保留已经通过推荐学习完成巩固的知识点，方便回看你的成长轨迹。</p>
      </div>
      <div class="history-grid">
        <article v-for="item in historyWeakPoints" :key="`history-${item.id}`" class="history-card">
          <div class="history-card-top">
            <span class="history-badge">已掌握</span>
            <span class="history-time">最近更新 {{ formatDate(item.last_seen_at) }}</span>
          </div>
          <h3>{{ item.node_name }}</h3>
          <span class="weak-first-seen">首次记录 {{ formatDate(item.first_seen_at) }}</span>
        </article>
      </div>
    </section>

    <section v-else-if="!errorMessage && !graphNodes.length && !showQuizPanel" class="panel empty-state">
      <div class="empty-orbit" />
      <h2>当前没有待补齐的薄弱点</h2>
      <p>继续提问时，系统会在选出解释路径后，自动记录少量最关键的知识节点。</p>
      <router-link class="empty-link" to="/chat">去聊天页继续提问</router-link>
    </section>
  </section>
</template>

<script setup>
import { nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  getWeakPointsGraphApi,
  listWeakPointHistoryApi,
  listWeakPointsApi,
  markMasteredApi,
} from "../api/weakPoints";
import { streamGenerateQuizApi, streamSubmitAnswerApi } from "../api/quiz";
import KnowledgeGraphCanvas from "../components/KnowledgeGraphCanvas.vue";
import MarkdownContent from "../components/MarkdownContent.vue";
import { findGraphNodeById, markGraphNodeMastered } from "../features/weak-points/graphState";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const weakPoints = ref([]);
const historyWeakPoints = ref([]);
const errorMessage = ref("");
const graphNodes = ref([]);
const graphEdges = ref([]);
const selectedNodeId = ref("");
const currentWeakPointId = ref(null);
const currentWeakPointName = ref("");
const isGraphLoading = ref(false);
const graphCanvas = ref(null);
const recommendationSummary = ref("");
const learningOrder = ref([]);
const recommendedNodes = ref([]);
const pendingNodes = ref([]);

const showQuizPanel = ref(false);
const quizNodeId = ref("");
const quizNodeName = ref("");
const quizNodeStatus = ref("");
const quizStep = ref("intro");
const quizQuestion = ref("");
const userAnswer = ref("");
const feedbackContent = ref("");
const isCorrect = ref(false);
const isGenerating = ref(false);
const isSubmitting = ref(false);

onMounted(async () => {
  await Promise.all([loadWeakPoints(), loadWeakPointHistory()]);
  await loadGraph();
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

async function loadGraph(nodeId = currentWeakPointId.value) {
  if (!nodeId) {
    graphNodes.value = [];
    graphEdges.value = [];
    learningOrder.value = [];
    recommendationSummary.value = "";
    recommendedNodes.value = [];
    pendingNodes.value = [];
    selectedNodeId.value = "";
    return;
  }

  isGraphLoading.value = true;
  try {
    const { data } = await getWeakPointsGraphApi(nodeId);
    graphNodes.value = data.nodes || [];
    graphEdges.value = data.edges || [];
    learningOrder.value = data.learning_order || [];
    recommendationSummary.value = data.summary || "";
    recommendedNodes.value = data.recommended_nodes || [];
    pendingNodes.value = data.pending_nodes || [];
    currentWeakPointName.value = data.target?.name || currentWeakPointName.value;
    selectedNodeId.value = data.target?.id || "";
    await nextTick();
    if (graphCanvas.value && graphNodes.value.length) {
      graphCanvas.value.restartLayout?.();
    }
  } catch (error) {
    console.error("加载图谱失败:", error);
    handleApiError(error, "加载图谱失败。");
  } finally {
    isGraphLoading.value = false;
  }
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
  if (!node || node.status === "weak") return;
  quizNodeId.value = nodeId;
  quizNodeName.value = node.name || nodeId;
  quizNodeStatus.value = node.status || "";
  showQuizPanel.value = true;
  quizStep.value = "intro";
  quizQuestion.value = "";
  userAnswer.value = "";
  feedbackContent.value = "";
}

function closeQuizPanel() {
  showQuizPanel.value = false;
  quizNodeId.value = "";
  quizNodeName.value = "";
  quizNodeStatus.value = "";
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
  if (isCorrect.value && quizNodeStatus.value !== "pending") {
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

function shouldAutoArchiveCurrentWeakPoint() {
  if (!currentWeakPointId.value || !recommendedNodes.value.length) return false;
  return recommendedNodes.value.every((item) => item.status === "mastered");
}

async function completeCurrentWeakPoint() {
  if (!currentWeakPointId.value) return;
  await markMasteredApi(currentWeakPointId.value);
  await Promise.all([
    loadWeakPoints({ preferredId: null }),
    loadWeakPointHistory(),
  ]);
  await loadGraph();
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
  gap: 22px;
}

.dashboard-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.app-title {
  margin: 0;
  font-size: 32px;
  line-height: 1.08;
  font-weight: 500;
}

.app-subtitle {
  margin: 0;
  max-width: 700px;
  color: var(--app-text-muted);
  line-height: 1.75;
}

.empty-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-md);
  background: #fff;
  color: #31445f;
  text-decoration: none;
  cursor: pointer;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.summary-card,
.panel {
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.summary-card {
  display: grid;
  gap: 10px;
  padding: 18px 20px;
}

.summary-card strong {
  display: block;
  color: var(--app-text);
  font-size: 28px;
  font-weight: 500;
}

.summary-card span {
  color: var(--app-text-muted);
}

.feedback {
  margin: 0;
  padding: 14px 16px;
}

.feedback.error {
  background: #fff5f5;
  color: #b42318;
  border: 1px solid #f0d3d3;
}

.weak-grid-layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  align-items: start;
}

.graph-section {
  min-width: 0;
}

.graph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.graph-header h2,
.history-header h2,
.recommendation-header h3,
.quiz-header h3,
.empty-state h2 {
  margin: 0;
  color: var(--app-text);
  font-weight: 500;
}

.graph-header h2,
.history-header h2,
.recommendation-header h3,
.empty-state h2 {
  font-size: 22px;
}

.quiz-header h3 {
  font-size: 16px;
}

.legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--app-text-muted);
  font-size: 13px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-dot.weak {
  background: #ef4444;
}

.legend-dot.learning {
  background: #f59e0b;
}

.legend-dot.recommended {
  background: #2563eb;
}

.legend-dot.pending {
  background: #8b5cf6;
}

.legend-dot.mastered {
  background: #22c55e;
}

.legend-dot.unknown {
  background: #94a3b8;
}

.graph-container {
  position: relative;
  min-height: 500px;
  border: 1px solid var(--app-line);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--app-shadow);
  overflow: hidden;
}

.graph-container :deep(.graph-canvas) {
  height: 500px;
  min-height: 500px;
  border-radius: 26px;
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

.quiz-panel,
.recommendation-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.recommendation-panel {
  padding: 22px;
  gap: 18px;
  max-height: 552px;
  overflow-y: auto;
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
  font-size: 22px;
}

.recommendation-summary {
  margin: 0;
  color: var(--app-text-muted);
  line-height: 1.8;
}

.recommendation-tip {
  margin: -4px 0 0;
  padding: 10px 12px;
  border-radius: 14px;
  background: #f3f8ff;
  color: #49657f;
  line-height: 1.65;
  font-size: 13px;
}

.recommendation-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  gap: 10px;
}

.learning-order li {
  line-height: 1.6;
}

.recommendation-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 12px;
}

.recommendation-list li {
  padding: 14px 14px 12px;
  border: 1px solid #e8eef6;
  border-radius: var(--app-radius-lg);
  background: var(--app-panel-soft);
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
  line-height: 1.75;
}

.quiz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #eef2f7;
}

.quiz-header h3 {
  font-size: 22px;
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
  padding: 20px;
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

.quiz-pending-tip {
  margin: 0 0 18px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #f7f2ff;
  color: #6d4bc5;
  line-height: 1.6;
  font-size: 13px;
}

.primary-btn,
.secondary-btn {
  padding: 10px 18px;
  border-radius: 12px;
  font-size: 14px;
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

.quiz-pending-badge {
  padding: 4px 10px;
  border-radius: 999px;
  background: #f3e8ff;
  color: #7c3aed;
  font-size: 12px;
  font-weight: 500;
}

.quiz-question {
  padding: 16px;
  border-radius: 12px;
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
  border-radius: 12px;
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
  border-radius: 12px;
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

.weak-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
}

.weak-card {
  padding: 22px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.weak-card.active {
  border-color: #c7daf3;
  box-shadow: 0 20px 46px rgba(37, 99, 235, 0.12);
  transform: translateY(-2px);
}

.weak-card-top,
.weak-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.weak-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #edf5ff;
  color: #34699a;
  font-size: 12px;
  font-weight: 500;
}

.weak-time,
.weak-first-seen {
  color: #8394a7;
  font-size: 12px;
}

.weak-card h2 {
  margin: 18px 0 10px;
  color: var(--app-text);
  font-size: 24px;
  font-weight: 500;
}

.weak-caption {
  margin: 0 0 24px;
  color: #5f7287;
  line-height: 1.7;
}

.weak-status-hint {
  color: #5f7287;
  font-size: 12px;
}

.history-section {
  padding: 22px;
}

.history-header {
  margin-bottom: 16px;
}

.history-header h2 {
  font-size: 22px;
}

.history-header p {
  margin: 0;
  color: var(--app-text-muted);
  line-height: 1.7;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.history-card {
  padding: 22px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
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
  padding: 6px 10px;
  border-radius: 999px;
  background: #e8f8ee;
  color: #20854e;
  font-size: 12px;
  font-weight: 500;
}

.history-time {
  color: #8394a7;
  font-size: 12px;
}

.history-card h3 {
  margin: 16px 0 10px;
  color: var(--app-text);
  font-size: 20px;
  font-weight: 500;
}

.empty-state {
  position: relative;
  overflow: hidden;
  padding: 64px 24px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
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

@media (max-width: 1024px) {
  .main-layout {
    grid-template-columns: 1fr;
  }

  .quiz-panel {
    max-height: none;
  }

  .recommendation-panel {
    max-height: none;
  }
}

@media (max-width: 860px) {
  .dashboard-hero {
    flex-direction: column;
  }

  .summary-row,
  .weak-grid-layout {
    grid-template-columns: 1fr;
  }

  .weak-card-top,
  .weak-card-bottom {
    flex-direction: column;
    align-items: flex-start;
  }

  .graph-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
