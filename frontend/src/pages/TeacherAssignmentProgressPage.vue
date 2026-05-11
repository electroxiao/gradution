<template>
  <section class="progress-page">
    <PageHeader :title="progress?.title || '作业完成情况'" title-tag="h2">
      <template #actions>
        <router-link class="secondary-link" :to="`/teacher/assignments/${assignmentId}`">编辑作业</router-link>
        <router-link class="secondary-link" to="/teacher/assignments">返回列表</router-link>
      </template>
    </PageHeader>

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
      <section class="student-panel shell-card">
        <div class="panel-header">
          <div>
            <h3>学生作业完成情况</h3>
            <p class="muted">点击学生行查看该学生最近一次提交详情。</p>
          </div>
          <div class="view-tabs">
            <button type="button" :class="{ active: matrixFilter === 'all' }" @click="matrixFilter = 'all'">全部</button>
            <button type="button" :class="{ active: matrixFilter === 'unsubmitted' }" @click="matrixFilter = 'unsubmitted'">未提交</button>
            <button type="button" :class="{ active: matrixFilter === 'submitted' }" @click="matrixFilter = 'submitted'">已提交</button>
          </div>
        </div>

        <div v-if="pagedStudentRows.length" class="student-table">
          <div class="student-table-head">
            <span class="col-student">学生</span>
            <span>提交状态</span>
            <span>提交时间</span>
            <span>操作</span>
          </div>
          <article
            v-for="row in pagedStudentRows"
            :key="row.student.id"
            class="student-row"
            @click="openStudentDetail(row)"
          >
            <div class="student-copy col-student">
              <h3>{{ row.student.username }}</h3>
              <p v-if="row.student.class_name" class="muted">{{ row.student.class_name }}</p>
              <p v-else class="muted">未分配班级</p>
            </div>
            <div class="status-stack">
              <span class="status-dot" :class="row.submitted ? 'submitted' : 'unsubmitted'"></span>
              <div>
                <strong>{{ row.submitted ? "已提交" : "未提交" }}</strong>
                <small>{{ row.submittedQuestionCount }}/{{ questionTotal }} 题</small>
              </div>
            </div>
            <span class="time-cell">{{ formatDateTime(row.latestSubmittedAt) }}</span>
            <button type="button" class="open-link compact-link" @click.stop="openStudentDetail(row)">
              查看详情
            </button>
          </article>
        </div>
        <div v-if="filteredStudentRows.length" class="pagination-bar">
          <span>共 {{ filteredStudentRows.length }} 名学生，每页 {{ pageSize }} 名</span>
          <div class="pagination-controls">
            <button type="button" :disabled="currentPage === 1" @click="setPage(currentPage - 1)">上一页</button>
            <button
              v-for="page in pageNumbers"
              :key="page"
              type="button"
              :class="{ active: currentPage === page }"
              @click="setPage(page)"
            >
              {{ page }}
            </button>
            <button type="button" :disabled="currentPage === totalPages" @click="setPage(currentPage + 1)">下一页</button>
          </div>
        </div>
        <div v-else class="empty-state">当前筛选下没有学生。</div>
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
            <dl class="overview-grid">
              <div class="overview-card time">
                <span class="overview-icon" aria-hidden="true">时</span>
                <div>
                  <dt>提交时间</dt>
                  <dd>{{ formatDateTime(selectedSubmission.submitted_at) }}</dd>
                </div>
              </div>
              <div class="overview-card count">
                <span class="overview-icon" aria-hidden="true">次</span>
                <div>
                  <dt>提交次数</dt>
                  <dd>{{ selectedSubmissions.length || selectedCell.submission_count }} 次</dd>
                </div>
              </div>
              <div class="overview-card runtime">
                <span class="overview-icon" aria-hidden="true">运</span>
                <div>
                  <dt>运行耗时</dt>
                  <dd>{{ formatRunTime(selectedSubmission.run_time_ms) }}</dd>
                </div>
              </div>
              <div class="overview-card duration">
                <span class="overview-icon" aria-hidden="true">答</span>
                <div>
                  <dt>作答耗时</dt>
                  <dd>{{ formatDuration(selectedSubmission.duration_seconds) }}</dd>
                </div>
              </div>
            </dl>

            <div class="detail-content-layout">
              <aside class="timeline-panel" aria-label="提交时间线">
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
                    :class="[timelineStatusClass(submission), { active: submission.id === selectedSubmission.id }]"
                    @click="selectSubmission(submission)"
                  >
                    <span class="timeline-marker" aria-hidden="true">{{ timelineStatusIcon(submission) }}</span>
                    <span class="timeline-copy">
                      <span class="timeline-title-row">
                        <strong>#{{ selectedSubmissions.length - index }} {{ statusText(submission.status) }}</strong>
                        <em v-if="index === 0">最新</em>
                      </span>
                      <span class="timeline-evidence">{{ evidenceText(submission) }}</span>
                      <small>{{ formatDateTime(submission.submitted_at) }}</small>
                    </span>
                  </button>
                </div>
              </aside>

              <div class="detail-main-column">
                <section class="detail-section">
                  <h4>提交代码</h4>
                  <ReadonlyCodeBlock :code="selectedSubmission.code || '未提交代码。'" background="#ffffff" />
                </section>

                <section class="detail-section">
                  <h4>测试结果</h4>
                  <div v-if="selectedResultItems.length" class="result-list">
                    <article class="result-card">
                      <div class="result-card-head">
                        <span class="result-state" :class="resultStateClass(activeResultItem)">
                          {{ resultStateText(activeResultItem) }}
                        </span>
                        <span class="result-runtime">执行用时: {{ formatRunTime(activeResultItem?.elapsed_ms) }}</span>
                      </div>
                      <div class="result-case-tabs" role="tablist" aria-label="测试用例">
                        <button
                          v-for="(item, index) in selectedResultItems"
                          :key="`${index}-${item.case_index}-${item.status}`"
                          type="button"
                          class="result-case-pill"
                          :class="[resultStateClass(item), { active: index === selectedResultIndex }]"
                          role="tab"
                          :aria-selected="index === selectedResultIndex"
                          @click="selectedResultIndex = index"
                        >
                          <span class="case-check" aria-hidden="true">{{ resultStateIcon(item) }}</span>
                          {{ resultCaseText(item) }}
                        </button>
                      </div>
                      <p v-if="activeResultItem?.summary">{{ activeResultItem.summary }}</p>
                      <template v-if="activeResultItem">
                        <div class="result-field">
                          <span>输入</span>
                          <ReadonlyCodeBlock :code="activeResultItem.input || '(空)'" :show-line-numbers="false" compact background="#f7f7f8" />
                        </div>
                        <template v-if="activeResultItem.check_mode !== 'observe_only'">
                          <div class="result-field">
                            <span>期望输出</span>
                            <ReadonlyCodeBlock :code="activeResultItem.expected_output || '(空)'" :show-line-numbers="false" compact background="#f7f7f8" />
                          </div>
                        </template>
                        <div class="result-field">
                          <span>实际输出</span>
                          <ReadonlyCodeBlock :code="activeResultItem.actual_output || '(空)'" :show-line-numbers="false" compact background="#f7f7f8" />
                        </div>
                      </template>
                      <div v-if="activeResultItem?.stderr" class="result-field">
                        <span>错误输出</span>
                        <ReadonlyCodeBlock :code="activeResultItem.stderr" :show-line-numbers="false" compact background="#f7f7f8" />
                      </div>
                    </article>
                  </div>
                  <p v-else class="section-empty">暂无测试结果。</p>
                </section>

                <section class="detail-section">
                  <div class="review-head">
                    <h4>AI 判定</h4>
                    <span class="decision-pill">{{ decisionSourceText(selectedSubmission.decision_source) }}</span>
                  </div>
                  <template v-if="selectedSubmission.ai_review_json">
                    <dl class="meta-grid compact-meta">
                      <div>
                        <dt>判定结果</dt>
                        <dd :class="decisionStatusClass(selectedSubmission.ai_review_json.decision || selectedSubmission.status)">
                          {{ statusText(selectedSubmission.ai_review_json.decision || selectedSubmission.status) }}
                        </dd>
                      </div>
                    </dl>
                    <p class="review-summary">{{ selectedSubmission.ai_review_json.summary || "AI 未返回总结。" }}</p>
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
                    <div v-if="selectedSubmission.ai_review_json.diagnoses?.length" class="review-list diagnosis-list">
                      <strong>AI 诊断</strong>
                      <article v-for="(item, index) in selectedSubmission.ai_review_json.diagnoses" :key="`diagnosis-${index}`" class="diagnosis-item">
                        <div class="diagnosis-head">
                          <span>{{ item.knowledge_node || "unknown" }}</span>
                          <small>{{ [item.stage, item.category].filter(Boolean).join(" / ") }}</small>
                        </div>
                        <p v-if="item.student_feedback">{{ item.student_feedback }}</p>
                        <p v-else-if="item.reason">{{ item.reason }}</p>
                        <small v-if="item.evidence">证据：{{ item.evidence }}</small>
                      </article>
                    </div>
                  </template>
                  <p v-else class="section-empty">暂无 AI 判定。</p>
                </section>

                <section class="detail-section teacher-review-section">
                  <div class="review-head">
                    <h4>教师改判</h4>
                  </div>
                  <p class="muted" v-if="selectedSubmission.reviewed_by_username">
                    最近由 {{ selectedSubmission.reviewed_by_username }} 于 {{ formatDateTime(selectedSubmission.reviewed_at) }} 复核
                  </p>
                  <textarea
                    v-model="reviewNote"
                    rows="3"
                    placeholder="输入改判备注，例如：SQL 结果对，但事务边界不符合要求。"
                  />
                </section>
              </div>
            </div>

            <div class="review-actions">
              <button type="button" class="review-button reject" :disabled="reviewing" @click="submitReview('teacher_rejected')">
                标记未通过
              </button>
              <button type="button" class="review-button accept" :disabled="reviewing" @click="submitReview('accepted')">
                标记通过
              </button>
            </div>
          </div>

          <p v-else-if="selectedCell.latest_submission_id" class="muted">提交详情加载中...</p>
          <p v-else class="muted">该学生还没有提交这道题。</p>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  getTeacherAssignmentProgressApi,
  listTeacherAssignmentQuestionSubmissionsApi,
  reviewTeacherAssignmentSubmissionApi,
} from "../api/assignments";
import PageHeader from "../components/PageHeader.vue";
import ReadonlyCodeBlock from "../components/ReadonlyCodeBlock.vue";
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
const currentPage = ref(1);
const selectedResultIndex = ref(0);
const pageSize = 10;

