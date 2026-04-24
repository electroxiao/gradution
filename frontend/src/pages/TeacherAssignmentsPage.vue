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
          <span>学生覆盖</span>
          <strong>{{ totalAssignees }}</strong>
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

    <section v-if="assignments.length" class="assignment-list">
      <article v-for="item in assignments" :key="item.id" class="assignment-card shell-card">
        <div class="assignment-main">
          <div class="assignment-head">
            <div class="assignment-badge">作</div>
            <div class="assignment-copy">
              <div class="title-row">
                <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
              </div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.description || "暂无说明" }}</p>
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
        </div>

        <div class="assignment-actions">
          <router-link class="open-link" :to="`/teacher/assignments/${item.id}/progress`">完成情况</router-link>
          <router-link class="primary-link compact-link" :to="`/teacher/assignments/${item.id}`">编辑作业</router-link>
        </div>
      </article>
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

const publishedCount = computed(() => assignments.value.filter((item) => item.status === "published").length);
const totalAssignees = computed(() =>
  assignments.value.reduce((total, item) => total + Number(item.assignee_count || 0), 0),
);
const totalAccepted = computed(() =>
  assignments.value.reduce((total, item) => total + Number(item.accepted_count || 0), 0),
);

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
  gap: 20px;
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
  font-size: 32px;
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
  padding: 0 18px;
  border-radius: var(--app-radius-md);
  text-decoration: none;
  white-space: nowrap;
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
  gap: 16px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 22px;
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

.assignment-list {
  display: grid;
  gap: 18px;
}

.assignment-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 22px;
  padding: 22px 24px;
  align-items: center;
}

.assignment-main {
  display: grid;
  gap: 18px;
}

.assignment-head {
  display: flex;
  gap: 16px;
  align-items: flex-start;
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
  margin: 10px 0 8px;
  color: var(--app-text);
  font-size: 26px;
  font-weight: 500;
}

.assignment-copy p {
  margin: 0;
  line-height: 1.7;
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
  gap: 14px;
}

.metric-item {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: var(--app-radius-lg);
  background: var(--app-panel-soft);
  border: 1px solid #e6eef7;
}

.metric-item strong {
  color: var(--app-text);
  font-size: 24px;
  font-weight: 500;
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

  .assignment-actions {
    justify-items: start;
  }
}

@media (max-width: 720px) {
  .page-header {
    display: grid;
  }

  .summary-row,
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .assignment-actions,
  .create-link,
  .primary-link,
  .open-link {
    width: 100%;
  }
}
</style>
