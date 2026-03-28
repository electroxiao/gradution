<template>
  <div class="page-shell auth-page">
    <div class="card auth-card">
      <h1>Java 智能编程导师</h1>
      <p>学生登录后进入辅导端，教师使用预置账号登录后进入教师工作台。</p>
      <form @submit.prevent="submit">
        <input v-model="username" placeholder="用户名" />
        <input v-model="password" type="password" placeholder="密码" />
        <button type="submit" :disabled="loading">
          {{ loading ? "提交中..." : (isRegister ? "注册" : "登录") }}
        </button>
      </form>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      <button class="text-btn" @click="isRegister = !isRegister">
        {{ isRegister ? "已有账号，去登录" : "没有账号，去注册" }}
      </button>
    </div>
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
  display: grid;
  place-items: center;
}

.auth-card {
  width: min(420px, 100%);
  padding: 32px;
}

.error {
  margin-top: 12px;
  color: #b91c1c;
}

form {
  display: grid;
  gap: 12px;
}

input,
button {
  padding: 12px 14px;
  border-radius: 10px;
}

.text-btn {
  margin-top: 12px;
  border: none;
  background: transparent;
}
</style>
