<template>
  <div class="detail-page" :class="{ 'ai-open': showAiPanel }">
    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <main v-if="assignment" class="assignment-lab" :style="labGridStyle">
      <aside class="problem-pane">
        <header class="problem-header">
          <router-link class="back-link" to="/assignments">返回作业</router-link>
          <h1>{{ assignment.title }}</h1>
          <p>{{ assignment.description || "完成题目后提交代码查看测试结果。" }}</p>
        </header>

        <div class="question-tabs">
          <button
            v-for="(question, index) in assignment.questions"
            :key="question.id"
            :class="{ active: activeQuestion?.id === question.id }"
            type="button"
            @click="selectQuestion(question)"
          >
            第 {{ index + 1 }} 题
          </button>
        </div>

        <section v-if="activeQuestion" class="problem-content">
          <h2>{{ activeQuestion.title || questionTypeText(activeQuestion.question_type) }}</h2>
          <span class="question-type-badge">{{ questionTypeText(activeQuestion.question_type) }}</span>
          <MarkdownContent :content="activeQuestion.prompt" />

          <div v-if="sampleCases.length" class="sample-list">
            <article v-for="item in sampleCases" :key="item.id" class="sample-card">
              <strong>示例输入</strong>
              <pre>{{ item.input_data || "(空)" }}</pre>
              <strong>示例输出</strong>
              <pre>{{ item.expected_output || "(空)" }}</pre>
            </article>
          </div>
        </section>
      </aside>

      <div class="resize-handle" @pointerdown="startProblemResize" />

      <section v-if="activeQuestion" ref="editorPane" class="editor-pane" :class="{ 'has-result': lastResult }">
        <header class="editor-toolbar">
          <div>
            <h2>{{ answerPaneTitle }}</h2>
          </div>
          <div class="toolbar-actions">
            <span class="language-pill">{{ questionTypeText(activeQuestion.question_type) }}</span>
            <span class="draft-pill">已自动保存</span>
            <button type="button" class="secondary-btn" @click="showAiPanel = !showAiPanel">
              {{ showAiPanel ? "收起 AI" : "AI 助教" }}
            </button>
            <button type="button" class="secondary-btn" :disabled="loadingPreviousResult" @click="showPreviousSubmissionResult">
              {{ loadingPreviousResult ? "加载中..." : "查看上次提交" }}
            </button>
            <button type="button" class="primary-btn" :disabled="submitting || !canSubmitAnswer" @click="submitAnswer">
              {{ submitting ? "提交中..." : submitButtonText }}
            </button>
          </div>
        </header>

        <div v-if="isProgrammingQuestion" class="editor-shell">
          <CodeEditor v-model="activeCode" />
        </div>
        <div v-else-if="activeQuestion.question_type === 'multiple_choice'" class="objective-shell">
          <label
            v-for="option in activeQuestion.options || []"
            :key="option.key"
            class="choice-option"
            :class="{ selected: objectiveAnswer === option.key }"
          >
            <input v-model="objectiveAnswer" type="radio" :value="option.key" />
            <span>{{ option.key }}</span>
            <p>{{ option.text }}</p>
          </label>
        </div>
        <div v-else class="objective-shell">
          <textarea v-model="objectiveAnswer" rows="10" placeholder="请输入你的答案，系统会结合参考答案进行 AI 语义判分。" />
        </div>

        <div v-if="lastResult" class="result-resize-handle" @pointerdown="startResultResize" />

        <section v-if="lastResult" class="result-console" :class="{ 'ai-rejected-result': isAiRejectedAfterPassingTests }">
          <header>
            <h3>测试结果</h3>
            <span :class="['result-status', lastResult.status]">{{ statusText(lastResult.status) }}</span>
          </header>
          <div v-if="isAiRejectedAfterPassingTests" class="ai-reject-alert">
            <strong>测试用例已通过，但 AI 判定未通过</strong>
            <p>请优先查看 AI 评审中的风险点和可能薄弱点。</p>
          </div>
          <div class="result-list">
            <div v-for="item in lastResult.results" :key="item.case_index" class="result-item" :class="item.status">
              <strong>{{ resultTitle(item) }}</strong>
              <p v-if="item.summary">{{ item.summary }}</p>
              <template v-if="shouldShowCaseIo(item)">
                <span>输入</span>
                <pre>{{ item.input || "(空)" }}</pre>
                <template v-if="item.check_mode !== 'observe_only'">
                  <span>期望输出</span>
                  <pre>{{ item.expected_output || "(空)" }}</pre>
                </template>
                <span>实际输出</span>
                <pre>{{ item.actual_output || "(空)" }}</pre>
              </template>
              <pre v-if="item.stderr">{{ item.stderr }}</pre>
            </div>
          </div>

          <section v-if="lastResult?.ai_review" class="ai-review-block">
            <header>
              <h3>AI 评审</h3>
              <span class="review-badge">{{ decisionSourceText(lastResult.decision_source) }}</span>
            </header>
            <p class="review-summary">{{ lastResult.ai_review.summary || "AI 未返回总结。" }}</p>
            <dl class="review-metrics">
              <div>
                <dt>AI 决策</dt>
                <dd>{{ statusText(lastResult.ai_review.decision || lastResult.status) }}</dd>
              </div>
              <div>
                <dt>评分</dt>
                <dd>{{ lastResult.ai_review.score ?? "--" }}</dd>
              </div>
              <div>
                <dt>置信度</dt>
                <dd>{{ formatConfidence(lastResult.ai_review.confidence) }}</dd>
              </div>
              <div>
                <dt>人工复核</dt>
                <dd>{{ lastResult.manual_review_required ? "需要" : "无需" }}</dd>
              </div>
            </dl>
            <div v-if="lastResult.ai_review.issues?.length" class="review-list">
              <strong>风险点</strong>
              <ul>
                <li v-for="(item, index) in lastResult.ai_review.issues" :key="`issue-${index}`">{{ item }}</li>
              </ul>
            </div>
            <div v-if="lastResult.ai_review.strengths?.length" class="review-list">
              <strong>实现优点</strong>
              <ul>
                <li v-for="(item, index) in lastResult.ai_review.strengths" :key="`strength-${index}`">{{ item }}</li>
              </ul>
            </div>
            <div v-if="lastResult.ai_review.diagnoses?.length" class="diagnosis-list">
              <strong>可能薄弱点</strong>
              <article v-for="(item, index) in lastResult.ai_review.diagnoses" :key="`diagnosis-${index}`" class="diagnosis-item">
                <div class="diagnosis-head">
                  <span>{{ item.knowledge_node || "unknown" }}</span>
                  <small>{{ formatConfidence(item.confidence) }}</small>
                </div>
                <div class="diagnosis-resolution" :class="item.graph_resolution?.status || 'unresolved'">
                  {{ graphResolutionText(item.graph_resolution) }}
                </div>
                <p v-if="item.student_feedback">{{ item.student_feedback }}</p>
                <p v-else-if="item.reason">{{ item.reason }}</p>
                <small v-if="item.evidence">证据：{{ item.evidence }}</small>
              </article>
            </div>
          </section>
        </section>
      </section>

      <div v-if="activeQuestion && showAiPanel" class="resize-handle ai-resize-handle" @pointerdown="startAiResize" />

      <aside v-if="activeQuestion && showAiPanel" class="ai-pane">
        <header class="ai-header">
          <div>
            <h2>作业助教</h2>
          </div>
          <button type="button" class="icon-btn" @click="showAiPanel = false">关闭</button>
        </header>

        <div class="ai-composer">
          <textarea ref="aiInput" v-model="aiMessage" rows="4" placeholder="描述你卡住的地方，或询问某个报错原因。" />
          <button type="button" :disabled="asking || !aiMessage.trim()" @click="askAi">
              {{ asking ? "思考中..." : "提问" }}
          </button>
        </div>

        <div v-if="asking" class="ai-state">正在结合题目、代码和图谱知识点分析...</div>
        <p v-if="aiHelpError" class="ai-error">{{ aiHelpError }}</p>

        <div v-if="aiAnswer" class="ai-answer">
          <MarkdownContent :content="aiAnswer" />
        </div>
        <div v-if="aiConcepts.length" class="concept-block">
          <strong>相关知识点</strong>
          <div class="concept-list">
            <span v-for="concept in aiConcepts" :key="concept">{{ concept }}</span>
          </div>
        </div>

        <details v-if="aiReasoningTrace.length || aiRetrievalTrace.length" class="trace-box">
          <summary>查看检索过程</summary>
          <div v-if="aiReasoningTrace.length" class="trace-group">
            <strong>推理轨迹</strong>
            <ul>
              <li v-for="(item, index) in aiReasoningTrace" :key="`reason-${index}`">
                {{ item.title }}：{{ item.summary }}
              </li>
            </ul>
          </div>
          <div v-if="aiRetrievalTrace.length" class="trace-group">
            <strong>检索轨迹</strong>
            <ul>
              <li v-for="(item, index) in aiRetrievalTrace" :key="`retrieval-${index}`">
                {{ item.title }}：{{ item.summary }}
              </li>
            </ul>
          </div>
        </details>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  getStudentAssignmentApi,
  listStudentAssignmentSubmissionsApi,
  streamAssignmentAiHelpApi,
  submitAssignmentQuestionApi,
} from "../api/assignments";
import CodeEditor from "../components/CodeEditor.vue";
import MarkdownContent from "../components/MarkdownContent.vue";
import { useAuthStore } from "../stores/auth";
import { clearAuthSession } from "../utils/authStorage";

