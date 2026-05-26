<template>
  <section class="students-page">
    <PageHeader title="学生画像" title-tag="h2" />

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <div class="students-workbench">
      <aside class="student-list-panel">
        <div class="list-head">
          <h3>学生列表</h3>
          <span>共 {{ filteredStudents.length }} 名学生</span>
        </div>

        <div class="list-controls">
          <label class="search-field">
            <span>搜索</span>
            <input v-model.trim="searchQuery" type="search" placeholder="搜索学生姓名" />
          </label>

          <div class="select-row">
            <label>
              <span>分类</span>
              <Listbox v-model="classFilter" as="div" class="animated-select">
                <div class="animated-select-wrap">
                  <ListboxButton class="animated-select-button">
                    <span>{{ classFilter || "全部班级" }}</span>
                    <ChevronDown :size="16" aria-hidden="true" />
                  </ListboxButton>
                  <Transition name="select-pop">
                    <ListboxOptions class="animated-select-options">
                      <ListboxOption v-slot="{ active, selected }" as="template" value="">
                        <li :class="['animated-select-option', { active, selected }]">全部班级</li>
                      </ListboxOption>
                      <ListboxOption
                        v-for="className in classOptions"
                        v-slot="{ active, selected }"
                        :key="className"
                        as="template"
                        :value="className"
                      >
                        <li :class="['animated-select-option', { active, selected }]">{{ className }}</li>
                      </ListboxOption>
                    </ListboxOptions>
                  </Transition>
                </div>
              </Listbox>
            </label>

            <label>
              <span>排序</span>
              <Listbox v-model="sortMode" as="div" class="animated-select">
                <div class="animated-select-wrap">
                  <ListboxButton class="animated-select-button">
                    <span>{{ sortLabel }}</span>
                    <ChevronDown :size="16" aria-hidden="true" />
                  </ListboxButton>
                  <Transition name="select-pop">
                    <ListboxOptions class="animated-select-options">
                      <ListboxOption v-slot="{ active, selected }" as="template" value="weak-desc">
                        <li :class="['animated-select-option', { active, selected }]">按薄弱点数</li>
                      </ListboxOption>
                      <ListboxOption v-slot="{ active, selected }" as="template" value="unfinished-desc">
                        <li :class="['animated-select-option', { active, selected }]">按未完成作业数</li>
                      </ListboxOption>
                      <ListboxOption v-slot="{ active, selected }" as="template" value="name-asc">
                        <li :class="['animated-select-option', { active, selected }]">按姓名</li>
                      </ListboxOption>
                    </ListboxOptions>
                  </Transition>
                </div>
              </Listbox>
            </label>
          </div>
        </div>

        <div v-if="!isStudentsLoading && pagedStudents.length" class="student-items">
          <button
            v-for="student in pagedStudents"
            :key="student.id"
            type="button"
            class="student-item"
            :class="{ active: student.id === activeStudentId }"
            @click="selectStudent(student.id)"
          >
            <span class="student-avatar">{{ studentInitial(student.username) }}</span>
            <span class="student-main">
              <strong>{{ student.username }}</strong>
              <small>{{ student.class_name || "未分班" }}</small>
            </span>
            <span class="student-status">
              <i :class="studentStatusClass(student)" aria-hidden="true"></i>
              <span class="weak-badge">{{ student.weak_point_count || 0 }}</span>
            </span>
          </button>
        </div>
        <div v-else-if="hasStudentsLoaded" class="list-empty">暂无匹配学生。</div>

        <div class="pagination-bar">
          <button type="button" :disabled="currentPage <= 1" aria-label="上一页" @click="goPage(currentPage - 1)">
            <ChevronLeft :size="16" aria-hidden="true" />
          </button>
          <span>{{ currentPage }}</span>
          <button type="button" :disabled="currentPage >= totalPages" aria-label="下一页" @click="goPage(currentPage + 1)">
            <ChevronRight :size="16" aria-hidden="true" />
          </button>
        </div>
      </aside>

      <section v-if="activeStudent" class="student-profile">
        <section class="summary-grid">
          <article class="summary-card weak-summary">
            <span class="summary-icon"><TriangleAlert :size="22" aria-hidden="true" /></span>
            <div>
              <p>当前薄弱点</p>
              <strong>{{ studentWeakPoints.length }} <small>个</small></strong>
            </div>
          </article>
          <article class="summary-card consultation-summary">
            <span class="summary-icon"><MessageCircleQuestion :size="22" aria-hidden="true" /></span>
            <div>
              <p>最近提问知识点</p>
              <strong>{{ studentConsultations.length }} <small>个</small></strong>
            </div>
          </article>
          <article class="summary-card assignment-summary">
            <span class="summary-icon"><ClipboardList :size="22" aria-hidden="true" /></span>
            <div>
              <p>未完成作业次数</p>
              <strong>{{ activeStudent.unfinished_assignment_count || 0 }} <small>次</small></strong>
            </div>
          </article>
        </section>

        <section class="portrait-card">
          <div class="portrait-head">
            <div>
              <h3>{{ activeStudent.username }}</h3>
              <p>{{ activeStudent.class_name || "未分班" }} · 学习画像</p>
            </div>
            <span class="portrait-meta">最近更新 {{ portraitUpdatedAt }}</span>
          </div>

          <div class="portrait-tabs" role="tablist" aria-label="学生画像分类">
            <button
              v-for="tab in portraitTabs"
              :key="tab.value"
              type="button"
              :class="{ active: activeTab === tab.value }"
              role="tab"
              :aria-selected="activeTab === tab.value"
              @click="activeTab = tab.value"
            >
              <component :is="tab.icon" :size="16" aria-hidden="true" />
              <span>{{ tab.label }}</span>
            </button>
          </div>

          <section v-if="activeTab === 'weak-points'" class="tab-panel">
            <div class="section-head">
              <h4>薄弱知识点</h4>
              <span>{{ studentWeakPoints.length }} 个待关注</span>
            </div>
            <div v-if="!isPortraitLoading && studentWeakPoints.length" class="knowledge-list">
              <div v-for="item in studentWeakPoints" :key="item.id" class="knowledge-row portrait-row">
                <div>
                  <strong>{{ item.node_name }}</strong>
                  <small>首次出现 {{ formatDate(item.first_seen_at) }}</small>
                </div>
                <span>{{ weakPointStatusText(item.status) }} · {{ formatDate(item.last_seen_at) }}</span>
              </div>
            </div>
            <div v-else-if="hasStudentsLoaded" class="empty-state">
              <span class="empty-mark"><SearchX :size="30" aria-hidden="true" /></span>
              <strong>暂无薄弱知识点</strong>
              <p>继续保持，棒极了！</p>
            </div>
          </section>

          <section v-else-if="activeTab === 'assignments'" class="tab-panel">
            <div class="section-head">
              <h4>作业情况</h4>
              <span>{{ studentAssignments.length }} 个作业</span>
            </div>
            <div v-if="!isPortraitLoading && studentAssignments.length" class="assignment-list">
              <article v-for="assignment in studentAssignments" :key="assignment.assignment_id" class="assignment-row">
                <div class="assignment-main">
                  <span class="status-pill" :class="assignment.status">{{ assignmentStatusText(assignment.status) }}</span>
                  <div>
                    <h4>{{ assignment.title }}</h4>
                    <p>
                      {{ assignment.accepted_question_count }}/{{ assignment.question_count }} 题通过 ·
                      {{ assignment.submitted_question_count }}/{{ assignment.question_count }} 题已提交
                    </p>
                  </div>
                </div>
                <div class="assignment-meta">
                  <span>截止 {{ formatDate(assignment.due_at) }}</span>
                  <span>最后提交 {{ formatDate(assignment.latest_submitted_at) }}</span>
                </div>
                <router-link
                  class="open-link"
                  :to="`/teacher/assignments/${assignment.assignment_id}/progress?studentId=${activeStudent.id}`"
                >
                  查看进度
                </router-link>
              </article>
            </div>
            <div v-else-if="hasStudentsLoaded" class="empty-state">
              <span class="empty-mark"><ClipboardList :size="30" aria-hidden="true" /></span>
              <strong>暂无已布置作业</strong>
              <p>该生暂时没有需要跟踪的作业。</p>
            </div>
          </section>

          <section v-else class="tab-panel consultation-panel">
            <div class="section-head">
              <h4>提问情况</h4>
              <span>{{ studentConsultations.length }} 个知识点</span>
            </div>
            <div v-if="!isPortraitLoading && studentConsultations.length" class="consultation-layout">
              <div class="consultation-list">
                <button
                  v-for="item in studentConsultations"
                  :key="item.knowledge_node_id"
                  type="button"
                  class="consultation-item"
                  :class="{ active: selectedConsultationNodeId === item.knowledge_node_id }"
                  @click="selectConsultationNode(item)"
                >
                  <span>
                    <strong>{{ item.node_name }}</strong>
                    <small>最近提问 {{ formatDate(item.last_seen_at) }}</small>
                  </span>
                  <em>{{ item.mention_count }} 次</em>
                </button>
              </div>

              <aside class="turn-panel">
                <div class="turn-head">
                  <div>
                    <h4>{{ selectedConsultation?.node_name || "选择知识点" }}</h4>
                    <p>{{ selectedConsultation ? "相关问答时间线" : "点击左侧知识点查看聊天定位" }}</p>
                  </div>
                  <MessagesSquare :size="20" aria-hidden="true" />
                </div>
                <div v-if="isTurnsLoading" class="timeline-empty">正在加载聊天记录...</div>
                <div v-else-if="consultationTurns.length" class="turn-timeline">
                  <article v-for="turn in consultationTurns" :key="turn.event_id" class="turn-card">
                    <button type="button" class="turn-summary" @click="toggleTurn(turn.event_id)">
                      <span class="timeline-dot" aria-hidden="true"></span>
                      <span>
                        <strong>{{ turn.session_title }}</strong>
                        <small>{{ formatDateTime(turn.asked_at) }}</small>
                      </span>
                      <ChevronDown :size="16" :class="{ expanded: expandedTurnId === turn.event_id }" aria-hidden="true" />
                    </button>
                    <div class="turn-preview">
                      <p><b>学生：</b>{{ summarizeText(turn.user_content) }}</p>
                      <p><b>AI：</b>{{ summarizeText(turn.assistant_content) }}</p>
                    </div>
                    <div v-if="expandedTurnId === turn.event_id" class="turn-full">
                      <section>
                        <h5>学生提问</h5>
                        <p>{{ turn.user_content }}</p>
                      </section>
                      <section>
                        <h5>AI 回答</h5>
                        <p>{{ turn.assistant_content }}</p>
                      </section>
                    </div>
                  </article>
                </div>
                <div v-else class="timeline-empty">
                  {{ selectedConsultation ? "暂无可展开的聊天记录。" : "尚未选择提问知识点。" }}
                </div>
              </aside>
            </div>
            <div v-else-if="hasStudentsLoaded" class="empty-state">
              <span class="empty-mark"><MessagesSquare :size="30" aria-hidden="true" /></span>
              <strong>暂无提问记录</strong>
              <p>该生暂无任何提问知识点记录。</p>
            </div>
          </section>
        </section>
      </section>

      <section v-else class="student-profile empty-profile">
        <div class="empty-state">
          <span class="empty-mark"><SearchX :size="30" aria-hidden="true" /></span>
          <strong>请选择学生</strong>
          <p>左侧筛选结果为空时，可以调整搜索或班级分类。</p>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from "@headlessui/vue";
