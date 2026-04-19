<template>
  <div class="dashboard-page">
    <header class="dashboard-hero">
      <div>
        <p class="eyebrow">Student Workspace</p>
        <h1>学习工作台</h1>
        <p>先看待完成作业，再按薄弱点和知识图谱继续学习。</p>
      </div>
      <router-link class="primary-link" :to="continueAssignmentLink">继续学习</router-link>
    </header>

    <section class="summary-row">
      <article>
        <span>作业总数</span>
        <strong>{{ assignments.length }}</strong>
      </article>
      <article>
        <span>待完成</span>
        <strong>{{ pendingAssignments.length }}</strong>
      </article>
      <article>
        <span>已通过题目</span>
        <strong>{{ acceptedTotal }}</strong>
      </article>
      <article>
        <span>待掌握薄弱点</span>
        <strong>{{ weakPoints.length }}</strong>
      </article>
    </section>

    <p v-if="assignmentError || weakPointError" class="feedback error">
      {{ assignmentError || weakPointError }}
    </p>

    <main class="dashboard-grid">
      <section class="panel assignment-panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Assignments</p>
            <h2>待完成作业</h2>
          </div>
          <router-link to="/assignments">全部作业</router-link>
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
              <router-link :to="`/assignments/${item.id}`">进入</router-link>
            </div>
          </article>
        </div>
        <div v-else class="empty-state">
          <h3>当前没有待完成作业</h3>
          <p>可以继续问 AI，或者查看薄弱点训练。</p>
          <div class="empty-actions">
            <router-link to="/chat">问 AI</router-link>
            <router-link to="/weak-points">薄弱点</router-link>
          </div>
        </div>
      </section>

      <aside class="side-stack">
        <section class="panel">
          <div class="panel-header">
            <div>
              <p class="eyebrow">Weak Points</p>
              <h2>薄弱点</h2>
            </div>
            <router-link to="/weak-points">去训练</router-link>
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
          <p class="eyebrow">AI Learning</p>
          <h2>从图谱继续问</h2>
          <p>遇到概念不清、代码报错或输出不对时，把现象发给知识图谱助教。</p>
          <router-link to="/chat">打开 AI 学习</router-link>
        </section>
      </aside>
    </main>
  </div>
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
  min-height: 100vh;
  padding: 24px;
  display: grid;
  gap: 18px;
  background: #f6f9fc;
}

.dashboard-hero,
.panel-header,
.assignment-item,
.item-side,
.empty-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.dashboard-hero h1 {
  margin: 6px 0 8px;
  color: #10283d;
  font-size: 36px;
}

.dashboard-hero p,
.panel p,
.assignment-item p,
.empty-state p,
.summary-row span,
.item-side span {
  margin: 0;
  color: #6f8297;
}

.eyebrow {
  margin: 0;
  color: #5b86b3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.panel,
.feedback {
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.7fr);
  gap: 16px;
  align-items: start;
}

.panel {
  padding: 18px;
  display: grid;
  gap: 16px;
}

.panel h2,
.assignment-item h3,
.empty-state h3 {
  margin: 0;
  color: #10283d;
}

.panel-header a,
.assignment-item a,
.empty-actions a,
.learning-card a,
.primary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  background: #fff;
  color: #18344f;
  text-decoration: none;
  cursor: pointer;
}

.assignment-item a,
.learning-card a {
  background: #10283d;
  border-color: #10283d;
  color: #fff;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.summary-row article {
  display: grid;
  gap: 6px;
  padding: 12px;
  border-radius: 8px;
  background: #f8fbff;
}

.summary-row strong {
  color: #10283d;
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
  padding: 14px;
  border: 1px solid #e6eef7;
  border-radius: 8px;
  background: #fbfdff;
}

.assignment-item > div:first-child {
  min-width: 0;
}

.assignment-item h3 {
  margin-top: 8px;
}

.item-side {
  align-items: flex-end;
  flex-direction: column;
  flex-shrink: 0;
}

.status {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 8px;
  background: #ecfdf3;
  color: #027a48;
  font-size: 12px;
}

.status.closed {
  background: #f2f4f7;
  color: #475467;
}

.weak-list article {
  display: grid;
  gap: 6px;
}

.weak-list strong {
  color: #10283d;
}

.learning-card {
  background: #f8fbff;
}

.feedback {
  padding: 12px 14px;
}

.feedback.error {
  color: #b42318;
  background: #fff8f8;
}

@media (max-width: 980px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .summary-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .dashboard-page {
    padding: 16px;
  }

  .dashboard-hero,
  .assignment-item {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-row {
    grid-template-columns: 1fr;
  }

  .item-side {
    align-items: stretch;
  }
}
</style>
