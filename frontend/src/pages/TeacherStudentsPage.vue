<template>
  <section v-if="!isInitialLoading" class="students-page" :class="{ 'content-ready': shouldAnimateReady }">
    <PageHeader title="学生薄弱点" title-tag="h2" />

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
            <span class="student-main">
              <strong>{{ student.username }}</strong>
              <small>{{ student.class_name || "未分班" }}</small>
            </span>
            <span class="weak-badge">{{ student.weak_point_count || 0 }}</span>
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

        <section class="detail-grid">
          <article class="detail-panel">
            <div class="section-head">
              <h4>薄弱知识点</h4>
            </div>
            <div class="table-head">
              <span>知识点</span>
            </div>
            <div v-if="!isWeakPointsLoading && studentWeakPoints.length" class="knowledge-list">
              <div v-for="item in studentWeakPoints" :key="item.id" class="knowledge-row">
                <strong>{{ item.node_name }}</strong>
                <span>最近出现 {{ formatDate(item.last_seen_at) }}</span>
              </div>
            </div>
            <div v-else-if="hasStudentsLoaded" class="empty-state">
              <span class="empty-mark"><SearchX :size="30" aria-hidden="true" /></span>
              <strong>暂无薄弱知识点</strong>
              <p>继续保持，棒极了！</p>
            </div>
          </article>

          <article class="detail-panel">
            <div class="section-head">
              <h4>最近提问知识点</h4>
            </div>
            <div v-if="!isWeakPointsLoading && studentConsultations.length" class="knowledge-list consultation-list">
              <div
                v-for="item in studentConsultations"
                :key="item.knowledge_node_id"
                class="knowledge-row consultation-row"
              >
                <strong>{{ item.node_name }}</strong>
                <span>{{ item.mention_count }} 次提问</span>
              </div>
            </div>
            <div v-else-if="hasStudentsLoaded" class="empty-state">
              <span class="empty-mark"><MessagesSquare :size="30" aria-hidden="true" /></span>
              <strong>暂无提问记录</strong>
              <p>该生暂无任何提问知识点记录。</p>
            </div>
          </article>
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
  listTeacherStudentConsultationsApi,
  listTeacherStudentWeakPointsApi,
  listTeacherStudentsApi,
} from "../api/teacher";
import PageHeader from "../components/PageHeader.vue";
import { clearAuthSession } from "../utils/authStorage";
import { useDelayedReadyAnimation } from "../utils/useDelayedReadyAnimation";

const router = useRouter();
const pageSize = 10;
const students = ref([]);
const activeStudentId = ref(null);
const studentWeakPoints = ref([]);
const studentConsultations = ref([]);
const searchQuery = ref("");
const classFilter = ref("");
const sortMode = ref("weak-desc");
const currentPage = ref(1);
const errorMessage = ref("");
const isInitialLoading = ref(true);
const shouldAnimateReady = useDelayedReadyAnimation(isInitialLoading);
const isStudentsLoading = ref(true);
const hasStudentsLoaded = ref(false);
const isWeakPointsLoading = ref(false);
let activeRequestId = 0;

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
  isWeakPointsLoading.value = true;
  errorMessage.value = "";

  try {
    const [weakPointsResponse, consultationsResponse] = await Promise.all([
      listTeacherStudentWeakPointsApi(studentId),
      listTeacherStudentConsultationsApi(studentId, 12),
    ]);
    if (requestId !== activeRequestId) return;
    studentWeakPoints.value = weakPointsResponse.data;
    studentConsultations.value = consultationsResponse.data || [];
  } catch (error) {
    if (requestId === activeRequestId) {
      handleApiError(error, "加载学生知识画像失败。");
    }
    return;
  } finally {
    if (requestId === activeRequestId) {
      isWeakPointsLoading.value = false;
    }
  }
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
  isWeakPointsLoading.value = false;
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
  grid-template-columns: minmax(232px, 272px) minmax(0, 1fr);
  gap: 14px;
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
  padding: 18px;
  display: grid;
  gap: 14px;
  align-self: start;
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
  font-size: 18px;
}

.list-head span {
  color: var(--app-text-muted);
  font-size: var(--compact-caption);
}

.list-controls {
  display: grid;
  gap: 10px;
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
  height: 38px;
  padding: 0 12px;
  border-radius: 8px;
}

.select-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
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
  gap: 6px;
  min-height: 526px;
  align-content: start;
}

.student-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  min-height: 48px;
  padding: 8px 8px 8px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.student-item:hover {
  background: #f7faff;
}

.student-item.active {
  background: #f8fbff;
  border-color: #8db3ff;
  box-shadow: 0 0 0 3px rgba(47, 103, 246, 0.08);
}

.student-main {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.student-main strong {
  color: var(--app-text);
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.student-main small {
  color: var(--app-text-muted);
  font-size: 12px;
}

.weak-badge {
  min-width: 34px;
  height: 28px;
  display: inline-grid;
  place-items: center;
  border-radius: 8px;
  background: #edf3ff;
  color: var(--app-primary);
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

@media (max-width: 1180px) {
  .students-workbench {
    grid-template-columns: minmax(208px, 240px) minmax(0, 1fr);
  }

  .summary-grid,
  .detail-grid {
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
}
</style>
