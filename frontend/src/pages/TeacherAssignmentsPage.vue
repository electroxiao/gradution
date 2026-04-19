<template>
  <section class="assignment-page">
    <header class="page-toolbar">
      <div>
        <p class="eyebrow">Assignments</p>
        <h2>作业管理</h2>
        <p>创建 Java 编程作业，选择学生发布，并查看提交概况。</p>
      </div>
      <router-link class="primary-link" to="/teacher/assignments/new">新建作业</router-link>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section class="summary-row">
      <article class="summary-item">
        <span>全部作业</span>
        <strong>{{ assignments.length }}</strong>
      </article>
      <article class="summary-item">
        <span>已发布</span>
        <strong>{{ publishedCount }}</strong>
      </article>
      <article class="summary-item">
        <span>学生覆盖</span>
        <strong>{{ totalAssignees }}</strong>
      </article>
      <article class="summary-item">
        <span>通过提交</span>
        <strong>{{ totalAccepted }}</strong>
      </article>
    </section>

    <section v-if="assignments.length" class="assignment-table">
      <div class="table-head">
        <span>作业</span>
        <span>状态</span>
        <span>题目</span>
        <span>学生</span>
        <span>提交</span>
        <span>通过</span>
        <span>操作</span>
      </div>
      <article v-for="item in assignments" :key="item.id" class="assignment-row">
        <div class="title-cell">
          <strong>{{ item.title }}</strong>
          <p>{{ item.description || "暂无说明" }}</p>
        </div>
        <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
        <span>{{ item.question_count }}</span>
        <span>{{ item.assignee_count }}</span>
        <span>{{ item.submitted_count }}</span>
        <span>{{ item.accepted_count }}</span>
        <div class="action-cell">
          <router-link class="open-link" :to="`/teacher/assignments/${item.id}/progress`">完成情况</router-link>
          <router-link class="open-link edit-link" :to="`/teacher/assignments/${item.id}`">编辑</router-link>
        </div>
      </article>
    </section>

    <div v-else-if="!errorMessage" class="empty">
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
  gap: 18px;
}

.page-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.page-toolbar h2 {
  margin: 6px 0 8px;
  font-size: 32px;
  color: #0f2840;
}

.page-toolbar p {
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

.primary-link,
.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 8px;
  background: #10283d;
  color: #fff;
  text-decoration: none;
  white-space: nowrap;
}

.open-link {
  min-height: 36px;
  background: #edf6ff;
  color: #1f5f99;
}

.edit-link {
  background: #10283d;
  color: #fff;
}

.action-cell {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-item,
.assignment-table,
.empty,
.feedback {
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.summary-item {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
}

.summary-item span {
  color: #6f8297;
  font-size: 13px;
}

.summary-item strong {
  color: #10283d;
  font-size: 24px;
}

.assignment-table {
  overflow: hidden;
}

.table-head,
.assignment-row {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 92px 70px 70px 70px 70px 170px;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
}

.table-head {
  background: #f8fbff;
  color: #6f8297;
  font-size: 13px;
  font-weight: 700;
}

.assignment-row {
  border-top: 1px solid #eef3f8;
  color: #31465c;
}

.title-cell {
  min-width: 0;
}

.title-cell strong {
  display: block;
  color: #10283d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.title-cell p {
  margin: 4px 0 0;
  color: #7b8da0;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status {
  justify-self: start;
  padding: 4px 8px;
  border-radius: 8px;
  background: #edf6ff;
  color: #1f5f99;
  font-size: 13px;
}

.status.published {
  background: #ecfdf3;
  color: #027a48;
}

.status.closed {
  background: #f2f4f7;
  color: #475467;
}

.empty {
  display: grid;
  justify-items: start;
  gap: 10px;
  padding: 22px;
  color: #6f8297;
}

.empty strong {
  color: #10283d;
  font-size: 20px;
}

.empty p {
  margin: 0;
}

.feedback {
  padding: 12px 14px;
}

.feedback.error {
  color: #b42318;
  background: #fff8f8;
}

@media (max-width: 980px) {
  .summary-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .table-head {
    display: none;
  }

  .assignment-row {
    grid-template-columns: 1fr auto;
    align-items: start;
  }

  .action-cell {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }

  .assignment-row > span:not(.status) {
    font-size: 13px;
  }
}

@media (max-width: 640px) {
  .page-toolbar {
    display: grid;
  }

  .summary-row {
    grid-template-columns: 1fr;
  }
}
</style>
