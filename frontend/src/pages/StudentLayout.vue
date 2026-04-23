<template>
  <div class="console-shell student-shell" :class="{ fullscreen: hideSidebar, collapsed: collapseSidebar }">
    <aside v-if="!hideSidebar" class="console-sidebar student-sidebar">
      <div class="sidebar-top">
        <div class="console-brand">
          <p class="brand-eyebrow">Student Workspace</p>
          <h1>学习空间</h1>
          <p>作业、薄弱点与 AI 助教</p>
        </div>

        <nav class="console-nav student-nav">
          <router-link to="/" active-class="" exact-active-class="router-link-active">
            <span class="nav-icon">台</span>
            <span class="nav-copy">
              <strong>学习工作台</strong>
              <small>今日进度</small>
            </span>
          </router-link>
          <router-link to="/assignments">
            <span class="nav-icon">作</span>
            <span class="nav-copy">
              <strong>我的作业</strong>
              <small>提交与结果</small>
            </span>
          </router-link>
          <router-link to="/chat">
            <span class="nav-icon">AI</span>
            <span class="nav-copy">
              <strong>AI 学习</strong>
              <small>知识问答</small>
            </span>
          </router-link>
          <router-link to="/weak-points">
            <span class="nav-icon">弱</span>
            <span class="nav-copy">
              <strong>薄弱点</strong>
              <small>针对性训练</small>
            </span>
          </router-link>
        </nav>
      </div>

      <div class="sidebar-bottom">
        <button class="logout-btn" type="button" @click="logout">退出登录</button>
      </div>
    </aside>

    <main class="console-main">
      <div v-if="!hideSidebar" class="console-topbar">
        <div class="topbar-spacer" />
        <div class="topbar-user">
          <span class="bell-dot">•</span>
          <span class="user-avatar student-avatar">学</span>
          <span class="user-name">学生</span>
        </div>
      </div>

      <div class="console-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();
const hideSidebar = computed(() => Boolean(route.meta.hideStudentSidebar));
const collapseSidebar = computed(() => Boolean(route.meta.collapseStudentSidebar));

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
}

.console-shell.fullscreen {
  grid-template-columns: 1fr;
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
  padding: 14px;
  border-radius: 18px;
  color: #31445f;
  text-decoration: none;
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
  font-weight: 500;
  font-size: 16px;
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

.student-avatar {
  background: #eef4ff;
  color: #476fcb;
}

.console-content {
  min-width: 0;
  padding: 18px 28px 28px;
}

.console-shell.collapsed {
  grid-template-columns: 82px minmax(0, 1fr);
}

.console-shell.collapsed .console-sidebar {
  padding-left: 12px;
  padding-right: 12px;
}

.console-shell.collapsed .console-brand h1,
.console-shell.collapsed .console-brand p:last-child,
.console-shell.collapsed .brand-eyebrow,
.console-shell.collapsed .nav-copy,
.console-shell.collapsed .logout-btn {
  display: none;
}

.console-shell.collapsed .console-nav a {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.console-shell.collapsed .console-sidebar:hover {
  width: 262px;
  z-index: 20;
  box-shadow: var(--app-shadow-strong);
}

.console-shell.collapsed .console-sidebar:hover .console-brand h1,
.console-shell.collapsed .console-sidebar:hover .console-brand p:last-child,
.console-shell.collapsed .console-sidebar:hover .brand-eyebrow,
.console-shell.collapsed .console-sidebar:hover .nav-copy,
.console-shell.collapsed .console-sidebar:hover .logout-btn {
  display: initial;
}

.console-shell.collapsed .console-sidebar:hover .nav-copy {
  display: grid;
}

.console-shell.collapsed .console-sidebar:hover .console-nav a {
  justify-content: flex-start;
  padding-left: 14px;
  padding-right: 14px;
}

@media (max-width: 980px) {
  .console-shell,
  .console-shell.collapsed {
    grid-template-columns: 1fr;
  }

  .console-sidebar {
    position: static;
    height: auto;
  }

  .console-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .console-topbar,
  .console-content {
    padding-left: 18px;
    padding-right: 18px;
  }
}

@media (max-width: 640px) {
  .console-nav {
    grid-template-columns: 1fr;
  }
}
</style>