const STARTER_CODE = `public class Main {
    public static void main(String[] args) {
        // 在这里编写你的代码
        
    }
}
`;
const DRAFT_PREFIX = "assignment-code-draft";
const STARTED_AT_PREFIX = "assignment-started-at";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const assignment = ref(null);
const activeQuestion = ref(null);
const codeByQuestion = ref({});
const answerByQuestion = ref({});
const startedAtByQuestion = ref({});
const lastResultByQuestion = ref({});
const aiMessage = ref("");
const aiAnswer = ref("");
const aiKeywords = ref([]);
const aiFacts = ref([]);
const aiReasoningTrace = ref([]);
const aiRetrievalTrace = ref([]);
const aiHelpError = ref("");
const errorMessage = ref("");
const submitting = ref(false);
const asking = ref(false);
const loadingPreviousResult = ref(false);
const showAiPanel = ref(false);
const aiInput = ref(null);
const editorPane = ref(null);
const problemPaneWidth = ref(320);
const aiPaneWidth = ref(360);
const resultPaneHeight = ref(0);

const sampleCases = computed(() => activeQuestion.value?.test_cases?.filter((item) => item.is_sample) || []);
const isProgrammingQuestion = computed(() => (activeQuestion.value?.question_type || "programming") === "programming");
const answerPaneTitle = computed(() => isProgrammingQuestion.value ? "Main.java" : "作答区");
const submitButtonText = computed(() => isProgrammingQuestion.value ? "提交运行" : "提交答案");
const objectiveAnswer = computed({
  get() {
    if (!activeQuestion.value) return "";
    return answerByQuestion.value[activeQuestion.value.id] ?? "";
  },
  set(value) {
    if (!activeQuestion.value) return;
    answerByQuestion.value[activeQuestion.value.id] = value;
  },
});
const canSubmitAnswer = computed(() => {
  if (!activeQuestion.value) return false;
  return isProgrammingQuestion.value ? activeCode.value.trim() : String(objectiveAnswer.value || "").trim();
});
const aiConcepts = computed(() => {
  const names = new Set(aiKeywords.value.map((item) => String(item)).filter(Boolean));
  for (const fact of aiFacts.value) {
    for (const key of ["seed", "target", "node_name", "frontier_entity"]) {
      if (fact?.[key]) names.add(String(fact[key]));
    }
    if (Array.isArray(fact?.nodes)) {
      fact.nodes.filter(Boolean).forEach((name) => names.add(String(name)));
    }
  }
  return Array.from(names).slice(0, 8);
});
const lastResult = computed(() => {
  if (!activeQuestion.value) return null;
  return lastResultByQuestion.value[activeQuestion.value.id] || null;
});
const labGridStyle = computed(() => {
  return {
    "--problem-pane-width": `${problemPaneWidth.value}px`,
    "--ai-pane-width": `${aiPaneWidth.value}px`,
    "--result-pane-height": resultPaneHeight.value ? `${resultPaneHeight.value}px` : "50%",
  };
});
const activeCode = computed({
  get() {
    if (!activeQuestion.value) return "";
    return codeByQuestion.value[activeQuestion.value.id] ?? resolveStarterCode(activeQuestion.value);
  },
  set(value) {
    if (!activeQuestion.value) return;
    codeByQuestion.value[activeQuestion.value.id] = value;
    saveCodeDraft(activeQuestion.value.id, value);
  },
});
const isAiRejectedAfterPassingTests = computed(() => {
  const result = lastResult.value;
  if (!result) return false;
  const aiDecision = result.ai_review?.decision;
  const testsPassed = Array.isArray(result.results)
    && result.results.length > 0
    && result.results.every((item) => item.status === "accepted");
  return testsPassed && (result.status === "ai_rejected" || aiDecision === "ai_rejected" || aiDecision === "wrong_answer");
});