import {
  ClipboardList,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  MessageCircleQuestion,
  MessagesSquare,
  SearchX,
  TriangleAlert,
} from "lucide-vue-next";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import {
  listTeacherStudentAssignmentsApi,
  listTeacherStudentConsultationTurnsApi,
  listTeacherStudentConsultationsApi,
  listTeacherStudentWeakPointsApi,
  listTeacherStudentsApi,
} from "../api/teacher";
import PageHeader from "../components/PageHeader.vue";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const pageSize = 10;
const students = ref([]);
const activeStudentId = ref(null);
const studentWeakPoints = ref([]);
const studentConsultations = ref([]);
const studentAssignments = ref([]);
const consultationTurns = ref([]);
const activeTab = ref("weak-points");
const selectedConsultationNodeId = ref(null);
const expandedTurnId = ref(null);
const searchQuery = ref("");
const classFilter = ref("");
const sortMode = ref("weak-desc");
const currentPage = ref(1);
const errorMessage = ref("");
const isInitialLoading = ref(true);
const isStudentsLoading = ref(true);
const hasStudentsLoaded = ref(false);
const isPortraitLoading = ref(false);
const isTurnsLoading = ref(false);
let activeRequestId = 0;
let activeTurnsRequestId = 0;

const portraitTabs = [
  { value: "weak-points", label: "薄弱点", icon: TriangleAlert },
  { value: "assignments", label: "作业情况", icon: ClipboardList },
  { value: "consultations", label: "提问情况", icon: MessageCircleQuestion },
];

