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
        <span>已提交</span>
        <strong>{{ submittedStudents }}</strong>
      </article>
      <article class="summary-card shell-card">
        <span>未提交</span>
        <strong>{{ unsubmittedStudents }}</strong>
      </article>
    </section>

    <main v-if="progress" class="progress-layout">
      <section class="matrix-panel shell-card">
        <div class="panel-header">
          <div>
            <h3>学生完成矩阵</h3>
            <p class="muted">点击格子查看该学生该题的全部提交记录。</p>
          </div>
          <div class="view-tabs">
            <button type="button" :class="{ active: matrixFilter === 'all' }" @click="matrixFilter = 'all'">全部</button>
            <button type="button" :class="{ active: matrixFilter === 'unsubmitted' }" @click="matrixFilter = 'unsubmitted'">未提交</button>
            <button type="button" :class="{ active: matrixFilter === 'submitted' }" @click="matrixFilter = 'submitted'">已提交</button>
          </div>
        </div>

        <div class="matrix-scroll">
          <div class="matrix-grid" :style="matrixStyle">
            <div class="matrix-head sticky-left">学生</div>
            <div v-for="question in progress.questions" :key="question.id" class="matrix-head">
              {{ question.title || `题目 ${question.sort_order + 1}` }}
            </div>

            <template v-for="student in filteredStudents" :key="student.id">
              <div class="student-cell sticky-left">{{ student.username }}</div>
              <button
                v-for="question in progress.questions"
                :key="`${student.id}-${question.id}`"
                type="button"
                class="progress-cell"
                :class="[cellFor(student.id, question.id).status, { muted: !isCellInFilter(cellFor(student.id, question.id)) }]"
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
        <div v-if="!filteredStudents.length" class="empty-state">当前筛选下没有学生。</div>
      </section>
    </main>

    <div v-if="selectedCell" class="modal-backdrop" @click.self="closeDetail">
      <section class="detail-dialog shell-card">
        <div class="detail-dialog-bar">
          <div class="detail-header">
            <div>
              <h3>{{ selectedStudent?.username }} / {{ selectedQuestion?.title }}</h3>
            </div>
            <span class="status-pill" :class="selectedCell.status">{{ statusText(selectedCell.status) }}</span>
          </div>
          <button type="button" class="close-button" @click="closeDetail">关闭</button>
        </div>

          <div v-if="selectedCell.latest_submission_id && selectedSubmission" class="detail-body">
            <section class="detail-section">
              <div class="review-head">
                <h4>提交时间线</h4>
                <span class="decision-pill secondary">{{ selectedSubmissions.length }} 次提交</span>
              </div>
              <div class="submission-timeline">
                <button
                  v-for="(submission, index) in selectedSubmissions"
                  :key="submission.id"
                  type="button"
                  class="timeline-item"
                  :class="{ active: submission.id === selectedSubmission.id }"
                  @click="selectSubmission(submission)"
                >
                  <strong>#{{ selectedSubmissions.length - index }} {{ statusText(submission.status) }}</strong>
                  <span>{{ evidenceText(submission) }}</span>
                  <small>{{ formatDateTime(submission.submitted_at) }}</small>
                </button>
              </div>
            </section>

            <dl class="meta-grid">
              <div>
                <dt>提交时间</dt>
                <dd>{{ formatDateTime(selectedSubmission.submitted_at) }}</dd>
              </div>
              <div>
                <dt>提交次数</dt>
                <dd>{{ selectedSubmissions.length || selectedCell.submission_count }}</dd>
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
                  <dt>证据类型</dt>
                  <dd>{{ evidenceText(selectedSubmission) }}</dd>
                </div>
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
                <span>绑定知识点：</span>
                <span v-for="node in selectedQuestion.knowledge_nodes" :key="node.id" class="tag-pill">{{ node.node_name }}</span>
              </div>
              <div v-if="aiDiagnoses.length" class="diagnosis-summary">
                <span>AI 诊断：</span>
                <span v-for="(d, idx) in aiDiagnoses" :key="idx" class="tag-pill diagnosis-tag" :class="d.resolved ? 'resolved' : 'unresolved'">
                  {{ d.knowledge_node || "unknown" }}
                  <small>({{ formatConfidence(d.confidence) }})</small>
                </span>
              </div>
              <p v-if="selectedSubmission.excluded_from_mastery_update" class="muted">
                该次提交因"{{ trustLabelText(selectedSubmission.trust_label) }}"未计入知识图谱画像更新。
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
                <strong>
                  {{ item.check_mode === "observe_only" ? "运行" : "用例" }}
                  {{ item.case_index || "编译" }}：{{ statusText(item.status) }}
                </strong>
                <p v-if="item.summary">{{ item.summary }}</p>
                <template v-if="item.is_sample || item.case_index === 0">
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
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  getTeacherAssignmentProgressApi,
  listTeacherAssignmentQuestionSubmissionsApi,
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
const selectedSubmissions = ref([]);
const errorMessage = ref("");
const reviewNote = ref("");
const reviewing = ref(false);
const matrixFilter = ref("all");

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
const fullySubmittedStudentIds = computed(() => {
  const ids = new Set();
  if (!progress.value?.questions.length) return ids;
  for (const student of progress.value.students || []) {
    const allSubmitted = progress.value.questions.every(
      (question) => cellFor(student.id, question.id).status !== "not_submitted",
    );
    if (allSubmitted) ids.add(student.id);
  }
  return ids;
});
const submittedStudents = computed(() => fullySubmittedStudentIds.value.size);
const unsubmittedStudents = computed(() => Math.max((progress.value?.students.length || 0) - submittedStudents.value, 0));
const filteredStudents = computed(() => {
  if (!progress.value) return [];
  if (matrixFilter.value === "submitted") {
    return progress.value.students.filter((student) => fullySubmittedStudentIds.value.has(student.id));
  }
  if (matrixFilter.value === "unsubmitted") {
    return progress.value.students.filter((student) => !fullySubmittedStudentIds.value.has(student.id));
  }
  return progress.value.students;
});