onMounted(async () => {
  await ensureCurrentUser();
  await loadAssignment();
});

async function ensureCurrentUser() {
  if (authStore.user || !authStore.token) return;
  try {
    await authStore.fetchMe();
  } catch {
    // Route guards will handle invalid sessions; draft keys still fall back to the current token namespace.
  }
}

async function loadAssignment() {
  try {
    const { data } = await getStudentAssignmentApi(route.params.assignmentId);
    assignment.value = data;
    if (data.questions?.length) {
      selectQuestion(data.questions[0]);
    }
  } catch (error) {
    handleApiError(error, "加载作业失败。");
  }
}

function selectQuestion(question) {
  activeQuestion.value = question;
  if ((question.question_type || "programming") === "programming" && !(question.id in codeByQuestion.value)) {
    codeByQuestion.value[question.id] = loadCodeDraft(question.id) ?? resolveStarterCode(question);
  }
  if ((question.question_type || "programming") !== "programming" && !(question.id in answerByQuestion.value)) {
    answerByQuestion.value[question.id] = "";
  }
  if (!startedAtByQuestion.value[question.id]) {
    const startedAt = loadStartedAt(question.id) || new Date().toISOString();
    startedAtByQuestion.value[question.id] = startedAt;
    saveStartedAt(question.id, startedAt);
  }
  aiMessage.value = "";
  clearAiHelp();
}