const activeStudent = computed(() =>
  students.value.find((student) => student.id === activeStudentId.value) || null,
);

const classOptions = computed(() => {
  const names = students.value
    .map((student) => student.class_name)
    .filter((className) => className && className.trim());
  return Array.from(new Set(names)).sort((a, b) => a.localeCompare(b, "zh-CN"));
});

const filteredStudents = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase();
  return students.value
    .filter((student) => {
      const matchesName = !keyword || (student.username || "").toLowerCase().includes(keyword);
      const matchesClass = !classFilter.value || student.class_name === classFilter.value;
      return matchesName && matchesClass;
    })
    .slice()
    .sort(compareStudents);
});

const totalPages = computed(() => Math.max(1, Math.ceil(filteredStudents.value.length / pageSize)));

const pagedStudents = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return filteredStudents.value.slice(start, start + pageSize);
});

const sortLabel = computed(() => {
  if (sortMode.value === "unfinished-desc") return "按未完成作业数";
  if (sortMode.value === "name-asc") return "按姓名";
  return "按薄弱点数";
});

const selectedConsultation = computed(() =>
  studentConsultations.value.find((item) => item.knowledge_node_id === selectedConsultationNodeId.value) || null,
);

const portraitUpdatedAt = computed(() => {
  const candidates = [
    ...studentWeakPoints.value.map((item) => item.last_seen_at),
    ...studentConsultations.value.map((item) => item.last_seen_at),
    ...studentAssignments.value.map((item) => item.latest_submitted_at),
  ].filter(Boolean);
  if (!candidates.length) return "--";
  return formatDateTime(candidates.sort().at(-1));
});

