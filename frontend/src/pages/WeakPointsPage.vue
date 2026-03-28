<template>
  <div class="weak-page">
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Learning Focus</p>
        <h1>我的薄弱点</h1>
        <p class="hero-text">系统会根据已选路径收敛出最值得优先补齐的 1 到 2 个核心节点，帮助你把复习重点压缩到真正关键的地方。</p>
      </div>
      <router-link class="back-link" to="/">返回聊天</router-link>
    </header>

    <section class="summary-strip">
      <article class="summary-card">
        <span class="summary-label">当前待掌握</span>
        <strong>{{ weakPoints.length }}</strong>
      </article>
      <article class="summary-card muted">
        <span class="summary-label">推荐方式</span>
        <strong>先补底层概念，再回到题目</strong>
      </article>
    </section>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section v-if="weakPoints.length" class="weak-grid">
      <article v-for="item in weakPoints" :key="item.id" class="weak-card">
        <div class="weak-card-top">
          <span class="weak-badge">核心薄弱点</span>
          <span class="weak-time">最近出现 {{ formatDate(item.last_seen_at) }}</span>
        </div>
        <h2>{{ item.node_name }}</h2>
        <p class="weak-caption">建议优先围绕这个知识点复盘概念定义、典型错误和与题目的关系。</p>
        <div class="weak-card-bottom">
          <span class="weak-first-seen">首次记录 {{ formatDate(item.first_seen_at) }}</span>
          <button @click="markMastered(item.id)">已掌握</button>
        </div>
      </article>
    </section>

    <section v-else-if="!errorMessage" class="empty-state">
      <div class="empty-orbit" />
      <h2>当前没有待补齐的薄弱点</h2>
      <p>继续提问时，系统会在选出解释路径后，自动记录少量最关键的知识节点。</p>
      <router-link class="empty-link" to="/">去聊天页继续提问</router-link>
    </section>
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

function formatDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  });
}

function handleApiError(error, fallbackMessage) {
  const status = error?.response?.status;
  if (status === 401 || status === 403) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_role");
    router.push("/login");
    return;
  }
  errorMessage.value = error?.response?.data?.detail || fallbackMessage;
}
</script>

<style scoped>
.weak-page {
  min-height: 100vh;
  padding: 36px 40px 48px;
  background:
    radial-gradient(circle at top left, rgba(220, 237, 255, 0.9) 0%, rgba(255, 255, 255, 0) 24%),
    linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.eyebrow {
  margin: 0 0 10px;
  color: #4f86c6;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.05;
  color: #10283d;
}

.hero-text {
  max-width: 700px;
  margin: 14px 0 0;
  color: #5f7287;
  line-height: 1.75;
}

.back-link,
.empty-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 11px 16px;
  border: 1px solid #dbe6f1;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #274863;
  text-decoration: none;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.summary-strip {
  display: grid;
  grid-template-columns: minmax(180px, 240px) minmax(260px, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.summary-card {
  padding: 18px 20px;
  border: 1px solid #e4edf6;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
}

.summary-card strong {
  display: block;
  margin-top: 8px;
  color: #12324a;
  font-size: 28px;
  font-weight: 700;
}

.summary-card.muted strong {
  font-size: 18px;
  line-height: 1.5;
}

.summary-label {
  color: #718399;
  font-size: 13px;
}

.feedback {
  margin: 0 0 20px;
  padding: 14px 16px;
  border-radius: 16px;
}

.feedback.error {
  background: #fff4f4;
  color: #b42318;
}

.weak-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
}

.weak-card {
  padding: 22px;
  border: 1px solid #e3ebf3;
  border-radius: 26px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, #f9fbfd 100%);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
}

.weak-card-top,
.weak-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.weak-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #edf5ff;
  color: #34699a;
  font-size: 12px;
  font-weight: 600;
}

.weak-time,
.weak-first-seen {
  color: #8394a7;
  font-size: 12px;
}

.weak-card h2 {
  margin: 18px 0 10px;
  color: #10283d;
  font-size: 24px;
}

.weak-caption {
  margin: 0 0 24px;
  color: #5f7287;
  line-height: 1.7;
}

.weak-card button {
  border: none;
  border-radius: 999px;
  padding: 10px 14px;
  background: #10283d;
  color: #ffffff;
  cursor: pointer;
}

.empty-state {
  position: relative;
  overflow: hidden;
  padding: 64px 24px;
  border: 1px solid #e7eef6;
  border-radius: 28px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  text-align: center;
}

.empty-orbit {
  position: absolute;
  top: -42px;
  left: 50%;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(181, 214, 255, 0.35) 0%, rgba(181, 214, 255, 0) 70%);
  transform: translateX(-50%);
}

.empty-state h2 {
  position: relative;
  margin: 0 0 12px;
  color: #10283d;
}

.empty-state p {
  position: relative;
  max-width: 560px;
  margin: 0 auto 22px;
  color: #64748b;
  line-height: 1.7;
}

@media (max-width: 860px) {
  .weak-page {
    padding: 24px 18px 36px;
  }

  .hero {
    flex-direction: column;
  }

  .summary-strip {
    grid-template-columns: 1fr;
  }

  .weak-card-top,
  .weak-card-bottom {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