async function submitAnswer() {
  submitting.value = true;
  errorMessage.value = "";
  try {
    const payload = {
      started_at: startedAtByQuestion.value[activeQuestion.value.id],
    };
    if (isProgrammingQuestion.value) {
      payload.code = activeCode.value;
    } else {
      payload.answer = objectiveAnswer.value;
    }
    const { data } = await submitAssignmentQuestionApi(assignment.value.id, activeQuestion.value.id, payload);
    ensureDefaultResultPaneHeight();
    lastResultByQuestion.value[activeQuestion.value.id] = data;
    if (data.submission?.submitted_at) {
      startedAtByQuestion.value[activeQuestion.value.id] = data.submission.submitted_at;
      saveStartedAt(activeQuestion.value.id, data.submission.submitted_at);
    }
  } catch (error) {
    handleApiError(error, "提交失败。");
  } finally {
    submitting.value = false;
  }
}

async function showPreviousSubmissionResult() {
  if (!activeQuestion.value || loadingPreviousResult.value) return;
  loadingPreviousResult.value = true;
  errorMessage.value = "";
  try {
    const { data } = await listStudentAssignmentSubmissionsApi(assignment.value.id);
    const previousSubmission = (data || []).find((item) => item.question_id === activeQuestion.value.id);
    if (!previousSubmission) {
      errorMessage.value = "当前题目还没有提交记录。";
      return;
    }
    ensureDefaultResultPaneHeight();
    lastResultByQuestion.value[activeQuestion.value.id] = submissionToRunResult(previousSubmission);
  } catch (error) {
    handleApiError(error, "加载上次提交结果失败。");
  } finally {
    loadingPreviousResult.value = false;
  }
}

async function askAi() {
  await requestAiHelp(aiMessage.value, false);
}

async function requestAiHelp(message, keepModalOnFailure) {
  if (!message?.trim() || asking.value) return;
  asking.value = true;
  errorMessage.value = "";
  aiHelpError.value = "";
  try {
    aiAnswer.value = "";
    await streamAssignmentAiHelpApi(
      assignment.value.id,
      activeQuestion.value.id,
      {
        message,
        code: activeCode.value,
        last_result: lastResult.value,
      },
      {
        onMetadata(data) {
          aiKeywords.value = data.keywords || [];
          aiFacts.value = data.facts || [];
          aiReasoningTrace.value = data.reasoning_trace || [];
          aiRetrievalTrace.value = data.retrieval_trace || [];
        },
        onAnswerDelta(data) {
          aiAnswer.value += data.content || "";
        },
        onAnswerDone(data) {
          aiAnswer.value = data.answer || aiAnswer.value;
        },
        onError(data) {
          throw new Error(data.detail || "AI 帮助失败。");
        },
      },
    );
  } catch (error) {
    if (keepModalOnFailure) {
      aiHelpError.value = error?.response?.data?.detail || error?.message || "AI 辅导暂时不可用，可以先根据运行结果继续修改。";
    } else {
      handleApiError(error, "AI 帮助失败。");
    }
  } finally {
    asking.value = false;
  }
}

