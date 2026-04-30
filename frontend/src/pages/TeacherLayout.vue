<template>
  <div class="console-shell teacher-shell" :class="{ collapsed: collapseSidebar, 'auto-collapsed': autoCollapseSidebar }">
    <aside class="console-sidebar">
      <div class="sidebar-top">
        <div class="console-brand">
          <h1>教师工作台</h1>
        </div>

        <nav class="console-nav">
          <router-link to="/teacher/dashboard">
            <span class="nav-icon">数</span>
            <span class="nav-copy"><strong>数据看板</strong></span>
          </router-link>
          <router-link to="/teacher/graph">
            <span class="nav-icon">图</span>
            <span class="nav-copy"><strong>知识图谱</strong></span>
          </router-link>
          <router-link to="/teacher/students">
            <span class="nav-icon">学</span>
            <span class="nav-copy"><strong>学生薄弱点</strong></span>
          </router-link>
          <router-link to="/teacher/assignments">
            <span class="nav-icon">作</span>
            <span class="nav-copy"><strong>作业管理</strong></span>
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
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();
const viewportWidth = ref(typeof window === "undefined" ? 1440 : window.innerWidth);
const autoCollapseSidebar = computed(() => viewportWidth.value <= 1120);
const collapseSidebar = computed(() => Boolean(route.meta.collapseTeacherSidebar || autoCollapseSidebar.value));

function syncViewportWidth() {
  viewportWidth.value = window.innerWidth;
}

onMounted(() => {
  window.addEventListener("resize", syncViewportWidth, { passive: true });
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", syncViewportWidth);
});

function logout() {
  authStore.logout();
  router.push("/login");
}
</script>

<style scoped>
.console-shell {
  --sidebar-width: 210px;
  --sidebar-collapsed-width: 54px;
  --sidebar-current-width: var(--sidebar-width);
  display: grid;
  grid-template-columns: var(--sidebar-current-width) minmax(0, 1fr);
  min-height: 100vh;
  background: var(--app-bg);
  transition: grid-template-columns 0.28s ease;
}

.console-shell.collapsed {
  --sidebar-current-width: var(--sidebar-collapsed-width);
}

.console-sidebar {
  position: sticky;
  top: 0;
  width: var(--sidebar-current-width);
  min-width: var(--sidebar-current-width);
  max-width: var(--sidebar-current-width);
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 18px 14px 16px;
  background: var(--app-sidebar);
  border-right: 1px solid var(--app-line);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03), 0 0 1px rgba(0, 0, 0, 0.02);
  backdrop-filter: blur(16px);
  overflow: hidden;
  transition:
    width 0.28s ease,
    padding 0.28s ease,
    box-shadow 0.28s ease,
    background-color 0.28s ease;
}

.sidebar-top {
  display: grid;
  gap: 22px;
  min-height: 0;
}

.console-brand {
  padding: 8px 4px;
}

.console-brand h1 {
  margin: 0 0 10px;
  color: var(--app-text);
  font-size: 20px;
  font-weight: 500;
}

.console-brand h1,
.nav-copy,
.logout-btn {
  overflow: hidden;
  white-space: nowrap;
  transition:
    opacity 0.18s ease,
    transform 0.24s ease,
    max-width 0.24s ease,
    margin 0.24s ease,
    padding 0.24s ease;
}

.console-nav {
  display: grid;
  gap: 8px;
}

.console-nav a {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 14px;
  text-decoration: none;
  color: #31445f;
}

.console-nav a:hover {
  background: #ffffff;
}

.console-nav a.router-link-active {
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(47, 103, 246, 0.16);
  color: #1f4fd0;
}

.nav-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid var(--app-line);
  color: #4a658a;
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 8px 20px rgba(20, 34, 53, 0.05);
}

.console-nav a.router-link-active .nav-icon {
  background: #2f67f6;
  border-color: #2f67f6;
  color: #ffffff;
}

.nav-copy strong {
  font-size: 14px;
  font-weight: 500;
}

.logout-btn {
  width: 100%;
  min-height: 38px;
  border: 1px solid var(--app-line);
  border-radius: 14px;
  background: #ffffff;
  color: #31445f;
  cursor: pointer;
}

.console-main {
  min-width: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  background: var(--app-bg);
}

.console-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px 0;
}

.topbar-user {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
  color: #405571;
  font-size: 13px;
}

.bell-dot {
  color: #8193a8;
  font-size: 16px;
}

.user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 34px;
  width: 34px;
  border-radius: 50%;
  background: #ffffff;
  color: #66788b;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
}

.console-content {
  min-width: 0;
  padding: 0 24px 24px;
  font-size: var(--compact-body);
  background: var(--app-bg);
}

.console-shell.collapsed .console-sidebar {
  padding-left: 8px;
  padding-right: 8px;
  flex: 0 0 var(--sidebar-current-width);
}

.console-shell.collapsed .console-brand h1,
.console-shell.collapsed .nav-copy,
.console-shell.collapsed .logout-btn {
  display: none;
  opacity: 0;
  max-width: 0;
  margin: 0;
  padding-left: 0;
  padding-right: 0;
  transform: translateX(-8px);
  pointer-events: none;
}

.console-shell.collapsed .console-nav a {
  justify-content: center;
  gap: 0;
  padding-left: 0;
  padding-right: 0;
}

.console-shell.collapsed .console-nav a.router-link-active {
  background: transparent;
  box-shadow: none;
  position: relative;
}

.console-shell.collapsed .console-nav a.router-link-active .nav-icon {
  position: relative;
  z-index: 1;
  box-shadow: none;
}

.console-shell.collapsed:not(.auto-collapsed) .console-sidebar:hover {
  width: 210px;
  min-width: 210px;
  max-width: 210px;
  z-index: 20;
  box-shadow: var(--app-shadow-strong);
}

.console-shell.collapsed:not(.auto-collapsed) .console-sidebar:hover .console-brand h1,
.console-shell.collapsed:not(.auto-collapsed) .console-sidebar:hover .nav-copy,
.console-shell.collapsed:not(.auto-collapsed) .console-sidebar:hover .logout-btn {
  display: block;
  opacity: 1;
  max-width: 180px;
  transform: translateX(0);
  pointer-events: auto;
}

.console-shell.collapsed:not(.auto-collapsed) .console-sidebar:hover .console-nav a {
  justify-content: flex-start;
  padding-left: 14px;
  padding-right: 14px;
}

.console-shell.collapsed:not(.auto-collapsed) .console-sidebar:hover .console-nav a.router-link-active {
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(47, 103, 246, 0.16);
}

@media (max-width: 980px) {
  .console-shell {
    --sidebar-width: 176px;
    --sidebar-collapsed-width: 54px;
  }

  .console-sidebar {
    padding-top: 18px;
    padding-bottom: 18px;
  }

  .console-content,
  .console-topbar {
    padding-left: 18px;
    padding-right: 18px;
  }
}

@media (max-width: 640px) {
  .console-shell {
    --sidebar-width: 157px;
    --sidebar-collapsed-width: 54px;
  }

  .console-topbar {
    padding-top: 14px;
  }
}
</style>
