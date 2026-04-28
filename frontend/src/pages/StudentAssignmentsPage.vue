<template>
  <section class="student-page">
    <header class="hero">
      <div>
        <h1>我的作业</h1>
        <p>查看教师发布的 Java 编程作业，提交代码并查看测试结果。</p>
      </div>
    </header>

    <section class="summary-row">
      <article class="summary-card">
        <span class="summary-dot blue" />
        <span>作业总数</span>
        <strong>{{ assignments.length }}</strong>
      </article>
      <article class="summary-card">
        <span class="summary-dot cyan" />
        <span>待完成</span>
        <strong>{{ pendingCount }}</strong>
      </article>
      <article class="summary-card">
        <span class="summary-dot green" />
        <span>已通过题目</span>
        <strong>{{ acceptedTotal }}</strong>
      </article>
    </section>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section v-if="assignments.length" class="assignment-panel">
      <div class="list-head">
        <h2>作业列表</h2>
      </div>

      <div class="assignment-table">
        <div class="assignment-table-head">
          <span class="col-name">作业名称</span>
          <span>状态</span>
          <span>题目</span>
          <span>已提交</span>
          <span>已通过</span>
          <span>完成进度</span>
          <span>操作</span>
        </div>

        <article v-for="item in assignments" :key="item.id" class="assignment-row">
          <div class="card-copy col-name">
            <h2>{{ item.title }}</h2>
            <p class="date-line">发布时间：{{ formatDateTime(item.created_at) }}</p>
            <p>{{ item.description || "暂无说明" }}</p>
          </div>

          <div><span class="status" :class="item.status">{{ statusText(item.status) }}</span></div>
          <strong class="number-cell">{{ item.question_count }}</strong>
          <strong class="number-cell">{{ item.submitted_count }}</strong>
          <strong class="number-cell">{{ item.accepted_count }}</strong>
          <span class="progress-text">完成 {{ item.accepted_count }}/{{ item.question_count }}</span>
          <div class="card-actions">
            <router-link class="open-link" :to="`/assignments/${item.id}`">进入作业</router-link>
          </div>
        </article>
      </div>
    </section>

    <section v-else-if="!errorMessage" class="empty">
      <h2>当前没有作业</h2>
      <p>教师发布作业后会出现在这里。</p>
      <div class="empty-actions">
        <router-link class="primary-link" to="/chat">去问 AI</router-link>
        <router-link class="back-link" to="/weak-points">查看薄弱点</router-link>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { listStudentAssignmentsApi } from "../api/assignments";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const assignments = ref([]);
const errorMessage = ref("");
const pendingCount = computed(() => {
  return assignments.value.filter((item) => (item.accepted_count || 0) < (item.question_count || 0)).length;
});
const acceptedTotal = computed(() => assignments.value.reduce((sum, item) => sum + (item.accepted_count || 0), 0));

onMounted(loadAssignments);

async function loadAssignments() {
  try {
    const { data } = await listStudentAssignmentsApi();
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
.student-page {
  display: grid;
  gap: 14px;
  font-size: var(--compact-body);
}

.hero h1 {
  margin: 0 0 8px;
  font-size: var(--compact-page-title);
  line-height: 1.08;
  font-weight: 500;
  color: var(--app-text);
}

.hero p {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
  line-height: 1.7;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card,
.assignment-panel,
.empty,
.feedback {
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.summary-card {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
}

.summary-card span,
.card-copy p,
.progress-text,
.empty p,
.cell-muted {
  color: var(--app-text-muted);
}

.summary-card strong {
  display: block;
  color: var(--app-text);
  font-size: var(--compact-stat-sm);
  font-weight: 400;
}

.summary-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.summary-dot.blue {
  background: #2f67f6;
}

.summary-dot.cyan {
  background: #1fb5a8;
}

.summary-dot.green {
  background: #22c55e;
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
}

.list-head h2 {
  margin: 0;
  color: var(--app-text);
  font-size: var(--compact-section-title);
  font-weight: 500;
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
  grid-template-columns: minmax(300px, 3fr) minmax(76px, 0.8fr) repeat(3, minmax(56px, 0.7fr)) minmax(88px, 0.9fr) minmax(92px, 0.9fr);
  gap: 10px;
  align-items: center;
}

.assignment-table-head {
  min-height: 48px;
  padding: 0 14px;
  border-bottom: 1px solid #e8eef6;
  background: #f8fbff;
  color: #2f3f55;
  font-size: var(--compact-body);
  font-weight: 500;
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

.card-copy {
  min-width: 0;
}

.col-name {
  min-width: 0;
}

.status {
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef5ff;
  color: #35639f;
  font-size: 12px;
  font-weight: 400;
}

.status.closed {
  background: #fff1f1;
  color: #d34949;
}

.card-copy h2,
.empty h2 {
  margin: 0 0 5px;
  color: var(--app-text);
  font-size: var(--compact-card-title);
  font-weight: 500;
}

.card-copy p,
.empty p {
  margin: 0;
  font-size: var(--compact-body);
  line-height: 1.45;
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.date-line {
  font-size: var(--compact-caption);
}

.number-cell {
  color: var(--app-text);
  font-size: 16px;
  font-weight: 500;
  text-align: center;
}

.card-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  min-width: 0;
}

.progress-text {
  font-size: 14px;
  text-align: center;
}

.open-link,
.back-link,
.primary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 8px;
  font-size: 14px;
  text-decoration: none;
  cursor: pointer;
}

.open-link,
.primary-link {
  background: var(--app-primary);
  color: #fff;
}

.back-link {
  background: #fff;
  color: #31445f;
  border: 1px solid var(--app-line);
}

.empty {
  display: grid;
  gap: 10px;
  justify-items: start;
  padding: 14px;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.feedback {
  padding: 11px 13px;
  font-size: var(--compact-body);
}

.feedback.error {
  color: #b42318;
  background: #fff5f5;
  border-color: #f0d3d3;
}

@media (max-width: 980px) {
  .summary-row {
    grid-template-columns: 1fr;
  }

  .assignment-panel {
    overflow-x: auto;
  }
}

@media (max-width: 720px) {
  .empty-actions {
    display: grid;
    width: 100%;
  }

  .open-link,
  .back-link,
  .primary-link {
    width: 100%;
  }
}
</style>