function clearAiHelp() {
  aiAnswer.value = "";
  aiKeywords.value = [];
  aiFacts.value = [];
  aiReasoningTrace.value = [];
  aiRetrievalTrace.value = [];
  aiHelpError.value = "";
}

function getDraftKey(questionId) {
  return `${DRAFT_PREFIX}:${getDraftOwnerKey()}:${route.params.assignmentId}:${questionId}`;
}

function getStartedAtKey(questionId) {
  return `${STARTED_AT_PREFIX}:${getDraftOwnerKey()}:${route.params.assignmentId}:${questionId}`;
}

function getDraftOwnerKey() {
  const user = authStore.user || {};
  const value = user.id ?? user.username ?? authStore.token ?? "anonymous";
  return encodeURIComponent(String(value));
}

function resolveStarterCode(question) {
  const starterCode = String(question?.starter_code || "").trim();
  return starterCode || STARTER_CODE;
}

function loadCodeDraft(questionId) {
  try {
    return window.localStorage.getItem(getDraftKey(questionId));
  } catch {
    return null;
  }
}

function saveCodeDraft(questionId, code) {
  try {
    window.localStorage.setItem(getDraftKey(questionId), code);
  } catch {
    // Ignore storage failures so editing and submission are not blocked.
  }
}

function loadStartedAt(questionId) {
  try {
    return window.localStorage.getItem(getStartedAtKey(questionId));
  } catch {
    return null;
  }
}

function saveStartedAt(questionId, startedAt) {
  try {
    window.localStorage.setItem(getStartedAtKey(questionId), startedAt);
  } catch {
    // Ignore storage failures so timing does not block editing and submission.
  }
}

function submissionToRunResult(submission) {
  return {
    submission,
    status: submission.status,
    results: Array.isArray(submission.results_json) ? submission.results_json : [],
    ai_review: submission.ai_review_json,
    decision_source: submission.decision_source,
    manual_review_required: submission.manual_review_required,
  };
}

function startProblemResize(event) {
  const startX = event.clientX;
  const startWidth = problemPaneWidth.value;
  event.currentTarget.setPointerCapture?.(event.pointerId);

  function handleMove(moveEvent) {
    const nextWidth = startWidth + moveEvent.clientX - startX;
    problemPaneWidth.value = Math.min(Math.max(nextWidth, 260), 560);
  }

  function handleUp() {
    window.removeEventListener("pointermove", handleMove);
    window.removeEventListener("pointerup", handleUp);
  }

  window.addEventListener("pointermove", handleMove);
  window.addEventListener("pointerup", handleUp);
}

function startAiResize(event) {
  const startX = event.clientX;
  const startWidth = aiPaneWidth.value;
  event.currentTarget.setPointerCapture?.(event.pointerId);

  function handleMove(moveEvent) {
    const nextWidth = startWidth - (moveEvent.clientX - startX);
    aiPaneWidth.value = Math.min(Math.max(nextWidth, 300), 620);
  }

  function handleUp() {
    window.removeEventListener("pointermove", handleMove);
    window.removeEventListener("pointerup", handleUp);
  }

  window.addEventListener("pointermove", handleMove);
  window.addEventListener("pointerup", handleUp);
}

function startResultResize(event) {
  const startY = event.clientY;
  const startHeight = resultPaneHeight.value || getDefaultResultPaneHeight();
  event.currentTarget.setPointerCapture?.(event.pointerId);

  function handleMove(moveEvent) {
    const nextHeight = startHeight - (moveEvent.clientY - startY);
    const maxHeight = getMaxResultPaneHeight();
    resultPaneHeight.value = Math.min(Math.max(nextHeight, 160), maxHeight);
  }

  function handleUp() {
    window.removeEventListener("pointermove", handleMove);
    window.removeEventListener("pointerup", handleUp);
  }

  window.addEventListener("pointermove", handleMove);
  window.addEventListener("pointerup", handleUp);
}

function ensureDefaultResultPaneHeight() {
  if (resultPaneHeight.value) return;
  resultPaneHeight.value = getDefaultResultPaneHeight();
}

function getDefaultResultPaneHeight() {
  const paneHeight = editorPane.value?.clientHeight || window.innerHeight;
  const toolbarHeight = editorPane.value?.querySelector(".editor-toolbar")?.clientHeight || 74;
  return Math.max(220, Math.floor((paneHeight - toolbarHeight - 8) / 2));
}

