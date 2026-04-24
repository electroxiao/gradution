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

    <section v-if="assignments.length" class="assignment-list">
      <article v-for="item in assignments" :key="item.id" class="assignment-card">
        <div class="card-main">
          <div class="card-head">
            <div class="card-icon">作</div>
            <div class="card-copy">
              <div class="card-topline">
                <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
                <span class="meta-text">{{ item.question_count }} 题</span>
              </div>
              <h2>{{ item.title }}</h2>
              <p>{{ item.description || "暂无说明" }}</p>
            </div>
          </div>

          <div class="metric-grid">
            <div class="metric-item">
              <span>总题数</span>
              <strong>{{ item.question_count }}</strong>
            </div>
            <div class="metric-item">
              <span>已提交</span>
              <strong>{{ item.submitted_count }}</strong>
            </div>
            <div class="metric-item">
              <span>已通过</span>
              <strong>{{ item.accepted_count }}</strong>
            </div>
          </div>
        </div>

        <div class="card-actions">
          <span class="progress-text">完成 {{ item.accepted_count }}/{{ item.question_count }}</span>
          <router-link class="open-link" :to="`/assignments/${item.id}`">进入作业</router-link>
        </div>
      </article>
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
  gap: 20px;
}

.hero h1 {
  margin: 0 0 8px;
  font-size: 32px;
  line-height: 1.08;
  font-weight: 500;
  color: var(--app-text);
}

.hero p {
  margin: 0;
  color: var(--app-text-muted);
  font-size: 14px;
  line-height: 1.7;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card,
.assignment-card,
.empty,
.feedback {
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.summary-card {
  display: grid;
  gap: 10px;
  padding: 18px 20px;
}

.summary-card span,
.card-copy p,
.progress-text,
.empty p {
  color: var(--app-text-muted);
}

.summary-card strong {
  display: block;
  color: var(--app-text);
  font-size: 28px;
  font-weight: 500;
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

.assignment-list {
  display: grid;
  gap: 16px;
}

.assignment-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  padding: 22px;
  align-items: flex-start;
}

.card-main {
  display: grid;
  gap: 16px;
}

.card-head {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  border-radius: 16px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  font-weight: 700;
  flex-shrink: 0;
}

.card-copy {
  min-width: 0;
}

.card-topline {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.status {
  padding: 5px 10px;
  border-radius: 999px;
  background: #eef5ff;
  color: #35639f;
  font-size: 12px;
  font-weight: 500;
}

.status.closed {
  background: #f0f2f5;
  color: #64748b;
}

.meta-text {
  color: var(--app-text-muted);
  font-size: 13px;
}

.card-copy h2,
.empty h2 {
  margin: 10px 0 6px;
  color: var(--app-text);
  font-size: 26px;
  font-weight: 500;
}

.card-copy p,
.empty p {
  margin: 0;
  line-height: 1.7;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 180px));
  gap: 12px;
}

.metric-item {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border: 1px solid #e6eef7;
  border-radius: var(--app-radius-lg);
  background: var(--app-panel-soft);
}

.metric-item span {
  color: var(--app-text-muted);
  font-size: 13px;
}

.metric-item strong {
  color: var(--app-text);
  font-size: 24px;
  font-weight: 500;
}

.card-actions {
  display: grid;
  justify-items: end;
  gap: 12px;
}

.progress-text {
  font-size: 13px;
}

.open-link,
.back-link,
.primary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 16px;
  border-radius: var(--app-radius-md);
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
  padding: 22px;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.feedback {
  padding: 14px 16px;
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

  .assignment-card {
    grid-template-columns: 1fr;
  }

  .card-actions {
    justify-items: start;
  }
}

@media (max-width: 720px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

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