watch([searchQuery, classFilter, sortMode], () => {
  currentPage.value = 1;
  syncActiveStudentWithFilters();
});

watch(filteredStudents, () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value;
  }
});

onMounted(async () => {
  await loadStudents();
});

async function loadStudents() {
  isStudentsLoading.value = true;
  try {
    const studentsResponse = await listTeacherStudentsApi();
    students.value = studentsResponse.data;
    if (filteredStudents.value.length) {
      await selectStudent(filteredStudents.value[0].id);
    }
  } catch (error) {
    handleApiError(error, "加载学生列表失败。");
  } finally {
    hasStudentsLoaded.value = true;
    isStudentsLoading.value = false;
    isInitialLoading.value = false;
  }
}

async function selectStudent(studentId) {
  if (!studentId) return;
  const requestId = ++activeRequestId;
  activeStudentId.value = studentId;
  studentWeakPoints.value = [];
  studentConsultations.value = [];
  studentAssignments.value = [];
  consultationTurns.value = [];
  selectedConsultationNodeId.value = null;
  expandedTurnId.value = null;
  isPortraitLoading.value = true;
  errorMessage.value = "";

  try {
    const [weakPointsResponse, consultationsResponse, assignmentsResponse] = await Promise.all([
      listTeacherStudentWeakPointsApi(studentId),
      listTeacherStudentConsultationsApi(studentId, 12),
      listTeacherStudentAssignmentsApi(studentId),
    ]);
    if (requestId !== activeRequestId) return;
    studentWeakPoints.value = weakPointsResponse.data;
    studentConsultations.value = consultationsResponse.data || [];
    studentAssignments.value = assignmentsResponse.data || [];
  } catch (error) {
    if (requestId === activeRequestId) {
      handleApiError(error, "加载学生知识画像失败。");
    }
    return;
  } finally {
    if (requestId === activeRequestId) {
      isPortraitLoading.value = false;
    }
  }
}

