<template>
  <section v-if="!isInitialLoading" class="app-page dashboard-page content-ready">
    <PageHeader title="数据看板" title-tag="h2">
      <template #actions>
        <button class="app-button-ghost" @click="loadDashboard">刷新数据</button>
      </template>
    </PageHeader>

    <div v-if="errorMessage" class="app-feedback error">{{ errorMessage }}</div>

    <section v-if="!isInitialLoading && dashboard" class="metrics-grid">
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

    <section class="rank-panels">
      <div class="rank-panel">
        <div class="panel-head">
          <div>
            <h3>薄弱点热点排行</h3>
          </div>
        </div>

        <div v-if="!isInitialLoading && dashboard?.top_nodes?.length" class="rank-list">
          <article v-for="(item, index) in dashboard.top_nodes" :key="item.id" class="rank-item">
            <div class="rank-index">{{ index + 1 }}</div>
            <div class="rank-copy">
              <strong>{{ item.node_name }}</strong>
              <span>被标记 {{ item.mark_count }} 次</span>
            </div>
            <div class="rank-bar">
              <div class="rank-fill weak-fill" :style="{ width: `${weakBarWidth(item.mark_count)}%` }" />
            </div>
          </article>
        </div>
        <div v-else-if="hasLoaded" class="empty-panel">暂无可展示的薄弱点统计。</div>
      </div>

      <div class="rank-panel">
        <div class="panel-head">
          <div>
            <h3>班级咨询热点排行</h3>
          </div>
        </div>

        <div v-if="!isInitialLoading && consultationHotspots.length" class="rank-list">
          <article
            v-for="(item, index) in consultationHotspots"
            :key="item.knowledge_node_id"
            class="rank-item"
          >
            <div class="rank-index consultation-index">{{ index + 1 }}</div>
            <div class="rank-copy">
              <strong>{{ item.node_name }}</strong>
              <span>{{ item.student_count }} 人 · {{ item.mention_count }} 次咨询</span>
            </div>
            <div class="rank-bar">
              <div
                class="rank-fill consultation-fill"
                :style="{ width: `${consultationBarWidth(item.mention_count)}%` }"
              />
            </div>
          </article>
        </div>
        <div v-else-if="hasLoaded" class="empty-panel">暂无学生咨询热点数据。</div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { getTeacherDashboardApi, listTeacherConsultationHotspotsApi } from "../api/teacher";
import PageHeader from "../components/PageHeader.vue";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const dashboard = ref(null);
const consultationHotspots = ref([]);
const errorMessage = ref("");
const hasLoaded = ref(false);
const isInitialLoading = ref(true);

onMounted(async () => {
  await loadDashboard();
});

async function loadDashboard() {
  if (!hasLoaded.value) isInitialLoading.value = true;
  try {
    const [dashboardResponse, hotspotsResponse] = await Promise.all([
      getTeacherDashboardApi(),
      listTeacherConsultationHotspotsApi({ limit: 8 }),
    ]);
    dashboard.value = dashboardResponse.data;
    consultationHotspots.value = hotspotsResponse.data || [];
  } catch (error) {
    handleApiError(error, "加载数据看板失败。");
  } finally {
    hasLoaded.value = true;
    isInitialLoading.value = false;
  }
}

function weakBarWidth(markCount) {
  if (!dashboard.value?.top_nodes?.length) return 0;
  const max = Math.max(...dashboard.value.top_nodes.map((item) => item.mark_count || 0), 1);
  return Math.max(18, (markCount / max) * 100);
}

function consultationBarWidth(mentionCount) {
  if (!consultationHotspots.value.length) return 0;
  const max = Math.max(...consultationHotspots.value.map((item) => item.mention_count || 0), 1);
  return Math.max(18, (mentionCount / max) * 100);
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
  gap: 14px;
  font-size: var(--compact-body);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.rank-panels {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  align-items: start;
}

.metric-card,
.rank-panel,
.empty-panel {
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.metric-card {
  padding: 14px 16px;
}

.metric-card span {
  color: var(--app-text-muted);
}

.metric-card strong {
  display: block;
  margin-top: 7px;
  color: var(--app-text);
  font-size: var(--compact-stat);
  font-weight: 400;
}

.rank-panel {
  padding: 16px;
  display: grid;
  gap: 12px;
}

.panel-head h3 {
  margin: 0;
  color: var(--app-text);
  font-size: var(--compact-section-title);
  font-weight: 500;
}

.rank-list {
  display: grid;
  gap: 10px;
}

.rank-item {
  display: grid;
  grid-template-columns: 34px minmax(0, 240px) minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.rank-index {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: var(--app-primary-soft);
  color: #4368af;
  font-size: 13px;
  font-weight: 500;
}

.consultation-index {
  background: #e9f8ef;
  color: #267344;
}

.rank-copy strong {
  display: block;
  color: var(--app-text);
  font-weight: 400;
}

.rank-copy span {
  color: var(--app-text-muted);
  font-size: 13px;
}

.rank-bar {
  height: 12px;
  border-radius: 999px;
  background: #edf1f6;
  overflow: hidden;
}

.rank-fill {
  height: 100%;
  border-radius: 999px;
}

.weak-fill {
  background: linear-gradient(90deg, #84aefc 0%, #2f67f6 100%);
}

.consultation-fill {
  background: linear-gradient(90deg, #74d99f 0%, #229954 100%);
}

.empty-panel {
  padding: 14px 16px;
  color: var(--app-text-muted);
}

@media (max-width: 960px) {
  .metrics-grid {
    grid-template-columns: repeat(3, minmax(150px, 1fr));
  }

  .rank-panels {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .rank-item {
    grid-template-columns: 42px 1fr;
  }

  .rank-bar {
    grid-column: 1 / -1;
  }
}
</style>
