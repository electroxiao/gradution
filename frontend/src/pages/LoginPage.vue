<template>
  <div class="page-shell auth-page">
    <section class="auth-hero">
      <div class="hero-card">
        <h1>Java 智能编程导师</h1>
        <p class="hero-copy">统一连接教师工作台、学生学习空间与知识图谱助教的课程控制台。</p>
        <div class="hero-stats">
          <article>
            <span>教学视图</span>
            <strong>教师工作台</strong>
          </article>
          <article>
            <span>学习视图</span>
            <strong>学生空间</strong>
          </article>
          <article>
            <span>辅助能力</span>
            <strong>AI 助教 + 图谱</strong>
          </article>
        </div>
      </div>

      <div class="auth-card">
        <div class="auth-head">
          <h2>{{ isRegister ? "创建账号" : "登录系统" }}</h2>
          <p>{{ isRegister ? "注册后即可进入对应身份的工作台。" : "使用你的账号进入教师或学生控制台。" }}</p>
        </div>

        <form @submit.prevent="submit">
          <label>
            用户名
            <input v-model="username" placeholder="输入用户名" />
          </label>
          <label>
            密码
            <input v-model="password" type="password" placeholder="输入密码" />
          </label>
          <button type="submit" class="submit-btn" :disabled="loading">
            {{ loading ? "提交中..." : (isRegister ? "注册并进入" : "登录进入") }}
          </button>
        </form>

        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

        <button class="text-btn" @click="isRegister = !isRegister">
          {{ isRegister ? "已有账号，去登录" : "没有账号，去注册" }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const router = useRouter();
const username = ref("");
const password = ref("");
const isRegister = ref(false);
const errorMessage = ref("");
const loading = ref(false);

async function submit() {
  errorMessage.value = "";
  loading.value = true;
  try {
    const payload = { username: username.value, password: password.value };
    if (isRegister.value) {
      await authStore.register(payload);
    } else {
      await authStore.login(payload);
    }
    router.push(authStore.role === "teacher" ? "/teacher/dashboard" : "/");
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || "登录失败，请检查输入或后端状态。";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: 32px;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at top left, rgba(47, 103, 246, 0.1), transparent 26%),
    linear-gradient(180deg, #f7f9fc 0%, #f3f6fb 100%);
}

.auth-hero {
  width: min(1180px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(360px, 420px);
  gap: 28px;
  align-items: stretch;
}

.hero-card,
.auth-card {
  border: 1px solid var(--app-line);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--app-shadow);
}

.hero-card {
  padding: 40px;
  display: grid;
  align-content: space-between;
  gap: 28px;
}

.hero-card h1,
.auth-head h2 {
  margin: 0 0 12px;
  color: var(--app-text);
  font-weight: 500;
}

.hero-card h1 {
  font-size: clamp(34px, 4vw, 54px);
  line-height: 1.04;
}

.hero-copy,
.auth-head p {
  margin: 0;
  color: var(--app-text-muted);
  line-height: 1.8;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.hero-stats article {
  padding: 18px;
  border-radius: 20px;
  background: var(--app-panel-soft);
  border: 1px solid #e4edf7;
}

.hero-stats span {
  color: var(--app-text-soft);
  font-size: 12px;
}

.hero-stats strong {
  display: block;
  margin-top: 8px;
  color: var(--app-text);
  font-size: 18px;
  font-weight: 500;
}

.auth-card {
  padding: 30px;
  display: grid;
  gap: 20px;
}

.auth-head h2 {
  font-size: 30px;
}

form {
  display: grid;
  gap: 14px;
}

label {
  display: grid;
  gap: 8px;
  color: #4f6074;
  font-size: 14px;
}

.submit-btn {
  min-height: 48px;
  border: 1px solid var(--app-primary);
  border-radius: 14px;
  background: var(--app-primary);
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 12px 26px rgba(47, 103, 246, 0.22);
}

.error {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff5f5;
  color: #b53f3f;
}

.text-btn {
  justify-self: start;
  padding: 0;
  border: none;
  background: transparent;
  color: #4368af;
  cursor: pointer;
}

@media (max-width: 980px) {
  .auth-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .auth-page {
    padding: 18px;
  }

  .hero-card,
  .auth-card {
    padding: 22px;
    border-radius: 24px;
  }

  .hero-stats {
    grid-template-columns: 1fr;
  }
}
</style>