function getMaxResultPaneHeight() {
  const paneHeight = editorPane.value?.clientHeight || window.innerHeight;
  const toolbarHeight = editorPane.value?.querySelector(".editor-toolbar")?.clientHeight || 74;
  return Math.max(220, paneHeight - toolbarHeight - 180);
}

function statusText(status) {
  return {
    accepted: "通过",
    wrong_answer: "答案错误",
    runtime_error: "运行错误",
    timeout: "超时",
    sandbox_error: "沙箱错误",
    needs_manual_review: "待人工复核",
    ai_rejected: "AI 判定未通过",
    published: "已发布",
    closed: "已关闭",
  }[status] || status;
}

function questionTypeText(value) {
  return {
    programming: "编程题",
    multiple_choice: "选择题",
    fill_blank: "填空题",
  }[value || "programming"] || "编程题";
}

function decisionSourceText(value) {
  return {
    testcase: "测试用例结果",
    ai_review: "AI 评审结果",
    hybrid: "混合判题结果",
    ai_with_testcases: "AI + 测试用例",
    observed_ai: "观察运行 + AI",
    ai_only: "AI 判题结果",
    teacher_override: "教师改判",
  }[value] || "系统判定";
}

function formatConfidence(value) {
  const number = Number(value);
  if (Number.isNaN(number)) return "--";
  return `${Math.round(number * 100)}%`;
}

function graphResolutionText(resolution) {
  const status = resolution?.status;
  if (status === "matched_existing") {
    return `已关联：${resolution.node_name || "知识图谱节点"}`;
  }
  if (status === "needs_teacher_review") return "待教师确认";
  if (status === "skipped_low_confidence") return "低置信诊断，暂不计入";
  if (status === "low_confidence_unmatched") return "低置信未匹配，待教师确认";
  if (status === "unresolved") return "暂未关联到图谱";
  return "暂未解析";
}

function resultTitle(item) {
  if (item?.case_index === 0) {
    return `编译阶段：${statusText(item.status)}`;
  }
  if (item?.check_mode === "observe_only") {
    return `运行 ${item?.case_index || "-"}：${statusText(item?.status)}`;
  }
  return `用例 ${item?.case_index || "-"}：${statusText(item?.status)}`;
}

function shouldShowCaseIo(item) {
  return item?.case_index !== 0 && item?.is_sample;
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
.detail-page {
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
  background: transparent;
}

.assignment-lab {
  display: grid;
  grid-template-columns: var(--problem-pane-width, 320px) 8px minmax(0, 1fr);
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
}

.detail-page.ai-open .assignment-lab {
  grid-template-columns: var(--problem-pane-width, 320px) 8px minmax(0, 1fr) 8px var(--ai-pane-width, 360px);
}

.problem-pane,
.editor-pane,
.ai-pane {
  min-width: 0;
  border-right: 1px solid var(--app-line);
  background: rgba(255, 255, 255, 0.96);
}

.problem-pane {
  height: 100vh;
  overflow: auto;
  padding: 16px;
  font-size: var(--compact-body);
}

.back-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--compact-control-height);
  margin-bottom: 10px;
  padding: 0 12px;
  border: 1px solid var(--app-line);
  border-radius: 14px;
  color: #31445f;
  text-decoration: none;
}

.resize-handle {
  width: 8px;
  height: 100vh;
  cursor: col-resize;
  background: #edf2f7;
  border-right: 1px solid var(--app-line);
}

.resize-handle:hover {
  background: #dbe8f5;
}

.ai-resize-handle {
  border-left: 1px solid var(--app-line);
  border-right: none;
}

.problem-header h1,
.problem-content h2,
.editor-toolbar h2,
.ai-header h2,
.result-console h3 {
  margin: 0;
  color: var(--app-text);
}

.problem-header h1 {
  margin: 0 0 8px;
  font-size: var(--compact-page-title);
  line-height: 1.08;
  font-weight: 500;
}

.problem-header p,
.muted {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
  line-height: 1.5;
}

.question-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 12px 0;
}

button,
.question-tabs button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--compact-control-height);
  padding: 0 11px;
  border: 1px solid var(--app-line);
  border-radius: 12px;
  background: #fff;
  color: #31445f;
  cursor: pointer;
}

.question-tabs button.active,
.primary-btn {
  background: var(--app-primary);
  border-color: var(--app-primary);
  color: #fff;
}

.secondary-btn,
.icon-btn {
  background: #fff;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.problem-content {
  display: grid;
  gap: 10px;
}

