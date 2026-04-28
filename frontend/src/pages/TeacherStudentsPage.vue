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
          <span>{{ student.class_name || "未分班" }} · {{ student.weak_point_count }} 个薄弱点</span>
        </button>
      </aside>

      <section class="student-detail">
        <div v-if="activeStudent" class="detail-header">
          <div>
            <h3>{{ activeStudent.username }}</h3>
            <p>{{ activeStudent.class_name || "未分班" }} · 当前未掌握 {{ studentWeakPoints.length }} 个节点，已记录 {{ studentMastery.length }} 个作业掌握条目</p>
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
          <div v-else-if="isWeakPointsLoading" class="empty">正在加载薄弱点...</div>
          <div v-else class="empty">该学生当前没有未掌握薄弱点。</div>
        </section>

        <section v-if="portraitSummary || isPortraitLoading" class="detail-section portrait-overview">
          <div class="section-head">
            <h4>画像概览</h4>
          </div>
          <div v-if="portraitSummary" class="portrait-grid">
            <div class="portrait-stat">
              <span>薄弱点</span>
              <strong>{{ portraitSummary.weak_count }}</strong>
            </div>
            <div class="portrait-stat gap">
              <span>根本性薄弱 (Gap)</span>
              <strong>{{ portraitSummary.gap_count }}</strong>
            </div>
            <div class="portrait-stat slip">
              <span>偶发失误 (Slip)</span>
              <strong>{{ portraitSummary.slip_count }}</strong>
            </div>
            <div class="portrait-stat">
              <span>趋势</span>
              <strong>↑{{ portraitSummary.improving_count }} →{{ portraitSummary.stable_count }} ↓{{ portraitSummary.declining_count }}</strong>
            </div>
          </div>
          <p v-if="portraitSummary?.recommendation" class="portrait-reco">{{ portraitSummary.recommendation }}</p>
          <div v-else-if="isPortraitLoading" class="empty">正在加载画像概览...</div>
        </section>

        <section class="detail-section">
          <div class="section-head">
            <h4>作业驱动掌握情况</h4>
            <span>{{ studentMastery.length }} 项</span>
          </div>
          <div v-if="studentMastery.length" class="mastery-list">
            <article
              v-for="item in enrichedMastery"
              :key="item.knowledge_node_id"
              class="mastery-card"
              :class="[item.status, item.portrait?.error_type === 'gap' ? 'has-gap' : '']"
            >
              <div class="mastery-top">
                <strong>
                  {{ item.node_name }}
                  <span v-if="item.portrait?.trend === 'improving'" class="trend-indicator up" title="上升趋势">↑</span>
                  <span v-else-if="item.portrait?.trend === 'declining'" class="trend-indicator down" title="下降趋势">↓</span>
                  <span v-if="item.portrait?.error_type === 'gap'" class="gap-badge" title="根本性薄弱">GAP</span>
                  <span v-else-if="item.portrait?.error_type === 'slip'" class="slip-badge" title="偶发失误">SLIP</span>
                </strong>
                <span class="status-pill" :class="item.status">{{ masteryStatusText(item.status) }}</span>
              </div>
              <div class="score-row">
                <span>掌握分</span>
                <strong>{{ item.mastery_score }}</strong>
              </div>
              <div v-if="item.portrait?.recent_scores?.length" class="mini-trend">
                <span
                  v-for="(point, idx) in item.portrait.recent_scores"
                  :key="idx"
                  class="trend-dot"
                  :class="point.status === 'accepted' ? 'pass' : 'fail'"
                  :title="`${point.status} · ${point.score}分`"
                ></span>
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
          <div v-else-if="isMasteryLoading" class="empty">正在加载作业掌握情况...</div>
          <div v-else class="empty">该学生还没有作业驱动的掌握记录。</div>
        </section>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { getStudentPortraitSummaryApi, listTeacherStudentMasteryApi, listTeacherStudentWeakPointsApi, listTeacherStudentsApi } from "../api/teacher";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const students = ref([]);
const activeStudentId = ref(null);
const studentWeakPoints = ref([]);
const studentMastery = ref([]);
const portraitSummary = ref(null);
const errorMessage = ref("");
const isWeakPointsLoading = ref(false);
const isMasteryLoading = ref(false);
const isPortraitLoading = ref(false);
let activeRequestId = 0;

const activeStudent = computed(() =>
  students.value.find((student) => student.id === activeStudentId.value) || null,
);

const enrichedMastery = computed(() => {
  if (!portraitSummary.value?.concepts) return studentMastery.value;
  const portraitMap = new Map();
  for (const c of portraitSummary.value.concepts) {
    portraitMap.set(c.knowledge_node_id, c);
  }
  return studentMastery.value.map((item) => ({
    ...item,
    portrait: portraitMap.get(item.knowledge_node_id) || null,
  }));
});

onMounted(async () => {
  await loadStudents();
});

async function loadStudents() {
  try {
    const { data } = await listTeacherStudentsApi();
    students.value = data;
    if (students.value.length) {
      selectStudent(students.value[0].id);
    }
  } catch (error) {
    handleApiError(error, "加载学生列表失败。");
  }
}

