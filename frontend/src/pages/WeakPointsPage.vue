<template>
  <div class="weak-page">
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Learning Focus</p>
        <h1>我的薄弱点</h1>
        <p class="hero-text">系统会根据已选路径收敛出最值得优先补齐的 1 到 2 个核心节点，帮助你把复习重点压缩到真正关键的地方。</p>
      </div>
      <router-link class="back-link" to="/">返回聊天</router-link>
    </header>

    <section class="summary-strip">
      <article class="summary-card">
        <span class="summary-label">当前待掌握</span>
        <strong>{{ weakPoints.length }}</strong>
      </article>
      <article class="summary-card muted">
        <span class="summary-label">推荐方式</span>
        <strong>先补底层概念，再回到题目</strong>
      </article>
    </section>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <div class="main-layout">
      <section class="graph-section">
        <div class="graph-header">
          <h2 class="section-title">知识点掌握情况图谱</h2>
          <div class="legend">
            <span class="legend-item"><span class="legend-dot weak"></span> 薄弱</span>
            <span class="legend-item"><span class="legend-dot learning"></span> 学习中</span>
            <span class="legend-item"><span class="legend-dot mastered"></span> 已掌握</span>
            <span class="legend-item"><span class="legend-dot unknown"></span> 未学习</span>
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

      <aside v-if="showQuizPanel" class="quiz-panel">
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
              检测到薄弱点 <strong>【{{ quizNodeName }}】</strong>，是否开始针对性训练？
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
    </div>

    <section v-if="weakPoints.length && !showQuizPanel" class="weak-grid">
      <article v-for="item in weakPoints" :key="item.id" class="weak-card">
        <div class="weak-card-top">
          <span class="weak-badge">核心薄弱点</span>
          <span class="weak-time">最近出现 {{ formatDate(item.last_seen_at) }}</span>
        </div>
        <h2>{{ item.node_name }}</h2>
        <p class="weak-caption">建议优先围绕这个知识点复盘概念定义、典型错误和与题目的关系。</p>
        <div class="weak-card-bottom">
          <span class="weak-first-seen">首次记录 {{ formatDate(item.first_seen_at) }}</span>
          <button @click="markMastered(item.id)">已掌握</button>
        </div>
      </article>
    </section>

    <section v-else-if="!errorMessage && !graphNodes.length && !showQuizPanel" class="empty-state">
      <div class="empty-orbit" />
      <h2>当前没有待补齐的薄弱点</h2>
      <p>继续提问时，系统会在选出解释路径后，自动记录少量最关键的知识节点。</p>
      <router-link class="empty-link" to="/">去聊天页继续提问</router-link>
    </section>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  getWeakPointsGraphApi,
  listWeakPointsApi,
  markMasteredApi,
} from "../api/weakPoints";
import { streamGenerateQuizApi, streamSubmitAnswerApi } from "../api/quiz";
import KnowledgeGraphCanvas from "../components/KnowledgeGraphCanvas.vue";
import MarkdownContent from "../components/MarkdownContent.vue";
import { findGraphNodeById, markGraphNodeMastered } from "../features/weak-points/graphState";

const router = useRouter();
const weakPoints = ref([]);
const errorMessage = ref("");
const graphNodes = ref([]);
const graphEdges = ref([]);
const selectedNodeId = ref("");
const isGraphLoading = ref(false);
const graphCanvas = ref(null);

const showQuizPanel = ref(false);
const quizNodeId = ref("");
const quizNodeName = ref("");
const quizStep = ref("intro");
const quizQuestion = ref("");
const userAnswer = ref("");
const feedbackContent = ref("");
const isCorrect = ref(false);
const isGenerating = ref(false);
const isSubmitting = ref(false);

onMounted(async () => {
  await Promise.all([loadWeakPoints(), loadGraph()]);
});

async function loadWeakPoints() {
  try {
    const { data } = await listWeakPointsApi();
    weakPoints.value = data;
  } catch (error) {
    handleApiError(error, "加载薄弱点失败。");
  }
}