async function selectConsultationNode(item) {
  if (!activeStudentId.value || !item?.knowledge_node_id) return;
  const requestId = ++activeTurnsRequestId;
  selectedConsultationNodeId.value = item.knowledge_node_id;
  consultationTurns.value = [];
  expandedTurnId.value = null;
  isTurnsLoading.value = true;
  errorMessage.value = "";
  try {
    const response = await listTeacherStudentConsultationTurnsApi(activeStudentId.value, item.knowledge_node_id, 20);
    if (requestId !== activeTurnsRequestId) return;
    consultationTurns.value = response.data || [];
  } catch (error) {
    if (requestId === activeTurnsRequestId) {
      handleApiError(error, "加载相关聊天记录失败。");
    }
  } finally {
    if (requestId === activeTurnsRequestId) {
      isTurnsLoading.value = false;
    }
  }
}

function toggleTurn(eventId) {
  expandedTurnId.value = expandedTurnId.value === eventId ? null : eventId;
}

function compareStudents(left, right) {
  if (sortMode.value === "unfinished-desc") {
    return (
      (right.unfinished_assignment_count || 0) - (left.unfinished_assignment_count || 0)
      || (right.weak_point_count || 0) - (left.weak_point_count || 0)
      || left.username.localeCompare(right.username, "zh-CN")
    );
  }
  if (sortMode.value === "name-asc") {
    return left.username.localeCompare(right.username, "zh-CN");
  }
  return (
    (right.weak_point_count || 0) - (left.weak_point_count || 0)
    || (right.unfinished_assignment_count || 0) - (left.unfinished_assignment_count || 0)
    || left.username.localeCompare(right.username, "zh-CN")
  );
}

function syncActiveStudentWithFilters() {
  const hasActive = filteredStudents.value.some((student) => student.id === activeStudentId.value);
  if (hasActive) return;
  const nextStudent = filteredStudents.value[0];
  if (nextStudent) {
    selectStudent(nextStudent.id);
    return;
  }
  activeRequestId += 1;
  activeStudentId.value = null;
  studentWeakPoints.value = [];
  studentConsultations.value = [];
  studentAssignments.value = [];
  consultationTurns.value = [];
  selectedConsultationNodeId.value = null;
  expandedTurnId.value = null;
  isPortraitLoading.value = false;
  isTurnsLoading.value = false;
}

function goPage(page) {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value);
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

function weakPointStatusText(status) {
  if (status === "mastered") return "已掌握";
  if (status === "reviewing") return "巩固中";
  return "未掌握";
}

function assignmentStatusText(status) {
  if (status === "completed") return "已完成";
  if (status === "submitted") return "已提交";
  if (status === "partial") return "部分提交";
  return "未提交";
}

function summarizeText(value, limit = 72) {
  const normalized = String(value || "").replace(/\s+/g, " ").trim();
  if (!normalized) return "暂无内容";
  return normalized.length > limit ? `${normalized.slice(0, limit)}...` : normalized;
}

function studentInitial(name) {
  const normalized = String(name || "").trim();
  return normalized ? normalized.slice(0, 1).toUpperCase() : "?";
}

function studentStatusClass(student) {
  if ((student.unfinished_assignment_count || 0) > 0) return "warn";
  if ((student.weak_point_count || 0) > 0) return "active";
  return "quiet";
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
  gap: 18px;
  font-size: var(--compact-body);
}

