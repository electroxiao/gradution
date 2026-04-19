<template>
  <div class="student-shell" :class="{ fullscreen: hideSidebar, collapsed: collapseSidebar }">
    <aside v-if="!hideSidebar" class="student-sidebar">
      <div class="student-brand">
        <p class="eyebrow">Student Workspace</p>
        <h1>学习空间</h1>
        <span>作业、图谱与 AI 助教</span>
      </div>

      <nav class="student-nav">
        <router-link to="/" active-class="" exact-active-class="router-link-active"><span class="nav-icon">台</span><span class="nav-text">学习工作台</span></router-link>
        <router-link to="/assignments"><span class="nav-icon">作</span><span class="nav-text">作业</span></router-link>
        <router-link to="/chat"><span class="nav-icon">AI</span><span class="nav-text">AI 学习</span></router-link>
        <router-link to="/weak-points"><span class="nav-icon">弱</span><span class="nav-text">薄弱点</span></router-link>
      </nav>

      <button class="logout-btn" type="button" @click="logout">退出登录</button>
    </aside>

    <main class="student-main">
      <router-view />
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
.student-shell {
  display: grid;
  grid-template-columns: 244px minmax(0, 1fr);
  min-height: 100vh;
  background: #f5f7fa;
}

.student-shell.collapsed {
  display: block;
  padding-left: 64px;
}

.student-shell.fullscreen {
  grid-template-columns: minmax(0, 1fr);
}

.student-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 26px;
  padding: 24px 16px;
  border-right: 1px solid #dfe7ef;
  background: #edf4fb;
  transition: width 0.18s ease, padding 0.18s ease;
  z-index: 10;
}

.student-shell.collapsed .student-sidebar {
  position: fixed;
  left: 0;
  top: 0;
  width: 64px;
  height: 100vh;
  padding: 18px 10px;
  overflow: hidden;
}

.student-shell.collapsed .student-sidebar:hover {
  left: 0;
  width: 244px;
  padding: 24px 16px;
  box-shadow: 14px 0 30px rgba(15, 23, 42, 0.12);
}

.student-shell.collapsed .student-brand h1,
.student-shell.collapsed .student-brand span,
.student-shell.collapsed .eyebrow,
.student-shell.collapsed .nav-text,
.student-shell.collapsed .logout-btn {
  width: 0;
  opacity: 0;
  pointer-events: none;
  white-space: nowrap;
}

.student-shell.collapsed .student-sidebar:hover .student-brand h1,
.student-shell.collapsed .student-sidebar:hover .student-brand span,
.student-shell.collapsed .student-sidebar:hover .eyebrow,
.student-shell.collapsed .student-sidebar:hover .nav-text,
.student-shell.collapsed .student-sidebar:hover .logout-btn {
  width: auto;
  opacity: 1;
  pointer-events: auto;
}

.student-brand h1 {
  margin: 8px 0 6px;
  color: #10283d;
  font-size: 28px;
}

.student-brand span,
.eyebrow {
  color: #68809a;
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.student-nav {
  display: grid;
  gap: 8px;
  align-content: start;
}

.student-nav a,
.student-nav button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #234462;
  font: inherit;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
}

.student-shell.collapsed .student-nav a {
  justify-content: center;
  padding: 12px 0;
  gap: 0;
}

.student-shell.collapsed .student-sidebar:hover .student-nav a {
  justify-content: flex-start;
  padding: 12px 14px;
  gap: 10px;
}

.nav-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  min-width: 26px;
  height: 26px;
  border-radius: 8px;
  background: #fff;
  color: #234462;
  font-size: 12px;
  font-weight: 800;
}

.nav-text,
.student-brand h1,
.student-brand span,
.eyebrow,
.logout-btn {
  transition: opacity 0.12s ease;
}

.student-nav a.router-link-active,
.student-nav button.active {
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.logout-btn {
  margin-top: auto;
  min-height: 40px;
  border: none;
  border-radius: 8px;
  background: #10283d;
  color: #fff;
  cursor: pointer;
}

.student-main {
  min-width: 0;
}

@media (max-width: 900px) {
  .student-shell {
    grid-template-columns: 1fr;
  }

  .student-shell.collapsed {
    display: grid;
    grid-template-columns: 1fr;
    padding-left: 0;
  }

  .student-sidebar {
    position: static;
    width: auto;
    height: auto;
    padding: 14px;
    gap: 14px;
  }

  .student-shell.collapsed .student-sidebar,
  .student-shell.collapsed .student-sidebar:hover {
    position: static;
    width: auto;
    padding: 14px;
    box-shadow: none;
  }

  .student-brand {
    display: none;
  }

  .student-shell.collapsed .nav-text,
  .student-shell.collapsed .logout-btn {
    opacity: 1;
    pointer-events: auto;
  }

  .student-nav {
    display: flex;
    gap: 8px;
    overflow-x: auto;
  }

  .student-nav a,
  .student-nav button {
    white-space: nowrap;
    flex: 0 0 auto;
  }

  .logout-btn {
    margin-top: 0;
  }

}
</style>