const cellMap = computed(() => {
  const map = new Map();
  for (const cell of progress.value?.cells || []) {
    map.set(`${cell.student_id}:${cell.question_id}`, cell);
  }
  return map;
});
const questionTotal = computed(() => progress.value?.questions.length || 0);
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
const studentRows = computed(() => {
  if (!progress.value) return [];
  return progress.value.students.map((student) => {
    const cells = progress.value.questions.map((question) => cellFor(student.id, question.id));
    const submittedCells = cells.filter((cell) => cell.status !== "not_submitted");
    const latestCell = submittedCells
      .slice()
      .sort((a, b) => new Date(b.submitted_at || 0).getTime() - new Date(a.submitted_at || 0).getTime())[0];
    const fallbackQuestion = progress.value.questions[0] || null;
    const detailQuestion =
      progress.value.questions.find((question) => question.id === latestCell?.question_id) || fallbackQuestion;
    return {
      student,
      submitted: fullySubmittedStudentIds.value.has(student.id),
      submittedQuestionCount: submittedCells.length,
      latestSubmittedAt: latestCell?.submitted_at || null,
      detailCell: latestCell || (detailQuestion ? cellFor(student.id, detailQuestion.id) : null),
      detailQuestion,
    };
  });
});
const filteredStudentRows = computed(() => {
  if (!progress.value) return [];
  if (matrixFilter.value === "submitted") {
    return studentRows.value.filter((row) => row.submitted);
  }
  if (matrixFilter.value === "unsubmitted") {
    return studentRows.value.filter((row) => !row.submitted);
  }
  return studentRows.value;
});
const totalPages = computed(() => Math.max(1, Math.ceil(filteredStudentRows.value.length / pageSize)));
const pageNumbers = computed(() => Array.from({ length: totalPages.value }, (_, index) => index + 1));
const pagedStudentRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return filteredStudentRows.value.slice(start, start + pageSize);
});
const selectedResultItems = computed(() => {
  const results = selectedSubmission.value?.results_json;
  return Array.isArray(results) ? results : [];
});
const activeResultItem = computed(() => selectedResultItems.value[selectedResultIndex.value] || null);

