<template>
  <div class="detail-page">
    <header class="hero">
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
        <button
          v-for="question in assignment.questions"
          :key="question.id"
          :class="{ active: activeQuestion?.id === question.id }"
          @click="selectQuestion(question)"
        >
          <strong>{{ question.title || `第 ${question.sort_order + 1} 题` }}</strong>
          <span>{{ question.language }}</span>
        </button>
      </aside>

      <section v-if="activeQuestion" class="question-panel">
        <article class="prompt-card">
          <h2>{{ activeQuestion.title || "编程题" }}</h2>
          <MarkdownContent :content="activeQuestion.prompt" />
          <div v-if="sampleCases.length" class="sample-list">
            <h3>示例测试</h3>
            <article v-for="item in sampleCases" :key="item.id" class="sample-card">
              <strong>输入</strong>
              <pre>{{ item.input_data || "(空)" }}</pre>
              <strong>期望输出</strong>
              <pre>{{ item.expected_output || "(空)" }}</pre>
            </article>
          </div>
        </article>

        <article class="code-card">
          <div class="section-title">
            <h3>代码</h3>
            <button type="button" :disabled="submitting || !code.trim()" @click="submitCode">
              {{ submitting ? "运行中..." : "提交运行" }}
            </button>
          </div>
          <textarea v-model="code" rows="16" spellcheck="false" />
        </article>

        <article v-if="lastResult" class="result-card">
          <h3>运行结果：{{ statusText(lastResult.status) }}</h3>
          <div class="result-list">
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
        </article>

        <article class="ai-card">
          <div class="section-title">
            <h3>作业助教</h3>
            <button type="button" :disabled="asking || !aiMessage.trim()" @click="askAi">
              {{ asking ? "思考中..." : "提问" }}
            </button>
          </div>
          <textarea v-model="aiMessage" rows="3" placeholder="描述你卡住的地方，或询问某个报错原因。" />
          <div v-if="aiAnswer" class="ai-answer">
            <MarkdownContent :content="aiAnswer" />
          </div>
        </article>
      </section>
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

const route = useRoute();
const router = useRouter();
const assignment = ref(null);
const activeQuestion = ref(null);
const code = ref(`public class Main {
    public static void main(String[] args) {
        // 在这里编写你的代码
    }
}
`);
const lastResult = ref(null);
const aiMessage = ref("");
const aiAnswer = ref("");
const errorMessage = ref("");
const submitting = ref(false);
const asking = ref(false);

const sampleCases = computed(() => activeQuestion.value?.test_cases?.filter((item) => item.is_sample) || []);

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
  lastResult.value = null;
  aiAnswer.value = "";
}

async function submitCode() {
  submitting.value = true;
  errorMessage.value = "";
  try {
    const { data } = await submitAssignmentQuestionApi(assignment.value.id, activeQuestion.value.id, {
      code: code.value,
    });
    lastResult.value = data;
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
      code: code.value,
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
  padding: 28px;
  display: grid;
  gap: 22px;
  background: #f7fbff;
}

.hero,
.section-title {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.hero h1 {
  margin: 8px 0 10px;
  font-size: 38px;
  color: #0f2840;
}

.hero p {
  margin: 0;
  color: #6f8297;
}

.eyebrow {
  color: #5b86b3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.back-link,
button {
  padding: 10px 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  background: #fff;
  color: #18344f;
  cursor: pointer;
  text-decoration: none;
}

.section-title button {
  background: #10283d;
  border-color: #10283d;
  color: #fff;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.workbench {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 16px;
}

.question-list,
.prompt-card,
.code-card,
.result-card,
.ai-card,
.feedback {
  padding: 18px;
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
}

.question-list {
  display: grid;
  gap: 8px;
  align-self: start;
}

.question-list button {
  display: grid;
  gap: 4px;
  text-align: left;
}

.question-list button.active {
  background: #edf6ff;
}

.question-panel {
  display: grid;
  gap: 16px;
}

.prompt-card h2,
.section-title h3,
.result-card h3 {
  margin: 0;
}

textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  font-family: Consolas, "Courier New", monospace;
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

pre {
  overflow: auto;
  margin: 6px 0 10px;
  padding: 10px;
  border-radius: 8px;
  background: #10283d;
  color: #fff;
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

@media (max-width: 900px) {
  .workbench {
    grid-template-columns: 1fr;
  }
}
</style>
