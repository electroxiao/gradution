<template>
  <section class="assignment-page">
    <PageHeader title="作业管理" title-tag="h2">
      <template #actions>
        <router-link class="primary-link create-link" to="/teacher/assignments/new">新建作业</router-link>
      </template>
    </PageHeader>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section v-if="!isInitialLoading" class="summary-row">
      <article class="summary-item shell-card blue">
        <div class="summary-icon"><ClipboardList :size="22" aria-hidden="true" /></div>
        <div class="summary-copy">
          <span>全部作业</span>
          <strong>{{ assignments.length }} <small>份</small></strong>
        </div>
      </article>
      <article class="summary-item shell-card cyan">
        <div class="summary-icon"><Send :size="22" aria-hidden="true" /></div>
        <div class="summary-copy">
          <span>已发布</span>
          <strong>{{ publishedCount }} <small>份</small></strong>
        </div>
      </article>
      <article class="summary-item shell-card amber">
        <div class="summary-icon"><Upload :size="22" aria-hidden="true" /></div>
        <div class="summary-copy">
          <span>提交次数</span>
          <strong>{{ totalSubmissions }} <small>次</small></strong>
        </div>
      </article>
      <article class="summary-item shell-card green">
        <div class="summary-icon"><CircleCheck :size="22" aria-hidden="true" /></div>
        <div class="summary-copy">
          <span>通过提交</span>
          <strong>{{ totalAccepted }} <small>次</small></strong>
        </div>
      </article>
    </section>

    <section v-if="!isInitialLoading && assignments.length" class="assignment-panel shell-card">
      <div class="list-head">
        <h3>作业列表</h3>
        <div class="filter-tabs">
          <button
            v-for="filter in filters"
            :key="filter.value"
            type="button"
            :class="{ active: activeFilter === filter.value }"
            @click="activeFilter = filter.value"
          >
            {{ filter.label }}
          </button>
        </div>
      </div>

      <div v-if="filteredAssignments.length" class="assignment-table">
        <div class="assignment-table-head">
          <span class="col-name">作业名称</span>
          <span>状态</span>
          <span>题目</span>
          <span>班级/学生</span>
          <span>提交</span>
          <span>通过</span>
          <span>操作</span>
        </div>
        <article v-for="item in pagedAssignments" :key="item.id" class="assignment-row">
          <div class="assignment-copy col-name">
            <h3>{{ item.title }}</h3>
            <p class="date-line">{{ assignmentTimeSummary(item) }}</p>
            <p class="type-line muted">{{ assignmentTypeSummary(item) }}</p>
          </div>

          <div><span class="status" :class="item.status">{{ statusText(item.status) }}</span></div>
          <strong class="number-cell">{{ item.question_count }}</strong>
          <strong class="number-cell">{{ classSummary(item) }} / {{ item.assignee_count }}</strong>
          <strong class="number-cell">{{ item.submitted_count }}</strong>
          <strong class="number-cell">{{ item.accepted_count }}</strong>

          <div class="assignment-actions">
            <router-link class="open-link compact-link" :to="`/teacher/assignments/${item.id}/progress`">查看完成情况</router-link>
            <router-link class="primary-link compact-link" :to="`/teacher/assignments/${item.id}`">编辑</router-link>
            <button type="button" class="danger-link compact-link" @click="openDeleteConfirm(item)">删除</button>
          </div>
        </article>
      </div>
      <div v-if="filteredAssignments.length" class="pagination-bar">
        <span>共 {{ filteredAssignments.length }} 条，每页 {{ pageSize }} 条</span>
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
      <div v-else class="empty-filter">当前筛选下没有作业。</div>
    </section>

    <Teleport to="body">
      <div v-if="deleteTarget" class="dialog-backdrop" @click.self="closeDeleteConfirm">
        <div class="dialog-card">
          <h4>删除作业</h4>
          <p>确定删除作业「{{ deleteTarget.title }}」吗？删除后相关题目、提交记录和统计数据将无法恢复。</p>
          <div class="dialog-actions">
            <button type="button" class="ghost-btn" @click="closeDeleteConfirm">取消</button>
            <button type="button" class="danger-btn" :disabled="deletingAssignmentId === deleteTarget.id" @click="confirmDelete">
              确认删除
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <div v-if="hasLoaded && !errorMessage && !assignments.length" class="empty shell-card">
      <strong>还没有作业</strong>
      <p>新建一份 Java 编程作业后，可以在这里跟踪发布和提交情况。</p>
      <router-link class="primary-link" to="/teacher/assignments/new">创建第一份作业</router-link>
    </div>
  </section>
</template>

<script setup>
import { CircleCheck, ClipboardList, Send, Upload } from "lucide-vue-next";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { deleteTeacherAssignmentApi, listTeacherAssignmentsApi } from "../api/assignments";
import PageHeader from "../components/PageHeader.vue";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const assignments = ref([]);
const errorMessage = ref("");
const hasLoaded = ref(false);
const isInitialLoading = ref(true);
const deleteTarget = ref(null);
const deletingAssignmentId = ref(null);
const activeFilter = ref("all");
const currentPage = ref(1);
const pageSize = 10;