onMounted(loadProgress);

watch(matrixFilter, () => {
  currentPage.value = 1;
});

watch(totalPages, (value) => {
  if (currentPage.value > value) currentPage.value = value;
});

watch(selectedSubmission, () => {
  selectedResultIndex.value = 0;
});

watch(selectedResultItems, (items) => {
  if (selectedResultIndex.value >= items.length) selectedResultIndex.value = 0;
});

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

function openStudentDetail(row) {
  if (!row.detailQuestion || !row.detailCell) return;
  selectCell(row.student, row.detailQuestion, row.detailCell);
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

function evidenceText(submission) {
  if (!submission) return "--";
  return submission.status === "accepted" ? "通过记录" : "薄弱点证据";
}

function timelineStatusClass(submission) {
  return submission?.status === "accepted" ? "passed" : "failed";
}

function timelineStatusIcon(submission) {
  return submission?.status === "accepted" ? "✓" : "×";
}

function isAcceptedResult(item) {
  return item?.status === "accepted";
}

function resultStateClass(item) {
  return isAcceptedResult(item) ? "passed" : "failed";
}

function resultStateText(item) {
  return isAcceptedResult(item) ? "通过" : "解答错误";
}

function resultStateIcon(item) {
  return isAcceptedResult(item) ? "✓" : "×";
}

function resultCaseText(item) {
  if (item?.case_index === 0) return "编译";
  if (item?.check_mode === "observe_only") return `运行 ${item?.case_index || "-"}`;
  return `Case ${item?.case_index || "-"}`;
}

function decisionStatusClass(status) {
  return status === "accepted" ? "decision-accepted" : "decision-rejected";
}

function statusText(status) {
  return {
    not_submitted: "未提交",
    submitted: "判题中",
    accepted: "通过",
    wrong_answer: "答案错误",
    runtime_error: "运行错误",
    timeout: "超时",
    sandbox_error: "沙箱错误",
    ai_rejected: "AI 判定未通过",
    teacher_rejected: "教师判定未通过",
  }[status] || status;
}

function decisionSourceText(value) {
  return {
    testcase: "测试用例结果",
    ai_review: "AI 判定结果",
    hybrid: "混合判题结果",
    ai_with_testcases: "AI + 测试用例",
    observed_ai: "观察运行 + AI",
    ai_only: "AI 判题结果",
    background_pending: "后台判题中",
    local_multiple_choice: "本地选择题判分",
    teacher_override: "教师改判",
  }[value] || "系统判定";
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

function setPage(page) {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value);
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
  gap: 14px;
  font-size: var(--compact-body);
}

.shell-card,
.feedback {
  border: 1px solid var(--app-line);
  border-radius: 12px;
  background: #ffffff;
  box-shadow: var(--app-shadow);
}

.detail-header,
.panel-header,
.review-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.muted {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
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
  min-height: var(--compact-control-height);
  padding: 0 12px;
  border: 1px solid var(--app-line);
  border-radius: 8px;
  background: #fff;
  color: #31445f;
  text-decoration: none;
  white-space: nowrap;
}

.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--compact-control-height);
  padding: 0 14px;
  border: 1px solid var(--app-line);
  border-radius: 6px;
  background: #fff;
  color: #31445f;
  text-decoration: none;
  white-space: nowrap;
  font-size: var(--compact-body);
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
}

