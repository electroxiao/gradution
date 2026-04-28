<template>
  <section class="assignment-page">
    <header class="page-header">
      <div>
        <h2>作业管理</h2>
        <p class="page-copy">统一管理作业发布、题目配置与学生完成情况。</p>
      </div>
      <router-link class="primary-link create-link" to="/teacher/assignments/new">新建作业</router-link>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section class="summary-row">
      <article class="summary-item shell-card blue">
        <div class="summary-icon">作</div>
        <div class="summary-copy">
          <span>全部作业</span>
          <strong>{{ assignments.length }}</strong>
        </div>
      </article>
      <article class="summary-item shell-card green">
        <div class="summary-icon">发</div>
        <div class="summary-copy">
          <span>已发布</span>
          <strong>{{ publishedCount }}</strong>
        </div>
      </article>
      <article class="summary-item shell-card purple">
        <div class="summary-icon">生</div>
        <div class="summary-copy">
          <span>提交次数</span>
          <strong>{{ totalSubmissions }}</strong>
        </div>
      </article>
      <article class="summary-item shell-card amber">
        <div class="summary-icon">通</div>
        <div class="summary-copy">
          <span>通过提交</span>
          <strong>{{ totalAccepted }}</strong>
        </div>
      </article>
    </section>

    <section v-if="assignments.length" class="assignment-panel shell-card">
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
          <span>学生</span>
          <span>提交</span>
          <span>通过</span>
          <span>操作</span>
        </div>
        <article v-for="item in pagedAssignments" :key="item.id" class="assignment-row">
          <div class="assignment-copy col-name">
            <h3>{{ item.title }}</h3>
            <p class="date-line">发布时间：{{ formatDateTime(item.created_at) }}</p>
            <p v-if="item.description" class="description-line">{{ item.description }}</p>
            <p v-else class="description-line muted">暂无说明</p>
          </div>

          <div><span class="status" :class="item.status">{{ statusText(item.status) }}</span></div>
          <strong class="number-cell">{{ item.question_count }}</strong>
          <strong class="number-cell">{{ item.assignee_count }}</strong>
          <strong class="number-cell">{{ item.submitted_count }}</strong>
          <strong class="number-cell">{{ item.accepted_count }}</strong>

          <div class="assignment-actions">
            <router-link class="open-link compact-link" :to="`/teacher/assignments/${item.id}/progress`">查看完成情况</router-link>
            <router-link class="primary-link compact-link" :to="`/teacher/assignments/${item.id}`">编辑</router-link>
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

    <div v-else-if="!errorMessage" class="empty shell-card">
      <strong>还没有作业</strong>
      <p>新建一份 Java 编程作业后，可以在这里跟踪发布和提交情况。</p>
      <router-link class="primary-link" to="/teacher/assignments/new">创建第一份作业</router-link>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { listTeacherAssignmentsApi } from "../api/assignments";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const assignments = ref([]);
const errorMessage = ref("");
const activeFilter = ref("all");
const currentPage = ref(1);
const pageSize = 10;

const filters = [
  { value: "all", label: "全部" },
  { value: "draft", label: "草稿箱" },
  { value: "published", label: "已发布" },
  { value: "closed", label: "已关闭" },
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
  try {
    const { data } = await listTeacherAssignmentsApi();
    assignments.value = data;
  } catch (error) {
    handleApiError(error, "加载作业失败。");
  }
}

function statusText(status) {
  return { draft: "草稿", published: "已发布", closed: "已关闭" }[status] || status;
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
  gap: 14px;
  font-size: var(--compact-body);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-header h2 {
  margin: 0 0 8px;
  color: var(--app-text);
  font-size: var(--compact-page-title);
  font-weight: 500;
}

.page-copy {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
}

.shell-card,
.feedback {
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.create-link,
.primary-link,
.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--compact-control-height);
  padding: 0 14px;
  border-radius: 10px;
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
  gap: 12px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 66px;
  padding: 12px 14px;
}

.summary-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 36px;
  width: 36px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.blue .summary-icon {
  background: #edf3ff;
  color: #2f67f6;
}

.green .summary-icon {
  background: #eefaf3;
  color: #12a15c;
}

.purple .summary-icon {
  background: #f2efff;
  color: #7a5af8;
}

.amber .summary-icon {
  background: #fff7e9;
  color: #f79009;
}

.summary-copy {
  display: grid;
  gap: 3px;
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
  font-size: var(--compact-stat-sm);
  font-weight: 400;
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
  border-radius: 10px;
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
  margin: 0 0 5px;
  color: var(--app-text);
  font-size: var(--compact-card-title);
  font-weight: 500;
  line-height: 1.18;
}

.assignment-copy p {
  margin: 0;
  font-size: var(--compact-body);
  line-height: 1.4;
}

.date-line {
  font-size: var(--compact-caption);
}

.description-line {
  margin-top: 4px !important;
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
  min-height: var(--compact-pill-height);
  padding: 0 9px;
  border-radius: 999px;
  background: #eef5ff;
  color: #35639f;
  font-size: 12px;
  font-weight: 400;
}

.status.published {
  background: #ecfdf3;
  color: #027a48;
}

.status.closed {
  background: #fff1f1;
  color: #d34949;
}

.assignment-table {
  display: grid;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid #e8eef6;
  border-radius: 14px;
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
  min-height: 48px;
  padding: 0 14px;
  background: #f8fbff;
  color: #2f3f55;
  font-size: var(--compact-body);
  font-weight: 500;
  border-bottom: 1px solid #e8eef6;
}

.assignment-row {
  min-height: 72px;
  padding: 12px 14px;
  border-bottom: 1px solid #edf1f6;
}

.assignment-row:last-child {
  border-bottom: 0;
}

.assignment-table-head > span:not(.col-name),
.assignment-row > :not(.col-name) {
  justify-self: center;
  text-align: center;
}

.col-name {
  min-width: 0;
}

.number-cell {
  color: var(--app-text);
  font-size: 16px;
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

.compact-link {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 8px;
  font-size: 14px;
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
  background: #f7f9fc;
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
  border-radius: 16px;
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
  .page-header {
    display: grid;
  }

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
