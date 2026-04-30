<template>
  <div
    class="console-shell student-shell"
    :class="{
      fullscreen: hideSidebar,
      collapsed: collapseSidebar,
      'chat-layout': isChatRoute,
      'assignment-lab-layout': isAssignmentDetailRoute,
      'auto-collapsed': autoCollapseSidebar,
    }"
  >
    <aside v-if="!hideSidebar" class="console-sidebar student-sidebar">
      <div class="sidebar-top">
        <div class="console-brand">
          <h1>学习空间</h1>
        </div>

        <nav class="console-nav student-nav">
          <router-link to="/" active-class="" exact-active-class="router-link-active">
            <span class="nav-icon">台</span>
            <span class="nav-copy"><strong>学习工作台</strong></span>
          </router-link>
          <router-link to="/assignments">
            <span class="nav-icon">作</span>
            <span class="nav-copy"><strong>我的作业</strong></span>
          </router-link>
          <router-link to="/chat">
            <span class="nav-icon">AI</span>
            <span class="nav-copy"><strong>AI 学习</strong></span>
          </router-link>
          <router-link to="/weak-points">
            <span class="nav-icon">弱</span>
            <span class="nav-copy"><strong>薄弱点</strong></span>
          </router-link>
        </nav>
      </div>

      <div class="sidebar-bottom">
        <button class="logout-btn" type="button" @click="logout">退出登录</button>
      </div>
    </aside>

    <main class="console-main">
      <div v-if="!hideSidebar && !isChatRoute" class="console-topbar">
        <div class="topbar-spacer" />
        <div class="topbar-user">
          <span class="bell-dot">•</span>
          <span class="user-avatar student-avatar">学</span>
          <span class="user-name">学生</span>
        </div>
      </div>

      <div class="console-content" :class="{ 'chat-content': isChatRoute, 'assignment-lab-content': isAssignmentDetailRoute }">
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
const hideSidebar = computed(() => Boolean(route.meta.hideStudentSidebar));
const isChatRoute = computed(() => route.path === "/chat");
const isAssignmentDetailRoute = computed(() => /^\/assignments\/[^/]+$/.test(route.path));
const autoCollapseSidebar = computed(() => viewportWidth.value <= 1120);
const collapseSidebar = computed(
  () => !hideSidebar.value && Boolean(route.meta.collapseStudentSidebar || isChatRoute.value || autoCollapseSidebar.value),
);

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

.console-shell.fullscreen {
  grid-template-columns: 1fr;
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
  color: #31445f;
  text-decoration: none;
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
  font-weight: 500;
  font-size: 14px;
}

.nav-copy small {
  color: var(--app-text-soft);
  font-size: 12px;
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

.student-avatar {
  background: #ffffff;
  color: #476fcb;
}

.console-content {
  min-width: 0;
  padding: 14px 24px 24px;
  font-size: var(--compact-body);
  background: var(--app-bg);
}

.console-content.chat-content {
  padding: 0;
  height: 100vh;
  overflow: hidden;
  font-size: initial;
}

.console-shell.assignment-lab-layout {
  height: 100vh;
  overflow: hidden;
}

.console-shell.assignment-lab-layout .console-main {
  height: 100vh;
  overflow: hidden;
}

.console-shell.assignment-lab-layout .console-topbar {
  display: none;
}

.console-content.assignment-lab-content {
  height: 100vh;
  padding: 0;
  overflow: hidden;
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

.console-shell.collapsed:not(.chat-layout):not(.auto-collapsed) .console-sidebar:hover {
  width: 210px;
  min-width: 210px;
  max-width: 210px;
  z-index: 20;
  box-shadow: var(--app-shadow-strong);
}

.console-shell.collapsed:not(.chat-layout):not(.auto-collapsed) .console-sidebar:hover .console-brand h1,
.console-shell.collapsed:not(.chat-layout):not(.auto-collapsed) .console-sidebar:hover .nav-copy,
.console-shell.collapsed:not(.chat-layout):not(.auto-collapsed) .console-sidebar:hover .logout-btn {
  display: block;
  opacity: 1;
  max-width: 180px;
  transform: translateX(0);
  pointer-events: auto;
}

.console-shell.collapsed:not(.chat-layout):not(.auto-collapsed) .console-sidebar:hover .console-nav a {
  justify-content: flex-start;
  padding-left: 14px;
  padding-right: 14px;
}

.console-shell.collapsed:not(.chat-layout):not(.auto-collapsed) .console-sidebar:hover .console-nav a.router-link-active {
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

  .console-topbar,
  .console-content {
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
    padding: 14px 14px 0;
  }

  .console-content {
    padding: 14px 14px 20px;
  }
}
</style>
