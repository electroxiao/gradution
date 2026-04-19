<template>
  <section class="progress-page">
    <header class="progress-toolbar">
      <div>
        <p class="eyebrow">Assignment Progress</p>
        <h2>{{ progress?.title || "作业完成情况" }}</h2>
        <p>按学生和题目查看最新提交、运行耗时和作答耗时。</p>
      </div>
      <div class="toolbar-actions">
        <router-link class="secondary-link" :to="`/teacher/assignments/${assignmentId}`">编辑作业</router-link>
        <router-link class="secondary-link" to="/teacher/assignments">返回列表</router-link>
      </div>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section v-if="progress" class="summary-row">
      <article class="summary-card">
        <span>发布学生</span>
        <strong>{{ progress.students.length }}</strong>
      </article>
      <article class="summary-card">
        <span>题目数量</span>
        <strong>{{ progress.questions.length }}</strong>
      </article>
      <article class="summary-card">
        <span>已提交格子</span>
        <strong>{{ submittedCells }}</strong>
      </article>
      <article class="summary-card">
        <span>通过格子</span>
        <strong>{{ acceptedCells }}</strong>
      </article>
    </section>

    <main v-if="progress" class="progress-layout">
      <section class="matrix-panel">
        <div class="matrix-scroll">
          <div class="matrix-grid" :style="matrixStyle">
            <div class="matrix-head sticky-left">学生</div>
            <div v-for="question in progress.questions" :key="question.id" class="matrix-head">
              {{ question.title || `题目 ${question.sort_order + 1}` }}
            </div>

            <template v-for="student in progress.students" :key="student.id">
              <div class="student-cell sticky-left">{{ student.username }}</div>
              <button
                v-for="question in progress.questions"
                :key="`${student.id}-${question.id}`"
                type="button"
                class="progress-cell"
                :class="cellFor(student.id, question.id).status"
                @click="selectCell(student, question, cellFor(student.id, question.id))"
              >
                <strong>{{ statusText(cellFor(student.id, question.id).status) }}</strong>
                <span>{{ cellFor(student.id, question.id).submission_count || 0 }} 次提交</span>
                <small>{{ formatDateTime(cellFor(student.id, question.id).submitted_at) }}</small>
                <small>
                  运行 {{ formatRunTime(cellFor(student.id, question.id).run_time_ms) }} /
                  作答 {{ formatDuration(cellFor(student.id, question.id).duration_seconds) }}
                </small>
              </button>
            </template>
          </div>
        </div>
      </section>

      <aside class="detail-panel">
        <template v-if="selectedCell">
          <div class="detail-header">
            <div>
              <p class="eyebrow">Submission Detail</p>
              <h3>{{ selectedStudent?.username }} / {{ selectedQuestion?.title }}</h3>
            </div>
            <span class="status-pill" :class="selectedCell.status">{{ statusText(selectedCell.status) }}</span>
          </div>

          <div v-if="selectedCell.latest_submission_id && selectedSubmission" class="detail-body">
            <dl class="meta-grid">
              <div>
                <dt>提交时间</dt>
                <dd>{{ formatDateTime(selectedSubmission.submitted_at) }}</dd>
              </div>
              <div>
                <dt>提交次数</dt>
                <dd>{{ selectedCell.submission_count }}</dd>
              </div>
              <div>
                <dt>运行耗时</dt>
                <dd>{{ formatRunTime(selectedSubmission.run_time_ms) }}</dd>
              </div>
              <div>
                <dt>作答耗时</dt>
                <dd>{{ formatDuration(selectedSubmission.duration_seconds) }}</dd>
              </div>
            </dl>

            <section class="detail-section">
              <h4>提交代码</h4>
              <pre class="code-block">{{ selectedSubmission.code }}</pre>
            </section>

            <section class="detail-section">
              <h4>测试结果</h4>
              <article
                v-for="item in selectedSubmission.results_json || []"
                :key="item.case_index"
                class="result-card"
                :class="item.status"
              >
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
              </article>
            </section>
          </div>

          <p v-else-if="selectedCell.latest_submission_id" class="muted">提交详情加载中...</p>
          <p v-else class="muted">该学生还没有提交这道题。</p>
        </template>

        <p v-else class="muted">点击矩阵中的单元格查看提交代码和运行结果。</p>
      </aside>
    </main>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { getTeacherAssignmentProgressApi, getTeacherAssignmentSubmissionApi } from "../api/assignments";
import { clearAuthSession } from "../utils/authStorage";

const route = useRoute();
const router = useRouter();
const assignmentId = Number(route.params.assignmentId);
const progress = ref(null);
const selectedCell = ref(null);
const selectedStudent = ref(null);
const selectedQuestion = ref(null);
const selectedSubmission = ref(null);
const errorMessage = ref("");

const cellMap = computed(() => {
  const map = new Map();
  for (const cell of progress.value?.cells || []) {
    map.set(`${cell.student_id}:${cell.question_id}`, cell);
  }
  return map;
});
const matrixStyle = computed(() => ({
  gridTemplateColumns: `180px repeat(${progress.value?.questions.length || 0}, minmax(190px, 1fr))`,
}));
const submittedCells = computed(() =>
  (progress.value?.cells || []).filter((cell) => cell.status !== "not_submitted").length,
);
const acceptedCells = computed(() =>
  (progress.value?.cells || []).filter((cell) => cell.status === "accepted").length,
);

onMounted(loadProgress);

async function loadProgress() {
  try {
    const { data } = await getTeacherAssignmentProgressApi(assignmentId);
    progress.value = data;
  } catch (error) {
    handleApiError(error, "加载完成情况失败。");
  }
}