const aiDiagnoses = computed(() => {
  const review = selectedSubmission.value?.ai_review_json;
  if (!review?.diagnoses?.length) return [];
  return review.diagnoses.map((d) => ({
    ...d,
    resolved: d.graph_resolution?.status === "matched_existing",
  }));
});

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
  selectedSubmissions.value = [];
  reviewNote.value = "";
  if (!cell.latest_submission_id) return;

  try {
    const { data } = await listTeacherAssignmentQuestionSubmissionsApi(assignmentId, student.id, question.id);
    selectedSubmissions.value = data.submissions || [];
    selectedSubmission.value = selectedSubmissions.value[0] || null;
    reviewNote.value = selectedSubmission.value?.teacher_review_note || "";
  } catch (error) {
    handleApiError(error, "加载提交详情失败。");
  }
}

function closeDetail() {
  selectedCell.value = null;
  selectedStudent.value = null;
  selectedQuestion.value = null;
  selectedSubmission.value = null;
  selectedSubmissions.value = [];
  reviewNote.value = "";
}

function selectSubmission(submission) {
  selectedSubmission.value = submission;
  reviewNote.value = submission.teacher_review_note || "";
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
    selectedSubmissions.value = selectedSubmissions.value.map((item) => (item.id === data.id ? data : item));
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

function isCellInFilter(cell) {
  if (matrixFilter.value === "submitted") return cell.status !== "not_submitted";
  if (matrixFilter.value === "unsubmitted") return cell.status === "not_submitted";
  return true;
}

function evidenceText(submission) {
  if (!submission) return "--";
  if (submission.excluded_from_mastery_update) return "未计入";
  return submission.status === "accepted" ? "正向证据" : "负向证据";
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
    observed_ai: "观察运行 + AI",
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
  display: block;
}

.matrix-panel {
  display: grid;
  gap: 16px;
  padding: 18px;
  overflow: hidden;
}

.view-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.view-tabs button {
  min-height: 36px;
  border-radius: 999px;
}

.view-tabs button.active {
  background: #18344f;
  border-color: #18344f;
  color: #fff;
}

.empty-state {
  padding: 14px;
  border: 1px solid #e3edf7;
  border-radius: 16px;
  background: #f8fbff;
  color: #6f8297;
  font-size: 13px;
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

.progress-cell.muted {
  opacity: 0.38;
}

.progress-cell strong {
  color: #10283d;
}

.progress-cell span,
.progress-cell small,
.timeline-item span,
.timeline-item small {
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

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(16, 40, 61, 0.42);
}

.detail-dialog {
  width: min(1080px, 100%);
  max-height: min(860px, calc(100vh - 48px));
  overflow: auto;
  padding: 20px;
}

.detail-dialog-bar {
  position: sticky;
  top: -20px;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin: -20px -20px 16px;
  padding: 18px 20px;
  border-bottom: 1px solid #e4edf6;
  background: rgba(255, 255, 255, 0.98);
}

.close-button {
  min-height: 36px;
  border-radius: 12px;
}

.submission-timeline {
  display: grid;
  gap: 8px;
}

.timeline-item {
  display: grid;
  justify-content: stretch;
  justify-items: start;
  gap: 3px;
  min-height: 64px;
  border-radius: 14px;
  text-align: left;
}

.timeline-item:hover {
  box-shadow: inset 0 0 0 1px rgba(31, 95, 153, 0.16);
}

.timeline-item.active {
  background: #eef6ff;
  border-color: #a9cbe8;
}

.timeline-item strong {
  color: #10283d;
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
  .summary-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
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

  .modal-backdrop {
    padding: 12px;
  }

  .detail-dialog {
    max-height: calc(100vh - 24px);
  }

  .detail-dialog-bar {
    display: grid;
  }
}

.diagnosis-summary {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.diagnosis-summary > span:first-child {
  color: #6f8297;
  font-size: 12px;
}

.diagnosis-tag {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.diagnosis-tag.resolved {
  background: #dff7e7;
  color: #027a48;
}

.diagnosis-tag.unresolved {
  background: #fff8ea;
  color: #9a6700;
}

.diagnosis-tag small {
  font-size: 10px;
  opacity: 0.75;
}
</style>
