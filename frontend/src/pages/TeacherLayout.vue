<template>
  <div class="teacher-shell">
    <aside class="teacher-sidebar">
      <div class="sidebar-scroll">
        <div class="teacher-brand">
          <p class="eyebrow">Teacher Console</p>
          <h1>教师工作台</h1>
          <span>图谱管理与学情观察</span>
        </div>

        <nav class="teacher-nav">
          <router-link to="/teacher/dashboard">数据看板</router-link>
          <router-link to="/teacher/graph">知识图谱</router-link>
          <router-link to="/teacher/students">学生薄弱点</router-link>
          <router-link to="/teacher/assignments">作业管理</router-link>
        </nav>
      </div>

      <div class="sidebar-footer">
        <button class="logout-btn" @click="logout">退出登录</button>
      </div>
    </aside>

    <main class="teacher-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const router = useRouter();

function logout() {
  authStore.logout();
  router.push("/login");
}
</script>

<style scoped>
.teacher-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  height: 100vh;
  background: linear-gradient(180deg, #f7fbff 0%, #ffffff 100%);
  overflow: hidden;
}

.teacher-sidebar {
  display: flex;
  flex-direction: column;
  padding: 28px 20px;
  background: linear-gradient(180deg, #eff6ff 0%, #e6f0fb 100%);
  border-right: 1px solid #d7e5f3;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
}

.sidebar-scroll {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 28px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.sidebar-footer {
  padding-top: 18px;
}

.teacher-brand h1 {
  margin: 8px 0 6px;
  color: #0f2840;
  font-size: 27px;
  font-weight: 500;
}

.teacher-brand span,
.eyebrow {
  color: #68809a;
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.teacher-nav {
  display: grid;
  gap: 8px;
}

.teacher-nav a {
  padding: 12px 14px;
  border-radius: 16px;
  color: #234462;
  text-decoration: none;
}

.teacher-nav a.router-link-active {
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
}

.logout-btn {
  width: 100%;
  padding: 12px 14px;
  border: none;
  border-radius: 16px;
  background: #10283d;
  color: #fff;
  cursor: pointer;
}

.teacher-main {
  min-width: 0;
  padding: 28px;
  height: 100vh;
  overflow-y: auto;
}

@media (max-width: 980px) {
  .teacher-shell {
    grid-template-columns: 1fr;
    height: auto;
    overflow: visible;
  }

  .teacher-sidebar,
  .teacher-main {
    position: static;
    height: auto;
  }

  .teacher-main {
    padding: 18px;
    overflow: visible;
  }

  .teacher-sidebar {
    overflow: visible;
  }

  .sidebar-scroll {
    overflow: visible;
    padding-right: 0;
  }
}
</style>
