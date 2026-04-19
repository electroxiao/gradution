<template>
  <section class="assignment-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Assignments</p>
        <h2>作业管理</h2>
        <p>创建 Java 编程作业，选择学生发布，并查看提交概况。</p>
      </div>
      <router-link class="primary-link" to="/teacher/assignments/new">新建作业</router-link>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section v-if="assignments.length" class="assignment-grid">
      <article v-for="item in assignments" :key="item.id" class="assignment-card">
        <div class="card-top">
          <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
          <span>{{ item.question_count }} 题</span>
        </div>
        <h3>{{ item.title }}</h3>
        <p>{{ item.description || "暂无说明" }}</p>
        <div class="stats">
          <span>学生 {{ item.assignee_count }}</span>
          <span>提交 {{ item.submitted_count }}</span>
          <span>通过 {{ item.accepted_count }}</span>
        </div>
        <router-link class="open-link" :to="`/teacher/assignments/${item.id}`">编辑作业</router-link>
      </article>
    </section>

    <div v-else-if="!errorMessage" class="empty">还没有作业，先创建一份 Java 编程作业。</div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { listTeacherAssignmentsApi } from "../api/assignments";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const assignments = ref([]);
const errorMessage = ref("");

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
  gap: 22px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.page-header h2 {
  margin: 8px 0 10px;
  font-size: 34px;
  color: #0f2840;
}

.page-header p {
  margin: 0;
  color: #6f8297;
}

.eyebrow {
  color: #5b86b3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.primary-link,
.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 11px 14px;
  border-radius: 8px;
  background: #10283d;
  color: #fff;
  text-decoration: none;
}

.assignment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.assignment-card,
.empty,
.feedback {
  padding: 18px;
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.06);
}

.assignment-card {
  display: grid;
  gap: 12px;
}

.assignment-card h3 {
  margin: 0;
  color: #10283d;
}

.assignment-card p {
  margin: 0;
  color: #6f8297;
  min-height: 44px;
}

.card-top,
.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #6f8297;
  font-size: 13px;
}

.status {
  padding: 3px 8px;
  border-radius: 8px;
  background: #edf6ff;
  color: #1f5f99;
}

.status.published {
  background: #ecfdf3;
  color: #027a48;
}

.status.closed {
  background: #f2f4f7;
  color: #475467;
}

.feedback.error {
  color: #b42318;
  background: #fff8f8;
}
</style>
