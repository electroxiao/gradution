<template>
  <section class="assignment-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Assignments</p>
        <h2>作业管理</h2>
        <p class="page-copy">统一管理作业发布、题目配置与学生完成情况。</p>
      </div>
    </header>

    <div class="page-actions">
      <router-link class="primary-link" to="/teacher/assignments/new">新建作业</router-link>
    </div>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section class="summary-row">
      <article class="summary-item shell-card">
        <span>全部作业</span>
        <strong>{{ assignments.length }}</strong>
      </article>
      <article class="summary-item shell-card">
        <span>已发布</span>
        <strong>{{ publishedCount }}</strong>
      </article>
      <article class="summary-item shell-card">
        <span>学生覆盖</span>
        <strong>{{ totalAssignees }}</strong>
      </article>
      <article class="summary-item shell-card">
        <span>通过提交</span>
        <strong>{{ totalAccepted }}</strong>
      </article>
    </section>

    <section v-if="assignments.length" class="assignment-list">
      <article v-for="item in assignments" :key="item.id" class="assignment-card shell-card">
        <div class="assignment-card-top">
          <div class="title-cell">
            <p class="card-label">Assignment</p>
            <strong>{{ item.title }}</strong>
            <p>{{ item.description || "暂无说明" }}</p>
          </div>
          <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
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

        <div class="action-cell">
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

.shell-card,
.feedback {
  border: 1px solid #e2ebf4;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
}

.page-header h2 {
  margin: 6px 0 10px;
  font-size: 30px;
  font-weight: 500;
  color: #0f2840;
}

.page-copy {
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

.page-actions {
  display: flex;
  justify-content: flex-end;
}

.primary-link,
.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 16px;
  border-radius: 14px;
  color: #fff;
  text-decoration: none;
  white-space: nowrap;
}

.primary-link {
  background: #10283d;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
}

.open-link {
  border: 1px solid #d4e4f2;
  background: rgba(237, 246, 255, 0.74);
  color: #1f5f99;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-item {
  display: grid;
  gap: 8px;
  padding: 18px;
}

.summary-item span,
.metric-item span {
  color: #6f8297;
  font-size: 13px;
}

.summary-item strong {
  color: #10283d;
  font-size: 28px;
  font-weight: 500;
}

.assignment-list {
  display: grid;
  gap: 14px;
}

.assignment-card {
  display: grid;
  gap: 18px;
  padding: 20px 22px;
}

.assignment-card-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.title-cell {
  min-width: 0;
}

.card-label {
  margin: 0 0 8px;
  color: #7a95b1;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.title-cell strong {
  display: block;
  color: #10283d;
  font-size: 22px;
  font-weight: 500;
}

.title-cell p {
  margin: 6px 0 0;
  color: #7b8da0;
  font-size: 14px;
  line-height: 1.6;
}

.status {
  justify-self: start;
  padding: 7px 12px;
  border-radius: 999px;
  background: #edf6ff;
  color: #1f5f99;
  font-size: 13px;
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
}

.metric-item {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #f8fbff;
  border: 1px solid #e6eef7;
}

.metric-item strong {
  color: #10283d;
  font-size: 22px;
  font-weight: 500;
}

.action-cell {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.compact-link {
  min-height: 40px;
}

.empty {
  display: grid;
  justify-items: start;
  gap: 10px;
  padding: 26px;
  color: #6f8297;
}

.empty strong {
  color: #10283d;
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
  background: #fff2f2;
}

@media (max-width: 980px) {
  .summary-row,
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .page-actions,
  .assignment-card-top,
  .action-cell,
  .summary-row,
  .metric-grid {
    display: grid;
  }

  .summary-row,
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .primary-link,
  .open-link {
    width: 100%;
  }
}
</style>