.problem-content h2,
.editor-toolbar h2,
.ai-header h2,
.result-console h3 {
  font-size: var(--compact-section-title);
  font-weight: 500;
}

.sample-list,
.result-list,
.review-list {
  display: grid;
  gap: 8px;
}

.sample-card,
.result-item,
.ai-answer,
.concept-block,
.trace-box,
.ai-state,
.ai-error {
  padding: 9px 10px;
  border-radius: 12px;
  background: var(--app-panel-soft);
}

pre {
  overflow: auto;
  margin: 6px 0 10px;
  padding: 10px;
  border-radius: 14px;
  background: #15263b;
  color: #fff;
}

.editor-pane {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100vh;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.88);
}

.editor-pane.has-result {
  grid-template-rows: auto minmax(0, 1fr) 8px minmax(160px, var(--result-pane-height, 50%));
}

.editor-toolbar,
.result-console header,
.ai-header,
.ai-review-block header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.editor-toolbar {
  padding: 12px 16px;
  border-bottom: 1px solid var(--app-line);
  background: rgba(255, 255, 255, 0.96);
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.language-pill,
.draft-pill,
.result-status {
  padding: 4px 8px;
  border-radius: 999px;
  background: #eef5ff;
  color: #35639f;
  font-size: var(--compact-caption);
}

.draft-pill {
  background: #f2f4f7;
  color: #667085;
}

.editor-shell {
  min-height: 0;
  padding: 8px;
  overflow: hidden;
}

.objective-shell {
  display: grid;
  align-content: start;
  gap: 12px;
  min-height: 0;
  overflow: auto;
  padding: 18px;
  background: #f8fbff;
}

.choice-option {
  display: grid;
  grid-template-columns: 20px 34px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  border: 1px solid #dce7f5;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
  cursor: pointer;
}

.choice-option.selected {
  border-color: #2563eb;
  box-shadow: inset 3px 0 0 #2563eb;
}

.choice-option input {
  margin-top: 5px;
}

.choice-option span {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  background: #eef4ff;
  color: #2563eb;
  font-weight: 800;
}

.choice-option p {
  margin: 4px 0 0;
  color: #22314d;
  line-height: 1.6;
}

.objective-shell textarea {
  min-height: 240px;
  border: 1px solid #dce7f5;
  border-radius: 8px;
  padding: 14px;
  resize: vertical;
  font: inherit;
}

.question-type-badge {
  display: inline-flex;
  margin-bottom: 12px;
  border-radius: 6px;
  background: #eef4ff;
  color: #2563eb;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 800;
}

.editor-shell :deep(.code-editor) {
  height: 100%;
  min-height: 0;
}

.editor-shell :deep(.cm-editor) {
  height: 100%;
  min-height: 0;
}

.result-resize-handle {
  height: 8px;
  cursor: row-resize;
  background: #edf2f7;
  border-top: 1px solid var(--app-line);
  border-bottom: 1px solid var(--app-line);
}

.result-resize-handle:hover {
  background: #dbe8f5;
}

.result-console {
  overflow: auto;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.96);
}

.result-console header {
  margin-bottom: 10px;
}

.ai-review-block {
  display: grid;
  gap: 10px;
  margin-top: 10px;
  padding: 12px;
  border-radius: 14px;
  background: var(--app-panel-soft);
}

.review-badge {
  padding: 4px 8px;
  border-radius: 999px;
  background: #eef5ff;
  color: #35639f;
  font-size: var(--compact-caption);
}

.ai-reject-alert {
  display: grid;
  gap: 4px;
  margin-bottom: 10px;
  padding: 9px 10px;
  border: 1px solid #f04438;
  border-radius: 12px;
  background: #fff1f0;
  color: #912018;
  box-shadow: 0 8px 20px rgba(180, 35, 24, 0.12);
}

.ai-reject-alert strong {
  color: #7a271a;
  font-size: var(--compact-body);
}

.ai-reject-alert p {
  margin: 0;
  color: #b42318;
  font-size: 13px;
}

.result-console.ai-rejected-result {
  border-top: 3px solid #f04438;
  background: #fffafa;
}

.result-console.ai-rejected-result .ai-review-block {
  border: 1px solid #f97066;
  background: #fff1f0;
}

.result-console.ai-rejected-result .review-badge,
.result-console.ai-rejected-result .result-status.ai_rejected {
  background: #d92d20;
  color: #fff;
}

.review-summary {
  margin: 0;
  color: #34495f;
}