function cellFor(studentId, questionId) {
  return cellMap.value.get(`${studentId}:${questionId}`) || {
    student_id: studentId,
    question_id: questionId,
    status: "not_submitted",
    submission_count: 0,
  };
}

async function selectCell(student, question, cell) {
  selectedCell.value = cell;
  selectedStudent.value = student;
  selectedQuestion.value = question;
  selectedSubmission.value = null;
  if (!cell.latest_submission_id) return;

  try {
    const { data } = await getTeacherAssignmentSubmissionApi(assignmentId, cell.latest_submission_id);
    selectedSubmission.value = data;
  } catch (error) {
    handleApiError(error, "加载提交详情失败。");
  }
}

function statusText(status) {
  return {
    not_submitted: "未提交",
    accepted: "通过",
    wrong_answer: "答案错误",
    runtime_error: "运行错误",
    timeout: "超时",
    sandbox_error: "沙箱错误",
  }[status] || status;
}

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatRunTime(value) {
  if (value === null || value === undefined) return "--";
  return `${value} ms`;
}

function formatDuration(value) {
  if (value === null || value === undefined) return "--";
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return minutes ? `${minutes}m ${seconds}s` : `${seconds}s`;
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
.progress-page {
  display: grid;
  gap: 16px;
}

.progress-toolbar,
.toolbar-actions,
.detail-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.progress-toolbar h2 {
  margin: 6px 0 8px;
  color: #0f2840;
  font-size: 32px;
}

.progress-toolbar p,
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

.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  background: #fff;
  color: #18344f;
  text-decoration: none;
  white-space: nowrap;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card,
.matrix-panel,
.detail-panel,
.feedback {
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.summary-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
}

.summary-card span {
  color: #6f8297;
  font-size: 13px;
}

.summary-card strong {
  color: #10283d;
  font-size: 24px;
}

.progress-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 14px;
  align-items: start;
}

.matrix-panel,
.detail-panel {
  overflow: hidden;
}

.matrix-scroll {
  overflow: auto;
}

.matrix-grid {
  display: grid;
  min-width: 760px;
}

.matrix-head,
.student-cell,
.progress-cell {
  min-height: 78px;
  padding: 10px;
  border-right: 1px solid #eef3f8;
  border-bottom: 1px solid #eef3f8;
}

.matrix-head {
  min-height: 48px;
  background: #f8fbff;
  color: #6f8297;
  font-size: 13px;
  font-weight: 700;
}

.sticky-left {
  position: sticky;
  left: 0;
  z-index: 1;
  border-left: 0;
}

.student-cell {
  display: flex;
  align-items: center;
  background: #fff;
  color: #10283d;
  font-weight: 700;
}

.progress-cell {
  display: grid;
  gap: 3px;
  text-align: left;
  border-top: 0;
  border-left: 0;
  background: #f8fbff;
  color: #475467;
  cursor: pointer;
}

.progress-cell strong {
  color: #10283d;
}

.progress-cell span,
.progress-cell small {
  color: #6f8297;
}

.progress-cell.accepted {
  background: #ecfdf3;
}

.progress-cell.wrong_answer {
  background: #fff7ed;
}

.progress-cell.runtime_error,
.progress-cell.timeout,
.progress-cell.sandbox_error {
  background: #fff8f8;
}

.detail-panel {
  position: sticky;
  top: 18px;
  display: grid;
  gap: 14px;
  max-height: calc(100vh - 120px);
  overflow: auto;
  padding: 16px;
}

.detail-header h3 {
  margin: 6px 0 0;
  color: #10283d;
}

.status-pill {
  padding: 5px 9px;
  border-radius: 8px;
  background: #f2f4f7;
  color: #475467;
  white-space: nowrap;
}

.status-pill.accepted {
  background: #ecfdf3;
  color: #027a48;
}

.status-pill.wrong_answer {
  background: #fff7ed;
  color: #c2410c;
}

.status-pill.runtime_error,
.status-pill.timeout,
.status-pill.sandbox_error {
  background: #fff8f8;
  color: #b42318;
}

.detail-body,
.detail-section {
  display: grid;
  gap: 12px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.meta-grid div {
  padding: 10px;
  border-radius: 8px;
  background: #f8fbff;
}

.meta-grid dt {
  color: #6f8297;
  font-size: 12px;
}

.meta-grid dd {
  margin: 4px 0 0;
  color: #10283d;
  font-weight: 700;
}

.detail-section h4 {
  margin: 0;
  color: #10283d;
}

pre {
  overflow: auto;
  margin: 6px 0 10px;
  padding: 10px;
  border-radius: 8px;
  background: #10283d;
  color: #fff;
}

.code-block {
  max-height: 360px;
}

.result-card {
  padding: 12px;
  border-radius: 8px;
  background: #f8fbff;
}

.result-card.accepted {
  background: #ecfdf3;
}

.result-card.wrong_answer {
  background: #fff7ed;
}

.result-card.runtime_error,
.result-card.timeout,
.result-card.sandbox_error,
.feedback.error {
  background: #fff8f8;
  color: #b42318;
}

.feedback {
  padding: 12px 14px;
}

@media (max-width: 1180px) {
  .progress-layout {
    grid-template-columns: 1fr;
  }

  .detail-panel {
    position: static;
    max-height: none;
  }
}

@media (max-width: 720px) {
  .progress-toolbar,
  .toolbar-actions,
  .detail-header {
    display: grid;
  }

  .summary-row,
  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
