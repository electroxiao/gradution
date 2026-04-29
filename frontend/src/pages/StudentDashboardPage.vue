<template>
  <section class="app-page dashboard-page">
    <header class="dashboard-hero">
      <div class="app-header-copy">
        <h1 class="app-title">学习工作台</h1>
        <p class="app-subtitle">先看待完成作业，再按薄弱点和知识图谱继续学习。</p>
      </div>
      <div class="dashboard-hero-actions">
        <router-link class="app-button" :to="continueAssignmentLink">继续学习</router-link>
        <router-link class="app-button-ghost" to="/chat">打开学习助手</router-link>
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
        <strong>{{ pendingAssignments.length }}</strong>
      </article>
      <article class="summary-card">
        <span class="summary-dot green" />
        <span>已通过题目</span>
        <strong>{{ acceptedTotal }}</strong>
      </article>
      <article class="summary-card">
        <span class="summary-dot amber" />
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
            <h2>待完成作业</h2>
          </div>
          <router-link class="app-button-ghost" to="/assignments">全部作业</router-link>
        </div>

        <div v-if="pendingAssignments.length" class="assignment-list">
          <article v-for="item in pendingAssignments.slice(0, 4)" :key="item.id" class="assignment-item">
            <div class="item-main">
              <div class="item-head">
                <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
                <span class="item-meta">{{ item.question_count }} 题</span>
              </div>
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
        <section class="panel learning-card">
          <div class="learning-card-head">
            <div>
              <h2>从图谱继续问</h2>
            </div>
          </div>
          <div class="learning-card-body">
            <div class="learning-copy">
              <p>遇到概念不清、代码报错或输出不对时，把现象发给知识图谱助教。</p>
              <router-link class="app-button" to="/chat">开始提问</router-link>
            </div>
            <div class="learning-visual" aria-hidden="true">
              <div class="visual-ribbon ribbon-one" />
              <div class="visual-ribbon ribbon-two" />
              <div class="visual-panel">
                <span class="visual-pill">AI</span>
                <span class="visual-line long" />
                <span class="visual-line mid" />
                <span class="visual-line short" />
              </div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
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
  display: grid;
  gap: 14px;
  font-size: var(--compact-body);
}

.dashboard-page .app-title {
  margin: 0 0 8px;
  font-size: var(--compact-page-title);
  line-height: 1.08;
  font-weight: 500;
}

.dashboard-page .app-subtitle {
  margin: 0;
  font-size: var(--compact-body);
  line-height: 1.7;
}

.dashboard-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
}

.dashboard-hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card,
.panel {
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

.summary-card span {
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

.summary-dot.amber {
  background: #f59e0b;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.52fr) minmax(280px, 0.88fr);
  gap: 14px;
  align-items: stretch;
}

.panel {
  padding: 16px;
  display: grid;
  gap: 12px;
}

.assignment-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.assignment-panel .assignment-list,
.assignment-panel .empty-state {
  flex: 1;
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
  margin: 0;
  color: var(--app-text);
  font-weight: 500;
}

.panel h2 {
  font-size: var(--compact-section-title);
}

.assignment-list {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  width: min(100%, 640px);
}

.weak-list,
.side-stack {
  display: grid;
  gap: 14px;
}

.side-stack {
  align-self: stretch;
}

.assignment-item,
.weak-list article,
.empty-state {
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid #e6eef7;
  background: var(--app-panel-soft);
}

.assignment-item {
  width: 100%;
  align-self: flex-start;
}

.assignment-panel .empty-state {
  width: min(100%, 640px);
}

.item-main {
  min-width: 0;
}

.item-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 5px;
}

.item-meta {
  color: var(--app-text-soft);
  font-size: 12px;
}

.assignment-item p,
.empty-state p,
.weak-list p,
.item-side span {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
  line-height: 1.45;
}

.assignment-item h3 {
  margin-bottom: 5px;
  font-size: var(--compact-card-title);
}

.item-side {
  align-items: flex-end;
  flex-direction: column;
  flex-shrink: 0;
  min-width: 120px;
}

.status {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef5ff;
  color: #37659f;
  font-size: 12px;
  font-weight: 400;
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
  font-weight: 400;
}

.learning-card p:last-of-type {
  margin: 0;
  color: var(--app-text-muted);
  line-height: 1.7;
}

.learning-card {
  align-content: start;
  gap: 16px;
}

.learning-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.learning-card .app-button {
  justify-self: start;
}

.learning-card .app-button-ghost {
  flex-shrink: 0;
}

.learning-card-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px;
  gap: 12px;
  align-items: center;
}

.learning-copy {
  display: grid;
  gap: 14px;
}

.learning-copy .app-button {
  width: fit-content;
}

.learning-visual {
  position: relative;
  min-height: 120px;
}

.visual-ribbon {
  position: absolute;
  left: 12px;
  right: 12px;
  border-radius: 999px;
  background: rgba(47, 103, 246, 0.1);
}

.ribbon-one {
  top: 20px;
  height: 18px;
}

.ribbon-two {
  top: 72px;
  height: 18px;
  background: rgba(47, 103, 246, 0.08);
}

.visual-panel {
  position: absolute;
  inset: 18px 14px 14px 32px;
  display: grid;
  gap: 10px;
  padding: 12px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(238, 244, 255, 0.92) 0%, rgba(255, 255, 255, 0.92) 100%);
  box-shadow: 0 18px 42px rgba(47, 103, 246, 0.08);
}

.visual-pill {
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #2f67f6;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.visual-line {
  display: block;
  height: 10px;
  border-radius: 999px;
  background: #dbe5f7;
}

.visual-line.long {
  width: 92%;
}

.visual-line.mid {
  width: 72%;
}

.visual-line.short {
  width: 54%;
}

@media (max-width: 980px) {
  .summary-row {
    grid-template-columns: repeat(4, minmax(120px, 1fr));
  }

  .dashboard-grid {
    grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.9fr);
  }

  .dashboard-hero-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .learning-card-body {
    grid-template-columns: 1fr;
  }

  .learning-visual {
    min-height: 124px;
  }
}

@media (max-width: 640px) {
  .summary-row,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .dashboard-hero-actions,
  .panel-header,
  .assignment-item,
  .item-side,
  .empty-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .learning-card-head {
    flex-direction: column;
  }
}
</style>
