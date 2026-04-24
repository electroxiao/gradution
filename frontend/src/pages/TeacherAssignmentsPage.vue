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

      <div v-if="filteredAssignments.length" class="assignment-list">
        <article v-for="item in filteredAssignments" :key="item.id" class="assignment-card">
          <div class="assignment-info">
            <div class="assignment-badge">作</div>
            <div class="assignment-copy">
              <div class="title-row">
                <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
              </div>
              <h3>{{ item.title }}</h3>
              <p class="date-line">发布时间：{{ formatDateTime(item.created_at) }}</p>
              <p v-if="item.description" class="description-line">{{ item.description }}</p>
              <p v-else class="description-line muted">暂无说明</p>
            </div>
          </div>

          <div class="metric-grid">
            <div class="metric-item">
              <span>题目</span>
              <strong>{{ item.question_count }}</strong>
            </div>
            <div class="metric-item">
              <span>学生</span>
              <strong>{{ item.assignee_count }}</strong>
            </div>
            <div class="metric-item">
              <span>提交</span>
              <strong>{{ item.submitted_count }}</strong>
            </div>
            <div class="metric-item">
              <span>通过</span>
              <strong>{{ item.accepted_count }}</strong>
            </div>
          </div>

          <div class="assignment-actions">
            <router-link class="open-link" :to="`/teacher/assignments/${item.id}/progress`">完成情况</router-link>
            <router-link class="primary-link compact-link" :to="`/teacher/assignments/${item.id}`">编辑作业</router-link>
          </div>
        </article>
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
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { listTeacherAssignmentsApi } from "../api/assignments";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const assignments = ref([]);
const errorMessage = ref("");
const activeFilter = ref("all");

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

onMounted(loadAssignments);

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
  gap: 22px;
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
  font-size: 36px;
  font-weight: 500;
}

.page-copy {
  margin: 0;
  color: var(--app-text-muted);
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
  min-height: 44px;
  padding: 0 22px;
  border-radius: 10px;
  text-decoration: none;
  white-space: nowrap;
  font-weight: 500;
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
  gap: 20px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 22px;
  min-height: 118px;
  padding: 24px 28px;
}

.summary-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  font-weight: 700;
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
  gap: 6px;
}

.summary-copy span,
.metric-item span,
.assignment-copy p,
.empty p {
  color: var(--app-text-muted);
}

.summary-copy strong {
  color: var(--app-text);
  font-size: 30px;
  font-weight: 500;
}

.assignment-panel {
  display: grid;
  gap: 22px;
  padding: 26px;
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
  font-size: 22px;
  font-weight: 600;
}

.filter-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.filter-tabs button {
  min-height: 42px;
  padding: 0 22px;
  border: 1px solid var(--app-line);
  border-radius: 10px;
  background: #fff;
  color: #31445f;
  font: inherit;
  cursor: pointer;
}

.filter-tabs button.active {
  border-color: var(--app-primary);
  background: var(--app-primary);
  color: #fff;
}

.assignment-list {
  display: grid;
  gap: 16px;
}

.assignment-card {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(420px, 0.78fr) auto;
  gap: 24px;
  padding: 24px;
  align-items: center;
  border: 1px solid var(--app-line);
  border-radius: 16px;
  background: #fff;
}

.assignment-info {
  display: flex;
  gap: 20px;
  align-items: center;
  min-width: 0;
}

.assignment-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  font-weight: 700;
  flex-shrink: 0;
}

.assignment-copy {
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.assignment-copy h3 {
  margin: 8px 0 10px;
  color: var(--app-text);
  font-size: 25px;
  font-weight: 600;
  line-height: 1.2;
}

.assignment-copy p {
  margin: 0;
  line-height: 1.6;
}

.date-line {
  font-size: 14px;
}

.description-line {
  margin-top: 4px !important;
  max-width: 520px;
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
  min-height: 30px;
  padding: 0 11px;
  border-radius: 999px;
  background: #eef5ff;
  color: #35639f;
  font-size: 12px;
  font-weight: 500;
}

.status.published {
  background: #ecfdf3;
  color: #027a48;
}

.status.closed {
  background: #f2f4f7;
  color: #475467;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding-left: 22px;
  border-left: 1px solid #edf1f6;
}

.metric-item {
  display: grid;
  place-items: center;
  gap: 8px;
  min-height: 86px;
  padding: 14px 18px;
  border-radius: 12px;
  background: #f8fafc;
  border: 0;
}

.metric-item strong {
  color: var(--app-text);
  font-size: 26px;
  font-weight: 600;
}

.assignment-actions {
  display: grid;
  justify-items: end;
  gap: 10px;
}

.compact-link {
  min-height: 42px;
}

.empty {
  display: grid;
  justify-items: start;
  gap: 10px;
  padding: 24px;
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
  font-size: 20px;
  font-weight: 500;
}

.empty p {
  margin: 0;
}

.feedback {
  padding: 14px 16px;
}

.feedback.error {
  color: #b42318;
  background: #fff4f4;
  border-color: #f0d3d3;
}

@media (max-width: 1080px) {
  .summary-row,
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .assignment-card {
    grid-template-columns: 1fr;
  }

  .metric-grid {
    padding-left: 0;
    border-left: 0;
  }

  .assignment-actions {
    display: flex;
    justify-content: flex-start;
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

  .summary-row,
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .assignment-panel {
    padding: 18px;
  }

  .assignment-info {
    align-items: flex-start;
  }

  .assignment-actions,
  .create-link,
  .primary-link,
  .open-link {
    width: 100%;
  }
}
</style>