.summary-card span {
  color: #6f8297;
  font-size: 13px;
}

.summary-card strong {
  color: #10283d;
  font-size: var(--compact-stat-sm);
  font-weight: 400;
}

.progress-layout {
  display: block;
}

.student-panel {
  display: grid;
  gap: 14px;
  padding: 16px;
  overflow-x: auto;
}

.view-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.view-tabs button {
  min-height: 30px;
  padding: 0 11px;
  border-radius: 999px;
  font-size: var(--compact-body);
}

.view-tabs button.active {
  background: #18344f;
  border-color: #18344f;
  color: #fff;
}

.empty-state {
  padding: 38px;
  border: 1px dashed #d9e2ed;
  border-radius: 10px;
  background: #ffffff;
  color: var(--app-text-muted);
  text-align: center;
  font-size: var(--compact-body);
}

.student-table {
  display: grid;
  width: 100%;
  min-width: 660px;
  overflow: hidden;
  border: 1px solid var(--app-line);
  border-radius: 8px;
  background: #fff;
}

.student-table-head,
.student-row {
  display: grid;
  grid-template-columns: minmax(300px, 3fr) minmax(120px, 1fr) minmax(120px, 1fr) minmax(120px, 0.8fr);
  gap: 10px;
  align-items: center;
}

