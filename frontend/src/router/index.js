import { createRouter, createWebHistory } from "vue-router";

import { meApi } from "../api/auth";
import { clearAuthSession, getAccessToken, getUserRole, setStoredUserRole } from "../utils/authStorage";
const ChatPage = () => import("../pages/ChatPage.vue");
const LoginPage = () => import("../pages/LoginPage.vue");
const TeacherDashboardPage = () => import("../pages/TeacherDashboardPage.vue");
const TeacherGraphPage = () => import("../pages/TeacherGraphPage.vue");
const TeacherStudentsPage = () => import("../pages/TeacherStudentsPage.vue");
const TeacherAssignmentsPage = () => import("../pages/TeacherAssignmentsPage.vue");
const TeacherAssignmentEditorPage = () => import("../pages/TeacherAssignmentEditorPage.vue");
const StudentAssignmentsPage = () => import("../pages/StudentAssignmentsPage.vue");
const StudentAssignmentDetailPage = () => import("../pages/StudentAssignmentDetailPage.vue");
const WeakPointsPage = () => import("../pages/WeakPointsPage.vue");
const TeacherLayout = () => import("../pages/TeacherLayout.vue");

function resolveHomePath() {
  return getUserRole() === "teacher" ? "/teacher/dashboard" : "/";
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginPage, meta: { public: true } },
    { path: "/", component: ChatPage, meta: { roles: ["student"] } },
    { path: "/weak-points", component: WeakPointsPage, meta: { roles: ["student"] } },
    { path: "/assignments", component: StudentAssignmentsPage, meta: { roles: ["student"] } },
    { path: "/assignments/:assignmentId", component: StudentAssignmentDetailPage, meta: { roles: ["student"] } },
    {
      path: "/teacher",
      component: TeacherLayout,
      meta: { roles: ["teacher"] },
      children: [
        { path: "", redirect: "/teacher/dashboard" },
        { path: "dashboard", component: TeacherDashboardPage, meta: { roles: ["teacher"] } },
        { path: "graph", component: TeacherGraphPage, meta: { roles: ["teacher"] } },
        { path: "students", component: TeacherStudentsPage, meta: { roles: ["teacher"] } },
        { path: "assignments", component: TeacherAssignmentsPage, meta: { roles: ["teacher"] } },
        { path: "assignments/new", component: TeacherAssignmentEditorPage, meta: { roles: ["teacher"] } },
        { path: "assignments/:assignmentId", component: TeacherAssignmentEditorPage, meta: { roles: ["teacher"] } },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const token = getAccessToken();
  let role = getUserRole();

  if (!to.meta.public && !token) {
    return "/login";
  }

  if (token && !role) {
    return meApi()
      .then(({ data }) => {
        const resolvedRole = data?.role || "student";
        setStoredUserRole(resolvedRole);
        if (to.path === "/login") {
          return resolvedRole === "teacher" ? "/teacher/dashboard" : "/";
        }
        if (to.meta.roles?.length && !to.meta.roles.includes(resolvedRole)) {
          return resolvedRole === "teacher" ? "/teacher/dashboard" : "/";
        }
        return true;
      })
      .catch(() => {
        clearAuthSession();
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