const filters = [
  { value: "all", label: "全部" },
  { value: "draft", label: "草稿箱" },
  { value: "published", label: "已发布" },
];

const publishedCount = computed(() => assignments.value.filter((item) => item.status === "published").length);
const totalSubmissions = computed(() =>
  assignments.value.reduce((total, item) => total + Number(item.submitted_count || 0), 0),
);
const totalAccepted = computed(() =>
  assignments.value.reduce((total, item) => total + Number(item.accepted_count || 0), 0),
);
const filteredAssignments = computed(() => {
  if (activeFilter.value === "all") return assignments.value;
  return assignments.value.filter((item) => item.status === activeFilter.value);
});
const totalPages = computed(() => Math.max(1, Math.ceil(filteredAssignments.value.length / pageSize)));
const pageNumbers = computed(() => Array.from({ length: totalPages.value }, (_, index) => index + 1));
const pagedAssignments = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return filteredAssignments.value.slice(start, start + pageSize);
});

onMounted(loadAssignments);

watch(activeFilter, () => {
  currentPage.value = 1;
});

watch(totalPages, (value) => {
  if (currentPage.value > value) currentPage.value = value;
});

async function loadAssignments() {
  if (!hasLoaded.value) isInitialLoading.value = true;
  try {
    const { data } = await listTeacherAssignmentsApi();
    assignments.value = data;
  } catch (error) {
    handleApiError(error, "加载作业失败。");
  } finally {
    hasLoaded.value = true;
    isInitialLoading.value = false;
  }
}

function openDeleteConfirm(item) {
  deleteTarget.value = item;
}

function closeDeleteConfirm() {
  if (deletingAssignmentId.value !== null) return;
  deleteTarget.value = null;
}

async function confirmDelete() {
  if (!deleteTarget.value) return;
  deletingAssignmentId.value = deleteTarget.value.id;
  try {
    await deleteTeacherAssignmentApi(deleteTarget.value.id);
    deleteTarget.value = null;
    await loadAssignments();
  } catch (error) {
    handleApiError(error, "删除作业失败。");
  } finally {
    deletingAssignmentId.value = null;
  }
}

function statusText(status) {
  return { draft: "草稿", published: "已发布", closed: "已发布" }[status] || status;
}

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function classSummary(item) {
  return item.class_names?.length ? item.class_names.join("、") : "--";
}

