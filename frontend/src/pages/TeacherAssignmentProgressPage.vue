<template>
  <section class="progress-page">
    <header class="progress-toolbar shell-card">
      <div>
        <h2>{{ progress?.title || "作业完成情况" }}</h2>
        <p>按学生和题目查看最新提交、运行耗时、AI 评审与教师复核结果。</p>
      </div>
      <div class="toolbar-actions">
        <router-link class="secondary-link" :to="`/teacher/assignments/${assignmentId}`">编辑作业</router-link>
        <router-link class="secondary-link" to="/teacher/assignments">返回列表</router-link>
      </div>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section v-if="progress" class="summary-row">
      <article class="summary-card shell-card">
        <span>发布学生</span>
        <strong>{{ progress.students.length }}</strong>
      </article>
      <article class="summary-card shell-card">
        <span>题目数量</span>
        <strong>{{ progress.questions.length }}</strong>
      </article>
      <article class="summary-card shell-card">
        <span>已提交格子</span>
        <strong>{{ submittedCells }}</strong>
      </article>
      <article class="summary-card shell-card">
        <span>通过格子</span>
        <strong>{{ acceptedCells }}</strong>
      </article>
    </section>

    <main v-if="progress" class="progress-layout">
      <section class="matrix-panel shell-card">
        <div class="panel-header">
          <div>
            <h3>学生完成矩阵</h3>
          </div>
          <p class="muted">点击任意格子查看代码、测试结果、AI 评审和教师复核。</p>
        </div>

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

      <aside class="detail-panel shell-card">
        <template v-if="selectedCell">
          <div class="detail-header">
            <div>
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
              <h4>作业画像信息</h4>
              <dl class="meta-grid">
                <div>
                  <dt>可信度标签</dt>
                  <dd>{{ trustLabelText(selectedSubmission.trust_label) }}</dd>
                </div>
                <div>
                  <dt>计入图谱画像</dt>
                  <dd>{{ selectedSubmission.excluded_from_mastery_update ? "否" : "是" }}</dd>
                </div>
              </dl>
              <div v-if="selectedQuestion?.knowledge_nodes?.length" class="tag-list">
                <span v-for="node in selectedQuestion.knowledge_nodes" :key="node.id" class="tag-pill">{{ node.node_name }}</span>
              </div>
              <p v-if="selectedSubmission.excluded_from_mastery_update" class="muted">
                该次提交因“异常速通”未计入知识图谱画像更新。
              </p>
            </section>

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

            <section v-if="selectedSubmission.ai_review_json" class="detail-section">
              <div class="review-head">
                <h4>AI 评审</h4>
                <span class="decision-pill">{{ decisionSourceText(selectedSubmission.decision_source) }}</span>
              </div>
              <p class="review-summary">{{ selectedSubmission.ai_review_json.summary || "AI 未返回总结。" }}</p>
              <dl class="meta-grid">
                <div>
                  <dt>AI 决策</dt>
                  <dd>{{ statusText(selectedSubmission.ai_review_json.decision || selectedSubmission.status) }}</dd>
                </div>
                <div>
                  <dt>评分</dt>
                  <dd>{{ selectedSubmission.ai_review_json.score ?? "--" }}</dd>
                </div>
                <div>
                  <dt>置信度</dt>
                  <dd>{{ formatConfidence(selectedSubmission.ai_review_json.confidence) }}</dd>
                </div>
                <div>
                  <dt>人工复核</dt>
                  <dd>{{ selectedSubmission.manual_review_required ? "需要" : "无需" }}</dd>
                </div>
              </dl>
              <div v-if="selectedSubmission.ai_review_json.issues?.length" class="review-list">
                <strong>风险点</strong>
                <ul>
                  <li v-for="(item, index) in selectedSubmission.ai_review_json.issues" :key="`issue-${index}`">{{ item }}</li>
                </ul>
              </div>
              <div v-if="selectedSubmission.ai_review_json.strengths?.length" class="review-list">
                <strong>实现优点</strong>
                <ul>
                  <li v-for="(item, index) in selectedSubmission.ai_review_json.strengths" :key="`strength-${index}`">{{ item }}</li>
                </ul>
              </div>
            </section>

            <section class="detail-section">
              <div class="review-head">
                <h4>教师复核</h4>
                <span v-if="selectedSubmission.teacher_review_status" class="decision-pill secondary">
                  {{ teacherReviewText(selectedSubmission.teacher_review_status) }}
                </span>
              </div>
              <p class="muted" v-if="selectedSubmission.reviewed_by_username">
                最近由 {{ selectedSubmission.reviewed_by_username }} 于 {{ formatDateTime(selectedSubmission.reviewed_at) }} 复核
              </p>
              <textarea
                v-model="reviewNote"
                rows="3"
                placeholder="输入改判备注，例如：SQL 结果对，但事务边界不符合要求。"
              />
              <div class="review-actions">
                <button type="button" :disabled="reviewing" @click="submitReview('accepted')">标记通过</button>
                <button type="button" :disabled="reviewing" @click="submitReview('needs_manual_review')">保持待复核</button>
                <button type="button" :disabled="reviewing" @click="submitReview('ai_rejected')">标记未通过</button>
              </div>
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

