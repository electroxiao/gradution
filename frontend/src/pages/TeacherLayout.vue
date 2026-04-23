<template>
  <div class="console-shell teacher-shell">
    <aside class="console-sidebar">
      <div class="sidebar-top">
        <div class="console-brand">
          <p class="brand-eyebrow">Teacher Console</p>
          <h1>教师工作台</h1>
          <p>图谱管理与学情观察</p>
        </div>

        <nav class="console-nav">
          <router-link to="/teacher/dashboard">
            <span class="nav-icon">数</span>
            <span class="nav-copy">
              <strong>数据看板</strong>
              <small>班级概览</small>
            </span>
          </router-link>
          <router-link to="/teacher/graph">
            <span class="nav-icon">图</span>
            <span class="nav-copy">
              <strong>知识图谱</strong>
              <small>节点与关系</small>
            </span>
          </router-link>
          <router-link to="/teacher/students">
            <span class="nav-icon">学</span>
            <span class="nav-copy">
              <strong>学生薄弱点</strong>
              <small>个体掌握情况</small>
            </span>
          </router-link>
          <router-link to="/teacher/assignments">
            <span class="nav-icon">作</span>
            <span class="nav-copy">
              <strong>作业管理</strong>
              <small>发布与复核</small>
            </span>
          </router-link>
        </nav>
      </div>

      <div class="sidebar-bottom">
        <button class="logout-btn" @click="logout">退出登录</button>
      </div>
    </aside>

    <main class="console-main">
      <div class="console-topbar">
        <div class="topbar-spacer" />
        <div class="topbar-user">
          <span class="bell-dot">•</span>
          <span class="user-avatar">教</span>
          <span class="user-name">教师</span>
        </div>
      </div>
      <div class="console-content">
        <router-view />
      </div>
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
.console-shell {
  display: grid;
  grid-template-columns: 262px minmax(0, 1fr);
  min-height: 100vh;
  background: var(--app-bg);
}

.console-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 22px 18px 20px;
  background: rgba(251, 252, 254, 0.96);
  border-right: 1px solid var(--app-line);
  backdrop-filter: blur(16px);
}

.sidebar-top {
  display: grid;
  gap: 28px;
  min-height: 0;
}

.console-brand {
  padding: 8px 4px;
}

.brand-eyebrow {
  margin: 0;
  color: #6b7f99;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.console-brand h1 {
  margin: 14px 0 10px;
  color: var(--app-text);
  font-size: 24px;
  font-weight: 500;
}

.console-brand p:last-child {
  margin: 0;
  color: var(--app-text-muted);
  line-height: 1.7;
}

.console-nav {
  display: grid;
  gap: 8px;
}

.console-nav a {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 14px;
  border-radius: 18px;
  text-decoration: none;
  color: #31445f;
}

.console-nav a:hover {
  background: rgba(47, 103, 246, 0.05);
}

.console-nav a.router-link-active {
  background: #edf3ff;
  color: #1f4fd0;
}

.nav-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid var(--app-line);
  color: #4a658a;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 8px 20px rgba(20, 34, 53, 0.05);
}

.console-nav a.router-link-active .nav-icon {
  background: #2f67f6;
  border-color: #2f67f6;
  color: #ffffff;
}

.nav-copy {
  display: grid;
  gap: 2px;
}

.nav-copy strong {
  font-size: 16px;
  font-weight: 500;
}

.nav-copy small {
  color: var(--app-text-soft);
  font-size: 12px;
}

.logout-btn {
  width: 100%;
  min-height: 48px;
  border: 1px solid var(--app-line);
  border-radius: 16px;
  background: #ffffff;
  color: #31445f;
  cursor: pointer;
}

.console-main {
  min-width: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.console-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 28px 0;
}

.topbar-user {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
  color: #405571;
}

.bell-dot {
  color: #8193a8;
  font-size: 20px;
}

.user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #eef2f7;
  color: #66788b;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
}

.console-content {
  min-width: 0;
  padding: 18px 28px 28px;
}

@media (max-width: 980px) {
  .console-shell {
    grid-template-columns: 1fr;
  }

  .console-sidebar {
    position: static;
    height: auto;
    gap: 18px;
  }

  .console-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .console-content,
  .console-topbar {
    padding-left: 18px;
    padding-right: 18px;
  }
}

@media (max-width: 640px) {
  .console-nav {
    grid-template-columns: 1fr;
  }

  .console-topbar {
    padding-top: 14px;
  }
}
</style>