.student-table-head {
  min-height: 36px;
  padding: 0 11px;
  background: #ffffff;
  color: #2f3f55;
  font-size: calc(var(--compact-body) * 0.9375);
  font-weight: 500;
  border-bottom: 1px solid var(--app-line);
}

.student-row {
  min-height: 58px;
  padding: 9px 11px;
  border-bottom: 1px solid var(--app-line);
  cursor: pointer;
  transition: background 0.16s ease;
}

.student-row:last-child {
  border-bottom: 0;
}

.student-row:hover {
  background: #f8fbff;
}

.student-table-head > span:not(.col-student),
.student-row > :not(.col-student) {
  justify-self: center;
  text-align: center;
  transform: translateX(-15px);
}

.col-student,
.student-copy {
  min-width: 0;
}

.student-copy h3 {
  margin: 0 0 4px;
  color: var(--app-text);
  font-size: calc(var(--compact-card-title) * 0.75);
  font-weight: 500;
  line-height: 1.12;
}

.student-copy p {
  margin: 0;
  font-size: calc(var(--compact-body) * 0.75 + 1px);
  line-height: 1.3;
}

.status-stack {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--app-text);
}

.status-stack > div {
  display: grid;
  gap: 3px;
  text-align: left;
}

.status-stack strong {
  font-size: 12px;
  font-weight: 500;
}

.status-stack small {
  color: var(--app-text-muted);
  font-size: 11px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.submitted {
  background: #12a15c;
}

.status-dot.unsubmitted {
  background: #ef4444;
}

.time-cell {
  color: var(--app-text-muted);
  font-size: 12px;
}

.compact-link {
  width: 100%;
  min-height: 29px;
  padding: 0 11px;
  border-radius: 8px;
  font-size: 11px;
  white-space: nowrap;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 2px 4px 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-controls button {
  min-width: 34px;
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid var(--app-line);
  border-radius: 8px;
  background: #fff;
  color: #31445f;
  cursor: pointer;
}

.pagination-controls button.active {
  border-color: var(--app-primary);
  background: var(--app-primary);
  color: #fff;
}

.pagination-controls button:disabled {
  background: #ffffff;
  color: var(--app-text-soft);
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
  width: min(1320px, 100%);
  max-height: min(860px, calc(100vh - 48px));
  overflow: auto;
  padding: 16px;
}

.detail-dialog-bar {
  position: sticky;
  top: -16px;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin: -16px -16px 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--app-line);
  background: #ffffff;
}

.close-button {
  min-height: 32px;
  border-radius: 8px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 14px 16px;
  border: 1px solid #dfe9f3;
  border-radius: 8px;
  background: #ffffff;
}

.overview-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  flex: 0 0 auto;
  border: 2px solid currentColor;
  font-size: 13px;
  font-weight: 700;
}

.overview-card.time .overview-icon,
.overview-card.count .overview-icon {
  color: #2f7df2;
}

.overview-card.runtime .overview-icon {
  color: #13a66b;
}

.overview-card.duration .overview-icon {
  color: #f2ae2e;
}

