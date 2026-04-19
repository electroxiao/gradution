<template>
  <div class="student-page">
    <header class="hero">
      <div>
        <p class="eyebrow">Assignments</p>
        <h1>我的作业</h1>
        <p>查看教师发布的 Java 编程作业，提交代码并查看测试结果。</p>
      </div>
    </header>

    <section class="summary-row">
      <article>
        <span>作业总数</span>
        <strong>{{ assignments.length }}</strong>
      </article>
      <article>
        <span>待完成</span>
        <strong>{{ pendingCount }}</strong>
      </article>
      <article>
        <span>已通过题目</span>
        <strong>{{ acceptedTotal }}</strong>
      </article>
    </section>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section v-if="assignments.length" class="assignment-grid">
      <article v-for="item in assignments" :key="item.id" class="assignment-card">
        <div class="card-top">
          <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
          <span>{{ item.question_count }} 题</span>
        </div>
        <h2>{{ item.title }}</h2>
        <p>{{ item.description || "暂无说明" }}</p>
        <div class="stats">
          <span>已提交 {{ item.submitted_count }}/{{ item.question_count }}</span>
          <span>通过 {{ item.accepted_count }}/{{ item.question_count }}</span>
        </div>
        <router-link class="open-link" :to="`/assignments/${item.id}`">进入作业</router-link>
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
  </div>
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
  min-height: 100vh;
  padding: 28px;
  display: grid;
  gap: 22px;
  background: #f7fbff;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.hero h1 {
  margin: 8px 0 10px;
  font-size: 38px;
  color: #0f2840;
}

.hero p {
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

.assignment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.assignment-card,
.empty,
.feedback,
.summary-row article {
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

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-row article {
  display: grid;
  gap: 6px;
}

.summary-row span {
  color: #6f8297;
}

.summary-row strong {
  color: #10283d;
  font-size: 26px;
}

.assignment-card h2,
.empty h2 {
  margin: 0;
  color: #10283d;
}

.assignment-card p,
.empty p {
  margin: 0;
  color: #6f8297;
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
  background: #ecfdf3;
  color: #027a48;
}

.status.closed {
  background: #f2f4f7;
  color: #475467;
}

.open-link,
.back-link,
.primary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #10283d;
  color: #fff;
  border: none;
  font: inherit;
  text-decoration: none;
  cursor: pointer;
}

.back-link {
  background: #fff;
  color: #18344f;
  border: 1px solid #d7e5f3;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.feedback.error {
  color: #b42318;
  background: #fff8f8;
}

@media (max-width: 720px) {
  .student-page {
    padding: 16px;
  }

  .hero {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-row {
    grid-template-columns: 1fr;
  }
}
</style>