import {
  getTeacherAssignmentProgressApi,
  getTeacherAssignmentSubmissionApi,
  reviewTeacherAssignmentSubmissionApi,
} from "../api/assignments";
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
const reviewNote = ref("");
const reviewing = ref(false);

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
  reviewNote.value = "";
  if (!cell.latest_submission_id) return;

  try {
    const { data } = await getTeacherAssignmentSubmissionApi(assignmentId, cell.latest_submission_id);
    selectedSubmission.value = data;
    reviewNote.value = data.teacher_review_note || "";
  } catch (error) {
    handleApiError(error, "加载提交详情失败。");
  }
}

async function submitReview(targetStatus) {
  if (!selectedSubmission.value?.id) return;
  reviewing.value = true;
  errorMessage.value = "";
  try {
    const { data } = await reviewTeacherAssignmentSubmissionApi(assignmentId, selectedSubmission.value.id, {
      status: targetStatus,
      note: reviewNote.value,
    });
    selectedSubmission.value = data;
    reviewNote.value = data.teacher_review_note || "";
    await loadProgress();
    if (selectedStudent.value && selectedQuestion.value) {
      selectedCell.value = cellFor(selectedStudent.value.id, selectedQuestion.value.id);
    }
  } catch (error) {
    handleApiError(error, "提交教师复核失败。");
  } finally {
    reviewing.value = false;
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
    needs_manual_review: "待人工复核",
    ai_rejected: "AI 判定未通过",
  }[status] || status;
}

function decisionSourceText(value) {
  return {
    testcase: "测试用例结果",
    ai_review: "AI 评审结果",
    hybrid: "混合判题结果",
    ai_with_testcases: "AI + 测试用例",
    ai_only: "AI 判题结果",
    teacher_override: "教师改判",
  }[value] || "系统判定";
}

function teacherReviewText(value) {
  return {
    pending: "待处理",
    approved: "教师通过",
    rejected: "教师驳回",
  }[value] || value;
}

function trustLabelText(value) {
  return {
    normal: "正常",
    suspicious_fast_pass: "异常速通",
  }[value] || "正常";
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

function formatConfidence(value) {
  const number = Number(value);
  if (Number.isNaN(number)) return "--";
  return `${Math.round(number * 100)}%`;
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
  gap: 22px;
}

.shell-card,
.feedback {
  border: 1px solid var(--app-line);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--app-shadow);
}

.progress-toolbar,
.toolbar-actions,
.detail-header,
.panel-header,
.review-head,
.review-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.progress-toolbar {
  padding: 20px 22px;
}

.progress-toolbar h2 {
  margin: 0 0 8px;
  color: var(--app-text);
  font-size: 32px;
}

.progress-toolbar p,
.muted {
  margin: 0;
  color: var(--app-text-muted);
}

.panel-header h3,
.detail-header h3 {
  margin: 0;
  color: #10283d;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid var(--app-line);
  border-radius: 14px;
  background: #fff;
  color: #31445f;
  text-decoration: none;
  white-space: nowrap;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  display: grid;
  gap: 6px;
  padding: 18px;
}

