<template>
  <div class="detail-page">
    <header class="detail-toolbar">
      <div>
        <p class="eyebrow">Java Practice</p>
        <h1>{{ assignment?.title || "作业" }}</h1>
        <p>{{ assignment?.description || "完成题目后提交代码查看测试结果。" }}</p>
      </div>
      <router-link class="back-link" to="/assignments">返回作业</router-link>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <main v-if="assignment" class="workbench">
      <aside class="question-list">
        <div class="panel-title">
          <h2>题目</h2>
          <span>{{ assignment.questions.length }} 题</span>
        </div>
        <button
          v-for="(question, index) in assignment.questions"
          :key="question.id"
          :class="{ active: activeQuestion?.id === question.id }"
          @click="selectQuestion(question)"
        >
          <span>第 {{ index + 1 }} 题</span>
          <strong>{{ question.title || `题目 ${index + 1}` }}</strong>
          <small>{{ question.language }}</small>
        </button>
      </aside>

      <section v-if="activeQuestion" class="coding-panel">
        <article class="prompt-card">
          <div class="section-title">
            <div>
              <span>题目说明</span>
              <h2>{{ activeQuestion.title || "编程题" }}</h2>
            </div>
            <button type="button" :disabled="submitting || !activeCode.trim()" @click="submitCode">
              {{ submitting ? "运行中..." : "提交运行" }}
            </button>
          </div>
          <MarkdownContent :content="activeQuestion.prompt" />
          <div v-if="sampleCases.length" class="sample-list">
            <article v-for="item in sampleCases" :key="item.id" class="sample-card">
              <strong>示例输入</strong>
              <pre>{{ item.input_data || "(空)" }}</pre>
              <strong>示例输出</strong>
              <pre>{{ item.expected_output || "(空)" }}</pre>
            </article>
          </div>
        </article>

        <article class="code-card">
          <div class="section-title">
            <div>
              <span>Main.java</span>
              <h3>代码编辑</h3>
            </div>
            <button type="button" :disabled="submitting || !activeCode.trim()" @click="submitCode">
              {{ submitting ? "运行中..." : "提交运行" }}
            </button>
          </div>
          <textarea v-model="activeCode" rows="20" spellcheck="false" />
        </article>
      </section>

      <aside v-if="activeQuestion" class="assist-panel">
        <article class="result-card">
          <div class="panel-title">
            <h2>运行结果</h2>
            <span v-if="lastResult">{{ statusText(lastResult.status) }}</span>
          </div>
          <div v-if="lastResult" class="result-list">
            <div v-for="item in lastResult.results" :key="item.case_index" class="result-item" :class="item.status">
              <strong>用例 {{ item.case_index || "编译" }}：{{ statusText(item.status) }}</strong>
              <p v-if="item.summary">{{ item.summary }}</p>
              <template v-if="item.is_sample || item.case_index === 0">
                <span>输入</span>
                <pre>{{ item.input || "(空)" }}</pre>
                <span>期望输出</span>
                <pre>{{ item.expected_output || "(空)" }}</pre>
                <span>实际输出</span>
                <pre>{{ item.actual_output || "(空)" }}</pre>
              </template>
              <pre v-if="item.stderr">{{ item.stderr }}</pre>
            </div>
          </div>
          <p v-else class="muted">提交运行后，测试结果会显示在这里。</p>
        </article>

        <article class="ai-card">
          <div class="panel-title">
            <h2>作业助教</h2>
            <button type="button" :disabled="asking || !aiMessage.trim()" @click="askAi">
              {{ asking ? "思考中..." : "提问" }}
            </button>
          </div>
          <textarea v-model="aiMessage" rows="4" placeholder="描述你卡住的地方，或询问某个报错原因。" />
          <div v-if="aiAnswer" class="ai-answer">
            <MarkdownContent :content="aiAnswer" />
          </div>
        </article>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  askAssignmentAiHelpApi,
  getStudentAssignmentApi,
  submitAssignmentQuestionApi,
} from "../api/assignments";
import MarkdownContent from "../components/MarkdownContent.vue";
import { clearAuthSession } from "../utils/authStorage";

const STARTER_CODE = `public class Main {
    public static void main(String[] args) {
        // 在这里编写你的代码
    }
}
`;

const route = useRoute();
const router = useRouter();
const assignment = ref(null);
const activeQuestion = ref(null);
const codeByQuestion = ref({});
const startedAtByQuestion = ref({});
const lastResultByQuestion = ref({});
const aiMessage = ref("");
const aiAnswer = ref("");
const errorMessage = ref("");
const submitting = ref(false);
const asking = ref(false);

