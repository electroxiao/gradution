<template>
  <section class="students-page">
    <header class="page-header">
      <div>
        <h2>学生薄弱点</h2>
        <p class="page-copy">按学生查看当前未掌握节点，以及作业驱动的知识点掌握分数。</p>
      </div>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <div class="students-layout">
      <aside class="student-list">
        <button
          v-for="student in students"
          :key="student.id"
          class="student-item"
          :class="{ active: student.id === activeStudentId }"
          @click="selectStudent(student.id)"
        >
          <strong>{{ student.username }}</strong>
          <span>{{ student.weak_point_count }} 个薄弱点</span>
        </button>
      </aside>

      <section class="student-detail">
        <div v-if="activeStudent" class="detail-header">
          <div>
            <h3>{{ activeStudent.username }}</h3>
            <p>当前未掌握 {{ studentWeakPoints.length }} 个节点，已记录 {{ studentMastery.length }} 个作业掌握条目</p>
          </div>
        </div>

        <section class="detail-section">
          <div class="section-head">
            <h4>当前未掌握节点</h4>
            <span>{{ studentWeakPoints.length }} 个</span>
          </div>
          <div v-if="studentWeakPoints.length" class="weak-cards">
            <article v-for="item in studentWeakPoints" :key="item.id" class="weak-card">
              <strong>{{ item.node_name }}</strong>
              <span>最近出现 {{ formatDate(item.last_seen_at) }}</span>
            </article>
          </div>
          <div v-else class="empty">该学生当前没有未掌握薄弱点。</div>
        </section>

        <section class="detail-section">
          <div class="section-head">
            <h4>作业驱动掌握情况</h4>
            <span>{{ studentMastery.length }} 项</span>
          </div>
          <div v-if="studentMastery.length" class="mastery-list">
            <article v-for="item in studentMastery" :key="item.knowledge_node_id" class="mastery-card" :class="item.status">
              <div class="mastery-top">
                <strong>{{ item.node_name }}</strong>
                <span class="status-pill" :class="item.status">{{ masteryStatusText(item.status) }}</span>
              </div>
              <div class="score-row">
                <span>掌握分</span>
                <strong>{{ item.mastery_score }}</strong>
              </div>
              <div class="meta-row">
                <span>正向证据 {{ item.positive_evidence_count }}</span>
                <span>负向证据 {{ item.negative_evidence_count }}</span>
              </div>
              <div class="evidence-strip">
                <span class="evidence-chip positive">通过 {{ item.positive_evidence_count }}</span>
                <span class="evidence-chip negative">未通过 {{ item.negative_evidence_count }}</span>
                <span class="evidence-chip muted">最近证据 {{ item.evidence?.length || 0 }}</span>
              </div>
              <div v-if="item.evidence?.length" class="evidence-list">
                <article
                  v-for="evidence in item.evidence"
                  :key="evidence.submission_id"
                  class="evidence-item"
                  :class="evidence.contribution"
                >
                  <div class="evidence-main">
                    <span class="evidence-badge" :class="evidence.contribution">
                      {{ contributionText(evidence.contribution) }}
                    </span>
                    <strong>{{ evidence.assignment_title }}</strong>
                    <span>{{ evidence.question_title }}</span>
                  </div>
                  <div class="evidence-meta">
                    <span>{{ statusText(evidence.status) }}</span>
                    <span>{{ decisionSourceText(evidence.decision_source) }}</span>
                    <span>作答 {{ formatDuration(evidence.duration_seconds) }}</span>
                    <span>{{ formatDateTime(evidence.submitted_at) }}</span>
                  </div>
                  <p v-if="evidence.ai_summary" class="evidence-summary">{{ evidence.ai_summary }}</p>
                  <div v-if="evidence.ai_score !== null || evidence.ai_confidence !== null" class="evidence-ai">
                    <span>AI 评分 {{ evidence.ai_score ?? "--" }}</span>
                    <span>置信度 {{ formatConfidence(evidence.ai_confidence) }}</span>
                  </div>
                  <div v-if="evidence.ai_diagnoses?.length" class="evidence-diagnoses">
                    <span
                      v-for="(diagnosis, index) in evidence.ai_diagnoses"
                      :key="`${evidence.submission_id}-diagnosis-${index}`"
                    >
                      {{ diagnosis.knowledge_node || "unknown" }} · {{ formatConfidence(diagnosis.confidence) }} ·
                      {{ graphResolutionText(diagnosis.graph_resolution) }}
                    </span>
                  </div>
                </article>
              </div>
              <div v-else class="evidence-empty">暂无可展示的作业提交证据。</div>
              <small>最近更新 {{ formatDate(item.last_evaluated_at) }}</small>
            </article>
          </div>
          <div v-else class="empty">该学生还没有作业驱动的掌握记录。</div>
        </section>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { listTeacherStudentMasteryApi, listTeacherStudentWeakPointsApi, listTeacherStudentsApi } from "../api/teacher";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const students = ref([]);
const activeStudentId = ref(null);
const studentWeakPoints = ref([]);
const studentMastery = ref([]);
const errorMessage = ref("");

const activeStudent = computed(() =>
  students.value.find((student) => student.id === activeStudentId.value) || null,
);

onMounted(async () => {
  await loadStudents();
});

async function loadStudents() {
  try {
    const { data } = await listTeacherStudentsApi();
    students.value = data;
    if (students.value.length) {
      await selectStudent(students.value[0].id);
    }
  } catch (error) {
    handleApiError(error, "加载学生列表失败。");
  }
}