.students-workbench {
  display: grid;
  grid-template-columns: minmax(238px, 286px) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.student-list-panel,
.summary-card,
.detail-panel,
.empty-profile {
  border: 1px solid var(--app-line);
  border-radius: 18px;
  background: #ffffff;
  box-shadow: var(--app-shadow-strong);
}

.student-list-panel {
  padding: 14px 12px 12px;
  display: grid;
  gap: 12px;
  align-self: start;
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}

.list-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}

.list-head h3,
.section-head h4 {
  margin: 0;
  color: var(--app-text);
  font-weight: 600;
}

.list-head h3 {
  font-size: 16px;
}

.list-head span {
  color: var(--app-text-muted);
  font-size: var(--compact-caption);
}

.list-controls {
  display: grid;
  gap: 8px;
}

.search-field,
.select-row label {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.search-field span,
.select-row span {
  color: var(--app-text-muted);
  font-size: 12px;
}

.search-field input,
.animated-select-button {
  height: 34px;
  padding: 0 10px;
  border-radius: 8px;
}

.select-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 8px;
}

.animated-select {
  width: 100%;
  min-width: 0;
}

.animated-select-wrap {
  position: relative;
}

.animated-select-button {
  width: 100%;
  min-height: 37px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid var(--app-line);
  background: #fff;
  color: #214666;
  font: inherit;
  text-align: left;
}

.animated-select-button:hover:not(:disabled),
.animated-select-button[aria-expanded="true"] {
  border-color: #bfd0ea;
  background: #fff;
}

.animated-select-button span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.animated-select-button svg {
  flex: 0 0 auto;
  color: #7890a7;
  transition: transform 140ms var(--motion-ease);
}

.animated-select-button[aria-expanded="true"] svg {
  transform: rotate(180deg);
}

.animated-select-options {
  position: absolute;
  z-index: 30;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 6px;
  list-style: none;
  border: 1px solid #dce8f5;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.12);
  transform-origin: top center;
}

.animated-select-option {
  padding: 9px 10px;
  border-radius: 7px;
  color: #214666;
  cursor: pointer;
  line-height: 1.25;
}

.animated-select-option.active {
  background: var(--app-primary-soft);
  color: var(--app-primary-deep);
}

.animated-select-option.selected {
  background: var(--app-primary);
  color: #ffffff;
}

.select-pop-enter-active,
.select-pop-leave-active {
  transition:
    opacity 140ms var(--motion-ease),
    transform 140ms var(--motion-ease);
}

.select-pop-enter-from,
.select-pop-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}

.select-pop-enter-to,
.select-pop-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.student-items {
  display: grid;
  gap: 2px;
  min-height: 500px;
  max-height: calc(100vh - 360px);
  overflow-y: auto;
  padding-right: 2px;
  align-content: start;
}