const sampleCases = computed(() => activeQuestion.value?.test_cases?.filter((item) => item.is_sample) || []);
const lastResult = computed(() => {
  if (!activeQuestion.value) return null;
  return lastResultByQuestion.value[activeQuestion.value.id] || null;
});
const activeCode = computed({
  get() {
    if (!activeQuestion.value) return "";
    return codeByQuestion.value[activeQuestion.value.id] ?? STARTER_CODE;
  },
  set(value) {
    if (!activeQuestion.value) return;
    codeByQuestion.value[activeQuestion.value.id] = value;
  },
});

onMounted(loadAssignment);

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
  if (!codeByQuestion.value[question.id]) {
    codeByQuestion.value[question.id] = STARTER_CODE;
  }
  if (!startedAtByQuestion.value[question.id]) {
    startedAtByQuestion.value[question.id] = new Date().toISOString();
  }
  aiMessage.value = "";
  aiAnswer.value = "";
}

async function submitCode() {
  submitting.value = true;
  errorMessage.value = "";
  try {
    const { data } = await submitAssignmentQuestionApi(assignment.value.id, activeQuestion.value.id, {
      code: activeCode.value,
      started_at: startedAtByQuestion.value[activeQuestion.value.id],
    });
    lastResultByQuestion.value[activeQuestion.value.id] = data;
  } catch (error) {
    handleApiError(error, "提交运行失败。");
  } finally {
    submitting.value = false;
  }
}

async function askAi() {
  asking.value = true;
  errorMessage.value = "";
  try {
    const { data } = await askAssignmentAiHelpApi(assignment.value.id, activeQuestion.value.id, {
      message: aiMessage.value,
      code: activeCode.value,
      last_result: lastResult.value,
    });
    aiAnswer.value = data.answer;
  } catch (error) {
    handleApiError(error, "AI 帮助失败。");
  } finally {
    asking.value = false;
  }
}

function statusText(status) {
  return {
    accepted: "通过",
    wrong_answer: "答案错误",
    runtime_error: "运行错误",
    timeout: "超时",
    sandbox_error: "沙箱错误",
    published: "已发布",
    closed: "已关闭",
  }[status] || status;
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
  min-height: 100vh;
  padding: 24px;
  display: grid;
  gap: 16px;
  background: #f7fbff;
}

.detail-toolbar,
.section-title,
.panel-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.detail-toolbar h1 {
  margin: 6px 0 8px;
  color: #0f2840;
  font-size: 34px;
}

.detail-toolbar p,
.section-title span,
.panel-title span,
.muted {
  margin: 0;
  color: #6f8297;
}

.eyebrow {
  margin: 0;
  color: #5b86b3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.workbench {
  display: grid;
  grid-template-columns: 230px minmax(0, 1fr) 360px;
  gap: 14px;
  align-items: start;
}

.question-list,
.prompt-card,
.code-card,
.result-card,
.ai-card,
.feedback {
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.question-list,
.result-card,
.ai-card {
  padding: 14px;
}

.question-list,
.assist-panel,
.coding-panel {
  display: grid;
  gap: 14px;
}

.question-list,
.assist-panel {
  position: sticky;
  top: 18px;
}

.question-list button {
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 10px;
  text-align: left;
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
  color: #18344f;
  cursor: pointer;
}

.question-list button.active {
  border-color: #9cc7ef;
  background: #f3f9ff;
}

.question-list button span,
.question-list button small {
  color: #6f8297;
  font-size: 12px;
}

.question-list button strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-card,
.code-card {
  padding: 16px;
}

.section-title h2,
.section-title h3,
.panel-title h2 {
  margin: 0;
  color: #10283d;
}

.sample-list,
.result-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.sample-card,
.result-item,
.ai-answer {
  padding: 12px;
  border-radius: 8px;
  background: #f8fbff;
}

textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  font-family: Consolas, "Courier New", monospace;
  resize: none;
}

.code-card textarea {
  min-height: clamp(360px, 54vh, 640px);
  margin-top: 12px;
}

.ai-card textarea {
  min-height: clamp(96px, 16vh, 150px);
}

pre {
  overflow: auto;
  margin: 6px 0 10px;
  padding: 10px;
  border-radius: 8px;
  background: #10283d;
  color: #fff;
}

.back-link,
button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  background: #fff;
  color: #18344f;
  cursor: pointer;
  text-decoration: none;
}

.section-title button,
.panel-title button {
  background: #10283d;
  border-color: #10283d;
  color: #fff;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.result-item.accepted {
  background: #ecfdf3;
}

.result-item.wrong_answer,
.result-item.runtime_error,
.result-item.timeout,
.result-item.sandbox_error,
.feedback.error {
  background: #fff8f8;
  color: #b42318;
}

.feedback {
  padding: 12px 14px;
}

@media (max-width: 1180px) {
  .workbench {
    grid-template-columns: 1fr;
  }

  .question-list,
  .assist-panel {
    position: static;
  }
}

@media (max-width: 720px) {
  .detail-page {
    padding: 16px;
  }

  .detail-toolbar,
  .section-title,
  .panel-title {
    display: grid;
  }
}
</style>