async function loadGraph() {
  isGraphLoading.value = true;
  try {
    const { data } = await getWeakPointsGraphApi();
    graphNodes.value = data.nodes || [];
    graphEdges.value = data.edges || [];
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

async function markMastered(nodeId) {
  try {
    const masteredItem = weakPoints.value.find((item) => item.id === nodeId);
    await markMasteredApi(nodeId);
    weakPoints.value = weakPoints.value.filter((item) => item.id !== nodeId);
    if (masteredItem) {
      handleMastered(masteredItem.node_name);
    }
  } catch (error) {
    handleApiError(error, "更新薄弱点失败。");
  }
}

function handleNodeSelect(nodeId) {
  selectedNodeId.value = nodeId;
  const node = findGraphNodeById(graphNodes.value, nodeId);
  if (node) {
    quizNodeId.value = nodeId;
    quizNodeName.value = node.name || nodeId;
    showQuizPanel.value = true;
    quizStep.value = "intro";
    quizQuestion.value = "";
    userAnswer.value = "";
    feedbackContent.value = "";
  }
}

function closeQuizPanel() {
  showQuizPanel.value = false;
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
}

function handleComplete() {
  if (isCorrect.value) {
    handleMastered(quizNodeId.value);
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
</script>

<style scoped>
.weak-page {
  min-height: 100vh;
  padding: 36px 40px 48px;
  background:
    radial-gradient(circle at top left, rgba(220, 237, 255, 0.9) 0%, rgba(255, 255, 255, 0) 24%),
    linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.eyebrow {
  margin: 0 0 10px;
  color: #4f86c6;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.05;
  color: #10283d;
}

.hero-text {
  max-width: 700px;
  margin: 14px 0 0;
  color: #5f7287;
  line-height: 1.75;
}

.back-link,
.empty-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 11px 16px;
  border: 1px solid #dbe6f1;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #274863;
  text-decoration: none;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.summary-strip {
  display: grid;
  grid-template-columns: minmax(180px, 240px) minmax(260px, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.summary-card {
  padding: 18px 20px;
  border: 1px solid #e4edf6;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
}

.summary-card strong {
  display: block;
  margin-top: 8px;
  color: #12324a;
  font-size: 28px;
  font-weight: 700;
}

.summary-card.muted strong {
  font-size: 18px;
  line-height: 1.5;
}

.summary-label {
  color: #718399;
  font-size: 13px;
}

.feedback {
  margin: 0 0 20px;
  padding: 14px 16px;
  border-radius: 16px;
}

.feedback.error {
  background: #fff4f4;
  color: #b42318;
}

.main-layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 32px;
}

.main-layout:not(:has(.quiz-panel)) {
  grid-template-columns: 1fr;
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

.section-title {
  margin: 0;
  color: #10283d;
  font-size: 20px;
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
  color: #64748b;
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

.legend-dot.mastered {
  background: #22c55e;
}

.legend-dot.unknown {
  background: #94a3b8;
}

.graph-container {
  position: relative;
  min-height: 500px;
  border: 1px solid #e2ebf4;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
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

.quiz-panel {
  border: 1px solid #e2ebf4;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  max-height: 600px;
}

.quiz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #eef2f7;
}

.quiz-header h3 {
  margin: 0;
  font-size: 16px;
  color: #10283d;
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
  font-weight: 700;
}

.intro-text {
  margin: 0 0 20px;
  color: #1e293b;
  font-size: 15px;
  line-height: 1.7;
}

.intro-text strong {
  color: #ef4444;
}

.intro-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
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
  font-weight: 600;
}

.quiz-node {
  color: #64748b;
  font-size: 13px;
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
  font-weight: 700;
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
  border: 1px solid #e3ebf3;
  border-radius: 26px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, #f9fbfd 100%);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
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
  font-weight: 600;
}

.weak-time,
.weak-first-seen {
  color: #8394a7;
  font-size: 12px;
}

.weak-card h2 {
  margin: 18px 0 10px;
  color: #10283d;
  font-size: 24px;
}

.weak-caption {
  margin: 0 0 24px;
  color: #5f7287;
  line-height: 1.7;
}

.weak-card button {
  border: none;
  border-radius: 999px;
  padding: 10px 14px;
  background: #10283d;
  color: #ffffff;
  cursor: pointer;
}

.empty-state {
  position: relative;
  overflow: hidden;
  padding: 64px 24px;
  border: 1px solid #e7eef6;
  border-radius: 28px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  text-align: center;
}

.empty-orbit {
  position: absolute;
  top: -42px;
  left: 50%;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(181, 214, 255, 0.35) 0%, rgba(181, 214, 255, 0) 70%);
  transform: translateX(-50%);
}

.empty-state h2 {
  position: relative;
  margin: 0 0 12px;
  color: #10283d;
}

.empty-state p {
  position: relative;
  max-width: 560px;
  margin: 0 auto 22px;
  color: #64748b;
  line-height: 1.7;
}

@media (max-width: 1024px) {
  .main-layout {
    grid-template-columns: 1fr;
  }

  .quiz-panel {
    max-height: none;
  }
}

@media (max-width: 860px) {
  .weak-page {
    padding: 24px 18px 36px;
  }

  .hero {
    flex-direction: column;
  }

  .summary-strip {
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