.student-item {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  gap: 9px;
  align-items: center;
  min-height: 54px;
  padding: 7px 8px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.student-item:hover {
  background: #f7faff;
}

.student-item.active {
  background: #f8fbff;
  border-color: #3f73ff;
  box-shadow: 0 0 0 2px rgba(47, 103, 246, 0.08);
}

.student-avatar {
  width: 34px;
  height: 34px;
  display: inline-grid;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #e8f0ff, #cfdcff);
  color: var(--app-primary);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0;
}

.student-main {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.student-main strong {
  color: var(--app-text);
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.student-main small {
  color: var(--app-text-muted);
  font-size: 11px;
}

.student-status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.student-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
}

.student-status i.active {
  background: #39c980;
}

.student-status i.warn {
  background: #f5b83d;
}

.weak-badge {
  min-width: 28px;
  height: 26px;
  display: inline-grid;
  place-items: center;
  border-radius: 9px;
  background: #edf3ff;
  color: var(--app-primary);
  font-size: 13px;
  font-weight: 600;
}

.student-item.active .weak-badge {
  background: #e8f0ff;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  min-height: 32px;
  color: var(--app-text-muted);
}

.pagination-bar button {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 8px;
  background: #ffffff;
  color: var(--app-text-muted);
  cursor: pointer;
}

.pagination-bar span {
  min-width: 34px;
  height: 30px;
  display: inline-grid;
  place-items: center;
  border-radius: 8px;
  background: #edf3ff;
  color: var(--app-primary);
  font-weight: 600;
}

.student-profile {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 13px;
}

.summary-card {
  min-height: 98px;
  padding: 18px;
  display: flex;
  gap: 14px;
  align-items: center;
}

.summary-icon {
  width: 48px;
  height: 48px;
  display: inline-grid;
  place-items: center;
  border-radius: 12px;
  flex-shrink: 0;
}

.weak-summary .summary-icon {
  background: #fff7e9;
  color: #f79009;
}

.consultation-summary .summary-icon {
  background: #e8fbfb;
  color: #0e9384;
}

.assignment-summary .summary-icon {
  background: #edf3ff;
  color: var(--app-primary);
}

.summary-card p {
  margin: 0 0 6px;
  color: #334155;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.2;
}

.summary-card strong {
  color: var(--app-text);
  font-size: 25px;
  font-weight: 600;
  line-height: 1;
}

.summary-card small {
  color: var(--app-text);
  font-size: 14px;
  font-weight: 500;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 14px;
}

.detail-panel {
  min-height: 390px;
  padding: 22px;
  display: grid;
  gap: 16px;
  align-content: start;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.section-head h4 {
  font-size: 18px;
}

.table-head {
  padding: 0 0 12px;
  border-bottom: 1px solid var(--app-line);
  color: var(--app-text-muted);
  font-size: 13px;
}

.knowledge-list {
  display: grid;
  gap: 8px;
}

.knowledge-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  min-height: 42px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f3f7;
}

.knowledge-row:last-child {
  border-bottom: 0;
}

.knowledge-row strong {
  color: var(--app-text);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.knowledge-row span {
  color: var(--app-text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.consultation-row span {
  color: var(--app-primary);
}

.empty-state,
.list-empty {
  display: grid;
  place-items: center;
  gap: 8px;
  min-height: 220px;
  color: var(--app-text-muted);
  text-align: center;
}

.list-empty {
  min-height: 526px;
}

.empty-state strong {
  color: #334155;
  font-size: 15px;
  font-weight: 500;
}

.empty-state p {
  margin: 0;
  color: var(--app-text-muted);
}

.empty-mark {
  width: 64px;
  height: 64px;
  display: inline-grid;
  place-items: center;
  border-radius: 20px;
  background: #edf3ff;
  color: #6e97e8;
  font-size: 30px;
}

.empty-profile {
  min-height: 640px;
  padding: 24px;
}

.feedback.error {
  padding: 12px;
  border: 1px solid #f0d3d3;
  border-radius: 8px;
  background: #fff5f5;
  color: #b42318;
}

.portrait-card {
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--app-line);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: var(--app-shadow-strong);
}

.portrait-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding-bottom: 14px;
  border-bottom: 1px solid #edf1f6;
}

.portrait-head h3 {
  margin: 0 0 4px;
  color: var(--app-text);
  font-size: 20px;
  font-weight: 600;
}

.portrait-head p,
.portrait-meta {
  margin: 0;
  color: var(--app-text-muted);
  font-size: 13px;
}

.portrait-tabs {
  display: flex;
  gap: 8px;
  margin: 14px 0;
  padding: 4px;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #f8fafc;
}

.portrait-tabs button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 12px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #4a6078;
  font: inherit;
  cursor: pointer;
}

.portrait-tabs button.active {
  background: #ffffff;
  color: var(--app-primary);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.tab-panel {
  min-height: 420px;
}

.section-head span {
  color: var(--app-text-muted);
  font-size: 13px;
}

.portrait-row {
  grid-template-columns: minmax(0, 1fr) auto;
  padding: 12px 0;
}

.portrait-row div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.portrait-row small {
  color: var(--app-text-muted);
  font-size: 12px;
}

.assignment-list {
  display: grid;
  gap: 10px;
}

.assignment-row {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(170px, 0.8fr) auto;
  gap: 16px;
  align-items: center;
  padding: 14px;
  border: 1px solid #edf1f6;
  border-radius: 8px;
  background: #ffffff;
}

.assignment-main {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-width: 0;
}

.assignment-main h4 {
  margin: 0 0 4px;
  color: var(--app-text);
  font-size: 15px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.assignment-main p,
.assignment-meta span {
  margin: 0;
  color: var(--app-text-muted);
  font-size: 12px;
}

.assignment-meta {
  display: grid;
  gap: 5px;
}

.status-pill {
  min-width: 64px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  border-radius: 999px;
  background: #edf3ff;
  color: var(--app-primary);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-pill.completed {
  background: #e8f7ef;
  color: #067647;
}

.status-pill.submitted {
  background: #eff8ff;
  color: #175cd3;
}

.status-pill.partial {
  background: #fff7e9;
  color: #b54708;
}

.status-pill.not_submitted {
  background: #fff1f3;
  color: #b42318;
}

.open-link {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 10px;
  border: 1px solid #dbe6f3;
  border-radius: 8px;
  color: var(--app-primary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.open-link:hover {
  background: #f5f8ff;
}

.consultation-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.72fr) minmax(0, 1.28fr);
  gap: 14px;
  align-items: start;
}

.consultation-list {
  display: grid;
  gap: 8px;
}

.consultation-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid #edf1f6;
  border-radius: 8px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
}

.consultation-item:hover,
.consultation-item.active {
  border-color: #9cbcff;
  background: #f8fbff;
}

.consultation-item span {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.consultation-item strong {
  color: var(--app-text);
  font-size: 14px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.consultation-item small {
  color: var(--app-text-muted);
  font-size: 12px;
}

.consultation-item em {
  color: var(--app-primary);
  font-size: 13px;
  font-style: normal;
  font-weight: 600;
  white-space: nowrap;
}

.turn-panel {
  min-height: 360px;
  padding: 14px;
  border: 1px solid #edf1f6;
  border-radius: 8px;
  background: #fbfcfe;
}

.turn-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.turn-head h4 {
  margin: 0 0 4px;
  color: var(--app-text);
  font-size: 16px;
}

.turn-head p {
  margin: 0;
  color: var(--app-text-muted);
  font-size: 12px;
}

.turn-timeline {
  display: grid;
  gap: 10px;
}

.turn-card {
  padding: 12px;
  border: 1px solid #e7edf5;
  border-radius: 8px;
  background: #ffffff;
}

.turn-summary {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.timeline-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--app-primary);
  box-shadow: 0 0 0 4px #e8f0ff;
}

.turn-summary strong {
  display: block;
  color: var(--app-text);
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.turn-summary small {
  color: var(--app-text-muted);
  font-size: 12px;
}

.turn-summary svg {
  color: #8091a7;
  transition: transform 140ms var(--motion-ease);
}

.turn-summary svg.expanded {
  transform: rotate(180deg);
}

.turn-preview {
  display: grid;
  gap: 5px;
  margin-top: 10px;
  padding-left: 19px;
}

.turn-preview p,
.turn-full p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.55;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.turn-full {
  display: grid;
  gap: 10px;
  margin-top: 12px;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.turn-full h5 {
  margin: 0 0 6px;
  color: var(--app-text);
  font-size: 13px;
}

.timeline-empty {
  min-height: 220px;
  display: grid;
  place-items: center;
  color: var(--app-text-muted);
  text-align: center;
}

@media (max-width: 1180px) {
  .students-workbench {
    grid-template-columns: minmax(208px, 240px) minmax(0, 1fr);
  }

  .summary-grid,
  .detail-grid,
  .consultation-layout,
  .assignment-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .students-workbench {
    grid-template-columns: 1fr;
  }

  .student-items,
  .list-empty {
    min-height: 0;
  }

  .knowledge-row {
    grid-template-columns: 1fr;
  }

  .knowledge-row span {
    white-space: normal;
  }

  .portrait-head,
  .portrait-tabs {
    align-items: stretch;
  }

  .portrait-head,
  .portrait-tabs {
    flex-direction: column;
  }

  .portrait-tabs {
    display: grid;
    grid-template-columns: 1fr;
  }

  .assignment-row,
  .assignment-main,
  .consultation-item {
    grid-template-columns: 1fr;
  }
}
</style>