.summary-card span {
  color: #6f8297;
  font-size: 13px;
}

.summary-card strong {
  color: #10283d;
  font-size: 28px;
}

.progress-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 16px;
  align-items: start;
}

.matrix-panel {
  display: grid;
  gap: 16px;
  padding: 18px;
  overflow: hidden;
}

.matrix-scroll {
  overflow: auto;
  border: 1px solid #e4edf6;
  border-radius: 18px;
  background: #f8fbff;
}

.matrix-grid {
  display: grid;
  min-width: 760px;
}

.matrix-head,
.student-cell,
.progress-cell {
  min-height: 78px;
  padding: 12px;
  border-right: 1px solid #e7eff7;
  border-bottom: 1px solid #e7eff7;
}

.matrix-head {
  min-height: 48px;
  background: #eef6ff;
  color: #6f8297;
  font-size: 13px;
  font-weight: 700;
}

.sticky-left {
  position: sticky;
  left: 0;
  z-index: 1;
}

.student-cell {
  display: flex;
  align-items: center;
  background: #fdfefe;
  color: #10283d;
  font-weight: 700;
}

.progress-cell {
  display: grid;
  gap: 3px;
  text-align: left;
  border-top: 0;
  border-left: 0;
  background: rgba(248, 251, 255, 0.88);
  color: #475467;
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
}

.progress-cell:hover {
  transform: translateY(-1px);
  box-shadow: inset 0 0 0 1px rgba(31, 95, 153, 0.16);
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
.progress-cell.sandbox_error,
.progress-cell.ai_rejected {
  background: #fff2f2;
}

.progress-cell.needs_manual_review {
  background: #fff4d8;
}

.detail-panel {
  position: sticky;
  top: 18px;
  display: grid;
  gap: 14px;
  max-height: calc(100vh - 120px);
  overflow: auto;
  padding: 18px;
}

.status-pill,
.decision-pill {
  padding: 7px 12px;
  border-radius: 999px;
  white-space: nowrap;
  font-weight: 700;
}

.status-pill {
  background: #f2f4f7;
  color: #475467;
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
.status-pill.sandbox_error,
.status-pill.ai_rejected {
  background: #fff2f2;
  color: #b42318;
}

.status-pill.needs_manual_review {
  background: #fff4d8;
  color: #9a6700;
}

.detail-body,
.detail-section,
.review-list {
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
  padding: 12px;
  border-radius: 14px;
  background: rgba(239, 246, 255, 0.72);
  border: 1px solid #deebf7;
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

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-pill {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: #eef6ff;
  color: #1f5f99;
  font-size: 12px;
  font-weight: 700;
}

.decision-pill {
  background: #eef6ff;
  color: #1f5f99;
}

.decision-pill.secondary {
  background: #f2f4f7;
  color: #475467;
}

.review-summary {
  margin: 0;
  color: #34495f;
}

.review-list ul {
  margin: 0;
  padding-left: 18px;
  color: #475467;
}

textarea,
button {
  font: inherit;
}

textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #d7e5f3;
  border-radius: 14px;
  resize: vertical;
}

button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid #d4e4f2;
  border-radius: 14px;
  background: #fff;
  color: #18344f;
  cursor: pointer;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

pre {
  overflow: auto;
  margin: 6px 0 10px;
  padding: 12px;
  border-radius: 14px;
  background: #10283d;
  color: #fff;
}

.code-block {
  max-height: 360px;
}

.result-card {
  padding: 12px;
  border-radius: 14px;
  background: #f8fbff;
  border: 1px solid #e5eef7;
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
.result-card.ai_rejected,
.feedback.error {
  background: #fff2f2;
  color: #b42318;
}

.result-card.needs_manual_review {
  background: #fff4d8;
  color: #9a6700;
}

.feedback {
  padding: 14px 16px;
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
  .panel-header,
  .detail-header,
  .review-head,
  .review-actions,
  .summary-row,
  .meta-grid {
    display: grid;
  }

  .summary-row,
  .meta-grid {
    grid-template-columns: 1fr;
  }

  .toolbar-actions .secondary-link,
  .review-actions button {
    width: 100%;
  }
}
</style>