.review-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.review-metrics div {
  padding: 9px;
  border-radius: 12px;
  background: #fff;
}

.review-metrics dt {
  color: #6f8297;
  font-size: 12px;
}

.review-metrics dd {
  margin: 4px 0 0;
  color: var(--app-text);
  font-weight: 400;
}

.review-list strong {
  color: #10283d;
}

.review-list ul {
  margin: 0;
  padding-left: 18px;
  color: #475467;
}

.diagnosis-list {
  display: grid;
  gap: 10px;
}

.diagnosis-list > strong,
.diagnosis-head span {
  color: #10283d;
}

.diagnosis-item {
  display: grid;
  gap: 5px;
  padding: 9px;
  border: 1px solid #d8e2ee;
  border-radius: 14px;
  background: #fff;
}

.diagnosis-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.diagnosis-head span {
  font-weight: 400;
}

.diagnosis-head small {
  flex: 0 0 auto;
  color: #35639f;
}

.diagnosis-resolution {
  justify-self: start;
  min-height: 24px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #f4f7fb;
  color: #526071;
  font-size: 12px;
  line-height: 1.2;
}

.diagnosis-resolution.matched_existing {
  background: #ecfdf3;
  color: #027a48;
}

.diagnosis-resolution.needs_teacher_review {
  background: #fff7e6;
  color: #9a5b00;
}

.diagnosis-item p,
.diagnosis-item small {
  margin: 0;
  color: #526071;
  font-size: 13px;
  line-height: 1.5;
}

.result-item.accepted,
.result-status.accepted {
  background: #ecfdf3;
  color: #027a48;
}

.result-item.wrong_answer,
.result-item.runtime_error,
.result-item.timeout,
.result-item.sandbox_error,
.result-item.needs_manual_review,
.result-item.ai_rejected,
.feedback.error {
  background: #fff8f8;
  color: #b42318;
}

.result-item.ai_rejected {
  border: 1px solid #f97066;
}

.result-status.ai_rejected,
.result-status.wrong_answer,
.result-status.runtime_error,
.result-status.timeout,
.result-status.sandbox_error,
.result-status.needs_manual_review {
  background: #fff1f0;
  color: #b42318;
}

.feedback {
  margin: 12px;
  padding: 10px 12px;
  border: 1px solid var(--app-line);
  border-radius: 14px;
  background: #fff;
}

.ai-pane {
  height: 100vh;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 10px;
  padding: 14px;
  border-right: none;
  border-left: 1px solid var(--app-line);
}

.ai-composer {
  display: grid;
  gap: 10px;
}

textarea {
  width: 100%;
  min-height: 92px;
  padding: 10px;
  border: 1px solid var(--app-line);
  border-radius: 14px;
  resize: none;
  font: inherit;
}

.ai-error {
  background: #fff8f8;
  color: #b42318;
}

.concept-block,
.trace-box {
  display: grid;
  gap: 10px;
}

.concept-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.concept-list span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #edf6ff;
  color: #1f5f99;
  font-size: var(--compact-caption);
}

.trace-box summary {
  color: #18344f;
  cursor: pointer;
  font-weight: 700;
}

.trace-group ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: #5f7287;
}

@media (max-width: 900px) {
  .assignment-lab,
  .detail-page.ai-open .assignment-lab {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(220px, 32vh) 1fr auto;
  }

  .problem-pane,
  .resize-handle,
  .editor-pane,
  .ai-pane {
    height: 100%;
    min-height: 0;
    border-right: none;
    border-bottom: 1px solid #dfe7ef;
  }

  .resize-handle {
    display: none;
  }

  .ai-pane {
    max-height: 100%;
  }

  .editor-pane {
    grid-template-rows: auto minmax(0, 1fr);
  }

  .editor-pane.has-result {
    grid-template-rows: auto minmax(0, 1fr) 8px minmax(160px, var(--result-pane-height, 50%));
  }
}

@media (max-width: 720px) {
  .problem-pane,
  .ai-pane,
  .result-console {
    padding: 12px;
  }

  .editor-toolbar,
  .ai-header,
  .result-console header,
  .ai-review-block header {
    align-items: stretch;
    flex-direction: column;
  }

  .toolbar-actions {
    width: 100%;
  }

  .review-metrics {
    grid-template-columns: 1fr 1fr;
  }

  .toolbar-actions button,
  .toolbar-actions .language-pill,
  .ai-composer button {
    width: 100%;
  }
}
</style>
