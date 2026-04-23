<template>
  <section class="dashboard-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Overview</p>
        <h2>数据看板</h2>
        <p class="page-copy">汇总全体学生当前被标记最多的薄弱点节点，帮助教师快速定位共性问题。</p>
      </div>
    </header>

    <div v-if="errorMessage" class="feedback error">{{ errorMessage }}</div>

    <section v-if="dashboard" class="metrics">
      <article class="metric-card">
        <span>学生总数</span>
        <strong>{{ dashboard.total_students }}</strong>
      </article>
      <article class="metric-card">
        <span>未掌握薄弱点</span>
        <strong>{{ dashboard.total_unmastered_weak_points }}</strong>
      </article>
      <article class="metric-card">
        <span>受影响学生数</span>
        <strong>{{ dashboard.affected_students }}</strong>
      </article>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>薄弱点热点排行</h3>
        <button @click="loadDashboard">刷新</button>
      </div>

      <div v-if="dashboard?.top_nodes?.length" class="rank-list">
        <article v-for="(item, index) in dashboard.top_nodes" :key="item.id" class="rank-item">
          <div class="rank-index">{{ index + 1 }}</div>
          <div class="rank-copy">
            <strong>{{ item.node_name }}</strong>
            <span>被标记 {{ item.mark_count }} 次</span>
          </div>
          <div class="rank-bar">
            <div class="rank-fill" :style="{ width: `${barWidth(item.mark_count)}%` }" />
          </div>
        </article>
      </div>
      <div v-else class="empty">暂无可展示的统计数据。</div>
    </section>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { getTeacherDashboardApi } from "../api/teacher";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const dashboard = ref(null);
const errorMessage = ref("");

onMounted(async () => {
  await loadDashboard();
});

async function loadDashboard() {
  try {
    const { data } = await getTeacherDashboardApi();
    dashboard.value = data;
  } catch (error) {
    handleApiError(error, "加载数据看板失败。");
  }
}

function barWidth(markCount) {
  if (!dashboard.value?.top_nodes?.length) return 0;
  const max = Math.max(...dashboard.value.top_nodes.map((item) => item.mark_count || 0), 1);
  return Math.max(18, (markCount / max) * 100);
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
.dashboard-page {
  display: grid;
  gap: 22px;
}

.page-header h2 {
  margin: 8px 0 10px;
  font-size: 30px;
  font-weight: 500;
  color: #0f2840;
}

.eyebrow {
  margin: 0;
  color: #5b86b3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.page-copy {
  margin: 0;
  color: #6f8297;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.metric-card,
.panel {
  border: 1px solid #e2ebf4;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
}

.metric-card {
  padding: 20px 22px;
}

.metric-card span {
  color: #71849a;
}

.metric-card strong {
  display: block;
  margin-top: 10px;
  font-size: 34px;
  color: #10283d;
}

.panel {
  padding: 20px 22px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.panel-head h3 {
  margin: 0;
  color: #10283d;
}

.panel-head button {
  border: none;
  border-radius: 999px;
  padding: 10px 14px;
  background: #edf4ff;
  color: #27517c;
  cursor: pointer;
}

.rank-list {
  display: grid;
  gap: 12px;
}

.rank-item {
  display: grid;
  grid-template-columns: 38px minmax(0, 240px) minmax(0, 1fr);
  gap: 14px;
  align-items: center;
}

.rank-index {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #eff5ff;
  color: #3869a0;
  font-weight: 700;
}

.rank-copy strong {
  display: block;
  color: #15314a;
}

.rank-copy span {
  color: #73859a;
  font-size: 13px;
}

.rank-bar {
  height: 10px;
  border-radius: 999px;
  background: #edf2f7;
  overflow: hidden;
}

.rank-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #7ab0f4 0%, #3b82f6 100%);
}

.feedback.error,
.empty {
  padding: 18px;
  border-radius: 18px;
  background: #fff8f8;
  color: #b42318;
}

.empty {
  background: #f8fbff;
  color: #6f8297;
}

@media (max-width: 960px) {
  .metrics {
    grid-template-columns: 1fr;
  }

  .rank-item {
    grid-template-columns: 38px 1fr;
  }

  .rank-bar {
    grid-column: 1 / -1;
  }
}
</style>
