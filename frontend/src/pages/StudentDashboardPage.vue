<template>
  <section class="app-page dashboard-page">
    <header class="app-header">
      <div class="app-header-copy">
        <p class="app-eyebrow">Student Workspace</p>
        <h1 class="app-title">学习工作台</h1>
        <p class="app-subtitle">先看待完成作业，再按薄弱点和知识图谱继续学习。</p>
      </div>
      <div class="app-toolbar">
        <router-link class="app-button" :to="continueAssignmentLink">继续学习</router-link>
      </div>
    </header>

    <section class="summary-row">
      <article class="summary-card">
        <span>作业总数</span>
        <strong>{{ assignments.length }}</strong>
      </article>
      <article class="summary-card">
        <span>待完成</span>
        <strong>{{ pendingAssignments.length }}</strong>
      </article>
      <article class="summary-card">
        <span>已通过题目</span>
        <strong>{{ acceptedTotal }}</strong>
      </article>
      <article class="summary-card">
        <span>待掌握薄弱点</span>
        <strong>{{ weakPoints.length }}</strong>
      </article>
    </section>

    <p v-if="assignmentError || weakPointError" class="app-feedback error">
      {{ assignmentError || weakPointError }}
    </p>

    <main class="dashboard-grid">
      <section class="panel assignment-panel">
        <div class="panel-header">
          <div>
            <p class="app-eyebrow">Assignments</p>
            <h2>待完成作业</h2>
          </div>
          <router-link class="app-button-ghost" to="/assignments">全部作业</router-link>
        </div>

        <div v-if="pendingAssignments.length" class="assignment-list">
          <article v-for="item in pendingAssignments.slice(0, 4)" :key="item.id" class="assignment-item">
            <div>
              <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
              <h3>{{ item.title }}</h3>
              <p>{{ item.description || "暂无说明" }}</p>
            </div>
            <div class="item-side">
              <span>{{ item.submitted_count }}/{{ item.question_count }} 已提交</span>
              <router-link class="app-button" :to="`/assignments/${item.id}`">进入</router-link>
            </div>
          </article>
        </div>
        <div v-else class="empty-state">
          <h3>当前没有待完成作业</h3>
          <p>可以继续问 AI，或者查看薄弱点训练。</p>
          <div class="empty-actions">
            <router-link class="app-button" to="/chat">问 AI</router-link>
            <router-link class="app-button-ghost" to="/weak-points">薄弱点</router-link>
          </div>
        </div>
      </section>

      <aside class="side-stack">
        <section class="panel">
          <div class="panel-header">
            <div>
              <p class="app-eyebrow">Weak Points</p>
              <h2>薄弱点</h2>
            </div>
            <router-link class="app-button-ghost" to="/weak-points">去训练</router-link>
          </div>
          <div v-if="weakPoints.length" class="weak-list">
            <article v-for="item in weakPoints.slice(0, 5)" :key="item.id || item.node_id || item.name">
              <strong>{{ item.name || item.node_name || item.title }}</strong>
              <p>{{ item.reason || item.description || "建议优先补齐这个知识点。" }}</p>
            </article>
          </div>
          <div v-else class="empty-state compact">
            <h3>暂无薄弱点</h3>
            <p>先在 AI 对话中围绕 Java 知识点提问。</p>
          </div>
        </section>

        <section class="panel learning-card">
          <p class="app-eyebrow">AI Learning</p>
          <h2>从图谱继续问</h2>
          <p>遇到概念不清、代码报错或输出不对时，把现象发给知识图谱助教。</p>
          <router-link class="app-button" to="/chat">打开 AI 学习</router-link>
        </section>
      </aside>
    </main>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { listStudentAssignmentsApi } from "../api/assignments";
import { listWeakPointsApi } from "../api/weakPoints";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const assignments = ref([]);
const weakPoints = ref([]);
const assignmentError = ref("");
const weakPointError = ref("");

const pendingAssignments = computed(() => {
  return assignments.value.filter((item) => (item.accepted_count || 0) < (item.question_count || 0));
});
const acceptedTotal = computed(() => assignments.value.reduce((sum, item) => sum + (item.accepted_count || 0), 0));
const continueAssignmentLink = computed(() => {
  return pendingAssignments.value.length ? `/assignments/${pendingAssignments.value[0].id}` : "/chat";
});

onMounted(() => {
  loadAssignments();
  loadWeakPoints();
});

async function loadAssignments() {
  try {
    const { data } = await listStudentAssignmentsApi();
    assignments.value = data;
  } catch (error) {
    handleApiError(error, "作业加载失败。", assignmentError);
  }
}

async function loadWeakPoints() {
  try {
    const { data } = await listWeakPointsApi();
    weakPoints.value = data;
  } catch (error) {
    handleApiError(error, "薄弱点加载失败。", weakPointError);
  }
}

function statusText(status) {
  return { draft: "草稿", published: "已发布", closed: "已关闭" }[status] || status;
}

function handleApiError(error, fallbackMessage, target) {
  const status = error?.response?.status;
  if (status === 401 || status === 403) {
    clearAuthSession();
    router.push("/login");
    return;
  }
  target.value = error?.response?.data?.detail || fallbackMessage;
}
</script>

<style scoped>
.dashboard-page {
  gap: 22px;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.summary-card,
.panel {
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.summary-card {
  padding: 20px 22px;
}

.summary-card span {
  color: var(--app-text-muted);
}

.summary-card strong {
  display: block;
  margin-top: 10px;
  color: var(--app-text);
  font-size: 30px;
  font-weight: 500;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.8fr);
  gap: 18px;
  align-items: start;
}

.panel {
  padding: 22px;
  display: grid;
  gap: 18px;
}

.panel-header,
.assignment-item,
.item-side,
.empty-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.panel h2,
.assignment-item h3,
.empty-state h3 {
  margin: 10px 0 0;
  color: var(--app-text);
  font-weight: 500;
}

.panel h2 {
  font-size: 24px;
}

.assignment-list,
.weak-list,
.side-stack {
  display: grid;
  gap: 12px;
}

.assignment-item,
.weak-list article,
.empty-state {
  padding: 16px;
  border-radius: 20px;
  border: 1px solid #e6eef7;
  background: var(--app-panel-soft);
}

.assignment-item p,
.empty-state p,
.weak-list p,
.item-side span {
  margin: 0;
  color: var(--app-text-muted);
  line-height: 1.65;
}

.assignment-item h3 {
  margin-bottom: 8px;
}

.item-side {
  align-items: flex-end;
  flex-direction: column;
  flex-shrink: 0;
}

.status {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  background: #eef5ff;
  color: #37659f;
  font-size: 12px;
  font-weight: 500;
}

.status.closed {
  background: #f0f2f5;
  color: #64748b;
}

.weak-list article {
  display: grid;
  gap: 6px;
}

.weak-list strong {
  color: var(--app-text);
  font-weight: 500;
}

.learning-card p:last-of-type {
  margin: 0;
  color: var(--app-text-muted);
  line-height: 1.7;
}

@media (max-width: 980px) {
  .summary-row,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .panel-header,
  .assignment-item,
  .item-side,
  .empty-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