async function selectStudent(studentId) {
  const requestId = ++activeRequestId;
  activeStudentId.value = studentId;
  studentWeakPoints.value = [];
  studentMastery.value = [];
  portraitSummary.value = null;
  isWeakPointsLoading.value = true;
  isMasteryLoading.value = true;
  isPortraitLoading.value = true;
  errorMessage.value = "";

  try {
    const weakPointsResponse = await listTeacherStudentWeakPointsApi(studentId);
    if (requestId !== activeRequestId) return;
    studentWeakPoints.value = weakPointsResponse.data;
  } catch (error) {
    if (requestId === activeRequestId) {
      handleApiError(error, "加载学生知识画像失败。");
      isMasteryLoading.value = false;
      isPortraitLoading.value = false;
    }
    return;
  } finally {
    if (requestId === activeRequestId) {
      isWeakPointsLoading.value = false;
    }
  }

  const masteryPromise = listTeacherStudentMasteryApi(studentId)
    .then(({ data }) => {
      if (requestId === activeRequestId) {
        studentMastery.value = data;
      }
    })
    .catch((error) => {
      if (requestId === activeRequestId) {
        handleApiError(error, "加载作业掌握情况失败。");
      }
    })
    .finally(() => {
      if (requestId === activeRequestId) {
        isMasteryLoading.value = false;
      }
    });

  const portraitPromise = getStudentPortraitSummaryApi(studentId)
    .then(({ data }) => {
      if (requestId === activeRequestId) {
        portraitSummary.value = normalizePortraitSummary(data);
      }
    })
    .catch(() => {
      if (requestId === activeRequestId) {
        portraitSummary.value = null;
      }
    })
    .finally(() => {
      if (requestId === activeRequestId) {
        isPortraitLoading.value = false;
      }
    });

  await Promise.allSettled([masteryPromise, portraitPromise]);
}

function normalizePortraitSummary(data) {
  if (!data) return null;
  return {
    ...data,
    improving_count: data.improving_count ?? data.trend_summary?.improving ?? 0,
    stable_count: data.stable_count ?? data.trend_summary?.stable ?? 0,
    declining_count: data.declining_count ?? data.trend_summary?.declining ?? 0,
    concepts: Array.isArray(data.concepts) ? data.concepts : [],
  };
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
  if (status === "low_confidence_unmatched") return "低置信待确认";
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
  gap: 16px;
  font-size: var(--compact-body);
}

.page-header h2 {
  margin: 0 0 8px;
  font-size: var(--compact-page-title);
  font-weight: 500;
  color: var(--app-text);
}

.page-copy {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
}

.students-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 14px;
}

.student-list,
.student-detail {
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.student-list {
  padding: 12px;
  display: grid;
  gap: 8px;
  align-self: start;
}

.student-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
}

.student-item strong {
  color: var(--app-text);
  font-weight: 400;
}

.student-item span {
  color: var(--app-text-muted);
  font-size: var(--compact-caption);
}

.student-item.active {
  background: var(--app-primary-soft);
  border-color: #cfdcf3;
}

.student-detail {
  padding: 16px;
  display: grid;
  gap: 14px;
}

.detail-header h3 {
  margin: 0;
  font-size: var(--compact-section-title);
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
  gap: 10px;
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
  font-size: 15px;
  font-weight: 500;
}

.weak-cards,
.mastery-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 10px;
}

.weak-card,
.mastery-card,
.feedback.error,
.empty {
  padding: 12px;
  border-radius: 14px;
  background: var(--app-panel-soft);
  color: var(--app-text-muted);
}

.weak-card strong,
.mastery-card strong {
  display: block;
  color: var(--app-text);
  font-weight: 400;
}

.mastery-card {
  display: grid;
  gap: 8px;
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
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 400;
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
  gap: 8px;
}

.evidence-item {
  display: grid;
  gap: 6px;
  padding: 9px;
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

.portrait-overview {
  padding: 12px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f0f4ff 0%, #f8faff 100%);
  border: 1px solid #dce4f5;
}

.portrait-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.portrait-stat {
  padding: 8px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #eef2f8;
  text-align: center;
}

.portrait-stat span {
  display: block;
  color: #6f8297;
  font-size: 12px;
  margin-bottom: 4px;
}

.portrait-stat strong {
  color: #10283d;
  font-size: 18px;
  font-weight: 400;
}

.portrait-stat.gap {
  background: #fff5f5;
  border-color: #f0d0d0;
}

.portrait-stat.gap strong {
  color: #b42318;
}

.portrait-stat.slip {
  background: #fff8ea;
  border-color: #f0dcb0;
}

.portrait-stat.slip strong {
  color: #9a6700;
}

.portrait-reco {
  margin: 12px 0 0;
  color: #31445f;
  font-size: 13px;
  line-height: 1.55;
}

.trend-indicator {
  display: inline-block;
  margin-left: 4px;
  font-weight: 700;
}

.trend-indicator.up {
  color: #16a34a;
}

.trend-indicator.down {
  color: #b42318;
}

.gap-badge,
.slip-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  vertical-align: middle;
}

.gap-badge {
  background: #fde7e7;
  color: #b42318;
}

.slip-badge {
  background: #fff0d8;
  color: #9a6700;
}

.mini-trend {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.trend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.trend-dot.pass {
  background: #16a34a;
}

.trend-dot.fail {
  background: #ef4444;
}

.mastery-card.has-gap {
  border-left: 3px solid #ef4444;
}

@media (max-width: 960px) {
  .students-layout {
    grid-template-columns: 1fr;
  }

  .portrait-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