function assignmentTypeSummary(item) {
  const counts = item.question_type_counts || {};
  const parts = [
    counts.multiple_choice ? `选择题 ${counts.multiple_choice}` : "",
    counts.fill_blank ? `填空题 ${counts.fill_blank}` : "",
    counts.programming ? `编程题 ${counts.programming}` : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "暂无题型统计";
}

function assignmentTimeSummary(item) {
  const start = item.starts_at ? `开始：${formatDateTime(item.starts_at)}` : "开始：发布后立即";
  const due = item.due_at ? `截止：${formatDateTime(item.due_at)}` : "截止：未设置";
  return `${start} · ${due}`;
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
.assignment-page {
  display: grid;
  gap: 11px;
  font-size: var(--compact-body);
}

.shell-card,
.feedback {
  border: 1px solid var(--app-line);
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.create-link,
.primary-link,
.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--compact-control-height);
  padding: 0 14px;
  border-radius: 6px;
  text-decoration: none;
  white-space: nowrap;
  font-size: var(--compact-body);
  font-weight: 400;
}

.primary-link,
.create-link {
  background: var(--app-primary);
  color: #fff;
}

.open-link {
  background: #fff;
  border: 1px solid var(--app-line);
  color: #31445f;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 9px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 78px;
  padding: 14px 18px;
}

.summary-icon {
  width: 48px;
  height: 48px;
  display: inline-grid;
  place-items: center;
  border-radius: 12px;
  flex-shrink: 0;
}

.blue .summary-icon {
  background: #edf3ff;
  color: var(--app-primary);
}

.green .summary-icon {
  background: #eaf8ef;
  color: #229954;
}

.cyan .summary-icon {
  background: #e8fbfb;
  color: #0e9384;
}

.amber .summary-icon {
  background: #fff7e9;
  color: #f79009;
}

.summary-copy {
  display: grid;
  gap: 6px;
}

.summary-copy span,
.metric-item span,
.assignment-copy p,
.empty p,
.cell-muted {
  color: var(--app-text-muted);
}

.summary-copy strong {
  color: var(--app-text);
  font-size: 25px;
  font-weight: 600;
  line-height: 1;
}

.summary-copy small {
  color: var(--app-text);
  font-size: 14px;
  font-weight: 500;
}

.summary-copy span {
  color: #334155;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.2;
}

.assignment-panel.shell-card,
.empty.shell-card,
.feedback {
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.assignment-panel {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.list-head h3 {
  margin: 0;
  color: var(--app-text);
  font-size: var(--compact-section-title);
  font-weight: 500;
}

.filter-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-tabs button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid var(--app-line);
  border-radius: 6px;
  background: #fff;
  color: #31445f;
  font: inherit;
  font-size: var(--compact-body);
  cursor: pointer;
}

.filter-tabs button.active {
  border-color: var(--app-primary);
  background: var(--app-primary);
  color: #fff;
}

.assignment-copy {
  min-width: 0;
}

.assignment-copy h3 {
  margin: 0 0 4px;
  color: var(--app-text);
  font-size: calc(var(--compact-card-title) * 0.75);
  font-weight: 500;
  line-height: 1.12;
}

.assignment-copy p {
  margin: 0;
  font-size: calc(var(--compact-body) * 0.75 + 1px);
  line-height: 1.3;
}

.date-line {
  font-size: calc(var(--compact-caption) * 0.75 + 1px);
}

.type-line {
  margin-top: 3px !important;
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.muted {
  color: var(--app-text-muted);
}

.status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: #eef4ff;
  color: #2952cc;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0.01em;
  box-shadow: 0 1px 2px rgba(17, 24, 39, 0.08);
}

.status.draft {
  background: #fff7ed;
  border-color: #fed7aa;
  color: #c2410c;
}

.status.published {
  background: #eaf8ef;
  border-color: #b7ebc6;
  color: #0f8a4b;
}

.status.closed {
  background: #fff1f2;
  border-color: #fecdd3;
  color: #be123c;
}

.assignment-table {
  display: grid;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--app-line);
  border-radius: 8px;
  background: #fff;
}

.assignment-table-head,
.assignment-row {
  display: grid;
  grid-template-columns: minmax(300px, 3fr) minmax(76px, 0.8fr) repeat(4, minmax(56px, 0.7fr)) minmax(176px, 1.2fr);
  gap: 10px;
  align-items: center;
}

.assignment-table-head {
  min-height: 36px;
  padding: 0 11px;
  background: #ffffff;
  color: #2f3f55;
  font-size: calc(var(--compact-body) * 0.9375);
  font-weight: 500;
  border-bottom: 1px solid var(--app-line);
}

.assignment-row {
  min-height: 46px;
  padding: 7px 11px;
  border-bottom: 1px solid var(--app-line);
}

.assignment-row:last-child {
  border-bottom: 0;
}

.assignment-table-head > span:not(.col-name),
.assignment-row > :not(.col-name) {
  justify-self: center;
  text-align: center;
  transform: translateX(-15px);
}

.col-name {
  min-width: 0;
}

.number-cell {
  color: var(--app-text);
  font-size: 12px;
  font-weight: 500;
  text-align: center;
}

.assignment-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.assignment-actions > * {
  flex: 1 1 0;
}

.compact-link {
  width: 100%;
  min-height: 29px;
  padding: 0 11px;
  border-radius: 8px;
  font-size: 11px;
  white-space: nowrap;
}

.danger-link {
  width: 100%;
  border: 1px solid #fecaca;
  background: #fff5f5;
  color: #c53030;
  cursor: pointer;
}

.danger-link:hover {
  background: #ffecec;
}

.danger-link:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: center;
  background: rgba(9, 19, 33, 0.46);
}

.dialog-card {
  width: min(92vw, 380px);
  padding: 18px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 28px 70px rgba(15, 23, 42, 0.28);
}

.dialog-card h4 {
  margin: 0 0 10px;
  color: var(--app-text);
}

.dialog-card p {
  margin: 0 0 16px;
  color: var(--app-text-muted);
  line-height: 1.45;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.ghost-btn,
.danger-btn {
  min-height: 34px;
  padding: 0 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.ghost-btn {
  background: #f4f7fb;
  color: #475569;
}

.danger-btn {
  background: #ef4444;
  color: #fff;
}

.danger-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
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

.empty {
  display: grid;
  justify-items: start;
  gap: 10px;
  padding: 16px;
}

.empty-filter {
  padding: 38px;
  border: 1px dashed #d9e2ed;
  border-radius: 10px;
  color: var(--app-text-muted);
  text-align: center;
}

.empty strong {
  color: var(--app-text);
  font-size: var(--compact-section-title);
  font-weight: 500;
}

.empty p {
  margin: 0;
}

.feedback {
  padding: 11px 13px;
  font-size: var(--compact-body);
}

.feedback.error {
  color: #b42318;
  background: #fff4f4;
  border-color: #f0d3d3;
}

@media (max-width: 1080px) {
  .summary-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .assignment-panel {
    overflow-x: auto;
  }
}

@media (max-width: 720px) {
  .list-head {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-row {
    grid-template-columns: 1fr;
  }

  .assignment-panel {
    padding: 14px;
  }

  .pagination-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .pagination-controls {
    flex-wrap: wrap;
  }
}
</style>
