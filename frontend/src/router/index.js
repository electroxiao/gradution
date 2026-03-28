import { createRouter, createWebHistory } from "vue-router";

import { meApi } from "../api/auth";
const ChatPage = () => import("../pages/ChatPage.vue");
const LoginPage = () => import("../pages/LoginPage.vue");
const TeacherDashboardPage = () => import("../pages/TeacherDashboardPage.vue");
const TeacherGraphPage = () => import("../pages/TeacherGraphPage.vue");
const TeacherStudentsPage = () => import("../pages/TeacherStudentsPage.vue");
const WeakPointsPage = () => import("../pages/WeakPointsPage.vue");
const TeacherLayout = () => import("../pages/TeacherLayout.vue");

function resolveHomePath() {
  return localStorage.getItem("user_role") === "teacher" ? "/teacher/dashboard" : "/";
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginPage, meta: { public: true } },
    { path: "/", component: ChatPage, meta: { roles: ["student"] } },
    { path: "/weak-points", component: WeakPointsPage, meta: { roles: ["student"] } },
    {
      path: "/teacher",
      component: TeacherLayout,
      meta: { roles: ["teacher"] },
      children: [
        { path: "", redirect: "/teacher/dashboard" },
        { path: "dashboard", component: TeacherDashboardPage, meta: { roles: ["teacher"] } },
        { path: "graph", component: TeacherGraphPage, meta: { roles: ["teacher"] } },
        { path: "students", component: TeacherStudentsPage, meta: { roles: ["teacher"] } },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const token = localStorage.getItem("access_token");
  let role = localStorage.getItem("user_role");

  if (!to.meta.public && !token) {
    return "/login";
  }

  if (token && !role) {
    return meApi()
      .then(({ data }) => {
        const resolvedRole = data?.role || "student";
        localStorage.setItem("user_role", resolvedRole);
        if (to.path === "/login") {
          return resolvedRole === "teacher" ? "/teacher/dashboard" : "/";
        }
        if (to.meta.roles?.length && !to.meta.roles.includes(resolvedRole)) {
          return resolvedRole === "teacher" ? "/teacher/dashboard" : "/";
        }
        return true;
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user_role");
        return "/login";
      });
  }

  if (to.path === "/login" && token) {
    return resolveHomePath();
  }

  const allowedRoles = to.meta.roles;
  if (allowedRoles?.length && role && !allowedRoles.includes(role)) {
    return resolveHomePath();
  }

  return true;
});

export default router;