.overview-card dt,
.overview-card dd {
  margin: 0;
}

.overview-card dt {
  color: #6f8297;
  font-size: 12px;
}

.overview-card dd {
  margin-top: 5px;
  color: #10283d;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.1;
}

.detail-content-layout {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(0, 3fr);
  gap: 16px;
  align-items: start;
}

.timeline-panel {
  position: sticky;
  top: 64px;
  display: grid;
  gap: 14px;
  align-self: start;
  padding: 14px;
  border: 1px solid #dfe9f3;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 16px 32px rgba(16, 40, 61, 0.08);
}

.submission-timeline {
  position: relative;
  display: grid;
  gap: 8px;
}

.timeline-item {
  position: relative;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 12px;
  min-height: 92px;
  padding: 0;
  border: 0;
  border-radius: 0;
  border-color: transparent;
  background: transparent;
  text-align: left;
}

.timeline-item::before,
.timeline-item::after {
  content: "";
  position: absolute;
  left: 13px;
  width: 2px;
  background: #d9e4ef;
}

.timeline-item::before {
  top: 0;
  bottom: calc(50% + 17px);
}

.timeline-item::after {
  top: calc(50% + 17px);
  bottom: -8px;
}

.timeline-item:first-child::before,
.timeline-item:last-child::after {
  display: none;
}

.timeline-item:hover {
  box-shadow: none;
}

.timeline-item:hover .timeline-copy {
  border-color: #c8dff5;
}

.timeline-marker {
  position: relative;
  z-index: 2;
  align-self: center;
  justify-self: center;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 22px;
  height: 22px;
  border: 2px solid #cfdbe8;
  border-radius: 50%;
  background: #ffffff;
  color: transparent;
  font-family: Arial, sans-serif;
  font-size: 0;
  font-weight: 700;
  line-height: 1;
}

.timeline-marker::before,
.timeline-marker::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  background: #ffffff;
  transform-origin: center;
}

.timeline-item.passed .timeline-marker {
  border-color: #16a34a;
  background: #16a34a;
  color: #ffffff;
}

.timeline-item.passed .timeline-marker::before {
  width: 9px;
  height: 5px;
  border-left: 2px solid #ffffff;
  border-bottom: 2px solid #ffffff;
  background: transparent;
  transform: translate(-50%, -58%) rotate(-45deg);
}

.timeline-item.failed .timeline-marker {
  border-color: #d83d3d;
  background: #d83d3d;
  color: #ffffff;
}

.timeline-item.failed .timeline-marker::before,
.timeline-item.failed .timeline-marker::after {
  width: 10px;
  height: 2px;
  border-radius: 999px;
  left: calc(50% - 0.5px);
  top: calc(50% + 0.5px);
}

.timeline-item.failed .timeline-marker::before {
  transform: translate(-50%, -50%) rotate(45deg);
}

.timeline-item.failed .timeline-marker::after {
  transform: translate(-50%, -50%) rotate(-45deg);
}

.timeline-copy {
  position: relative;
  z-index: 2;
  display: grid;
  gap: 6px;
  min-width: 0;
  min-height: 92px;
  padding: 13px 16px;
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #ffffff;
}

.timeline-item.active .timeline-copy {
  border-color: #a9cbe8;
  background: #eef6ff;
}

.timeline-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.timeline-title-row em {
  padding: 3px 8px;
  border-radius: 999px;
  background: #dfeeff;
  color: #2f7df2;
  font-size: 12px;
  font-style: normal;
  white-space: nowrap;
}

.timeline-item strong {
  color: #10283d;
  min-width: 0;
}

.timeline-evidence,
.timeline-item small {
  color: #6f8297;
}

