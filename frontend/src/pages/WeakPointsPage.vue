<template>
  <div class="page-shell">
    <div class="card weak-page">
      <header class="weak-header">
        <div>
          <h2>我的薄弱点</h2>
          <p>这里显示系统累计判定为未掌握的知识节点。</p>
        </div>
        <router-link to="/">返回聊天</router-link>
      </header>

      <div v-if="!weakPoints.length && !errorMessage" class="empty">暂无未掌握节点。</div>
      <p v-if="errorMessage" class="empty error">{{ errorMessage }}</p>

      <article v-for="item in weakPoints" :key="item.id" class="weak-item">
        <div>
          <strong>{{ item.node_name }}</strong>
          <p>最近一次出现：{{ item.last_seen_at }}</p>
        </div>
        <button @click="markMastered(item.id)">已掌握</button>
      </article>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { listWeakPointsApi, markMasteredApi } from "../api/weakPoints";

const router = useRouter();
const weakPoints = ref([]);
const errorMessage = ref("");

onMounted(async () => {
  await loadWeakPoints();
});

async function loadWeakPoints() {
  try {
    const { data } = await listWeakPointsApi();
    weakPoints.value = data;
  } catch (error) {
    handleApiError(error, "加载薄弱点失败。");
  }
}

async function markMastered(nodeId) {
  try {
    await markMasteredApi(nodeId);
    weakPoints.value = weakPoints.value.filter((item) => item.id !== nodeId);
  } catch (error) {
    handleApiError(error, "更新薄弱点失败。");
  }
}

function handleApiError(error, fallbackMessage) {
  const status = error?.response?.status;
  if (status === 401 || status === 403) {
    localStorage.removeItem("access_token");
    router.push("/login");
    return;
  }
  errorMessage.value = error?.response?.data?.detail || fallbackMessage;
}
</script>

<style scoped>
.weak-page {
  padding: 24px;
}

.weak-header,
.weak-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.weak-item {
  padding: 14px 0;
  border-top: 1px solid #e5edf4;
}

.empty {
  padding: 24px 0;
  color: #64748b;
}

.error {
  color: #b91c1c;
}
</style>