async function selectStudent(studentId) {
  activeStudentId.value = studentId;
  try {
    const [weakPointsResponse, masteryResponse] = await Promise.all([
      listTeacherStudentWeakPointsApi(studentId),
      listTeacherStudentMasteryApi(studentId),
    ]);
    studentWeakPoints.value = weakPointsResponse.data;
    studentMastery.value = masteryResponse.data;
  } catch (error) {
    handleApiError(error, "加载学生知识画像失败。");
  }
}

function masteryStatusText(status) {
  return {
    weak: "薄弱",
    partial: "基本掌握",
    good: "掌握较好",
  }[status] || status;
}

function contributionText(value) {
  return {
    positive: "正向",
    negative: "负向",
    excluded: "未计入",
  }[value] || value;
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
  }[status] || status;
}

function decisionSourceText(value) {
  return {
    testcase: "测试用例",
    ai_review: "AI 评审",
    hybrid: "混合判题",
    ai_with_testcases: "AI + 测试",
    observed_ai: "观察运行 + AI",
    ai_only: "仅 AI",
    teacher_override: "教师改判",
  }[value] || "系统判定";
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

function formatDuration(value) {
  if (value === null || value === undefined) return "--";
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return minutes ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

function formatConfidence(value) {
  if (value === null || value === undefined) return "--";
  const number = Number(value);
  if (Number.isNaN(number)) return "--";
  return `${Math.round(number * 100)}%`;
}

function graphResolutionText(resolution) {
  const status = resolution?.status;
  if (status === "matched_existing") return `已关联 ${resolution.node_name || ""}`.trim();
  if (status === "needs_teacher_review") return "待教师确认";
  if (status === "skipped_low_confidence") return "低置信未计入";
  if (status === "unresolved") return "未关联";
  return "未解析";
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
.students-page {
  display: grid;
  gap: var(--app-gap-xl);
}

.page-header h2 {
  margin: 0 0 8px;
  font-size: 32px;
  font-weight: 500;
  color: var(--app-text);
}

.page-copy {
  margin: 0;
  color: var(--app-text-muted);
}

.students-layout {
  display: grid;
  grid-template-columns: 296px minmax(0, 1fr);
  gap: 20px;
}

.student-list,
.student-detail {
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.student-list {
  padding: 16px;
  display: grid;
  gap: 10px;
  align-self: start;
}

.student-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border: 1px solid transparent;
  border-radius: 18px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
}

.student-item strong {
  color: var(--app-text);
  font-weight: 500;
}

.student-item span {
  color: var(--app-text-muted);
  font-size: 13px;
}

.student-item.active {
  background: var(--app-primary-soft);
  border-color: #cfdcf3;
}

.student-detail {
  padding: 24px;
  display: grid;
  gap: 20px;
}

.detail-header h3 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
  color: var(--app-text);
}

.detail-header p,
.section-head span,
.mastery-card small {
  margin: 6px 0 0;
  color: var(--app-text-muted);
}

.detail-section {
  display: grid;
  gap: 14px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.section-head h4 {
  margin: 0;
  color: var(--app-text);
  font-size: 17px;
  font-weight: 500;
}

.weak-cards,
.mastery-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
}

.weak-card,
.mastery-card,
.feedback.error,
.empty {
  padding: 18px;
  border-radius: 20px;
  background: var(--app-panel-soft);
  color: var(--app-text-muted);
}

.weak-card strong,
.mastery-card strong {
  display: block;
  color: var(--app-text);
  font-weight: 500;
}

.mastery-card {
  display: grid;
  gap: 10px;
  border: 1px solid #e2ebf4;
}

.mastery-card.weak {
  background: #fff4f4;
}

.mastery-card.partial {
  background: #fff8ea;
}

.mastery-card.good {
  background: #eefbf3;
}

.mastery-top,
.score-row,
.meta-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.status-pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.status-pill.weak {
  background: #fde7e7;
  color: #b42318;
}

.status-pill.partial {
  background: #fff0d8;
  color: #9a6700;
}

.status-pill.good {
  background: #dff7e7;
  color: #027a48;
}

.score-row span,
.meta-row span {
  color: var(--app-text-muted);
  font-size: 13px;
}

.evidence-strip,
.evidence-meta,
.evidence-ai,
.evidence-diagnoses {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.evidence-chip,
.evidence-badge,
.evidence-meta span,
.evidence-ai span,
.evidence-diagnoses span {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1.2;
}

.evidence-chip.positive,
.evidence-badge.positive {
  background: #dff7e7;
  color: #027a48;
}

.evidence-chip.negative,
.evidence-badge.negative {
  background: #fde7e7;
  color: #b42318;
}

.evidence-chip.muted,
.evidence-badge.excluded {
  background: #eef2f7;
  color: #526071;
}

.evidence-list {
  display: grid;
  gap: 10px;
}

.evidence-item {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid #e1eaf3;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.68);
}

.evidence-item.positive {
  border-color: #bfe8cd;
}

.evidence-item.negative {
  border-color: #f0caca;
}

.evidence-main {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 4px 8px;
  align-items: center;
}

.evidence-main strong,
.evidence-main span:last-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.evidence-main span:last-child {
  grid-column: 2;
  color: var(--app-text-muted);
  font-size: 13px;
}

.evidence-meta span,
.evidence-ai span {
  background: #f4f7fb;
  color: #526071;
}

.evidence-diagnoses span {
  background: #eef5ff;
  color: #35639f;
}

.evidence-summary,
.evidence-empty {
  margin: 0;
  color: var(--app-text-muted);
  font-size: 13px;
  line-height: 1.55;
}

.feedback.error {
  background: #fff5f5;
  color: #b42318;
  border: 1px solid #f0d3d3;
}

@media (max-width: 960px) {
  .students-layout {
    grid-template-columns: 1fr;
  }
}
</style>