.status-pill,
.decision-pill {
  padding: 5px 10px;
  border-radius: 999px;
  white-space: nowrap;
  font-size: var(--compact-caption);
  font-weight: 500;
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
.status-pill.ai_rejected,
.status-pill.teacher_rejected {
  background: #fff2f2;
  color: #b42318;
}

.detail-body,
.detail-section,
.review-list {
  display: grid;
  gap: 10px;
}

.detail-body {
  gap: 16px;
}

.detail-main-column {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.detail-section {
  padding: 14px;
  border: 1px solid #e0e9f2;
  border-radius: 8px;
  background: #ffffff;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.meta-grid div {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.meta-grid dt {
  color: #6f8297;
  font-size: 12px;
}

.meta-grid dd {
  margin: 4px 0 0;
  color: #10283d;
  font-weight: 500;
}

.meta-grid dd.decision-accepted {
  color: #16a34a;
}

.meta-grid dd.decision-rejected {
  color: #b42318;
}

.compact-meta {
  grid-template-columns: minmax(0, 1fr);
}

.detail-section h4 {
  margin: 0;
  color: #10283d;
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

.diagnosis-list {
  display: grid;
  gap: 10px;
}

.diagnosis-item {
  display: grid;
  gap: 6px;
  padding: 10px;
  border: 1px solid #d8e2ee;
  border-radius: 8px;
  background: #fff;
}

.diagnosis-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.diagnosis-head span {
  color: #10283d;
}

.diagnosis-head small,
.diagnosis-item p,
.diagnosis-item small {
  margin: 0;
  color: #526071;
  font-size: 13px;
}

.section-empty {
  margin: 0;
  color: #7c8da0;
  font-size: var(--compact-body);
}

.result-list {
  display: grid;
  gap: 10px;
}

textarea,
button {
  font: inherit;
}

textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  resize: vertical;
}

button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--compact-control-height);
  padding: 0 12px;
  border: 1px solid #d4e4f2;
  border-radius: 8px;
  background: #fff;
  color: #18344f;
  cursor: pointer;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.result-card {
  display: grid;
  gap: 16px;
  padding: 14px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e5eef7;
  color: #243447;
}

.result-card-head {
  display: flex;
  align-items: baseline;
  gap: 18px;
}

.result-state {
  font-size: 22px;
  line-height: 1.15;
}

.result-state.passed {
  color: #16a34a;
}

.result-state.failed {
  color: #b42318;
}

.result-runtime {
  color: #8a919b;
  font-size: 14px;
}

.result-case-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.result-case-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #7c838d;
  cursor: pointer;
}

.result-case-pill.active {
  background: #f0f1f3;
  color: #243447;
}

.case-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  color: #fff;
  font-size: 11px;
  line-height: 1;
}

.result-case-pill.passed .case-check {
  background: #16a34a;
}

.result-case-pill.failed .case-check {
  background: #b42318;
}

.result-field {
  display: grid;
  gap: 8px;
}

.result-field > span {
  color: #8a919b;
  font-size: 13px;
}

.feedback.error {
  background: #fff2f2;
  color: #b42318;
}

.feedback {
  padding: 11px 13px;
}

.teacher-review-section textarea {
  min-height: 90px;
}

.review-actions {
  position: sticky;
  bottom: -16px;
  z-index: 2;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  margin: 0 -16px -16px;
  padding: 14px 16px;
  border-top: 1px solid var(--app-line);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
}

.review-button {
  min-height: 30px;
  width: auto;
  flex: 0 0 auto;
  padding: 0 14px;
  border-radius: 8px;
  font-weight: 600;
}

.review-button.reject {
  border-color: #f3b8b8;
  background: #fff2f2;
  color: #b42318;
}

.review-button.accept {
  border-color: #1f6feb;
  background: #1f6feb;
  color: #ffffff;
}

.detail-dialog :is(h3, h4, strong, dt, dd, button, .status-pill, .decision-pill, .overview-icon, .review-button) {
  font-weight: 400;
}

@media (max-width: 1180px) {
  .summary-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .detail-content-layout {
    grid-template-columns: 1fr;
  }

  .timeline-panel {
    position: static;
  }
}

@media (max-width: 720px) {
  .panel-header,
  .detail-header,
  .review-head,
  .summary-row,
  .overview-grid,
  .meta-grid,
  .pagination-bar {
    display: grid;
  }

  .summary-row,
  .overview-grid,
  .meta-grid {
    grid-template-columns: 1fr;
  }

  .overview-card {
    padding: 12px;
  }

  .review-actions {
    justify-content: stretch;
  }

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

</style>
